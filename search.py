import os
import requests
from ddgs import DDGS

def tim_kiem_va_tai_pdf(tu_khoa, thu_muc_luu="1_TaiLieu_Tho", so_luong=10):
    if not os.path.exists(thu_muc_luu):
        os.makedirs(thu_muc_luu)
        
    print("\n📚 BẠN MUỐN TÌM LOẠI TÀI LIỆU NÀO?")
    print("  [1] Nghiên cứu chuyên sâu (Sách, Luận văn, Báo cáo)")
    print("  [2] Hướng dẫn thực hành (Manual, Guide, Tutorial)")
    print("  [3] Tìm kiếm chung chung (Chấp nhận mọi loại)")
    
    loai_tl = input("\n👉 Lựa chọn của bạn (1/2/3): ").strip()

    danh_sach_cau_lenh = []
    if loai_tl == '1':
        danh_sach_cau_lenh = [
            f"{tu_khoa} thesis filetype:pdf", 
            f"{tu_khoa} report filetype:pdf",
            f"{tu_khoa} research filetype:pdf"
        ]
    elif loai_tl == '2':
        danh_sach_cau_lenh = [
            f"{tu_khoa} manual filetype:pdf", 
            f"{tu_khoa} guide filetype:pdf"
        ]
    else:
        danh_sach_cau_lenh = [f"{tu_khoa} filetype:pdf"]

    print(f"\n🔍 Đang tung lưới tìm kiếm nhiều nhánh...\n")
    
    ket_qua = []
    da_thay = set() 
    blacklist_domains = ['academia.edu', 'researchgate.net', 'scribd.com', 'issuu.com']
    tu_khoa_rac = ['slide', 'presentation', 'ppt']

    # Vòng lặp duyệt qua từng nhánh
    for cau_lenh in danh_sach_cau_lenh:
        if len(ket_qua) >= so_luong:
            break 
            
        print(f"  -> Đang quét nhánh: '{cau_lenh}'")
        
        # ĐẶT BẪY LỖI CỤC BỘ Ở ĐÂY
        try:
            results = DDGS().text(cau_lenh, max_results=15)
        except Exception as e:
            print(f"     [!] Nhánh này không có kết quả. Đang chuyển nhánh tiếp theo...")
            continue # Bỏ qua nhánh này, chạy tiếp nhánh sau
            
        if not results:
            continue
            
        for res in results:
            url = res['href'].lower()
            title = res['title'].lower()
            
            if url in da_thay: 
                continue 
            if any(domain in url for domain in blacklist_domains): 
                continue 
            if loai_tl in ['1', '2'] and any(rac in title or rac in url for rac in tu_khoa_rac):
                continue 
                
            ket_qua.append(res)
            da_thay.add(url)
            
            if len(ket_qua) == so_luong:
                break

    print("-" * 50)
    if not ket_qua:
        print("Không tìm thấy tài liệu nào phù hợp trên tất cả các nhánh.")
        return
        
    for i, res in enumerate(ket_qua):
        print(f"[{i + 1}] {res['title']}")
        print(f"    Link: {res['href']}\n")


    lua_chon = input("👉 Nhập số thứ tự file muốn tải (vd: 1,3) hoặc Enter để hủy: ")
    
    if not lua_chon.strip():
        print("Đã hủy tải file.")
        return
        
    danh_sach_chon = [int(x.strip()) for x in lua_chon.split(',') if x.strip().isdigit()]
    
    for so_thu_tu in danh_sach_chon:
        if 1 <= so_thu_tu <= len(ket_qua):
            mục_tiêu = ket_qua[so_thu_tu - 1]
            url = mục_tiêu['href']
            ten_file = "".join(c for c in mục_tiêu['title'] if c.isalnum() or c in (' ', '_')).rstrip() + ".pdf"
            duong_dan_luu = os.path.join(thu_muc_luu, ten_file)
            
            print(f"⏳ Đang tải: {ten_file} ...")
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                content_type = response.headers.get('Content-Type', '').lower()
                if 'pdf' not in content_type and 'application/octet-stream' not in content_type:
                    print(f"  -> ❌ Bị lừa: Đây là trang web chặn tải ngầm ({content_type})!")
                    continue
                
                if not response.content.startswith(b'%PDF'):
                    print(f"  -> ❌ File hỏng: Cấu trúc lõi không phải là PDF chuẩn. Bỏ qua!")
                    continue
                
                size_kb = len(response.content) / 1024
                if size_kb < 50:
                    print(f"  -> ⚠️ Cảnh báo: File chuẩn PDF nhưng dung lượng quá nhỏ ({size_kb:.1f} KB).")
                
                with open(duong_dan_luu, 'wb') as f:
                    f.write(response.content)
                print(f"  -> ✅ Tải thành công! ({size_kb:.1f} KB)")
                
            except Exception as e:
                print(f"  -> ❌ Lỗi khi tải: {e}")

if __name__ == "__main__":
    tu_khoa_can_tim = input("Nhập chủ đề bạn muốn tìm (VD: Java GUI, SQL Database): ")
    if tu_khoa_can_tim.strip():
        tim_kiem_va_tai_pdf(tu_khoa_can_tim)