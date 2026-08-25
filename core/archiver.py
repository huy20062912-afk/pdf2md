"""
archiver.py
~~~~~~~~~~~
Di chuyển file nguồn đã được xử lý vào thư mục lưu trữ (archive).

Được gọi sau khi một file được chuyển đổi sang Markdown thành công,
để giữ thư mục nguồn luôn sạch sẽ và tránh xử lý lại file cũ.

Cách sử dụng:
    from core.archiver import move_to_archive

    move_to_archive(
        file_path="/path/to/source.pdf",
        archive_folder="5_ArchivedFiles",
        log_callback=print,
    )
"""

import os
import shutil


def move_to_archive(file_path: str, archive_folder: str, log_callback=None) -> bool:
    """Di chuyển một file đã xử lý xong vào thư mục lưu trữ.

    Args:
        file_path      : Đường dẫn đầy đủ tới file nguồn cần di chuyển.
        archive_folder : Đường dẫn tới thư mục lưu trữ đích.
        log_callback   : Hàm nhận chuỗi log (tuỳ chọn). Nếu None, dùng print().

    Returns:
        True nếu di chuyển thành công, False nếu có lỗi.
    """
    def _log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    try:
        os.makedirs(archive_folder, exist_ok=True)

        filename = os.path.basename(file_path)
        dest_path = os.path.join(archive_folder, filename)

        # Xử lý xung đột tên: nếu file đã tồn tại ở đích, thêm số đếm
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(archive_folder, f"{base}_{counter}{ext}")
                counter += 1

        shutil.move(file_path, dest_path)
        _log(f"   -> 📦 [Archived] {filename} → {archive_folder}")
        return True

    except Exception as e:
        _log(f"   -> ⚠️ [Archive Error] Không thể di chuyển '{os.path.basename(file_path)}': {e}")
        return False
