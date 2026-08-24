import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()

# --- Constants ---
MODEL_NAME = "gemini-3.5-flash-lite"
MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds between retries on rate-limit errors
MAP_SLEEP = 4     # seconds between each file summarization (free-tier: 15 RPM)


def _get_client():
    """Lazy-initialize the Gemini client so import never crashes."""
    from google import genai  # same SDK as ai_summary.py

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY không được tìm thấy. "
            "Hãy thêm vào file .env hoặc biến môi trường."
        )
    return genai.Client(api_key=api_key)


def _generate_with_retry(client, prompt: str, log) -> str:
    """
    Call the Gemini API with simple retry logic for transient rate-limit errors.
    Returns the response text, or raises on permanent failure.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME, contents=prompt
            )
            return response.text
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = any(
                kw in error_str for kw in ("429", "resource_exhausted", "quota", "rate")
            )
            if is_rate_limit and attempt < MAX_RETRIES:
                wait = RETRY_DELAY * attempt
                log(
                    f"   ⚠️ Rate limit hit (lần {attempt}/{MAX_RETRIES}). "
                    f"Chờ {wait}s rồi thử lại..."
                )
                time.sleep(wait)
            else:
                raise


def summarize_single_file(file_path, client=None) -> str:
    """
    Giai đoạn MAP: Đọc và tóm tắt một file Markdown đơn lẻ.
    Nhận client tuỳ chọn để tái sử dụng kết nối.
    """
    if client is None:
        client = _get_client()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            return "[File trống — bỏ qua]"

        prompt = (
            "Hãy đọc tài liệu sau và tóm tắt chi tiết thành các gạch đầu dòng ngắn gọn. "
            "Tập trung vào các luận điểm chính, phương pháp và kết luận:\n\n"
            f"{content}"
        )
        return _generate_with_retry(client, prompt, print)
    except Exception as e:
        return f"[Lỗi trích xuất file {file_path}: {e}]"


def create_master_summary(input_dir: str, output_filepath: str, log_callback=None):
    """
    Luồng Map-Reduce: tóm tắt toàn bộ file .md trong input_dir,
    rồi tổng hợp thành một Master Summary tại output_filepath.

    Args:
        input_dir       : Thư mục chứa các file .md đầu vào.
        output_filepath : Đường dẫn đầy đủ đến file đầu ra (sẽ được tạo tự động).
        log_callback    : Hàm nhận chuỗi log (thread-safe với GUI).
    """
    def log(message: str):
        if log_callback:
            log_callback(message)
        else:
            print(message)

    # ── 0. Khởi tạo client (sẽ báo lỗi ngay nếu không có API key) ──
    try:
        client = _get_client()
    except EnvironmentError as e:
        log(f"❌ Lỗi cấu hình: {e}")
        return

    # ── 1. Quét file .md ──
    md_files = sorted(Path(input_dir).glob("*.md"))
    if not md_files:
        log("⚠️ Không tìm thấy file .md nào trong thư mục này.")
        return

    # ── 2. Đảm bảo thư mục xuất tồn tại ──
    output_path = Path(output_filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── 3. MAP: Tóm tắt từng file ──
    log(f"🔍 Bắt đầu phân tích {len(md_files)} file tài liệu...")
    all_summaries = []

    for i, file_path in enumerate(md_files, 1):
        log(f"⏳ Đang xử lý ({i}/{len(md_files)}): {file_path.name}")
        file_summary = summarize_single_file(file_path, client)
        all_summaries.append(
            f"### Tóm tắt của: {file_path.name}\n{file_summary}\n"
        )

        # Rate-limit guard (free tier: 15 RPM → ~4s/request)
        if i < len(md_files):
            time.sleep(MAP_SLEEP)

    # ── 4. Lưu kết quả trung gian (MAP stage) để tránh mất dữ liệu ──
    partial_path = output_path.parent / "_partial_summaries.md"
    try:
        with open(partial_path, "w", encoding="utf-8") as f:
            f.write("# Kết quả trung gian (MAP stage)\n\n")
            f.write("\n".join(all_summaries))
        log(f"💾 Đã lưu tóm tắt trung gian tại: {partial_path}")
    except Exception as e:
        log(f"⚠️ Không thể lưu tóm tắt trung gian: {e}")

    # ── 5. REDUCE: Tổng hợp Master Summary ──
    log("\n🧠 Đang tổng hợp Master Summary từ các kết quả...")
    combined_text = "\n".join(all_summaries)

    master_prompt = (
        "Dựa trên các bản tóm tắt của nhiều tài liệu dưới đây, "
        "hãy viết một báo cáo tổng hợp (Master Summary) cực kỳ chi tiết và chuyên nghiệp. "
        "Hãy phân tích các điểm chung, đối chiếu sự khác biệt, và đưa ra kết luận tổng quan. "
        "Định dạng đầu ra bằng Markdown chuẩn:\n\n"
        f"{combined_text}"
    )

    try:
        master_text = _generate_with_retry(client, master_prompt, log)

        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(master_text)

        log(f"\n✅ Hoàn tất! Báo cáo tổng hợp đã được lưu tại:\n📂 {output_filepath}")

        # Clean up partial file on success
        try:
            partial_path.unlink()
        except Exception:
            pass

    except Exception as e:
        log(
            f"⚠️ Lỗi khi tạo Master Summary: {e}\n"
            f"   📄 Kết quả trung gian vẫn được lưu tại: {partial_path}"
        )