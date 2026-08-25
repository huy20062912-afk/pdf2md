import os
import sys
import time
import io
import pymupdf
import pytesseract
import pdfplumber
import concurrent.futures
from PIL import Image
from markitdown import MarkItDown
from core.archiver import move_to_archive

md_converter = MarkItDown()

# --- 1. CÁC HÀM XỬ LÝ NỘI DUNG (GIỮ NGUYÊN) ---

def _log(message, log_callback=None):
    """Send conversion progress to the GUI or print it in command-line mode."""
    if log_callback:
        log_callback(message)
    else:
        print(message)

def table_to_markdown(table_data):
    if not table_data: return ""
    md_table = "\n\n> **📊 [Bảng biểu]:**\n\n"
    for i, row in enumerate(table_data):
        clean_row = [str(cell).replace('\n', ' ').strip() if cell is not None else " " for cell in row]
        md_table += "| " + " | ".join(clean_row) + " |\n"
        if i == 0:
            md_table += "|" + "|".join(["---"] * len(row)) + "|\n"
    return md_table + "\n"

def process_pdf_hybrid(pdf_path, ocr_lang='vie+eng'):
    doc = pymupdf.open(pdf_path)
    full_markdown = []

    with pdfplumber.open(pdf_path) as pdf_table_reader:
        for page_num in range(len(doc)):
            page = doc[page_num]
            plumber_page = pdf_table_reader.pages[page_num]
            page_md = f"### Trang {page_num + 1}\n\n"

            # 1. Quét Bảng biểu
            tables = plumber_page.extract_tables()
            if tables:
                for table in tables: page_md += table_to_markdown(table)

            # 2. Quét Chữ gốc
            native_text = page.get_text().strip()
            if native_text: page_md += native_text + "\n\n"

            # 3. QUÉT OCR (ĐÃ TỐI ƯU HÓA)
            # CHIẾN THUẬT 1: Chỉ chạy OCR nếu trang này có quá ít chữ (dưới 100 ký tự)
            # Ngầm hiểu: Đây là file scan hoặc ảnh chụp toàn trang
            if len(native_text) < 100:
                images = page.get_images(full=True)
                for img_info in images:
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    try:
                        img = Image.open(io.BytesIO(image_bytes))
                        
                        # CHIẾN THUẬT 2: Giảm kích thước nếu ảnh quá to (Tối đa 2000px)
                        max_size = 2000
                        if img.width > max_size or img.height > max_size:
                            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                            
                        ocr_text = pytesseract.image_to_string(img, lang=ocr_lang).strip()
                        if ocr_text: page_md += f"> **[OCR]:**\n> {ocr_text}\n\n"
                    except Exception:
                        pass
            
            full_markdown.append(page_md)

    return "\n---\n".join(full_markdown)

def is_file_ready(file_path):
    try:
        init_size = os.path.getsize(file_path)
        time.sleep(1)
        return init_size == os.path.getsize(file_path) and init_size > 0
    except Exception:
        return False

# --- 2. HÀM CÔNG NHÂN (CHUYÊN TRỊ 1 FILE ĐỘC LẬP) ---

def worker_xu_ly_file(file_path, filename, output_folder, log_callback=None, archive_folder=None):
    """Hàm này sẽ được chạy song song ở nhiều luồng khác nhau"""
    base_name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1].lower()
    output_md_path = os.path.join(output_folder, f"{base_name}.md")

    _log(f"⚡ [Bắt đầu] Đang chuyển đổi: {filename} ...", log_callback)
    try:
        if ext == '.pdf':
            content = process_pdf_hybrid(file_path)
        else:
            res = md_converter.convert(file_path)
            content = res.text_content.strip()

        with open(output_md_path, 'w', encoding='utf-8') as f:
            f.write(content)

        _log(f"   -> ✅ [Xong] Đã xuất Markdown cho: {filename}", log_callback)

        # Di chuyển file gốc vào thư mục lưu trữ nếu được bật
        if archive_folder:
            move_to_archive(file_path, archive_folder, log_callback)

    except Exception as e:
        _log(f"   -> ❌ [Lỗi] {filename}: {e}", log_callback)

# --- 3. VÒNG LẶP THEO DÕI & CHIA VIỆC ---

def watch_and_auto_convert(input_folder, output_folder, interval=2, max_workers=4, log_callback=None, archive_folder=None):
    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)

    _log(f"👀 Đang theo dõi thư mục: '{input_folder}'", log_callback)
    _log(f"🚀 Kích hoạt siêu tốc: Tối đa {max_workers} file cùng lúc", log_callback)
    if archive_folder:
        _log(f"📦 Lưu trữ file gốc vào: '{archive_folder}'", log_callback)
    _log("👉 Hãy thả file vào thư mục đầu vào...\n", log_callback)

    da_xu_ly = set()

    # Mở xưởng (Pool) với số lượng công nhân được chỉ định
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        while True:
            try:
                files = os.listdir(input_folder)
                for filename in files:
                    file_path = os.path.join(input_folder, filename)

                    if os.path.isdir(file_path) or filename.startswith('.') or filename.endswith('.tmp'):
                        continue

                    if filename not in da_xu_ly:
                        if not is_file_ready(file_path):
                            continue
                        
                        # Thay vì tự làm, ném việc cho "công nhân" chạy ngầm
                        executor.submit(
                            worker_xu_ly_file,
                            file_path,
                            filename,
                            output_folder,
                            log_callback,
                            archive_folder,
                        )
                        da_xu_ly.add(filename) # Ghi nhớ ngay để không giao việc trùng lặp

                time.sleep(interval)

            except KeyboardInterrupt:
                _log("\n🛑 Đã dừng theo dõi.", log_callback)
                break
            except Exception as e:
                _log(f"Lỗi hệ thống: {e}", log_callback)
                time.sleep(interval)

# --- 4. KHỞI ĐỘNG ---

if __name__ == "__main__":
    THU_MUC_VAO = sys.argv[1] if len(sys.argv) > 1 else "2_Da_Duyet"
    THU_MUC_RA = sys.argv[2] if len(sys.argv) > 2 else "3_KetQua_MD"
    
    # Bạn có thể đổi số max_workers (ví dụ 4 hoặc 8 tùy độ mạnh CPU của máy)
    watch_and_auto_convert(THU_MUC_VAO, THU_MUC_RA, max_workers=4)
