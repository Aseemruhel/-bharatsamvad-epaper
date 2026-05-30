"""
Bharat Samvad — OG/Twitter Card patcher for existing article files.

Adds Open Graph + Twitter Card meta tags into <head> of every
bharatsamvad-*.html file in the current folder, so X/WhatsApp/etc. show
inline link previews. Safe to re-run: skips files already patched.

Usage:
    python add_og_tags.py
"""
import re, html
from pathlib import Path

# ===== CONFIG =====
SITE_URL = "https://bharatsamwad.org"
# If your domain isn't live yet, temporarily set:
# SITE_URL = "https://bharatsamvad-epaper.pages.dev"
DEFAULT_IMAGE = "/og-default.jpg"   # relative to SITE_URL
DEFAULT_TITLE = "Bharat Samvad"
DEFAULT_DESC  = "Bharat Samvad — Trilingual e-paper"

def attr(s):
    return html.escape(str(s), quote=True)

def extract_english_headline_and_subdeck(html_text):
    """Try to pull headline + subdeck from the data-lang='en' block.
       Falls back to first <h2 class='headline'> / <p class='subdeck'>,
       then to <title> tag."""
    en_block_match = re.search(
        r'<div[^>]*data-lang="en"[^>]*>(.*?)</div>\s*</div>',
        html_text, re.DOTALL
    )
    scope = en_block_match.group(1) if en_block_match else html_text

    head_m = re.search(r'<h2\s+class="headline"[^>]*>(.*?)</h2>', scope, re.DOTALL)
    sub_m  = re.search(r'<p\s+class="subdeck"[^>]*>(.*?)</p>',     scope, re.DOTALL)

    def clean(t):
        if not t: return None
        t = re.sub(r'<[^>]+>', '', t)              # strip inner tags
        t = html.unescape(t)
        return ' '.join(t.split())                  # collapse whitespace

    headline = clean(head_m.group(1)) if head_m else None
    subdeck  = clean(sub_m.group(1))  if sub_m  else None

    if not headline:
        t = re.search(r'<title>(.*?)</title>', html_text, re.DOTALL)
        headline = clean(t.group(1)) if t else None

    return headline or DEFAULT_TITLE, subdeck or DEFAULT_DESC

def build_meta_block(filename, headline, subdeck):
    page_url = f"{SITE_URL.rstrip('/')}/{filename}"
    img_url  = f"{SITE_URL.rstrip('/')}{DEFAULT_IMAGE}"
    return f'''<meta property="og:type" content="article">
<meta property="og:site_name" content="Bharat Samvad">
<meta property="og:title" content="{attr(headline)}">
<meta property="og:description" content="{attr(subdeck)}">
<meta property="og:url" content="{attr(page_url)}">
<meta property="og:image" content="{attr(img_url)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Bharat Samvad — सत्य · संतुलन · सरोकार">
<meta property="og:locale" content="hi_IN">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{attr(headline)}">
<meta name="twitter:description" content="{attr(subdeck)}">
<meta name="twitter:image" content="{attr(img_url)}">
<link rel="canonical" href="{attr(page_url)}">
'''

def patch_file(path: Path):
    text = path.read_text(encoding="utf-8")
    if 'property="og:title"' in text:
        return "skipped (already patched)"
    if '</head>' not in text:
        return "skipped (no </head> found)"
    headline, subdeck = extract_english_headline_and_subdeck(text)
    block = build_meta_block(path.name, headline, subdeck)
    new_text = text.replace('</head>', block + '</head>', 1)
    path.write_text(new_text, encoding="utf-8")
    return f"patched | title={headline[:60]!r}"

def main():
    here = Path('.')
    files = sorted(here.glob("bharatsamvad-*.html"))
    if not files:
        print("No bharatsamvad-*.html files found in current folder.")
        return
    print(f"Found {len(files)} file(s).")
    for f in files:
        status = patch_file(f)
        print(f"  • {f.name}: {status}")
    print("\nDone.")
    print(f"Next: upload og-default.jpg to your repo root so it's at {SITE_URL}/og-default.jpg")

if __name__ == "__main__":
    main()
