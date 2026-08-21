import os
import xml.etree.ElementTree as ET
import requests
from ddgs import DDGS

# --- Hằng số bộ lọc ---
BLACKLIST_DOMAINS = ['academia.edu', 'researchgate.net', 'scribd.com', 'issuu.com']
TU_KHOA_RAC = ['slide', 'presentation', 'ppt']
# DDGS may switch its default provider between releases.  Prefer the provider
# this feature advertises, then try alternatives only when it is unavailable.
SEARCH_BACKENDS = ('duckduckgo', 'bing', 'brave')
REQUEST_TIMEOUT = 20
SEARXNG_URL = os.getenv('SEARXNG_URL', '').rstrip('/')

SEARCH_SOURCES = {
    'general': 'General PDFs (DDGS → SearXNG)',
    'research': 'Research papers (Semantic Scholar → arXiv → OpenAIRE)',
    'biomedical': 'Biomedical research (Europe PMC → Semantic Scholar)',
    'ddgs': 'General PDFs (DDGS)',
    'semantic_scholar': 'Research papers (Semantic Scholar)',
    'arxiv': 'Computer Science / AI / Math (arXiv)',
    'openaire': 'Open-access research (OpenAIRE)',
    'europe_pmc': 'Biomedical research (Europe PMC)',
    'searxng': 'General web (self-hosted SearXNG)',
}


def _log(message, callback):
    """Gửi log ra callback (GUI) hoặc print ra terminal nếu không có callback."""
    if callback:
        callback(message)
    else:
        print(message)


def _search_text(query, max_results, log_callback):
    """Search with a predictable provider order and report connection errors."""
    errors = []

    for backend in SEARCH_BACKENDS:
        try:
            return DDGS().text(query, max_results=max_results, backend=backend)
        except Exception as error:
            errors.append(f"{backend}: {error}")

    _log(
        "     [!] Không thể kết nối tới công cụ tìm kiếm. "
        "Hãy kiểm tra kết nối Internet hoặc DNS rồi thử lại.",
        log_callback,
    )
    for error in errors:
        _log(f"         Chi tiết: {error}", log_callback)
    return None


def _result(title, href, source, has_pdf=False, description=''):
    """Create the result shape shared by every provider and the GUI."""
    return {
        'title': (title or 'Untitled document').strip(),
        'href': href or '',
        'source': source,
        'has_pdf': has_pdf,
        'description': description or '',
    }


def _looks_like_pdf(url):
    """Return True only when a web-search URL visibly targets a PDF file."""
    return url.lower().split('?', maxsplit=1)[0].endswith('.pdf')


def _deduplicate(results, limit):
    """Discard incomplete results and duplicates by URL or normalized title."""
    unique_results = []
    seen_urls = set()
    seen_titles = set()

    for result in results:
        url = result.get('href', '').strip()
        title = ' '.join(result.get('title', '').lower().split())
        if not url or url.lower() in seen_urls or title in seen_titles:
            continue
        unique_results.append(result)
        seen_urls.add(url.lower())
        seen_titles.add(title)
        if len(unique_results) >= limit:
            break

    return unique_results


def _get_json(url, params, provider, log_callback):
    """Fetch JSON from an official research API with a useful error message."""
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        _log(f"     [!] {provider} không phản hồi: {error}", log_callback)
        return None


def _search_ddgs(tu_khoa, loai_tl, so_luong, log_callback):
    """Search the general web through DDGS, preserving the original behaviour."""
    if loai_tl == '1':
        queries = [
            f"{tu_khoa} thesis filetype:pdf",
            f"{tu_khoa} report filetype:pdf",
            f"{tu_khoa} research filetype:pdf",
        ]
    elif loai_tl == '2':
        queries = [
            f"{tu_khoa} manual filetype:pdf",
            f"{tu_khoa} guide filetype:pdf",
        ]
    else:
        queries = [f"{tu_khoa} filetype:pdf"]

    results = []
    for query in queries:
        if len(results) >= so_luong:
            break

        _log(f"  -> Đang quét: '{query}'", log_callback)
        provider_results = _search_text(query, max_results=15, log_callback=log_callback)
        if provider_results is None:
            break

        for item in provider_results:
            href = item.get('href', '')
            title = item.get('title', '')
            lowered = f"{title} {href}".lower()
            if any(domain in href.lower() for domain in BLACKLIST_DOMAINS):
                continue
            if loai_tl in ('1', '2') and any(word in lowered for word in TU_KHOA_RAC):
                continue
            results.append(_result(
                title,
                href,
                'DDGS',
                has_pdf=_looks_like_pdf(href),
                description=item.get('body', ''),
            ))

    return _deduplicate(results, so_luong)


def _search_semantic_scholar(tu_khoa, so_luong, log_callback):
    """Search Semantic Scholar and prefer its declared open-access PDF URL."""
    _log("  -> Đang tìm trên Semantic Scholar...", log_callback)
    data = _get_json(
        'https://api.semanticscholar.org/graph/v1/paper/search',
        {
            'query': tu_khoa,
            'limit': so_luong,
            'fields': 'title,url,abstract,openAccessPdf',
        },
        'Semantic Scholar',
        log_callback,
    )
    if not data:
        return []

    results = []
    for paper in data.get('data', []):
        pdf_url = (paper.get('openAccessPdf') or {}).get('url')
        results.append(_result(
            paper.get('title'),
            pdf_url or paper.get('url'),
            'Semantic Scholar',
            has_pdf=bool(pdf_url),
            description=paper.get('abstract', ''),
        ))
    return _deduplicate(results, so_luong)


def _search_arxiv(tu_khoa, so_luong, log_callback):
    """Search arXiv's public Atom API and return its canonical PDF links."""
    _log("  -> Đang tìm trên arXiv...", log_callback)
    try:
        response = requests.get(
            'https://export.arxiv.org/api/query',
            params={
                'search_query': f'all:"{tu_khoa}"',
                'start': 0,
                'max_results': so_luong,
                'sortBy': 'relevance',
                'sortOrder': 'descending',
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except (requests.RequestException, ET.ParseError) as error:
        _log(f"     [!] arXiv không phản hồi: {error}", log_callback)
        return []

    namespace = {'atom': 'http://www.w3.org/2005/Atom'}
    results = []
    for entry in root.findall('atom:entry', namespace):
        title = entry.findtext('atom:title', default='', namespaces=namespace)
        summary = entry.findtext('atom:summary', default='', namespaces=namespace)
        pdf_url = next(
            (
                link.get('href') for link in entry.findall('atom:link', namespace)
                if link.get('type') == 'application/pdf'
            ),
            '',
        )
        results.append(_result(title, pdf_url, 'arXiv', has_pdf=bool(pdf_url), description=summary))
    return _deduplicate(results, so_luong)


def _search_openaire(tu_khoa, so_luong, log_callback):
    """Search OpenAIRE's open-access research-product index."""
    _log("  -> Đang tìm trên OpenAIRE...", log_callback)
    data = _get_json(
        'https://api.openaire.eu/graph/v3/research-products',
        {
            'search': tu_khoa,
            'type': 'publication',
            'pageSize': so_luong,
        },
        'OpenAIRE',
        log_callback,
    )
    if not data:
        return []

    results = []
    for product in data.get('results', []):
        urls = [
            url for instance in product.get('instances', [])
            for url in instance.get('urls', [])
        ]
        pdf_url = next((url for url in urls if url.lower().split('?')[0].endswith('.pdf')), '')
        href = pdf_url or next(iter(urls), '')
        results.append(_result(
            product.get('mainTitle'),
            href,
            'OpenAIRE',
            has_pdf=bool(pdf_url),
            description=' '.join((product.get('descriptions') or [])[:1]),
        ))
    return _deduplicate(results, so_luong)


def _search_europe_pmc(tu_khoa, so_luong, log_callback):
    """Search Europe PMC and use direct PDF links only when they are supplied."""
    _log("  -> Đang tìm trên Europe PMC...", log_callback)
    data = _get_json(
        'https://www.ebi.ac.uk/europepmc/webservices/rest/search',
        {
            'query': tu_khoa,
            'format': 'json',
            'resultType': 'core',
            'pageSize': so_luong,
        },
        'Europe PMC',
        log_callback,
    )
    if not data:
        return []

    results = []
    for article in data.get('resultList', {}).get('result', []):
        links = (article.get('fullTextUrlList') or {}).get('fullTextUrl', [])
        pdf_url = next(
            (link.get('url', '') for link in links if link.get('documentStyle', '').lower() == 'pdf'),
            '',
        )
        source = article.get('source', '')
        article_id = article.get('id', '')
        landing_page = f"https://europepmc.org/article/{source}/{article_id}" if source and article_id else ''
        results.append(_result(
            article.get('title'),
            pdf_url or landing_page,
            'Europe PMC',
            has_pdf=bool(pdf_url),
            description=article.get('abstractText', ''),
        ))
    return _deduplicate(results, so_luong)


def _search_searxng(tu_khoa, so_luong, log_callback):
    """Search a locally configured SearXNG instance without adding a dependency."""
    if not SEARXNG_URL:
        _log("     [!] Chưa cấu hình SearXNG_URL cho SearXNG.", log_callback)
        return []

    _log("  -> Đang tìm trên SearXNG...", log_callback)
    data = _get_json(
        f'{SEARXNG_URL}/search',
        {'q': tu_khoa, 'format': 'json'},
        'SearXNG',
        log_callback,
    )
    if not data:
        return []

    return _deduplicate([
        _result(
            item.get('title'),
            item.get('url'),
            'SearXNG',
            has_pdf=_looks_like_pdf(item.get('url', '')),
            description=item.get('content', ''),
        )
        for item in data.get('results', [])
    ], so_luong)


def _prioritize_direct_pdfs(results, limit):
    """Show direct PDFs before metadata/landing-page results from every source."""
    direct_first = sorted(results, key=lambda result: not result.get('has_pdf', False))
    return _deduplicate(direct_first, limit)


def _search_research(tu_khoa, so_luong, log_callback):
    """Combine broad scholarly sources, preferring their direct-PDF results."""
    results = []
    for search_provider in (_search_semantic_scholar, _search_arxiv, _search_openaire):
        results.extend(search_provider(tu_khoa, so_luong, log_callback))
    return _prioritize_direct_pdfs(results, so_luong)


def _search_biomedical(tu_khoa, so_luong, log_callback):
    """Combine biomedical-first and broad scholarly sources."""
    results = _search_europe_pmc(tu_khoa, so_luong, log_callback)
    results.extend(_search_semantic_scholar(tu_khoa, so_luong, log_callback))
    return _prioritize_direct_pdfs(results, so_luong)


def _search_general(tu_khoa, loai_tl, so_luong, log_callback):
    """Use DDGS first and SearXNG only when it has not filled the result list."""
    results = _search_ddgs(tu_khoa, loai_tl, so_luong, log_callback)
    if len(results) < so_luong and SEARXNG_URL:
        results.extend(_search_searxng(tu_khoa, so_luong, log_callback))
    return _prioritize_direct_pdfs(results, so_luong)



def tim_kiem_pdf(tu_khoa, loai_tl='3', so_luong=10, log_callback=None, source='general'):
    """
    Tìm kiếm tài liệu từ một nguồn và trả về danh sách kết quả tương thích GUI.

    Args:
        tu_khoa    (str): Từ khóa tìm kiếm.
        loai_tl    (str): Loại tài liệu - '1' (Nghiên cứu), '2' (Hướng dẫn), '3' (Chung).
        so_luong   (int): Số lượng kết quả tối đa cần tìm.
        log_callback (callable | None): Hàm nhận chuỗi log. Nếu None, dùng print().
        source (str): Một khóa trong SEARCH_SOURCES. Mặc định là 'general'.

    Returns:
        list[dict]: Danh sách kết quả, mỗi phần tử có 'title' và 'href'.
    """
    source = source.lower().strip()
    search_functions = {
        'general': lambda: _search_general(tu_khoa, loai_tl, so_luong, log_callback),
        'research': lambda: _search_research(tu_khoa, so_luong, log_callback),
        'biomedical': lambda: _search_biomedical(tu_khoa, so_luong, log_callback),
        'ddgs': lambda: _search_ddgs(tu_khoa, loai_tl, so_luong, log_callback),
        'semantic_scholar': lambda: _search_semantic_scholar(tu_khoa, so_luong, log_callback),
        'arxiv': lambda: _search_arxiv(tu_khoa, so_luong, log_callback),
        'openaire': lambda: _search_openaire(tu_khoa, so_luong, log_callback),
        'europe_pmc': lambda: _search_europe_pmc(tu_khoa, so_luong, log_callback),
        'searxng': lambda: _search_searxng(tu_khoa, so_luong, log_callback),
    }
    search_function = search_functions.get(source)
    if not search_function:
        _log(f"❌ Nguồn tìm kiếm không hợp lệ: {source}", log_callback)
        return []

    _log(f"🔍 Đang tìm trên: {SEARCH_SOURCES[source]}...", log_callback)
    ket_qua = search_function()

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
