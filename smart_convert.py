import os
import sys
import pymupdf
import pytesseract
from PIL import Image
import io
from markitdown import MarkItDown

md_converter = MarkItDown()

def process_pdf_hybrid(pdf_path, ocr_lang='vie+eng'):
    """Chỉ đọc chữ gốc và quét OCR các vùng là hình ảnh trong PDF"""
    doc = pymupdf.open(pdf_path)
    full_markdown = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_md = f"### Trang {page_num + 1}\n\n"
        
        # 1. Lấy chữ gốc (Text layer)
        native_text = page.get_text().strip()
        if native_text:
            page_md += native_text + "\n\n"

        # 2. Lấy hình ảnh và chạy OCR
        images = page.get_images(full=True)
        for img_info in images:
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            try:
                img = Image.open(io.BytesIO(image_bytes))
                ocr_text = pytesseract.image_to_string(img, lang=ocr_lang).strip()
                if ocr_text:
                    page_md += f"> **[OCR - Chữ từ ảnh]:**\n> {ocr_text}\n\n"
            except Exception as e:
                pass # Bỏ qua lỗi ảnh để không làm gián đoạn
        
        full_markdown.append(page_md)
        
    return "\n---\n".join(full_markdown)

def convert_single_file(file_path):
    """Chuyển đổi 1 file bất kỳ ra file .md tương ứng"""
    if not os.path.isfile(file_path):
        print(f"Lỗi: Không tìm thấy file '{file_path}'")
        return

    # Tạo tên file đầu ra (ví dụ: tailieu.pdf -> tailieu.md)
    base_name = os.path.splitext(file_path)[0]
    output_md = f"{base_name}.md"
    ext = os.path.splitext(file_path)[1].lower()

    print(f"[*] Đang xử lý: {os.path.basename(file_path)}...")
    
    try:
        if ext == '.pdf':
            content = process_pdf_hybrid(file_path)
        else:
            result = md_converter.convert(file_path)
            content = result.text_content.strip()

        with open(output_md, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f" -> Thành công! Đã lưu tại: {output_md}")
    except Exception as e:
        print(f" -> Có lỗi khi xử lý: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Cách dùng:")
        print("  Chuyển 1 file  : python smart_convert.py <đường_dẫn_file>")
        print("  Chuyển thư mục : python smart_convert.py <đường_dẫn_thư_mục>")
        sys.exit(1)

    target_path = sys.argv[1]

    if os.path.isfile(target_path):
        # Nếu truyền vào 1 file -> Chỉ chạy 1 file
        convert_single_file(target_path)
    elif os.path.isdir(target_path):
        # Nếu truyền vào thư mục -> Quét toàn bộ thư mục
        print(f"Đang quét thư mục: {target_path}...\n")
        for filename in os.listdir(target_path):
            full_path = os.path.join(target_path, filename)
            if os.path.isfile(full_path) and not filename.startswith('.'):
                convert_single_file(full_path)
    else:
        print("Đường dẫn không hợp lệ!")