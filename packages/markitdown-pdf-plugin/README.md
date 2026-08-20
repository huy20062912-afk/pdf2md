# markitdown-pdf-plugin

Một plugin đơn giản cho [MarkItDown](https://github.com/microsoft/markitdown) để chuyển đổi file **PDF** sang **Markdown**.

## Cài đặt

```bash
pip install -e .
```

## Sử dụng

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=True)
result = md.convert("file.pdf")
print(result.text_content)
```

Hoặc qua CLI:

```bash
markitdown --use-plugins file.pdf
```

> **Lưu ý**: Plugin chỉ hoạt động với PDF có text thực. PDF dạng ảnh scan sẽ không extract được text.
