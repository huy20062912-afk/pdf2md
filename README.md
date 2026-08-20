# 🚀 Automated PDF-to-Markdown Pipeline

Một hệ thống tự động hóa hỗ trợ thu thập, kiểm duyệt (Human-in-the-loop) và bóc tách dữ liệu từ tài liệu PDF sang định dạng Markdown. Dự án được tối ưu hóa đa luồng và tích hợp bộ lọc nội dung thông minh.

## ✨ Tính năng nổi bật
* **Smart Search (`search.py`):** Tự động cào dữ liệu PDF, loại bỏ các trang web rác, slide thuyết trình và file hỏng (kiểm tra qua Magic Bytes `%PDF`).
* **Multi-threaded OCR & Parsing (`auto_convert.py`):** Theo dõi thư mục thời gian thực và xử lý đa luồng nhiều file cùng lúc.
* **Hybrid Extraction:** Nhận diện thông minh văn bản thuần, bảng biểu (qua `pdfplumber`), và linh hoạt chuyển sang Tesseract OCR đối với ảnh hoặc tài liệu scan.
* **Human-in-the-Loop:** Chia luồng thư mục rõ ràng giúp người dùng dễ dàng nghiệm thu chất lượng tài liệu trước khi đưa vào bóc tách.

## 📂 Kiến trúc luồng dữ liệu (Data Flow)
1. `1_TaiLieu_Tho/`: Nơi chứa tài liệu thô được tự động tải về từ `search.py`.
2. `2_Da_Duyet/`: Khu vực kích hoạt. Chuyển file PDF đạt chất lượng vào đây để hệ thống tự động bóc tách.
3. `3_KetQua_MD/`: Thư mục đích chứa các file `.md` đã hoàn thiện.

## ⚙️ Cài đặt môi trường
Dự án yêu cầu Python 3.x và công cụ Tesseract OCR được cài đặt sẵn trên hệ điều hành.

1. Clone repository:
   ```bash
   git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
   cd your-repo-name
2. Kích hoạt môi trường ảo (Khuyến nghị):
    python3 -m venv .venv
    source .venv/bin/activate
3. Cài đặt các thư viện cần thiết:
    pip install -r requirements.txt
🚀 Hướng dẫn sử dụng:
Mở Terminal 1: Chạy hệ thống theo dõi và chuyển đổi ngầm:
python3 auto_convert.py

Mở Terminal 2: Khởi chạy công cụ săn tài liệu thông minh:
python3 search.py

### Lợi ích của file cấu trúc này:
Nó không chỉ giải thích cách chạy code mà còn khoe được những "từ khóa đắt giá" về mặt kỹ thuật như *Multi-threaded, Human-in-the-loop, Hybrid Extraction, Magic Bytes*. Bất kỳ ai nhìn vào cũng sẽ thấy đây là một kiến trúc được tổ chức rất bài bản.

<FollowUp label="Chuẩn bị thư viện" query="Để phần Cài đặt trong README hoạt động đúng, bạn đã chạy lệnh `pip freeze"> requirements.txt` để gom các thư viện lại chưa?"/>
