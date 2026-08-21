import os
import requests
from ddgs import DDGS

# --- Hằng số bộ lọc ---
BLACKLIST_DOMAINS = ['academia.edu', 'researchgate.net', 'scribd.com', 'issuu.com']
TU_KHOA_RAC = ['slide', 'presentation', 'ppt']


def _log(message, callback):
    """Gửi log ra callback (GUI) hoặc print ra terminal nếu không có callback."""
    if callback:
        callback(message)
    else:
        print(message)


def tim_kiem_pdf(tu_khoa, loai_tl='3', so_luong=10, log_callback=None):
    """
    Tìm kiếm PDF trên DuckDuckGo và trả về danh sách kết quả.

    Args:
        tu_khoa    (str): Từ khóa tìm kiếm.
        loai_tl    (str): Loại tài liệu - '1' (Nghiên cứu), '2' (Hướng dẫn), '3' (Chung).
        so_luong   (int): Số lượng kết quả tối đa cần tìm.
        log_callback (callable | None): Hàm nhận chuỗi log. Nếu None, dùng print().

    Returns:
        list[dict]: Danh sách kết quả, mỗi phần tử có 'title' và 'href'.
    """
    # Xây dựng danh sách câu lệnh tìm kiếm theo loại tài liệu
    if loai_tl == '1':
        danh_sach_cau_lenh = [
            f"{tu_khoa} thesis filetype:pdf",
            f"{tu_khoa} report filetype:pdf",
            f"{tu_khoa} research filetype:pdf",
        ]
    elif loai_tl == '2':
        danh_sach_cau_lenh = [
            f"{tu_khoa} manual filetype:pdf",
            f"{tu_khoa} guide filetype:pdf",
        ]
    else:
        danh_sach_cau_lenh = [f"{tu_khoa} filetype:pdf"]

    _log(f"🔍 Đang tung lưới tìm kiếm nhiều nhánh...", log_callback)

    ket_qua = []
    da_thay = set()

    for cau_lenh in danh_sach_cau_lenh:
        if len(ket_qua) >= so_luong:
            break

        _log(f"  -> Đang quét nhánh: '{cau_lenh}'", log_callback)

        try:
            results = DDGS().text(cau_lenh, max_results=15)
        except Exception:
            _log("     [!] Nhánh này không có kết quả. Đang chuyển nhánh tiếp theo...", log_callback)
            continue

        if not results:
            continue

        for res in results:
            url = res['href'].lower()
            title = res['title'].lower()

            if url in da_thay:
                continue
            if any(domain in url for domain in BLACKLIST_DOMAINS):
                continue
            if loai_tl in ['1', '2'] and any(rac in title or rac in url for rac in TU_KHOA_RAC):
                continue

            ket_qua.append(res)
            da_thay.add(url)

            if len(ket_qua) == so_luong:
                break

    _log("-" * 50, log_callback)

    if not ket_qua:
        _log("Không tìm thấy tài liệu nào phù hợp trên tất cả các nhánh.", log_callback)
    else:
        _log(f"✅ Tìm thấy {len(ket_qua)} kết quả.", log_callback)

    return ket_qua


def tai_pdf(ket_qua, danh_sach_chon, thu_muc_luu="1_TaiLieu_Tho", log_callback=None):
    """
    Tải các file PDF từ danh sách kết quả theo chỉ số người dùng chọn.

    Args:
        ket_qua        (list[dict]): Danh sách kết quả từ tim_kiem_pdf().
        danh_sach_chon (list[int]) : Danh sách chỉ số (1-based) các file muốn tải.
        thu_muc_luu    (str)       : Thư mục lưu file PDF.
        log_callback   (callable | None): Hàm nhận chuỗi log. Nếu None, dùng print().
    """
    os.makedirs(thu_muc_luu, exist_ok=True)

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/114.0.0.0 Safari/537.36'
        )
    }

    for so_thu_tu in danh_sach_chon:
        if not (1 <= so_thu_tu <= len(ket_qua)):
            _log(f"  -> ⚠️ Chỉ số {so_thu_tu} không hợp lệ. Bỏ qua.", log_callback)
            continue

        muc_tieu = ket_qua[so_thu_tu - 1]
        url = muc_tieu['href']
        ten_file = "".join(c for c in muc_tieu['title'] if c.isalnum() or c in (' ', '_')).rstrip() + ".pdf"
        duong_dan_luu = os.path.join(thu_muc_luu, ten_file)

        _log(f"⏳ Đang tải: {ten_file} ...", log_callback)
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '').lower()
            if 'pdf' not in content_type and 'application/octet-stream' not in content_type:
                _log(f"  -> ❌ Bị lừa: Đây là trang web chặn tải ngầm ({content_type})!", log_callback)
                continue

            if not response.content.startswith(b'%PDF'):
                _log("  -> ❌ File hỏng: Cấu trúc lõi không phải là PDF chuẩn. Bỏ qua!", log_callback)
                continue

            size_kb = len(response.content) / 1024
            if size_kb < 50:
                _log(f"  -> ⚠️ Cảnh báo: File chuẩn PDF nhưng dung lượng quá nhỏ ({size_kb:.1f} KB).", log_callback)

            with open(duong_dan_luu, 'wb') as f:
                f.write(response.content)

            _log(f"  -> ✅ Tải thành công! ({size_kb:.1f} KB) → {duong_dan_luu}", log_callback)

        except Exception as e:
            _log(f"  -> ❌ Lỗi khi tải: {e}", log_callback)


# --- Entry point cho terminal (hoạt động độc lập, không phụ thuộc GUI) ---
if __name__ == "__main__":
    tu_khoa_can_tim = input("Nhập chủ đề bạn muốn tìm (VD: Java GUI, SQL Database): ").strip()
    if not tu_khoa_can_tim:
        print("Không có từ khóa. Thoát.")
        exit()

    print("\n📚 BẠN MUỐN TÌM LOẠI TÀI LIỆU NÀO?")
    print("  [1] Nghiên cứu chuyên sâu (Sách, Luận văn, Báo cáo)")
    print("  [2] Hướng dẫn thực hành (Manual, Guide, Tutorial)")
    print("  [3] Tìm kiếm chung chung (Chấp nhận mọi loại)")
    loai = input("\n👉 Lựa chọn của bạn (1/2/3): ").strip()

    ket_qua = tim_kiem_pdf(tu_khoa_can_tim, loai_tl=loai)

    if not ket_qua:
        exit()

    for i, res in enumerate(ket_qua):
        print(f"[{i + 1}] {res['title']}")
        print(f"    Link: {res['href']}\n")

    lua_chon = input("👉 Nhập số thứ tự file muốn tải (vd: 1,3) hoặc Enter để hủy: ")
    if not lua_chon.strip():
        print("Đã hủy tải file.")
        exit()

    danh_sach_chon = [int(x.strip()) for x in lua_chon.split(',') if x.strip().isdigit()]
    tai_pdf(ket_qua, danh_sach_chon)