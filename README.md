# 🚀 PDF-to-Markdown Pipeline

Hệ thống tự động hóa hỗ trợ thu thập, kiểm duyệt (Human-in-the-Loop) và bóc tách dữ liệu từ tài liệu PDF sang định dạng Markdown. Dự án được tối ưu hóa đa luồng, tích hợp bộ lọc nội dung thông minh và giao diện đồ họa (GUI).

## ✨ Tính năng nổi bật

- **Smart Search (`core/search.py`):** Tự động tìm kiếm PDF từ nhiều nguồn (web, Semantic Scholar, ArXiv...), loại bỏ slide thuyết trình và file hỏng (kiểm tra qua Magic Bytes `%PDF`).
- **Multi-threaded OCR & Parsing (`core/auto_convert.py`):** Theo dõi thư mục thời gian thực và xử lý đa luồng nhiều file cùng lúc.
- **Hybrid Extraction:** Nhận diện thông minh văn bản thuần, bảng biểu (qua `pdfplumber`), và tự động chuyển sang Tesseract OCR đối với ảnh hoặc tài liệu scan.
- **AI Summarization (`core/ai_summary.py`, `core/master_summary.py`):** Tóm tắt từng bài báo và tổng hợp thành một báo cáo Master Summary duy nhất.
- **Human-in-the-Loop:** Luồng thư mục rõ ràng giúp người dùng kiểm duyệt chất lượng tài liệu trước khi bóc tách.
- **GUI Desktop App (`gui.py`):** Giao diện đồ họa hiện đại xây dựng với `customtkinter`, hỗ trợ Dark/Light mode.
- **Download History:** Lưu lại lịch sử các file đã tải về cùng tóm tắt nội dung.

## 📂 Kiến trúc luồng dữ liệu (Data Flow)

```
1_RawPDF/           ← Tài liệu thô tải về từ Search
2_Quality_Checked/  ← Khu vực kích hoạt: chuyển PDF đạt chất lượng vào đây
3_Result_MD/        ← File .md đã hoàn thiện
4_Summarized_files/ ← Báo cáo Master Summary do AI tổng hợp
5_ArchivedFiles/    ← File PDF gốc sau khi đã xử lý (tuỳ chọn)
```

## ⚙️ Cài đặt môi trường

Yêu cầu **Python 3.x** và **Tesseract OCR** được cài đặt trên hệ điều hành.

**Cài Tesseract (Ubuntu/Debian):**
```bash
sudo apt install tesseract-ocr tesseract-ocr-vie
```

**Cài đặt dự án:**
```bash
# 1. Clone repository
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name

# 2. Tạo và kích hoạt môi trường ảo (khuyến nghị)
python3 -m venv .venv
source .venv/bin/activate

# 3. Cài đặt các thư viện
pip install -r requirement.txt
```

## 🚀 Hướng dẫn sử dụng

### Chạy ứng dụng GUI (khuyến nghị)

```bash
python3 gui.py
```

Giao diện gồm 5 tab:

| Tab | Chức năng |
|---|---|
| 🔄 **Convert** | Theo dõi thư mục và tự động chuyển PDF → Markdown |
| 🔍 **Search** | Tìm kiếm và tải PDF từ web/các nguồn nghiên cứu |
| 📊 **Summarize** | Tóm tắt hàng loạt file .md bằng AI |
| ⚙️ **Settings** | Cấu hình số luồng, ngôn ngữ OCR, thư mục mặc định |
| 📜 **History** | Xem và xóa lịch sử file đã tải |

### Cấu hình API Key (cho tính năng AI)

Tạo file `.env` tại thư mục gốc:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

## 📦 Cấu trúc dự án

```
doc2md/
├── gui.py                  # Ứng dụng GUI chính
├── core/
│   ├── auto_convert.py     # Watcher & bộ máy chuyển đổi đa luồng
│   ├── search.py           # Tìm kiếm & tải PDF từ nhiều nguồn
│   ├── smart_convert.py    # Hybrid extraction (text + OCR)
│   ├── ai_summary.py       # Tóm tắt từng bài bằng AI
│   ├── master_summary.py   # Tổng hợp Master Summary
│   ├── archiver.py         # Lưu trữ file gốc sau xử lý
│   └── history_manager.py  # Quản lý lịch sử tải
├── requirement.txt
└── README.md
```
