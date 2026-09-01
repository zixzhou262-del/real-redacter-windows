from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path

from offline_anonymizer.anonymizer.token_registry import TokenRegistry
from offline_anonymizer.core.document import Document, DocumentNode, TokenSpan
from offline_anonymizer.security.mapping_crypto import write_mapping


@dataclass
class HtmlRenderResult:
    html: str
    mapping: dict[str, dict[str, str]]


class HtmlRenderer:
    """Render anonymized document models into a local HTML review page."""

    def render(
        self,
        document: Document,
        registry: TokenRegistry,
        mapping_filename: str = "token_mapping.json",
    ) -> HtmlRenderResult:
        mapping = self._build_mapping(registry)
        body = "\n".join(self._render_node(node, registry) for node in document.blocks)
        html = self._page(document, body, mapping_filename)
        return HtmlRenderResult(html=html, mapping=mapping)

    def write(
        self,
        document: Document,
        registry: TokenRegistry,
        html_path: str | Path,
        mapping_path: str | Path,
    ) -> HtmlRenderResult:
        html_output = Path(html_path)
        mapping_output = Path(mapping_path)
        result = self.render(document, registry, mapping_output.name)
        html_output.write_text(result.html, encoding="utf-8")
        write_mapping(mapping_output, result.mapping)
        return result

    def _render_node(self, node: DocumentNode, registry: TokenRegistry) -> str:
        if node.node_type == "heading":
            level = int(node.metadata.get("level", 1))
            level = max(1, min(level, 6))
            return f"<h{level} data-node-id=\"{escape(node.node_id)}\">{self._render_children_or_content(node, registry)}</h{level}>"
        if node.node_type == "paragraph":
            return f"<p data-node-id=\"{escape(node.node_id)}\">{self._render_children_or_content(node, registry)}</p>"
        if node.node_type == "text":
            return self._render_text_node(node, registry)
        if node.node_type == "list":
            tag = "ol" if node.metadata.get("list_type") == "ordered" else "ul"
            items = "\n".join(self._render_node(child, registry) for child in node.children)
            return f"<{tag} data-node-id=\"{escape(node.node_id)}\">\n{items}\n</{tag}>"
        if node.node_type == "list_item":
            return f"<li data-node-id=\"{escape(node.node_id)}\">{self._render_children_or_content(node, registry)}</li>"
        if node.node_type == "table":
            rows = "\n".join(self._render_node(child, registry) for child in node.children)
            return f"<table data-node-id=\"{escape(node.node_id)}\"><tbody>\n{rows}\n</tbody></table>"
        if node.node_type == "table_row":
            cells = "\n".join(self._render_node(child, registry) for child in node.children)
            return f"<tr data-node-id=\"{escape(node.node_id)}\">\n{cells}\n</tr>"
        if node.node_type == "table_cell":
            return f"<td data-node-id=\"{escape(node.node_id)}\">{self._render_children_or_content(node, registry)}</td>"
        if node.node_type == "code_block":
            return (
                f"<pre data-node-id=\"{escape(node.node_id)}\"><code>"
                f"{escape(node.content)}"
                "</code></pre>"
            )
        if node.node_type == "blank_line":
            return "<br>"
        return self._render_children_or_content(node, registry)

    def _render_children_or_content(
        self, node: DocumentNode, registry: TokenRegistry
    ) -> str:
        if node.children:
            return "".join(self._render_node(child, registry) for child in node.children)
        return escape(node.content)

    def _render_text_node(self, node: DocumentNode, registry: TokenRegistry) -> str:
        if not node.tokens:
            return escape(node.content)

        pieces: list[str] = []
        cursor = 0
        for span in sorted(node.tokens, key=lambda item: item.start):
            if span.start < cursor or span.end > len(node.content):
                continue
            pieces.append(escape(node.content[cursor : span.start]))
            pieces.append(self._render_token_anchor(node, span, registry))
            cursor = span.end
        pieces.append(escape(node.content[cursor:]))
        return "".join(pieces)

    def _render_token_anchor(
        self, node: DocumentNode, span: TokenSpan, registry: TokenRegistry
    ) -> str:
        token = registry.get_token(span.token_id)
        if token is None:
            token_type = str(span.metadata.get("token_type", "unknown"))
            label = node.content[span.start : span.end]
            missing = " data-token-missing=\"true\""
        else:
            token_type = token.token_type
            label = token.masked_value
            missing = ""
        title = f"类型：{token_type} | Token ID：{span.token_id}"

        return (
            f"<span class=\"masked-token token-{escape(token_type)}\" contenteditable=\"false\" "
            f"data-token-id=\"{escape(span.token_id)}\" "
            f"data-token-type=\"{escape(token_type)}\""
            f" title=\"{escape(title)}\""
            f"{missing}>"
            f"{escape(label)}"
            "</span>"
        )

    def _build_mapping(self, registry: TokenRegistry) -> dict[str, dict[str, str]]:
        return {
            token.token_id: {
                "type": token.token_type,
                "original": token.original_value,
                "masked": token.masked_value,
            }
            for token in registry.all_tokens()
        }

    def _page(self, document: Document, body: str, mapping_filename: str) -> str:
        return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(Path(document.source_path).name)} - 脱敏预览</title>
    <style>
      :root {{
        color-scheme: light;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      body {{
        margin: 0;
        background: #f6f7f8;
        color: #202124;
      }}
      .app-shell {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) 280px;
        min-height: 100vh;
      }}
      .document-surface {{
        max-width: 920px;
        width: min(920px, calc(100vw - 340px));
        margin: 24px auto;
        padding: 28px;
        background: #fff;
        border: 1px solid #d9dde3;
        border-radius: 8px;
        line-height: 1.75;
      }}
      .document-surface:focus {{
        outline: 2px solid #4c8bf5;
        outline-offset: 2px;
      }}
      .masked-token {{
        display: inline-block;
        padding: 1px 6px;
        border: 1px solid #8ab4f8;
        border-radius: 4px;
        background: #e8f0fe;
        color: #174ea6;
        white-space: nowrap;
        cursor: pointer;
      }}
      .masked-token.is-selected {{
        border-color: #185abc;
        background: #d2e3fc;
      }}
      .token-company {{
        border-color: #4c8bf5;
        background: #e8f0fe;
        color: #174ea6;
      }}
      .token-money {{
        border-color: #34a853;
        background: #e6f4ea;
        color: #0d652d;
      }}
      .token-number {{
        border-color: #fbbc04;
        background: #fef7e0;
        color: #7a4f01;
      }}
      .token-phone, .token-email {{
        border-color: #a142f4;
        background: #f3e8fd;
        color: #681da8;
      }}
      .token-date {{
        border-color: #00acc1;
        background: #e0f7fa;
        color: #006064;
      }}
      .token-person {{
        border-color: #ff7043;
        background: #fbe9e7;
        color: #a13d1d;
      }}
      .inspector {{
        border-left: 1px solid #d9dde3;
        background: #fff;
        padding: 18px;
      }}
      .inspector h2 {{
        margin: 0 0 14px;
        font-size: 15px;
      }}
      .field {{
        margin: 0 0 12px;
      }}
      .label {{
        display: block;
        color: #5f6368;
        font-size: 12px;
        margin-bottom: 2px;
      }}
      .value {{
        overflow-wrap: anywhere;
      }}
      .warning {{
        color: #b3261e;
      }}
      table {{
        border-collapse: collapse;
        width: 100%;
      }}
      td {{
        border: 1px solid #d9dde3;
        padding: 6px 8px;
      }}
      pre {{
        padding: 12px;
        overflow: auto;
        background: #f1f3f4;
        border-radius: 6px;
      }}
      @media (max-width: 760px) {{
        .app-shell {{
          grid-template-columns: 1fr;
        }}
        .document-surface {{
          width: calc(100vw - 32px);
          box-sizing: border-box;
          margin: 16px;
          padding: 18px;
        }}
        .inspector {{
          border-left: 0;
          border-top: 1px solid #d9dde3;
        }}
      }}
    </style>
  </head>
  <body data-mapping-src="{escape(mapping_filename)}">
    <main class="app-shell">
      <article class="document-surface" contenteditable="true" spellcheck="false">
{body}
      </article>
      <aside class="inspector" aria-live="polite">
        <h2>Token</h2>
        <p class="field"><span class="label">Token ID</span><span class="value" id="token-id">-</span></p>
        <p class="field"><span class="label">类型</span><span class="value" id="token-type">-</span></p>
        <p class="field"><span class="label">原始内容</span><span class="value" id="token-original">-</span></p>
        <p class="field"><span class="label">完整性</span><span class="value" id="token-health">未检查</span></p>
      </aside>
    </main>
    <script>
      const tokenState = {{ mapping: {{}}, protected: false }};
      async function loadTokenMapping() {{
        const source = document.body.dataset.mappingSrc;
        if (!source) return;
        try {{
          const response = await fetch(source, {{ cache: "no-store" }});
          const payload = await response.json();
          if (payload && payload.__real_redact_mapping__) {{
            tokenState.mapping = {{}};
            tokenState.protected = true;
          }} else {{
            tokenState.mapping = payload || {{}};
            tokenState.protected = false;
          }}
        }} catch (error) {{
          tokenState.mapping = {{}};
          tokenState.protected = true;
        }}
      }}
      function showToken(token) {{
        document.querySelectorAll(".masked-token.is-selected").forEach((item) => {{
          item.classList.remove("is-selected");
        }});
        token.classList.add("is-selected");
        const tokenId = token.dataset.tokenId;
        const tokenType = token.dataset.tokenType;
        const record = tokenState.mapping[tokenId] || {{}};
        document.getElementById("token-id").textContent = tokenId || "-";
        document.getElementById("token-type").textContent = tokenType || record.type || "-";
        document.getElementById("token-original").textContent = tokenState.protected
          ? "映射已保护，请在应用中恢复查看"
          : (record.original || "未加载");
      }}
      function updateTokenHealth() {{
        if (tokenState.protected) {{
          const anchors = Array.from(document.querySelectorAll(".masked-token"));
          const target = document.getElementById("token-health");
          target.classList.toggle("warning", false);
          target.textContent = `Token 锚点 ${{anchors.length}} 个；映射已保护`;
          return;
        }}
        const expected = new Set(Object.keys(tokenState.mapping));
        const anchors = Array.from(document.querySelectorAll(".masked-token"));
        const current = new Set(anchors.map((item) => item.dataset.tokenId).filter(Boolean));
        const missing = Array.from(expected).filter((tokenId) => !current.has(tokenId));
        const unknown = Array.from(current).filter((tokenId) => !expected.has(tokenId));
        const target = document.getElementById("token-health");
        target.classList.toggle("warning", missing.length > 0 || unknown.length > 0);
        if (missing.length === 0 && unknown.length === 0) {{
          target.textContent = "正常";
        }} else {{
          target.textContent = `缺失 ${{missing.length}}，未知 ${{unknown.length}}`;
        }}
      }}
      document.addEventListener("click", (event) => {{
        const token = event.target.closest(".masked-token");
        if (!token) return;
        showToken(token);
      }});
      const observer = new MutationObserver(updateTokenHealth);
      observer.observe(document.querySelector(".document-surface"), {{
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["data-token-id"]
      }});
      loadTokenMapping().then(updateTokenHealth);
    </script>
  </body>
</html>
"""
