"""Build the PDF versions of the technical report from the Markdown sources.

  pip install markdown                 # build-time only, not a dashboard dependency
  python docs/build_pdf.py             # writes docs/Intrinsic_Report_EN.pdf and docs/Intrinsic_Informe_ES.pdf

Markdown -> HTML (with the stylesheet below) -> PDF through headless Google Chrome. Set CHROME to the browser binary
if it is not at the default macOS location.
"""
import os
import pathlib
import subprocess
import sys
import tempfile

import markdown

DOCS = pathlib.Path(__file__).resolve().parent
CHROME = os.environ.get('CHROME', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
REPORTS = (('REPORT.md', 'Intrinsic_Report_EN', 'en'), ('INFORME.md', 'Intrinsic_Informe_ES', 'es'))
CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Serif:wght@300;400&display=swap');
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
body { font-family: 'IBM Plex Sans', Helvetica, Arial, sans-serif; color: #18202B; font-size: 10.2pt; line-height: 1.5; }
h1 { font-family: 'IBM Plex Serif', Georgia, serif; font-weight: 400; font-size: 25pt; margin: 0 0 4pt; letter-spacing: -.01em; }
h2 { font-size: 14pt; font-weight: 600; margin: 20pt 0 6pt; padding-top: 8pt; border-top: 1px solid #DCE2E8; color: #0E5C52; break-after: avoid; }
h3 { font-size: 11pt; font-weight: 600; margin: 12pt 0 4pt; break-after: avoid; }
p { margin: 0 0 7pt; } strong { font-weight: 600; }
blockquote { margin: 8pt 0; padding: 6pt 10pt; border-left: 3px solid #1F9E8C; background: #F2F7F6; color: #3D4855; font-size: 9.4pt; }
blockquote p { margin: 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt; font-size: 8.8pt; break-inside: avoid; }
th { text-align: left; font-weight: 600; background: #EEF2F5; border-bottom: 1px solid #C9D2DB; padding: 4pt 6pt; }
td { border-bottom: 1px solid #E6EAEE; padding: 3.5pt 6pt; vertical-align: top; }
td:not(:first-child), th:not(:first-child) { font-variant-numeric: tabular-nums; }
code { font-family: 'IBM Plex Mono', monospace; font-size: 8.6pt; background: #F1F3F5; padding: 0 3px; border-radius: 3px; }
pre { background: #0F151C; color: #DCE6EE; padding: 9pt 11pt; border-radius: 6px; font-size: 7.6pt; line-height: 1.4; overflow: hidden; break-inside: avoid; }
pre code { background: none; color: inherit; padding: 0; font-size: inherit; }
img { max-width: 100%; display: block; margin: 8pt auto 10pt; border-radius: 6px; break-inside: avoid; }
img[src$='.jpg'] { border: 1px solid #DCE2E8; }
hr { border: 0; border-top: 1px solid #DCE2E8; margin: 10pt 0; }
ul { margin: 0 0 8pt; padding-left: 16pt; } li { margin-bottom: 3pt; }
a { color: #0E5C52; text-decoration: none; }
"""


def main():
    with tempfile.TemporaryDirectory() as tmp:
        for src, out, lang in REPORTS:
            body = markdown.markdown((DOCS / src).read_text(), extensions=['tables', 'fenced_code', 'sane_lists'])
            page = pathlib.Path(tmp, out + '.html')
            page.write_text(f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'>"
                            f"<base href='{DOCS.as_uri()}/'><title>{out}</title><style>{CSS}</style></head>"
                            f"<body>{body}</body></html>")
            subprocess.run([CHROME, '--headless=new', '--disable-gpu', f'--user-data-dir={tmp}/chrome',
                            '--no-pdf-header-footer', '--virtual-time-budget=8000',
                            f'--print-to-pdf={DOCS / (out + ".pdf")}', page.as_uri()],
                           check=True, capture_output=True)
            print(f'{out}.pdf written')


if __name__ == '__main__':
    sys.exit(main())
