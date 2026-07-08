"""HTML sanitization utility for XSS prevention."""

import html


def sanitize_html(text: str) -> str:
    """将HTML/JS标签转义为实体，防止XSS存储型漏洞。
    
    替换: < → &lt;  > → &gt;  & → &amp;  " → &quot;  ' → &#x27;
    如果输入为 None 或非字符串，原样返回。
    """
    if text is None:
        return None
    if not isinstance(text, str):
        return text
    return html.escape(text, quote=True)
