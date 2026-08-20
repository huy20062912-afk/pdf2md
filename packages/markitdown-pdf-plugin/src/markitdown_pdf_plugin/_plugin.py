from typing import BinaryIO, Any
from pypdf import PdfReader

from markitdown import (
    MarkItDown,
    DocumentConverter,
    DocumentConverterResult,
    StreamInfo,
)

# Phiên bản plugin interface — hiện chỉ hỗ trợ version 1
__plugin_interface_version__ = 1

ACCEPTED_MIME_TYPE_PREFIXES = [
    "application/pdf",
]

ACCEPTED_FILE_EXTENSIONS = [".pdf"]


def register_converters(markitdown: MarkItDown, **kwargs: Any) -> None:
    """
    Được gọi tự động khi MarkItDown khởi tạo với enable_plugins=True.
    Đăng ký PdfConverter vào hệ thống.
    """
    markitdown.register_converter(PdfConverter())


class PdfConverter(DocumentConverter):
    """
    Chuyển đổi file PDF sang Markdown bằng thư viện pypdf.
    Lưu ý: chỉ hoạt động với PDF có text thực (không phải ảnh scan).
    """

    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> bool:
        """Trả về True nếu file là PDF (dựa trên extension hoặc MIME type)."""
        mimetype = (stream_info.mimetype or "").lower()
        extension = (stream_info.extension or "").lower()

        if extension in ACCEPTED_FILE_EXTENSIONS:
            return True

        for prefix in ACCEPTED_MIME_TYPE_PREFIXES:
            if mimetype.startswith(prefix):
                return True

        return False

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,
    ) -> DocumentConverterResult:
        """
        Đọc từng trang PDF và ghép thành nội dung Markdown.
        Mỗi trang được phân cách bằng dòng ngang (---).
        """
        reader = PdfReader(file_stream)

        # Lấy tiêu đề từ metadata nếu có
        title = None
        if reader.metadata and reader.metadata.title:
            title = reader.metadata.title

        # Đọc text từng trang và ghép lại
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                pages_text.append(f"## Trang {i + 1}\n\n{text.strip()}")

        # Nối các trang, phân cách bằng dấu ---
        markdown = "\n\n---\n\n".join(pages_text)

        return DocumentConverterResult(
            title=title,
            markdown=markdown,
        )
