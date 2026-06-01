# -*- coding: utf-8 -*-
"""Reusable trilingual (हिंदी/English/اردو) article builder for Bharat Samvad."""

import re

STYLE = open("_style.tmp", encoding="utf-8").read()
URDU  = open("_urdu.tmp", encoding="utf-8").read()

# ==================== PDF DOWNLOAD BUTTON ====================
PDF_BUTTON = '''
<button onclick="downloadAsPDF()" class="pdf-download-btn" title="Download this article as PDF">
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
        <polyline points="14 2 14 8 20 8"></polyline>
        <line x1="16" y1="13" x2="8" y2="13"></line>
        <line x1="16" y1="17" x2="8" y2="17"></line>
    </svg>
    Download PDF
</button>
'''

# ==================== TOGGLE + PRINT CSS ====================
TOGGLE_CSS = '''
/* ===== language toggle ===== */
.langbar{position:sticky;top:0;z-index:50;display:flex;justify-content:center;gap:0;
  background:rgba(26,23,20,.92);padding:10px;backdrop-filter:blur(4px);}
.langbar button{font-family:Georgia,'Tiro Devanagari Hindi','Noto Nastaliq Urdu',serif;
  font-size:15px;font-weight:bold;color:#e8dfce;background:transparent;border:1.5px solid #6f1212;
  padding:7px 20px;cursor:pointer;transition:all .15s;}
.langbar button:first-child{border-radius:4px 0 0 4px;}
.langbar button:last-child{border-radius:0 4px 4px 0;border-left:none;}
.langbar button:not(:first-child):not(:last-child){border-left:none;}
.langbar button.active{background:#9a1b1b;color:#fff;border-color:#9a1b1b;}
.langbar button:hover:not(.active){background:#3a342c;}

/* PDF Download Button */
.pdf-download-btn{
    display:inline-flex;align-items:center;gap:6px;padding:8px 16px;
    background:#1a1a1a;color:#fff;border:none;border-radius:4px;
    font-size:0.95rem;font-weight:500;cursor:pointer;transition:all .2s;
    margin-left:12px;
}
.pdf-download-btn:hover{background:#333;}

/* Language blocks */
.langblock{display:none;} .langblock.show{display:block;}
.lang-ur{font-family:'Noto Nastaliq Urdu',serif;}
.lang-ur .headline,.lang-ur .masthead h1{font-family:'Noto Nastaliq Urdu',serif;line-height:1.9;}
.lang-ur .body{direction:rtl;text-align:right;}
.lang-ur .body p,.lang-ur .subdeck{line-height:2.4;font-size:16px;}
.lang-ur .body h3{line-height:2.2;}
.lang-ur .subdeck{border-left:none;border-right:3px solid var(--gold);padding-left:0;padding-right:12px;}
.lang-ur .body p.lead::first-letter{float:none;font-size:inherit;padding:0;color:inherit;}
.lang-ur .box li{line-height:2.2;}
.lang-ur .box h4{border-bottom:2px solid var(--accent);}
.lang-ur .pull{text-align:right;}
.lang-en .headline,.lang-en .masthead h1{font-family:'Rozha One',Georgia,serif;}
.lang-en .body{font-family:Georgia,serif;}

/* news photo */
.newsfig{column-span:all;break-inside:avoid;margin:4px 0 16px;}
.newsfig img{width:100%;height:auto;display:block;border:1px solid var(--rule);box-shadow:3px 3px 0 rgba(38,34,28,.18);}
.newsfig figcaption{font-family:"Mukta",sans-serif;font-size:12.5px;line-height:1.4;color:var(--ink-soft);padding:7px 2px;border-bottom:1px solid #cbbfa3;}
.newsfig figcaption b{font-family:"Khand",sans-serif;font-weight:700;letter-spacing:.5px;color:var(--accent-dk);text-transform:uppercase;margin-right:5px;}
.lang-ur .newsfig figcaption{text-align:right;}

/* ===== poll widget ===== */
.bs-poll{break-inside:avoid;column-span:all;background:#efe7d3;border:1.5px solid var(--ink);
  border-top:4px solid var(--accent);box-shadow:3px 3px 0 rgba(38,34,28,.18);
  padding:18px 20px 16px;margin:8px 0 18px;}
.bs-poll .eyebrow{font-family:'Khand',sans-serif;font-weight:700;letter-spacing:3px;font-size:11px;
  text-transform:uppercase;color:#fff;background:var(--accent);display:inline-block;padding:3px 11px;margin-bottom:10px;}
.bs-poll h4{font-family:'Rozha One',Georgia,serif;font-size:21px;line-height:1.25;color:var(--ink);margin-bottom:14px;border:none;padding:0;}
.bs-poll .opt{display:block;width:100%;text-align:left;font-family:inherit;font-size:15px;color:var(--ink);
  background:var(--paper);border:1.5px solid var(--ink);padding:11px 14px;margin-bottom:9px;cursor:pointer;
  position:relative;overflow:hidden;transition:transform .1s;}
.bs-poll .opt:hover{transform:translateX(3px);}
.bs-poll .opt .barfill{position:absolute;inset:0;background:rgba(154,27,27,.16);width:0;transition:width .5s ease;z-index:0;}
.bs-poll .opt .lbl{position:relative;z-index:1;display:flex;justify-content:space-between;gap:10px;}
.bs-poll .opt .pct{font-weight:bold;color:var(--accent-dk);font-family:'Khand',sans-serif;}
.bs-poll.voted .opt{cursor:default;}
.bs-poll.voted .opt:hover{transform:none;}
.bs-poll .meta{font-family:'Mukta',sans-serif;font-size:12px;color:var(--ink-soft);margin-top:8px;
  display:flex;justify-content:space-between;align-items:center;gap:10px;}
.bs-poll .thanks{color:var(--accent-dk);font-weight:600;}
.lang-ur .bs-poll h4{font-family:'Noto Nastaliq Urdu',serif;line-height:1.9;}
.lang-ur .bs-poll .opt{text-align:right;font-family:'Noto Nastaliq Urdu',serif;line-height:1.9;}
.lang-ur .bs-poll .opt:hover{transform:translateX(-3px);}
.lang-ur .bs-poll .meta{flex-direction:row-reverse;}

/* ==================== PRINT STYLES (PDF) ==================== */
@media print {
    .langbar, .pdf-download-btn, .top-bar, .sidebar, .footer, 
    .share-buttons, .comments, .related-articles, nav {
        display: none !important;
    }
    body, .sheet { background:#fff !important; color:#000 !important; margin:0; padding:0; }
    .sheet { box-shadow:none; max-width:100%; margin:0 auto; }
    .langblock { display:block !important; break-after:page; page-break-after:always; }
    .langblock:last-child { page-break-after:avoid; }
    h1, h2, h3, .headline, .kicker { color:#000 !important; break-after:avoid; }
    .kicker { color:#9a1b1b !important; font-weight:700; }
    .masthead h1 { font-size:32px !important; }
    p, li { line-height:1.75; orphans:3; widows:3; }
    figure, .newsfig, .box, .pull { break-inside:avoid; }
    @page { margin:1.5cm; size:A4; }
}
'''

TOGGLE_JS = r'''
<script>
function downloadAsPDF() {
    let headline = document.querySelector('.headline') ? 
                   document.querySelector('.headline').textContent.trim() : 'Article';
    
    let cleanTitle = headline
        .replace(/[^a-zA-Z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .toLowerCase()
        .substring(0, 60);
    
    const filename = "2026-06-01-page4-" + cleanTitle + ".pdf";

    const toast = document.createElement('div');
    toast.style.cssText = "position:fixed;bottom:30px;left:50%;transform:translateX(-50%);background:#1a1a1a;color:white;padding:14px 28px;border-radius:6px;z-index:10000;font-size:1rem;box-shadow:0 4px 12px rgba(0,0,0,0.3);";
    toast.textContent = 'Opening Print to PDF...';
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
        window.print();
    }, 700);
}

/* Poll functions (kept minimal) */
var BS_POLL_T = { hi:{eyebrow:"जनमत · आपकी राय"}, en:{eyebrow:"Poll · Your Opinion"}, ur:{eyebrow:"رائے شماری · آپ کی رائے"} };
var BS_LANG = "hi";

function setLang(l){
  BS_LANG=l;
  document.querySelectorAll('.langblock').forEach(b=>b.classList.toggle('show', b.dataset.lang===l));
  document.querySelectorAll('.langbar button').forEach(btn=>btn.classList.toggle('active', btn.dataset.l===l));
  document.documentElement.lang=(l==='ur'?'ur':(l==='en'?'en':'hi'));
}
document.addEventListener('DOMContentLoaded',function(){
  var s='hi'; try{s=localStorage.getItem('bs_lang')||'hi';}catch(e){}
  setLang(s);
});
</script>
'''

BAR = f'''  <div class="langbar">
    <button data-l="hi" onclick="setLang('hi')">हिंदी</button>
    <button data-l="en" onclick="setLang('en')">English</button>
    <button data-l="ur" onclick="setLang('ur')">اردو</button>
    {PDF_BUTTON}
  </div>'''

MAST = {"hi":"भारत संवाद","en":"Bharat Samwad","ur":"بھارت سنواد"}

def block(typ, txt):
    if typ == "lead": return f'<p class="lead">{txt}</p>'
    if typ == "h3":   return f'<h3>{txt}</h3>'
    return f'<p>{txt}</p>'

def render_lang(lang, A, photo_b64=None):
    figure = ""
    if photo_b64 and A.get("caption"):
        figure = f'<figure class="newsfig"><img src="data:image/jpeg;base64,{photo_b64}" alt=""><figcaption>{A["caption"]}</figcaption></figure>'
    
    body = ""
    for typ, txt in A.get("body", []):
        body += block(typ, txt)

    rtl = ' dir="rtl"' if lang == "ur" else ''
    return f'''  <div class="langblock lang-{lang}"{rtl} data-lang="{lang}">
    <div class="masthead" style="border-bottom:2px solid var(--rule);padding:4px 0 6px;">
      <h1 style="font-size:36px;">{MAST[lang]}</h1>
    </div>
    <div class="strip">
      <span>{A.get("strip_left","")}</span>
      <span class="mid">{A.get("strip_mid","")}</span>
      <span>{A.get("date","")} · bharatsamwad-epaper</span>
    </div>
    <span class="kicker">{A.get("kicker","")}</span>
    <h2 class="headline">{A.get("head","")}</h2>
    <p class="subdeck">{A.get("sub","")}</p>
    <div class="byline">{A.get("byline","")}</div>
    <div class="body">
{figure}{body}
    </div>
    <div class="foot">
      <span>{A.get("foot_l","")}</span><span>{A.get("foot_m","")}</span><span>{A.get("foot_p","")}</span>
    </div>
  </div>'''

def build(outfile, title, langs, photo_b64=None):
    blocks = "\n".join(render_lang(l, langs[l], photo_b64) for l in ("hi", "en", "ur"))
    
    html = f'''<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
{URDU}
{STYLE}
{TOGGLE_CSS}
</style>
</head>
<body>
{BAR}
  <div class="sheet">
{blocks}
  </div>
{TOGGLE_JS}
</body>
</html>'''
    
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(html)
    return html
