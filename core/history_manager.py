import json
import os
from datetime import datetime

def save_to_history(file_name, source_link, summary_content):
    # Đường dẫn tới file JSON lưu lịch sử
    history_file = "history.json"
    
    # ==========================================
    # KHỐI 1: CHUẨN BỊ DỮ LIỆU (Tạo "từ điển" mới)
    # ==========================================
    new_record = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file": file_name,
        "link": source_link,
        "summary": summary_content
    }

    # ==========================================
    # KHỐI 2: ĐỌC LỊCH SỬ CŨ (Nếu đã từng lưu)
    # ==========================================
    # Kiểm tra xem file history.json đã tồn tại trong máy chưa
    if os.path.exists(history_file):
        # Mở file ở chế độ 'r' (read - đọc)
        with open(history_file, "r", encoding="utf-8") as f:
            history_list = json.load(f) # Tải nội dung file vào biến history_list
    else:
        # Nếu file chưa tồn tại (chạy lần đầu), tạo một danh sách trống
        history_list = [] 

    # ==========================================
    # KHỐI 3: CẬP NHẬT VÀ GHI ĐÈ
    # ==========================================
    # Nhét bản ghi mới vào cuối danh sách cũ
    history_list.append(new_record)
    
    # Mở file ở chế độ 'w' (write - ghi đè) để lưu lại danh sách đã cập nhật
    with open(history_file, "w", encoding="utf-8") as f:
        # dump: đổ dữ liệu từ Python vào file JSON
        # indent=4: thụt đầu dòng 4 ô cho file JSON đẹp và dễ đọc
        json.dump(history_list, f, ensure_ascii=False, indent=4)


# ==========================================
# HÀM CẦU NỐI: Dùng bởi search.py
# ==========================================
def save_download(title, url, filename, saved_to):
    """Gọi từ search.py sau khi tải PDF thành công.
    
    Ánh xạ các tham số từ luồng tải xuống sang save_to_history().
    - title    → file_name
    - url      → source_link
    - filename + saved_to → summary_content (thông tin lưu file)
    """
    summary = f"Saved as '{filename}' in folder '{saved_to}'"
    save_to_history(
        file_name=title,
        source_link=url,
        summary_content=summary,
    )


def load_history():
    """Đọc toàn bộ lịch sử từ history.json.
    
    Returns:
        Danh sách các bản ghi (dict). Trả về [] nếu file chưa tồn tại hoặc hỏng.
    """
    history_file = "history.json"
    if not os.path.exists(history_file):
        return []
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def clear_history():
    """Xóa toàn bộ lịch sử tải."""
    history_file = "history.json"
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=4)