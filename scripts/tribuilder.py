import html
from pathlib import Path

LANG_META = {
    "hi": {"button": "हिंदी", "class": "lang-hi", "dir": "ltr", "masthead": "भारत संवाद"},
    "en": {"button": "English", "class": "lang-en", "dir": "ltr", "masthead": "Bharat Samvad"},
    "ur": {"button": "اردو", "class": "lang-ur", "dir": "rtl", "masthead": "بھارت سنواد"},
}

def _read_template(name):
    p = Path(__file__).resolve().parent / name
    return p.read_text(encoding="utf-8") if p.exists() else ""

def _e(value):
    return html.escape(str(value), quote=False)

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
      <h1 style="font-size:36px;">{meta["masthead"]}</h1>
    </div>
    <div class="strip">
      <span>{_e(article.get("strip_left",""))}</span>
      <span class="mid">{_e(article.get("strip_mid",""))}</span>
      <span>{_e(article.get("date",""))} · bharatsamvad-epaper</span>
    </div>
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

def build(out_path, title, langs):
    css = _read_template("_style.tmp") + "\n" + _read_template("_urdu.tmp")
    buttons = "\n".join(
        f'    <button data-l="{lang}" onclick="setLang(\'{lang}\')">{LANG_META[lang]["button"]}</button>'
        for lang in ("hi", "en", "ur") if lang in langs
    )
    blocks = "\n".join(_render_lang(lang, langs[lang]) for lang in ("hi","en","ur") if lang in langs)
    default_lang = "hi" if "hi" in langs else next(iter(langs))
    doc = f'''<!DOCTYPE html>
<html lang="{default_lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_e(title)}</title>
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
