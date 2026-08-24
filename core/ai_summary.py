import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Cảnh báo: Không tìm thấy GEMINI_API_KEY trong file .env")

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-3.5-flash-lite"


def summarize_paper(title: str, abstract_text: str, log_callback):
    """
    Tóm tắt bài báo bằng AI (blocking — gọi từ background thread).

    Args:
        title         (str)     : Tiêu đề bài báo (fallback khi không có abstract).
        abstract_text (str)     : Abstract / mô tả bài báo.
        log_callback  (callable): Nhận chuỗi log (thread-safe với GUI).
    """
    def _log(msg):
        if log_callback:
            log_callback(msg)

    content = abstract_text.strip() if abstract_text and abstract_text.strip() else title.strip()
    if not content:
        _log("   ✨ AI: Không có đủ thông tin để tóm tắt bài báo này.")
        return

    # Giới hạn 600 ký tự để tiết kiệm token
    MAX_CHARS = 600
    if len(content) > MAX_CHARS:
        content = content[:MAX_CHARS].rsplit(' ', 1)[0] + "..."

    try:
        prompt = (
            "Dịch và tóm tắt cốt lõi của nghiên cứu sau sang tiếng Việt "
            "một cách chuyên nghiệp trong tối đa 2 câu ngắn gọn: "
            + content
        )
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        _log(f"   ✨ AI: {response.text.strip()}")

    except Exception as e:
        _log(f"   ⚠️ Lỗi kết nối AI: {e}")

    finally:
        time.sleep(1)  # Tránh vượt giới hạn RPM