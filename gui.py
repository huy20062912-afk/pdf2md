import threading
import customtkinter as ctk
from tkinter import filedialog
from core.auto_convert import watch_and_auto_convert
from core.search import tim_kiem_pdf, tai_pdf

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

        # Hệ thống lưới: 1 hàng, 2 cột
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ==================== TRÁI: SIDEBAR ====================
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)
        self.sidebar_frame.grid_rowconfigure(4, weight=1)  # Đẩy nội dung lên trên

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, text="PDF2MD",
            font=ctk.CTkFont(size=22, weight="bold")
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

        self.btn_nav_settings = ctk.CTkButton(
            self.sidebar_frame, text="⚙️  Settings", **nav_style,
            command=self.show_settings_panel
        )
        self.btn_nav_settings.grid(row=3, column=0, padx=15, pady=5, sticky="ew")

        # Nút chuyển Dark/Light ở cuối sidebar
        self.theme_switch = ctk.CTkSwitch(
            self.sidebar_frame, text="Light Mode",
            command=self.toggle_theme,
            font=ctk.CTkFont(size=12)
        )
        self.theme_switch.grid(row=5, column=0, padx=20, pady=20, sticky="sw")

        # ==================== PHẢI: CÁC PANEL ====================
        self._build_convert_panel()
        self._build_search_panel()
        self._build_settings_panel()

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
            font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 2), sticky="w")

        ctk.CTkLabel(
            self.panel_convert,
            text="Theo dõi thư mục và tự động chuyển đổi PDF sang Markdown",
            text_color="gray60", font=ctk.CTkFont(size=12)
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
            font=ctk.CTkFont(size=14, weight="bold"), height=38,
            command=self.start_watcher
        )
        self.btn_start.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        self.btn_stop = ctk.CTkButton(
            btn_row, text="⏹  Dừng",
            fg_color="#e74c3c", hover_color="#c0392b",
            font=ctk.CTkFont(size=14, weight="bold"), height=38,
            state="disabled",
            command=self.stop_watcher
        )
        self.btn_stop.grid(row=0, column=1, sticky="ew")

        # --- Live Log ---
        ctk.CTkLabel(
            self.panel_convert, text="Live Log",
            font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=5, column=0, padx=20, pady=(5, 0), sticky="w")

        self.textbox_log = ctk.CTkTextbox(self.panel_convert, state="disabled", font=ctk.CTkFont(size=12))
        self.textbox_log.grid(row=6, column=0, columnspan=3, padx=20, pady=(4, 20), sticky="nsew")
        self.panel_convert.grid_rowconfigure(6, weight=1)

    # ------------------------------------------------------------------ #
    #  BUILDER: PANEL SEARCH                                               #
    # ------------------------------------------------------------------ #
    def _build_search_panel(self):
        self.panel_search = ctk.CTkFrame(self, corner_radius=10)
        self.panel_search.grid_rowconfigure(4, weight=1)
        self.panel_search.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.panel_search, text="PDF Search & Download",
            font=ctk.CTkFont(size=22, weight="bold")
        ).grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 2), sticky="w")

        ctk.CTkLabel(
            self.panel_search, text="Tìm kiếm và tải PDF tự động từ DuckDuckGo",
            text_color="gray60", font=ctk.CTkFont(size=12)
        ).grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 15), sticky="w")

        # Từ khóa
        ctk.CTkLabel(self.panel_search, text="Từ khóa:").grid(
            row=2, column=0, padx=20, pady=6, sticky="w")
        self.entry_keyword = ctk.CTkEntry(
            self.panel_search, placeholder_text="VD: machine learning, Python tutorial...")
        self.entry_keyword.grid(row=2, column=1, padx=(0, 10), pady=6, sticky="ew")

        # Loại tài liệu
        ctk.CTkLabel(self.panel_search, text="Loại tài liệu:").grid(
            row=3, column=0, padx=20, pady=6, sticky="w")
        self.combo_doc_type = ctk.CTkComboBox(
            self.panel_search,
            values=["1 - Nghiên cứu (Thesis, Report)", "2 - Hướng dẫn (Manual, Guide)", "3 - Tổng quát"]
        )
        self.combo_doc_type.set("3 - Tổng quát")
        self.combo_doc_type.grid(row=3, column=1, padx=(0, 10), pady=6, sticky="ew")

        ctk.CTkButton(
            self.panel_search, text="🔍  Tìm kiếm",
            font=ctk.CTkFont(size=14, weight="bold"), height=38,
            command=self.run_search
        ).grid(row=3, column=2, padx=(0, 20), pady=6)

        # Log tìm kiếm
        self.textbox_search_log = ctk.CTkTextbox(self.panel_search, state="disabled", font=ctk.CTkFont(size=12))
        self.textbox_search_log.grid(row=4, column=0, columnspan=3, padx=20, pady=(10, 20), sticky="nsew")

    # ------------------------------------------------------------------ #
    #  BUILDER: PANEL SETTINGS                                             #
    # ------------------------------------------------------------------ #
    def _build_settings_panel(self):
        self.panel_settings = ctk.CTkFrame(self, corner_radius=10)
        self.panel_settings.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.panel_settings, text="Settings",
            font=ctk.CTkFont(size=22, weight="bold")
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
            font=ctk.CTkFont(size=14, weight="bold")
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
            font=ctk.CTkFont(size=14, weight="bold"), height=38,
            command=self._apply_settings
        ).grid(row=6, column=0, columnspan=3, padx=20, pady=25, sticky="ew")

    # ------------------------------------------------------------------ #
    #  ĐIỀU HƯỚNG SIDEBAR                                                  #
    # ------------------------------------------------------------------ #
    def _hide_all_panels(self):
        for panel in [self.panel_convert, self.panel_search, self.panel_settings]:
            panel.grid_forget()

    def _highlight_nav(self, active_btn):
        for btn in [self.btn_nav_convert, self.btn_nav_search, self.btn_nav_settings]:
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

    def show_settings_panel(self):
        self._hide_all_panels()
        self.panel_settings.grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        self._highlight_nav(self.btn_nav_settings)

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
                max_workers=workers
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

        self.log(f"🔍 Đang tìm kiếm: '{keyword}'...", self.textbox_search_log)

        threading.Thread(
            target=tim_kiem_pdf,
            args=(keyword, loai_tl, 10, lambda msg: self.log(msg, self.textbox_search_log)),
            daemon=True
        ).start()

    # ------------------------------------------------------------------ #
    #  LOGIC: SETTINGS PANEL                                               #
    # ------------------------------------------------------------------ #
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