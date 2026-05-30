import html
from pathlib import Path

# ========================================================================
# Site URL — used to build canonical & OG URLs for social previews (X etc).
# Change this to your live domain. If bharatsamwad.org isn't fully resolving
# yet (DNS still propagating), temporarily set this to
#   "https://bharatsamvad-epaper.pages.dev"
# so X / WhatsApp can still fetch og-default.jpg.
# ========================================================================
SITE_URL = "https://bharatsamwad.org"

LANG_META = {
    "hi": {"button": "हिंदी", "class": "lang-hi", "dir": "ltr", "masthead": "भारत संवाद", "og_locale": "hi_IN"},
    "en": {"button": "English", "class": "lang-en", "dir": "ltr", "masthead": "Bharat Samwad", "og_locale": "en_IN"},
    "ur": {"button": "اردو", "class": "lang-ur", "dir": "rtl", "masthead": "بھارت سنواد", "og_locale": "ur_PK"},
}

def _read_template(name):
    p = Path(__file__).resolve().parent / name
    return p.read_text(encoding="utf-8") if p.exists() else ""

def _e(value):
    return html.escape(str(value), quote=False)

def _attr(value):
    # For HTML attributes: also escape quotes.
    return html.escape(str(value), quote=True)

def _render_body(article):
    parts = []
    for typ, text in article.get("body", []):
        if typ == "lead":
            parts.append(f'<p class="lead">{_e(text)}</p>')
        elif typ == "p":
            parts.append(f"<p>{_e(text)}</p>")
        elif typ == "h3":
            parts.append(f"<h3>{_e(text)}</h3>")
        elif typ == "BOX":
            items = [f"<li><b>{_e(label)}</b>{_e(val)}</li>" for label, val in article.get("box_items", [])]
            parts.append('<div class="box">' + f'<h4>{_e(article.get("box_title",""))}</h4><ul>{"".join(items)}</ul></div>')
        elif typ == "PULL":
            q = _e(article.get("pull_q", ""))
            c = _e(article.get("pull_c", ""))
            cite = f"<cite>{c}</cite>" if c else ""
            parts.append(f'<div class="pull">"{q}"{cite}</div>')
    return "\n".join(parts)

def _render_lang(lang, article):
    meta = LANG_META[lang]
    dir_attr = f' dir="{meta["dir"]}"' if meta["dir"] == "rtl" else ""
    return f'''
  <div class="langblock {meta["class"]}"{dir_attr} data-lang="{lang}">
    <div class="masthead" style="border-bottom:2px solid var(--rule);padding:4px 0 6px;">
  <a href="index.html" class="home-logo" title="Home">
    <h1 style="font-size:36px;">{meta["masthead"]}</h1>
  </a>
</div>
    <div class="strip">
      <span>{_e(article.get("strip_left",""))}</span>
      <span class="mid">{_e(article.get("strip_mid",""))}</span>
      <span>{_e(article.get("date",""))} · bharatsamwad-epaper</span>
    </div>
    <a class="back-home-btn" href="index.html">← Back to Main Menu</a>
    <span class="kicker">{_e(article.get("kicker",""))}</span>
    <h2 class="headline">{_e(article.get("head",""))}</h2>
    <p class="subdeck">{_e(article.get("sub",""))}</p>
    <div class="byline">{article.get("byline","")}</div>
    <div class="body">
{_render_body(article)}
    </div>
    <div class="foot">
      <span>{_e(article.get("foot_l",""))}</span><span>{_e(article.get("foot_m",""))}</span><span>{_e(article.get("foot_p",""))}</span>
    </div>
  </div>'''

def _social_meta(out_path, langs, default_lang):
    """Build OG + Twitter Card meta tags for inline previews on X, WhatsApp etc."""
    # Prefer the English headline/subdeck for the card (wider audience on X);
    # fall back to default-language block if no English block exists.
    src = langs.get("en") or langs.get(default_lang) or next(iter(langs.values()))
    og_title = src.get("head") or "Bharat Samwad"
    og_desc  = src.get("sub")  or "Bharat Samwad — Trilingual e-paper"
    og_locale = LANG_META.get(default_lang, LANG_META["hi"])["og_locale"]
    filename = Path(out_path).name
    page_url = f"{SITE_URL.rstrip('/')}/{filename}"
    img_url  = f"{SITE_URL.rstrip('/')}/og-default.jpg"
    return f'''<meta property="og:type" content="article">
<meta property="og:site_name" content="Bharat Samwad">
<meta property="og:title" content="{_attr(og_title)}">
<meta property="og:description" content="{_attr(og_desc)}">
<meta property="og:url" content="{_attr(page_url)}">
<meta property="og:image" content="{_attr(img_url)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Bharat Samwad — सत्य · संतुलन · सरोकार">
<meta property="og:locale" content="{og_locale}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{_attr(og_title)}">
<meta name="twitter:description" content="{_attr(og_desc)}">
<meta name="twitter:image" content="{_attr(img_url)}">
<link rel="canonical" href="{_attr(page_url)}">'''

def build(out_path, title, langs):
    css = _read_template("_style.tmp") + "\n" + _read_template("_urdu.tmp")
    buttons = "\n".join(
    f"    <button data-l=\"{lang}\" onclick=\"setLang('{lang}')\">{LANG_META[lang]['button']}</button>"
    for lang in ("hi", "en", "ur") if lang in langs
    )
    blocks = "\n".join(_render_lang(lang, langs[lang]) for lang in ("hi","en","ur") if lang in langs)
    default_lang = "hi" if "hi" in langs else next(iter(langs))
    social = _social_meta(out_path, langs, default_lang)
    doc = f'''<!DOCTYPE html>
<html lang="{default_lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_e(title)}</title>
{social}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Tiro+Devanagari+Hindi:ital@0;1&family=Mukta:wght@400;500;600;700&family=Khand:wght@500;600;700&family=Rozha+One&family=Noto+Nastaliq+Urdu:wght@400;600;700&display=swap" rel="stylesheet">
<style>
{css}
</style>
</head>
<body>
  <div class="langbar">
{buttons}
  </div>
  <div class="sheet">
{blocks}
  </div>
<script>
function setLang(l){{
  document.querySelectorAll('.langblock').forEach(b=>b.classList.toggle('show', b.dataset.lang===l));
  document.querySelectorAll('.langbar button').forEach(btn=>btn.classList.toggle('active', btn.dataset.l===l));
  document.documentElement.lang=(l==='ur'?'ur':(l==='en'?'en':'hi'));
  document.documentElement.dir=(l==='ur'?'rtl':'ltr');
  try{{localStorage.setItem('bs_lang',l);}}catch(e){{}}
}}
document.addEventListener('DOMContentLoaded',function(){{
  var s='{default_lang}'; try{{s=localStorage.getItem('bs_lang')||'{default_lang}';}}catch(e){{}}
  if(!document.querySelector('[data-lang="'+s+'"]')) s='{default_lang}';
  setLang(s);
}});
</script>
</body>
</html>'''
    Path(out_path).write_text(doc, encoding="utf-8")
