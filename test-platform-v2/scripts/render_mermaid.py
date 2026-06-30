"""Extract Mermaid blocks from a Markdown file and render each as PNG.

Usage: python scripts/render_mermaid.py [markdown_file] [output_dir]
Default: docs/CamelTv测试平台-完整PRD.md → docs/diagrams/
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HTML_TEMPLATE = """<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{ startOnLoad: true, theme: 'default' }});</script>
<style>
  body {{ margin: 20px; background: white; }}
  .mermaid {{ display: flex; justify-content: center; }}
</style>
</head><body>
<div class="mermaid">
{content}
</div>
</body></html>"""


def extract_mermaid_blocks(text: str) -> list[tuple[int, str, str]]:
    """Return list of (index, diagram_type, content) for each ```mermaid block."""
    blocks = []
    pattern = re.compile(r'```mermaid\s*\n(.*?)```', re.DOTALL)
    for i, match in enumerate(pattern.finditer(text)):
        content = match.group(1).strip()
        # Extract diagram type from first line
        first_line = content.split('\n')[0]
        dtype = first_line.strip() if first_line else 'graph'
        blocks.append((i, dtype, content))
    return blocks


def render_diagrams(prd_path: str, output_dir: str) -> list[str]:
    """Render all Mermaid blocks in a markdown file to PNGs. Returns list of saved paths."""
    from playwright.sync_api import sync_playwright

    text = Path(prd_path).read_text(encoding="utf-8")
    blocks = extract_mermaid_blocks(text)

    if not blocks:
        print("No Mermaid blocks found.")
        return []

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    saved = []
    # Type labels for filenames
    type_short = {
        'graph': 'arch', 'flowchart': 'flow', 'sequenceDiagram': 'seq',
        'stateDiagram': 'state', 'erDiagram': 'er', 'timeline': 'timeline',
        'classDiagram': 'class',
    }

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for idx, dtype, content in blocks:
            filename = f"{idx:02d}-{type_short.get(dtype.split()[0], 'diagram')}-{dtype.replace(' ', '-').replace('_', '-')}.png"
            filepath = out / filename

            html = HTML_TEMPLATE.format(content=content)
            page = browser.new_page(viewport={"width": 1200, "height": 900})
            page.set_content(html)

            # Wait for mermaid to render
            try:
                page.wait_for_selector("svg", timeout=15000)
                page.wait_for_timeout(1000)  # let animations settle
            except Exception:
                print(f"  [{filename}] Warning: no SVG rendered, capturing anyway")

            # Screenshot just the mermaid div
            el = page.query_selector(".mermaid")
            if el:
                el.screenshot(path=str(filepath))
                print(f"  [OK] {filename}")
                saved.append(str(filepath))
            page.close()

        browser.close()

    print(f"\nRendered {len(saved)}/{len(blocks)} diagrams to {output_dir}")
    return saved


if __name__ == "__main__":
    prd = sys.argv[1] if len(sys.argv) > 1 else "docs/CamelTv测试平台-完整PRD.md"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "docs/diagrams"
    render_diagrams(prd, out_dir)
