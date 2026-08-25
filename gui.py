import threading
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
from core.auto_convert import watch_and_auto_convert
from core.search import SEARCH_SOURCES, tim_kiem_pdf, tai_pdf
from core.ai_summary import summarize_paper
from core.master_summary import create_master_summary
from core.history_manager import load_history, clear_history

# --- Thiết lập giao diện mặc định ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class PipelineApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Cấu hình cửa sổ chính
        self.title("PDF-to-Markdown Pipeline")
        self.geometry("950x620")
        self.minsize(800, 500)

        # Trạng thái watcher (đang chạy hay không)
        self._watcher_running = False
        self._watcher_thread = None
        self._search_results = []

        # Hệ thống lưới: 1 hàng, 2 cột
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ==================== TRÁI: SIDEBAR ====================
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)
        self.sidebar_frame.grid_rowconfigure(6, weight=1)  # Đẩy nội dung lên trên

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, text="PDF2MD",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(25, 30))

        # Nút điều hướng
        nav_style = dict(anchor="w", fg_color="transparent",
                         text_color=("gray10", "#DCE4EE"),
                         hover_color=("gray70", "gray30"),
                         font=ctk.CTkFont(size=14))

        self.btn_nav_convert = ctk.CTkButton(
            self.sidebar_frame, text="🔄  Convert", **nav_style,
            command=self.show_convert_panel
        )
        self.btn_nav_convert.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        self.btn_nav_search = ctk.CTkButton(
            self.sidebar_frame, text="🔍  Search", **nav_style,
            command=self.show_search_panel
        )
        self.btn_nav_search.grid(row=2, column=0, padx=15, pady=5, sticky="ew")

        self.btn_nav_summarize = ctk.CTkButton(
            self.sidebar_frame, text="📊  Summarize", **nav_style,
            command=self.show_summarize_panel
        )
        self.btn_nav_summarize.grid(row=3, column=0, padx=15, pady=5, sticky="ew")

        self.btn_nav_settings = ctk.CTkButton(
            self.sidebar_frame, text="⚙️  Settings", **nav_style,
            command=self.show_settings_panel
        )
        self.btn_nav_settings.grid(row=4, column=0, padx=15, pady=5, sticky="ew")

        self.btn_nav_history = ctk.CTkButton(
            self.sidebar_frame, text="📜  History", **nav_style,
            command=self.show_history_panel
        )
        self.btn_nav_history.grid(row=5, column=0, padx=15, pady=5, sticky="ew")

        # Nút chuyển Dark/Light ở cuối sidebar
        self.theme_switch = ctk.CTkSwitch(
            self.sidebar_frame, text="Light Mode",
            command=self.toggle_theme,
            font=ctk.CTkFont(size=14)
        )
        self.theme_switch.grid(row=7, column=0, padx=20, pady=20, sticky="sw")

        # ==================== PHẢI: CÁC PANEL ====================
        self._build_convert_panel()
        self._build_search_panel()
        self._build_summarize_panel()
        self._build_settings_panel()
        self._build_history_panel()

        # Hiển thị panel Convert mặc định
        self.show_convert_panel()


    # ------------------------------------------------------------------ #
    #  BUILDER: PANEL CONVERT                                              #
    # ------------------------------------------------------------------ #
    def _build_convert_panel(self):
        self.panel_convert = ctk.CTkFrame(self, corner_radius=10)
        self.panel_convert.grid_rowconfigure(5, weight=1)
        self.panel_convert.grid_columnconfigure(1, weight=1)

        # Tiêu đề
        ctk.CTkLabel(
            self.panel_convert, text="Document Converter",
            font=ctk.CTkFont(size=26, weight="bold")
        ).grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 2), sticky="w")

        ctk.CTkLabel(
            self.panel_convert,
            text="Theo dõi thư mục và tự động chuyển đổi PDF sang Markdown",
            text_color="gray60", font=ctk.CTkFont(size=14)
        ).grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 15), sticky="w")

        # --- Thư mục nguồn (Input) ---
        ctk.CTkLabel(self.panel_convert, text="Thư mục nguồn:").grid(
            row=2, column=0, padx=20, pady=6, sticky="w")
        self.entry_approved = ctk.CTkEntry(
            self.panel_convert, placeholder_text="Thư mục chứa file PDF đã duyệt...")
        self.entry_approved.grid(row=2, column=1, padx=(0, 10), pady=6, sticky="ew")
        ctk.CTkButton(
            self.panel_convert, text="Chọn", width=80,
            command=lambda: self._browse_folder(self.entry_approved)
        ).grid(row=2, column=2, padx=(0, 20), pady=6)

        # --- Thư mục xuất (Output) ---
        ctk.CTkLabel(self.panel_convert, text="Thư mục xuất:").grid(
            row=3, column=0, padx=20, pady=6, sticky="w")
        self.entry_output = ctk.CTkEntry(
            self.panel_convert, placeholder_text="Thư mục lưu file .md kết quả...")
        self.entry_output.grid(row=3, column=1, padx=(0, 10), pady=6, sticky="ew")
        ctk.CTkButton(
            self.panel_convert, text="Chọn", width=80,
            command=lambda: self._browse_folder(self.entry_output)
        ).grid(row=3, column=2, padx=(0, 20), pady=6)

        # --- Nút Start / Stop ---
        btn_row = ctk.CTkFrame(self.panel_convert, fg_color="transparent")
        btn_row.grid(row=4, column=0, columnspan=3, padx=20, pady=10, sticky="ew")
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)

        self.btn_start = ctk.CTkButton(
            btn_row, text="▶  Bắt đầu theo dõi",
            fg_color="#2ecc71", hover_color="#27ae60",
            font=ctk.CTkFont(size=16, weight="bold"), height=42,
            command=self.start_watcher
        )
        self.btn_start.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        self.btn_stop = ctk.CTkButton(
            btn_row, text="⏹  Dừng",
            fg_color="#e74c3c", hover_color="#c0392b",
            font=ctk.CTkFont(size=16, weight="bold"), height=42,
            state="disabled",
            command=self.stop_watcher
        )
        self.btn_stop.grid(row=0, column=1, sticky="ew")

        # --- Live Log ---
        ctk.CTkLabel(
            self.panel_convert, text="Live Log",
            font=ctk.CTkFont(size=15, weight="bold")
        ).grid(row=5, column=0, padx=20, pady=(5, 0), sticky="w")

        self.textbox_log = ctk.CTkTextbox(self.panel_convert, state="disabled", font=ctk.CTkFont(size=14))
        self.textbox_log.grid(row=6, column=0, columnspan=3, padx=20, pady=(4, 20), sticky="nsew")
        self.panel_convert.grid_rowconfigure(6, weight=1)

    # ------------------------------------------------------------------ #
    #  BUILDER: PANEL SEARCH                                               #
    # ------------------------------------------------------------------ #
    def _build_search_panel(self):
        self.panel_search = ctk.CTkFrame(self, corner_radius=10)
        self.panel_search.grid_rowconfigure(5, weight=1)
        self.panel_search.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.panel_search, text="PDF Search & Download",
            font=ctk.CTkFont(size=26, weight="bold")
        ).grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 2), sticky="w")

        ctk.CTkLabel(
            self.panel_search, text="Tìm tài liệu từ web và các nguồn nghiên cứu mở",
            text_color="gray60", font=ctk.CTkFont(size=14)
        ).grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 15), sticky="w")

        # Từ khóa
        ctk.CTkLabel(self.panel_search, text="Từ khóa:").grid(
            row=2, column=0, padx=20, pady=6, sticky="w")
        self.entry_keyword = ctk.CTkEntry(
            self.panel_search, placeholder_text="VD: machine learning, Python tutorial...")
        self.entry_keyword.grid(row=2, column=1, padx=(0, 10), pady=6, sticky="ew")

        # Nguồn tìm kiếm
        ctk.CTkLabel(self.panel_search, text="Nguồn tìm kiếm:").grid(
            row=3, column=0, padx=20, pady=6, sticky="w")
        self.search_source_by_label = {label: key for key, label in SEARCH_SOURCES.items()}
        self.combo_search_source = ctk.CTkComboBox(
            self.panel_search, values=list(self.search_source_by_label)
        )
        self.combo_search_source.set(SEARCH_SOURCES['general'])
        self.combo_search_source.grid(row=3, column=1, columnspan=2, padx=(0, 20), pady=6, sticky="ew")

        # Loại tài liệu (chỉ ảnh hưởng đến nguồn tìm kiếm web DDGS)
        ctk.CTkLabel(self.panel_search, text="Loại web PDF:").grid(
            row=4, column=0, padx=20, pady=6, sticky="w")
        self.combo_doc_type = ctk.CTkComboBox(
            self.panel_search,
            values=["1 - Nghiên cứu (Thesis, Report)", "2 - Hướng dẫn (Manual, Guide)", "3 - Tổng quát"]
        )
        self.combo_doc_type.set("3 - Tổng quát")
        self.combo_doc_type.grid(row=4, column=1, padx=(0, 10), pady=6, sticky="ew")

        ctk.CTkButton(
            self.panel_search, text="🔍  Tìm kiếm",
            font=ctk.CTkFont(size=16, weight="bold"), height=42,
            command=self.run_search
        ).grid(row=4, column=2, padx=(0, 20), pady=6)

        # Số kết quả tìm kiếm
        ctk.CTkLabel(self.panel_search, text="Số kết quả:").grid(
            row=5, column=0, padx=20, pady=6, sticky="w")
        self.slider_result_count = ctk.CTkSlider(
            self.panel_search, from_=1, to=10, number_of_steps=9,
            command=self._update_result_count_label
        )
        self.slider_result_count.set(5)
        self.slider_result_count.grid(row=5, column=1, padx=(0, 10), pady=6, sticky="ew")
        self.lbl_result_count = ctk.CTkLabel(
            self.panel_search, text="5",
            font=ctk.CTkFont(size=14, weight="bold"), width=30
        )
        self.lbl_result_count.grid(row=5, column=2, padx=(0, 20), pady=6, sticky="w")

        # Log tìm kiếm
        self.textbox_search_log = ctk.CTkTextbox(self.panel_search, state="disabled", font=ctk.CTkFont(size=14))
        self.textbox_search_log.grid(row=6, column=0, columnspan=3, padx=20, pady=(10, 10), sticky="nsew")
        self.panel_search.grid_rowconfigure(6, weight=1)

        # Tải kết quả đã chọn
        download_frame = ctk.CTkFrame(self.panel_search, fg_color="transparent")
        download_frame.grid(row=7, column=0, columnspan=3, padx=20, pady=(0, 20), sticky="ew")
        download_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(download_frame, text="Tải kết quả số:").grid(
            row=0, column=0, padx=(0, 10), pady=4, sticky="w")
        self.entry_download_selection = ctk.CTkEntry(
            download_frame, placeholder_text="VD: 1,3,5")
        self.entry_download_selection.grid(row=0, column=1, padx=(0, 10), pady=4, sticky="ew")
        self.btn_download = ctk.CTkButton(
            download_frame, text="⬇  Tải PDF đã chọn", width=150,
            state="disabled", command=self.download_selected_results
        )
        self.btn_download.grid(row=0, column=2, pady=4)

        ctk.CTkLabel(download_frame, text="Thư mục tải về:").grid(
            row=1, column=0, padx=(0, 10), pady=4, sticky="w")
        self.entry_download_folder = ctk.CTkEntry(download_frame)
        self.entry_download_folder.insert(0, "1_TaiLieu_Tho")
        self.entry_download_folder.grid(row=1, column=1, padx=(0, 10), pady=4, sticky="ew")
        ctk.CTkButton(
            download_frame, text="Chọn", width=150,
            command=lambda: self._browse_folder(self.entry_download_folder)
        ).grid(row=1, column=2, pady=4)

    # ------------------------------------------------------------------ #
    #  BUILDER: PANEL SETTINGS                                             #
    # ------------------------------------------------------------------ #
    def _build_settings_panel(self):
        self.panel_settings = ctk.CTkFrame(self, corner_radius=10)
        self.panel_settings.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.panel_settings, text="Settings",
            font=ctk.CTkFont(size=26, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")

        # Max Workers
        ctk.CTkLabel(self.panel_settings, text="Max Workers:").grid(
            row=1, column=0, padx=20, pady=10, sticky="w")
        self.slider_workers = ctk.CTkSlider(
            self.panel_settings, from_=1, to=8, number_of_steps=7,
            command=self._update_worker_label
        )
        self.slider_workers.set(4)
        self.slider_workers.grid(row=1, column=1, padx=(0, 20), pady=10, sticky="ew")
        self.lbl_worker_val = ctk.CTkLabel(self.panel_settings, text="4")
        self.lbl_worker_val.grid(row=1, column=2, padx=(0, 20))

        # OCR Language
        ctk.CTkLabel(self.panel_settings, text="Ngôn ngữ OCR:").grid(
            row=2, column=0, padx=20, pady=10, sticky="w")
        self.combo_ocr_lang = ctk.CTkComboBox(
            self.panel_settings, values=["vie+eng", "vie", "eng"]
        )
        self.combo_ocr_lang.set("vie+eng")
        self.combo_ocr_lang.grid(row=2, column=1, padx=(0, 20), pady=10, sticky="ew")

        # Thư mục mặc định
        ctk.CTkLabel(
            self.panel_settings, text="Thư mục mặc định",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=3, column=0, columnspan=2, padx=20, pady=(20, 5), sticky="w")

        ctk.CTkLabel(self.panel_settings, text="Thư mục nguồn:").grid(
            row=4, column=0, padx=20, pady=6, sticky="w")
        self.entry_default_approved = ctk.CTkEntry(
            self.panel_settings, placeholder_text="2_Da_Duyet")
        self.entry_default_approved.grid(row=4, column=1, padx=(0, 10), pady=6, sticky="ew")
        ctk.CTkButton(
            self.panel_settings, text="Chọn", width=80,
            command=lambda: self._browse_folder(self.entry_default_approved)
        ).grid(row=4, column=2, padx=(0, 20))

        ctk.CTkLabel(self.panel_settings, text="Thư mục xuất:").grid(
            row=5, column=0, padx=20, pady=6, sticky="w")
        self.entry_default_output = ctk.CTkEntry(
            self.panel_settings, placeholder_text="3_KetQua_MD")
        self.entry_default_output.grid(row=5, column=1, padx=(0, 10), pady=6, sticky="ew")
        ctk.CTkButton(
            self.panel_settings, text="Chọn", width=80,
            command=lambda: self._browse_folder(self.entry_default_output)
        ).grid(row=5, column=2, padx=(0, 20))

        ctk.CTkButton(
            self.panel_settings, text="💾  Lưu cài đặt",
            font=ctk.CTkFont(size=16, weight="bold"), height=42,
            command=self._apply_settings
        ).grid(row=6, column=0, columnspan=3, padx=20, pady=25, sticky="ew")

    # ------------------------------------------------------------------ #
    #  BUILDER: PANEL SUMMARIZE                                            #
    # ------------------------------------------------------------------ #
    def _build_summarize_panel(self):
        self.panel_summarize = ctk.CTkFrame(self, corner_radius=10)
        self.panel_summarize.grid_columnconfigure(1, weight=1)
        self.panel_summarize.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(
            self.panel_summarize, text="Master Summary",
            font=ctk.CTkFont(size=26, weight="bold")
        ).grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 2), sticky="w")

        ctk.CTkLabel(
            self.panel_summarize,
            text="Tóm tắt hàng loạt file .md bằng AI và tổng hợp thành báo cáo duy nhất",
            text_color="gray60", font=ctk.CTkFont(size=14)
        ).grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 15), sticky="w")

        # --- Thư mục nguồn (chứa file .md) ---
        ctk.CTkLabel(self.panel_summarize, text="Thư mục .md:").grid(
            row=2, column=0, padx=20, pady=6, sticky="w")
        self.entry_sum_input = ctk.CTkEntry(
            self.panel_summarize,
            placeholder_text="Thư mục chứa các file .md cần tóm tắt (VD: 3_KetQua_MD)")
        self.entry_sum_input.grid(row=2, column=1, padx=(0, 10), pady=6, sticky="ew")
        ctk.CTkButton(
            self.panel_summarize, text="Chọn", width=80,
            command=lambda: self._browse_folder(self.entry_sum_input)
        ).grid(row=2, column=2, padx=(0, 20), pady=6)

        # --- Thư mục xuất (output folder) ---
        ctk.CTkLabel(self.panel_summarize, text="Thư mục xuất:").grid(
            row=3, column=0, padx=20, pady=6, sticky="w")
        self.entry_sum_output = ctk.CTkEntry(
            self.panel_summarize,
            placeholder_text="Thư mục lưu báo cáo (VD: 4_Summarized_files)")
        self.entry_sum_output.insert(0, "4_Summarized_files")
        self.entry_sum_output.grid(row=3, column=1, padx=(0, 10), pady=6, sticky="ew")
        ctk.CTkButton(
            self.panel_summarize, text="Chọn", width=80,
            command=lambda: self._browse_folder(self.entry_sum_output)
        ).grid(row=3, column=2, padx=(0, 20), pady=6)

        # --- Nút chạy ---
        self.btn_summarize = ctk.CTkButton(
            self.panel_summarize, text="🧠  Tạo Master Summary",
            fg_color="#8e44ad", hover_color="#6c3483",
            font=ctk.CTkFont(size=16, weight="bold"), height=42,
            command=self.run_master_summary
        )
        self.btn_summarize.grid(
            row=4, column=0, columnspan=3, padx=20, pady=10, sticky="ew")

        # --- Live Log ---
        ctk.CTkLabel(
            self.panel_summarize, text="Live Log",
            font=ctk.CTkFont(size=15, weight="bold")
        ).grid(row=5, column=0, padx=20, pady=(5, 0), sticky="w")

        self.textbox_sum_log = ctk.CTkTextbox(
            self.panel_summarize, state="disabled", font=ctk.CTkFont(size=14))
        self.textbox_sum_log.grid(
            row=6, column=0, columnspan=3, padx=20, pady=(4, 20), sticky="nsew")
        self.panel_summarize.grid_rowconfigure(6, weight=1)

    # ------------------------------------------------------------------ #
    #  ĐIỀU HƯỚNG SIDEBAR                                                  #
    # ------------------------------------------------------------------ #
    def _hide_all_panels(self):
        for panel in [
            self.panel_convert, self.panel_search,
            self.panel_summarize, self.panel_settings,
            self.panel_history,
        ]:
            panel.grid_forget()

    def _highlight_nav(self, active_btn):
        for btn in [
            self.btn_nav_convert, self.btn_nav_search,
            self.btn_nav_summarize, self.btn_nav_settings,
            self.btn_nav_history,
        ]:
            btn.configure(fg_color="transparent")
        active_btn.configure(fg_color=("gray75", "gray25"))

    def show_convert_panel(self):
        self._hide_all_panels()
        self.panel_convert.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        self._highlight_nav(self.btn_nav_convert)

    def show_search_panel(self):
        self._hide_all_panels()
        self.panel_search.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        self._highlight_nav(self.btn_nav_search)

    def show_summarize_panel(self):
        self._hide_all_panels()
        self.panel_summarize.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        self._highlight_nav(self.btn_nav_summarize)

    def show_settings_panel(self):
        self._hide_all_panels()
        self.panel_settings.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        self._highlight_nav(self.btn_nav_settings)

    def show_history_panel(self):
        self._hide_all_panels()
        self.panel_history.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        self._highlight_nav(self.btn_nav_history)
        self._refresh_history()

    # ------------------------------------------------------------------ #
    #  HELPER: LOG & BROWSE                                                #
    # ------------------------------------------------------------------ #
    def log(self, message, textbox=None):
        """Ghi thông điệp vào textbox log một cách thread-safe."""
        if textbox is None:
            textbox = self.textbox_log
        def _append():
            textbox.configure(state="normal")
            textbox.insert("end", message + "\n")
            textbox.configure(state="disabled")
            textbox.see("end")
        self.after(0, _append)  # Thread-safe: gọi từ main thread

    def _browse_folder(self, entry_widget):
        folder = filedialog.askdirectory()
        if folder:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, folder)

    # ------------------------------------------------------------------ #
    #  LOGIC: WATCHER (CONVERT PANEL)                                      #
    # ------------------------------------------------------------------ #
    def start_watcher(self):
        approved = self.entry_approved.get().strip()
        output = self.entry_output.get().strip()

        if not approved or not output:
            self.log("❌ Vui lòng chọn đầy đủ thư mục nguồn và thư mục xuất.")
            return

        workers = int(self.slider_workers.get())

        self._watcher_running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.log(f"👀 Đang theo dõi: {approved}")
        self.log(f"🚀 Max workers: {workers}\n")

        self._watcher_thread = threading.Thread(
            target=self._run_watcher,
            args=(approved, output, workers),
            daemon=True
        )
        self._watcher_thread.start()

    def _run_watcher(self, approved, output, workers):
        """Chạy trong background thread để không đóng băng UI."""
        try:
            watch_and_auto_convert(
                input_folder=approved,
                output_folder=output,
                max_workers=workers,
                log_callback=lambda message: self.log(message, self.textbox_log),
            )
        except Exception as e:
            self.log(f"❌ Lỗi hệ thống: {e}")
        finally:
            self.after(0, self._on_watcher_stopped)

    def stop_watcher(self):
        self._watcher_running = False
        self.log("🛑 Đã yêu cầu dừng theo dõi...")
        self._on_watcher_stopped()

    def _on_watcher_stopped(self):
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")

    # ------------------------------------------------------------------ #
    #  LOGIC: SEARCH PANEL                                                 #
    # ------------------------------------------------------------------ #
    def run_search(self):
        keyword = self.entry_keyword.get().strip()
        if not keyword:
            self.log("❌ Vui lòng nhập từ khóa tìm kiếm.", self.textbox_search_log)
            return

        # Lấy loại tài liệu từ combo (ký tự đầu là '1', '2', hoặc '3')
        loai_tl = self.combo_doc_type.get()[0]
        source_label = self.combo_search_source.get()
        source = self.search_source_by_label[source_label]
        so_luong = int(self.slider_result_count.get())

        self._search_results = []
        self.btn_download.configure(state="disabled")
        self.log(f"🔍 Đang tìm kiếm: '{keyword}' ({source_label}) — tối đa {so_luong} kết quả...\n", self.textbox_search_log)

        threading.Thread(
            target=self._search_worker,
            args=(keyword, loai_tl, source, so_luong),
            daemon=True
        ).start()

    def _search_worker(self, keyword, loai_tl, source, so_luong=5):
        """Chạy tìm kiếm trong background thread và hiển thị kết quả."""
        ket_qua = tim_kiem_pdf(
            keyword, loai_tl, so_luong,
            log_callback=lambda msg: self.log(msg, self.textbox_search_log),
            source=source,
        )

        if not ket_qua:
            return

        self.log("\n📋 Danh sách kết quả:", self.textbox_search_log)
        for i, res in enumerate(ket_qua):
            self.log(f"  [{i + 1}] {res['title']}", self.textbox_search_log)
            self.log(f"       Nguồn: {res.get('source', 'Không rõ nguồn')}", self.textbox_search_log)
            if res.get('has_pdf'):
                self.log("       📄 Link PDF trực tiếp", self.textbox_search_log)
            else:
                self.log("       🔗 Trang thông tin (chưa xác nhận PDF)", self.textbox_search_log)
            self.log(f"       🔗 {res['href']}", self.textbox_search_log)
            # Ask AI to summarise the paper inline (runs in its own daemon thread)
            summarize_paper(
                title=res['title'],
                abstract_text=res.get('description', ''),
                log_callback=lambda msg: self.log(msg, self.textbox_search_log),

            )
            self.log("", self.textbox_search_log)  # blank line separator

        self.after(0, lambda: self._set_search_results(ket_qua))

    def _set_search_results(self, results):
        """Store the last displayed results so their 1-based numbers can be downloaded."""
        self._search_results = results
        self.btn_download.configure(state="normal" if results else "disabled")

    def download_selected_results(self):
        """Validate the selected numbers, then download them without freezing the GUI."""
        if not self._search_results:
            self.log("❌ Hãy tìm kiếm tài liệu trước khi tải.", self.textbox_search_log)
            return

        selection = self.entry_download_selection.get().strip()
        if not selection:
            self.log("❌ Nhập số thứ tự kết quả muốn tải, ví dụ: 1,3,5.", self.textbox_search_log)
            return

        selected_numbers = []
        for value in selection.split(','):
            value = value.strip()
            if value.isdigit() and int(value) not in selected_numbers:
                selected_numbers.append(int(value))

        valid_numbers = [
            number for number in selected_numbers
            if 1 <= number <= len(self._search_results)
        ]
        if not valid_numbers:
            self.log("❌ Không có số thứ tự hợp lệ trong danh sách kết quả.", self.textbox_search_log)
            return

        invalid_numbers = sorted(set(selected_numbers) - set(valid_numbers))
        if invalid_numbers:
            self.log(
                f"⚠️ Bỏ qua kết quả không hợp lệ: {', '.join(map(str, invalid_numbers))}.",
                self.textbox_search_log,
            )

        output_folder = self.entry_download_folder.get().strip()
        if not output_folder:
            self.log("❌ Chọn thư mục tải về trước khi tiếp tục.", self.textbox_search_log)
            return

        self.btn_download.configure(state="disabled")
        self.log(f"⬇ Bắt đầu kiểm tra và tải {len(valid_numbers)} kết quả đã chọn...", self.textbox_search_log)
        threading.Thread(
            target=self._download_worker,
            args=(list(self._search_results), valid_numbers, output_folder),
            daemon=True,
        ).start()

    def _download_worker(self, results, selected_numbers, output_folder):
        """Run the safe core downloader in a worker thread."""
        try:
            tai_pdf(
                results,
                selected_numbers,
                thu_muc_luu=output_folder,
                log_callback=lambda msg: self.log(msg, self.textbox_search_log),
            )
        finally:
            self.after(0, lambda: self.btn_download.configure(
                state="normal" if self._search_results else "disabled"
            ))

    # ------------------------------------------------------------------ #
    #  LOGIC: SUMMARIZE PANEL                                              #
    # ------------------------------------------------------------------ #
    def run_master_summary(self):
        input_dir = self.entry_sum_input.get().strip()
        output_dir = self.entry_sum_output.get().strip()

        if not input_dir:
            self.log("❌ Vui lòng chọn thư mục chứa file .md.", self.textbox_sum_log)
            return
        if not output_dir:
            self.log("❌ Vui lòng chọn thư mục xuất.", self.textbox_sum_log)
            return

        # Build output file path: <output_dir>/master_summary.md
        output_filepath = str(Path(output_dir) / "master_summary.md")

        self.btn_summarize.configure(state="disabled")
        self.log(
            f"📊 Bắt đầu tóm tắt các file .md từ: {input_dir}\n"
            f"   → Kết quả sẽ lưu tại: {output_filepath}\n",
            self.textbox_sum_log
        )

        threading.Thread(
            target=self._summarize_worker,
            args=(input_dir, output_filepath),
            daemon=True
        ).start()

    def _summarize_worker(self, input_dir, output_filepath):
        """Run create_master_summary in a background thread."""
        try:
            create_master_summary(
                input_dir=input_dir,
                output_filepath=output_filepath,
                log_callback=lambda msg: self.log(msg, self.textbox_sum_log),
            )
        except Exception as e:
            self.log(f"❌ Lỗi hệ thống: {e}", self.textbox_sum_log)
        finally:
            self.after(0, lambda: self.btn_summarize.configure(state="normal"))

    # ------------------------------------------------------------------ #
    #  BUILDER: PANEL HISTORY                                              #
    # ------------------------------------------------------------------ #
    def _build_history_panel(self):
        self.panel_history = ctk.CTkFrame(self, corner_radius=10)
        self.panel_history.grid_rowconfigure(2, weight=1)
        self.panel_history.grid_columnconfigure(0, weight=1)

        # Tiêu đề
        ctk.CTkLabel(
            self.panel_history, text="Download History",
            font=ctk.CTkFont(size=26, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 2), sticky="w")

        ctk.CTkLabel(
            self.panel_history,
            text="Danh sách các file đã tải thành công",
            text_color="gray60", font=ctk.CTkFont(size=14)
        ).grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w")

        # Textbox hiển thị lịch sử
        self.textbox_history = ctk.CTkTextbox(
            self.panel_history, state="disabled", font=ctk.CTkFont(size=13)
        )
        self.textbox_history.grid(
            row=2, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="nsew"
        )

        # Nút hành động
        btn_row = ctk.CTkFrame(self.panel_history, fg_color="transparent")
        btn_row.grid(row=3, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_row, text="🔄  Làm mới",
            font=ctk.CTkFont(size=14, weight="bold"), height=38,
            command=self._refresh_history
        ).grid(row=0, column=0, padx=(0, 8), sticky="ew")

        ctk.CTkButton(
            btn_row, text="🗑️  Xóa lịch sử",
            fg_color="#e74c3c", hover_color="#c0392b",
            font=ctk.CTkFont(size=14, weight="bold"), height=38,
            command=self._clear_history_action
        ).grid(row=0, column=1, sticky="ew")

    def _refresh_history(self):
        """Load records from history.json and render them into the textbox."""
        records = load_history()
        self.textbox_history.configure(state="normal")
        self.textbox_history.delete("1.0", "end")

        if not records:
            self.textbox_history.insert("end", "Chưa có lịch sử tải nào.\n")
        else:
            # Show newest first
            for i, rec in enumerate(reversed(records), 1):
                self.textbox_history.insert("end", f"─" * 60 + "\n")
                self.textbox_history.insert("end", f"[{i}] {rec.get('time', 'N/A')}\n")
                self.textbox_history.insert("end", f"  📄 File   : {rec.get('file', 'N/A')}\n")
                self.textbox_history.insert("end", f"  🔗 Link   : {rec.get('link', 'N/A')}\n")
                self.textbox_history.insert("end", f"  📝 Summary: {rec.get('summary', 'N/A')}\n")
            self.textbox_history.insert("end", f"─" * 60 + "\n")
            self.textbox_history.insert(
                "end", f"\nTổng cộng: {len(records)} file đã tải.\n"
            )

        self.textbox_history.configure(state="disabled")
        self.textbox_history.see("1.0")

    def _clear_history_action(self):
        """Ask for confirmation then wipe history.json."""
        confirmed = messagebox.askyesno(
            title="Xác nhận",
            message="Bạn có chắc muốn xóa toàn bộ lịch sử tải không?"
        )
        if confirmed:
            clear_history()
            self._refresh_history()

    # ------------------------------------------------------------------ #
    #  LOGIC: SETTINGS PANEL                                               #
    # ------------------------------------------------------------------ #

    def _update_result_count_label(self, value):
        self.lbl_result_count.configure(text=str(int(value)))

    def _update_worker_label(self, value):
        self.lbl_worker_val.configure(text=str(int(value)))

    def _apply_settings(self):
        approved = self.entry_default_approved.get().strip()
        output = self.entry_default_output.get().strip()

        # Áp dụng vào Convert panel nếu có giá trị
        if approved:
            self.entry_approved.delete(0, "end")
            self.entry_approved.insert(0, approved)
        if output:
            self.entry_output.delete(0, "end")
            self.entry_output.insert(0, output)

        self.log("✅ Đã lưu và áp dụng cài đặt vào panel Convert.")
        self.show_convert_panel()

    def toggle_theme(self):
        if self.theme_switch.get():
            ctk.set_appearance_mode("Light")
            self.theme_switch.configure(text="Dark Mode")
        else:
            ctk.set_appearance_mode("Dark")
            self.theme_switch.configure(text="Light Mode")


if __name__ == "__main__":
    app = PipelineApp()
    app.mainloop()
