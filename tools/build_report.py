"""Минимальный Markdown → HTML для печатной версии отчёта, без зависимостей."""
import html
from pathlib import Path
import re


def inline(text):
    text = html.escape(text)
    text = re.sub(r"!\[([^]]*)\]\(([^)]+)\)",
                  r'<figure><img src="\2" alt="\1"><figcaption>\1</figcaption></figure>', text)
    text = re.sub(r"\[([^]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", text)


def main():
    root = Path(__file__).resolve().parents[1]
    lines = (root / "REPORT.md").read_text(encoding="utf-8").splitlines()
    result = []
    code = False
    table = False
    for line in lines:
        if line.startswith("```"):
            result.append("</code></pre>" if code else "<pre><code>")
            code = not code
            continue
        if code:
            result.append(html.escape(line) + "\n")
            continue
        if table and not line.startswith("|"):
            result.append("</tbody></table>")
            table = False
        if line.startswith("|"):
            cells = line.strip("|").split("|")
            if all(re.fullmatch(r"[\s:–-]+", cell) for cell in cells):
                continue
            tag = "td" if table else "th"
            if not table:
                result.append("<table><tbody>")
                table = True
            result.append("<tr>" + "".join(
                f"<{tag}>{inline(cell.strip())}</{tag}>" for cell in cells) + "</tr>")
        elif match := re.match(r"^(#{1,6}) (.+)", line):
            level = len(match[1])
            result.append(f"<h{level}>{inline(match[2])}</h{level}>")
        elif line == "---":
            result.append('<hr class="pagebreak">')
        elif line.strip():
            result.append("<p>" + inline(line) + "</p>")
    if table:
        result.append("</tbody></table>")
    document = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Отчёт — RasterLab</title>
<style>
body{font:16px/1.55 Georgia,serif;max-width:1060px;margin:40px auto;padding:0 30px;color:#18212f}
h1,h2,h3{font-family:Arial,sans-serif;line-height:1.25;break-after:avoid}
h1{margin-top:42px} h2{margin-top:30px} h3{margin-top:24px}
table{border-collapse:collapse;width:100%;font-size:14px;margin:20px 0}
th,td{border:1px solid #b6c3d1;padding:8px;text-align:left} th{background:#eaf0f6}
tr,figure{break-inside:avoid} img{max-width:100%;height:auto}
figure{display:inline-block;margin:12px 0;padding:12px;background:#f1f5f9}
figcaption{font:13px Arial,sans-serif;color:#526175;margin-top:6px}
pre{overflow:auto;background:#eef2f6;padding:15px;font-size:13px;white-space:pre-wrap}
code{font-family:Consolas,monospace} a{color:#185ba5}
@media print{body{margin:0;padding:0;font-size:11pt;max-width:none}
@page{size:A4;margin:20mm} .pagebreak{break-after:page;visibility:hidden}
table{font-size:9pt} pre{font-size:9pt} figure{padding:4px} img{max-height:70mm}}
</style></head><body>""" + "\n".join(result) + "</body></html>"
    (root / "REPORT.html").write_text(document, encoding="utf-8")
    print("REPORT.html created")


if __name__ == "__main__":
    main()
