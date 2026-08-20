import os
import pymupdf
import pytesseract
from PIL import Image
import io
import sys
from markitdown import MarkItDown

# Khởi tạo công cụ MarkItDown cho các file không phải PDF
md_converter = MarkItDown()

def process_pdf_hybrid(pdf_path, ocr_lang='vie+eng'):
    """
    Xử lý riêng cho file PDF: Kết hợp chữ gốc và OCR hình ảnh.
    """
    doc = pymupdf.open(pdf_path)
    full_markdown = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_md = f"### Trang {page_num + 1}\n\n"
        
        # Lấy chữ gốc (Text layer)
        native_text = page.get_text().strip()
        if native_text:
            page_md += native_text + "\n\n"

        # Lấy hình ảnh và chạy OCR
        images = page.get_images(full=True)
        for img_info in images:
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            try:
                img = Image.open(io.BytesIO(image_bytes))
                # --- THÊM DÒNG NÀY ĐỂ MÁY BÁO CÁO TIẾN ĐỘ ---
                print(f"    -> Đang quét OCR một ảnh ở Trang {page_num + 1}...")
                ocr_text = pytesseract.image_to_string(img, lang=ocr_lang).strip()
                if ocr_text:
                    page_md += f"> **[OCR - Chữ từ ảnh]:**\n> {ocr_text}\n\n"
            except Exception as e:
                page_md += f"> *(Lỗi phân tích hình ảnh: {e})*\n\n"
        
        full_markdown.append(page_md)
        
    return "\n---\n".join(full_markdown)

def process_other_files(file_path):
    """
    Xử lý các file Word, Excel, PowerPoint... bằng MarkItDown
    """
    try:
        result = md_converter.convert(file_path)
        return result.text_content.strip()
    except Exception as e:
        return f"Lỗi khi đọc file bằng MarkItDown: {e}"

def batch_process_and_merge(input_folder, output_filepath, ocr_lang='vie+eng'):
    """
    Duyệt thư mục, xử lý từng file và gộp vào một file Markdown.
    """
    if not os.path.exists(input_folder):
        print(f"Không tìm thấy thư mục: {input_folder}")
        return

    # Mở file tổng để ghi dần (dùng chế độ 'w' để ghi đè nếu file đã tồn tại)
    with open(output_filepath, 'w', encoding='utf-8') as f_out:
        f_out.write("# TỔNG HỢP TÀI LIỆU\n\n")
        
        # Lấy danh sách file và sắp xếp theo tên
        files = sorted(os.listdir(input_folder))
        
        for filename in files:
            file_path = os.path.join(input_folder, filename)
            
            # Bỏ qua các thư mục con hoặc file ẩn
            if os.path.isdir(file_path) or filename.startswith('.'):
                continue
                
            print(f"[*] Đang xử lý: {filename} ...")
            f_out.write(f"## 📄 File: {filename}\n\n")
            
            # Phân loại đuôi file để xử lý
            ext = os.path.splitext(filename)[1].lower()
            
            if ext == '.pdf':
                content = process_pdf_hybrid(file_path, ocr_lang)
            else:
                # Giao cho markitdown xử lý .docx, .xlsx, .pptx, v.v.
                content = process_other_files(file_path)
                
            # Ghi nội dung vào file tổng
            f_out.write(content)
            f_out.write("\n\n" + "="*40 + "\n\n")

    print(f"\n🎉 HOÀN TẤT! Đã gộp toàn bộ vào file: {output_filepath}")

# === HƯỚNG DẪN CHẠY ===
if __name__ == "__main__":
    # Kiểm tra xem người dùng đã nhập đường dẫn thư mục chưa
    if len(sys.argv) < 2:
        print("Cách dùng: python3 gop_tai_lieu.py <đường_dẫn_tới_thư_mục_chứa_tài_liệu>")
        sys.exit(1)

    THU_MUC_CHUA_FILE = sys.argv[1]
    
    # Tạo đường dẫn lưu file tổng hợp NẰM NGAY TRONG thư mục người dùng truyền vào
    FILE_TONG_HOP = os.path.join(THU_MUC_CHUA_FILE, "ket_qua_tong_hop.md")

    # Kiểm tra xem thư mục có tồn tại không
    if not os.path.isdir(THU_MUC_CHUA_FILE):
        print(f"Lỗi: Không tìm thấy thư mục '{THU_MUC_CHUA_FILE}'")
        sys.exit(1)

    # Chạy trình gộp
    print(f"Đang chuẩn bị gộp các tài liệu trong thư mục: {THU_MUC_CHUA_FILE}")
    batch_process_and_merge(THU_MUC_CHUA_FILE, FILE_TONG_HOP, ocr_lang='vie')