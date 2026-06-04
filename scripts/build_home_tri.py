from pathlib import Path
import html

# This value is replaced at runtime by scripts/build_from_markdown.py.
DAYS = []

# Replaced at runtime by build_from_markdown.py from content/ticker.md.
# Each item is a short English string shown in the scrolling ticker.
TICKER_ITEMS = []

# How many most-recent days to keep on the homepage. The rest go to archive.html.
RECENT_LIMIT = 3

STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Tiro+Devanagari+Hindi:ital@0;1&family=Mukta:wght@400;500;600;700&family=Khand:wght@500;600;700&family=Rozha+One&family=Noto+Nastaliq+Urdu:wght@400;600;700&display=swap');

:root{
  --bg:#15110e;
  --paper:#f4efe2;
  --paper2:#eee5d2;
  --ink:#1a1714;
  --soft:#3a342c;
  --rule:#26221c;
  --accent:#a51616;
  --accent-dark:#731010;
  --gold:#92733a;
}

*{
  box-sizing:border-box;
  margin:0;
  padding:0;
}

body{
  background:radial-gradient(circle at 90% 20%,rgba(255,255,255,.04) 0 1px,transparent 1px 18px),var(--bg);
  color:var(--ink);
  font-family:"Tiro Devanagari Hindi",Georgia,serif;
  line-height:1.55;
}

.topbar{
  position:sticky;
  top:0;
  z-index:50;
  background:#15100d;
  border-bottom:5px solid var(--accent);
  display:flex;
  justify-content:center;
  padding:11px 10px 10px;
}

.langbar{
  display:flex;
  justify-content:center;
}

.langbar button{
  min-width:86px;
  font-family:Georgia,"Tiro Devanagari Hindi","Noto Nastaliq Urdu",serif;
  font-size:15px;
  font-weight:700;
  color:#f3ead7;
  background:#17110e;
  border:1px solid var(--accent-dark);
  border-right:none;
  padding:14px 18px;
  cursor:pointer;
  transition:all .15s ease;
}

.langbar button:first-child{
  border-radius:4px 0 0 4px;
}

.langbar button:last-child{
  border-radius:0 4px 4px 0;
  border-right:1px solid var(--accent-dark);
}

.langbar button.active{
  background:var(--accent);
  border-color:var(--accent);
  color:#fff;
}

.langbar button:hover:not(.active){
  background:#2b211b;
}

.wrap{
  max-width:760px;
  margin:0 auto;
  background:var(--paper);
  min-height:100vh;
  padding:32px 38px 46px;
  box-shadow:0 20px 60px rgba(0,0,0,.55);
  position:relative;
}

.wrap::before{
  content:"";
  position:absolute;
  top:0;
  left:0;
  right:0;
  height:1px;
  background:#c9b98e;
}

.mast{
  text-align:center;
  padding:7px 0 13px;
  border-bottom:4px double var(--rule);
  margin-bottom:13px;
}

.home-logo{
  color:inherit;
  text-decoration:none;
  display:inline-block;
}

.home-logo:hover{
  color:var(--accent);
}

.mast h1{
  font-family:"Rozha One","Tiro Devanagari Hindi",serif;
  font-size:76px;
  line-height:.9;
  letter-spacing:1px;
  color:var(--ink);
}

.mast .tag{
  margin-top:7px;
  font-family:"Khand",sans-serif;
  color:var(--accent-dark);
  letter-spacing:8px;
  font-size:14px;
  font-weight:700;
}

.navribbon{
  text-align:center;
  margin:8px 0 6px;
  font-family:"Khand","Mukta",sans-serif;
  letter-spacing:1px;
}

.navribbon .navlink{
  text-decoration:none;
  color:var(--accent-dark);
  font-weight:700;
  font-size:14px;
  padding:4px 12px;
  text-transform:uppercase;
  border-bottom:2px solid transparent;
}

.navribbon .navlink:hover{
  border-bottom-color:var(--gold);
}

.navribbon .navlink.active{
  color:var(--accent);
  border-bottom-color:var(--accent);
}

.navribbon .navsep{
  color:var(--soft);
  margin:0 4px;
}

.issue{
  text-align:center;
  font-size:14px;
  color:var(--soft);
  padding:8px 0 18px;
  letter-spacing:1px;
}

.empty-note{
  text-align:center;
  padding:50px 12px;
  color:var(--soft);
  font-style:italic;
}

.langblock{
  display:none;
}

.langblock.show{
  display:block;
}

.day{
  margin:24px 0 28px;
}

.day-head{
  display:grid;
  grid-template-columns:auto 1fr auto;
  align-items:center;
  gap:14px;
  margin-bottom:18px;
}

.day-head h2{
  font-family:"Tiro Devanagari Hindi",Georgia,serif;
  color:var(--accent-dark);
  font-size:25px;
  font-weight:400;
  line-height:1;
}

.day-head .line{
  height:2px;
  background:var(--rule);
  opacity:.95;
}

.badge{
  display:inline-block;
  background:var(--accent);
  color:#fff;
  font-family:"Khand",sans-serif;
  font-weight:700;
  font-size:12px;
  letter-spacing:1px;
  padding:4px 11px;
  text-transform:uppercase;
}

.card{
  display:block;
  color:var(--ink);
  text-decoration:none;
  background:var(--paper2);
  border:1.4px solid var(--rule);
  padding:17px 18px 15px;
  margin:13px 0;
  box-shadow:3px 4px 0 rgba(38,34,28,.12);
}

.card:hover{
  outline:2px solid var(--accent);
  outline-offset:2px;
}

.card small{
  display:block;
  color:var(--accent-dark);
  font-family:"Khand",sans-serif;
  font-weight:700;
  letter-spacing:1px;
  font-size:13px;
  margin-bottom:6px;
}

.card strong{
  display:block;
  font-size:23px;
  line-height:1.28;
  font-weight:400;
  color:var(--ink);
}

.card span{
  display:block;
  margin-top:8px;
  font-size:13px;
  color:var(--soft);
}

.footer{
  margin-top:26px;
  padding-top:10px;
  border-top:4px double var(--rule);
  display:flex;
  justify-content:space-between;
  color:var(--soft);
  font-family:"Mukta",sans-serif;
  font-size:11px;
  text-transform:uppercase;
  letter-spacing:.4px;
}

.en{
  font-family:Georgia,serif;
}

.en .mast h1{
  font-family:"Rozha One",Georgia,serif;
}

.en .day-head h2{
  font-family:Georgia,serif;
  font-size:24px;
}

.en .card strong{
  font-family:Georgia,serif;
  font-size:22px;
}

.ur{
  direction:rtl;
  font-family:"Noto Nastaliq Urdu",serif;
}

.ur .mast h1{
  font-family:"Noto Nastaliq Urdu",serif;
  font-size:58px;
  line-height:1.65;
}

.ur .mast .tag{
  letter-spacing:2px;
  font-family:"Noto Nastaliq Urdu",serif;
}

.ur .navribbon{
  font-family:"Noto Nastaliq Urdu",serif;
  letter-spacing:0;
}

.ur .day-head{
  direction:rtl;
}

.ur .day-head h2{
  font-family:"Noto Nastaliq Urdu",serif;
  font-size:24px;
  line-height:2;
}

.ur .card{
  text-align:right;
}

.ur .card strong{
  font-family:"Noto Nastaliq Urdu",serif;
  font-size:21px;
  line-height:2.05;
}

.ur .card span{
  line-height:2;
}


/* breaking-news ticker */
.ticker-wrap{
  background:#0d0907;
  border-bottom:2px solid var(--accent);
  border-top:1px solid #2a1f1a;
  overflow:hidden;
  position:relative;
  z-index:40;
}
.ticker-label{
  position:absolute;
  left:0;
  top:0;
  bottom:0;
  display:flex;
  align-items:center;
  padding:0 14px;
  background:var(--accent);
  color:#fff;
  font-family:"Khand","Mukta",sans-serif;
  font-weight:700;
  font-size:13px;
  letter-spacing:2px;
  text-transform:uppercase;
  z-index:2;
  box-shadow:6px 0 12px -4px rgba(0,0,0,.6);
}
.ticker-label::after{
  content:"";
  position:absolute;
  right:-10px;
  top:0;
  bottom:0;
  width:0;
  border-top:18px solid transparent;
  border-bottom:18px solid transparent;
  border-left:10px solid var(--accent);
}
.ticker-track{
  display:flex;
  gap:60px;
  padding:11px 18px 11px 110px;
  white-space:nowrap;
  width:max-content;
  animation:ticker-scroll 60s linear infinite;
  font-family:"Mukta",Georgia,sans-serif;
  font-size:14px;
  color:#f3ead7;
}
.ticker-item{
  display:inline-flex;
  align-items:center;
  gap:60px;
}
.ticker-item::before{
  content:"\25C6";
  color:var(--gold);
  font-size:9px;
  margin-right:14px;
}
.ticker-wrap:hover .ticker-track{
  animation-play-state:paused;
}
@keyframes ticker-scroll{
  from{ transform:translateX(0); }
  to  { transform:translateX(-50%); }
}
@media(max-width:700px){
  .ticker-label{font-size:11px; padding:0 10px;}
  .ticker-label::after{border-top-width:16px; border-bottom-width:16px;}
  .ticker-track{padding-left:90px; gap:40px; font-size:13px; animation-duration:45s;}
  .ticker-item::before{margin-right:10px;}
}

@media(max-width:700px){
  .wrap{
    padding:25px 22px 38px;
  }

  .mast h1{
    font-size:54px;
  }

  .langbar button{
    min-width:76px;
    padding:11px 13px;
  }

  .day-head{
    grid-template-columns:1fr;
    gap:7px;
  }

  .day-head .line{
    height:1.5px;
  }

  .badge{
    width:max-content;
  }

  .card strong{
    font-size:20px;
  }
}

@media print{
  body{
    background:white;
  }

  .topbar{
    display:none;
  }

  .wrap{
    box-shadow:none;
    max-width:none;
  }
}
"""


def e(x):
    return html.escape(str(x), quote=False)


def page(lang, days, kind="home"):
    """Render one language block. kind is 'home' or 'archive'."""
    klass = {"hi": "hi", "en": "en", "ur": "ur"}[lang]

    names = {
        "hi": "भारत संवाद",
        "en": "Bharat Samwad",
        "ur": "بھارت سنواد",
    }

    tag = {
        "hi": "सत्य · सृजन · सरोकार",
        "en": "Truth · Creation · Concern",
        "ur": "سچ · تخلیق · سروکار",
    }

    home_label = {
        "hi": "मुखपृष्ठ",
        "en": "Home",
        "ur": "مرکزی صفحہ",
    }

    archive_label = {
        "hi": "पुरालेख",
        "en": "Archive",
        "ur": "آرکائیو",
    }

    issue = {
        "hi": "ई-पेपर · सभी संस्करण",
        "en": "E-paper · All editions",
        "ur": "ای پیپر · تمام ایڈیشن",
    }

    archive_sub = {
        "hi": "ई-पेपर · पुराने संस्करण",
        "en": "E-paper · Older editions",
        "ur": "ای پیپر · پرانی اشاعتیں",
    }

    latest = {
        "hi": "ताज़ा",
        "en": "Latest",
        "ur": "تازہ",
    }

    read = {
        "hi": "पूरा लेख पढ़ें →",
        "en": "Read full article →",
        "ur": "پورا مضمون پڑھیں ←",
    }

    no_articles = {
        "hi": "अभी कोई लेख उपलब्ध नहीं है।",
        "en": "No articles yet.",
        "ur": "ابھی کوئی مضمون دستیاب نہیں۔",
    }

    no_older = {
        "hi": "अभी कोई पुराना संस्करण नहीं है।",
        "en": "No older editions yet.",
        "ur": "ابھی کوئی پرانی اشاعت موجود نہیں۔",
    }

    h_active = " active" if kind == "home" else ""
    a_active = " active" if kind == "archive" else ""
    sub_text = archive_sub[lang] if kind == "archive" else issue[lang]
    empty_text = no_older[lang] if kind == "archive" else no_articles[lang]

    body = [
        f'<div class="langblock {klass}" data-lang="{lang}">',
        '<div class="mast">',
        f'<a href="index.html" class="home-logo" title="Back to Main Page"><h1>{names[lang]}</h1></a>',
        f'<div class="tag">{tag[lang]}</div>',
        '</div>',
        '<div class="navribbon">',
        f'<a class="navlink{h_active}" href="index.html">{home_label[lang]}</a>',
        '<span class="navsep">·</span>',
        f'<a class="navlink{a_active}" href="archive.html">{archive_label[lang]}</a>',
        '</div>',
        f'<div class="issue">{sub_text}</div>',
    ]

    if not days:
        body.append(f'<div class="empty-note">{empty_text}</div>')

    for day in days:
        date_text = e(day["date"][lang])
        badge = latest[lang] if day.get("latest") else ""

        body.append('<section class="day">')
        body.append('<div class="day-head">')
        body.append(f'<h2>{date_text}</h2>')
        body.append('<div class="line"></div>')
        body.append(f'<span class="badge">{badge}</span>' if badge else '<span></span>')
        body.append('</div>')

        for card in day["cards"]:
            body.append(
                f'<a class="card" href="{e(card["href"])}">'
                f'<small>{e(card["label"][lang])}</small>'
                f'<strong>{e(card["title"][lang])}</strong>'
                f'<span>{read[lang]}</span>'
                '</a>'
            )

        body.append('</section>')

    body.append(
        '<div class="footer">'
        f'<span>{names[lang]}</span>'
        '<span>© 2026</span>'
        '<span>bharatsamwad-epaper</span>'
        '</div>'
    )

    body.append('</div>')
    return "\n".join(body)



def render_ticker():
    """Render the scrolling ticker HTML. Empty string if no items."""
    if not TICKER_ITEMS:
        return ""
    # Duplicate items so the loop appears seamless (animation goes to -50%)
    items_html = "".join(f'<span class="ticker-item">{e(item)}</span>' for item in TICKER_ITEMS)
    return (
        '<div class="ticker-wrap">'
        '<div class="ticker-label">Breaking</div>'
        f'<div class="ticker-track">{items_html}{items_html}</div>'
        '</div>'
    )


def build_doc(days, kind, title_text, with_ticker=False):
    ticker_html = render_ticker() if with_ticker else ""
    return f"""<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_text}</title>
<style>{STYLE}</style>
</head>
<body>
<div class="topbar">
  <div class="langbar">
    <button data-l="hi" onclick="setLang('hi')">हिंदी</button>
    <button data-l="en" onclick="setLang('en')">English</button>
    <button data-l="ur" onclick="setLang('ur')">اردو</button>
  </div>
</div>
{ticker_html}

<div class="wrap">
  {page("hi", days, kind)}
  {page("en", days, kind)}
  {page("ur", days, kind)}
</div>

<script>
function setLang(l){{
  document.querySelectorAll('.langblock').forEach(function(b){{
    b.classList.toggle('show', b.dataset.lang === l);
  }});

  document.querySelectorAll('.langbar button').forEach(function(btn){{
    var active = btn.dataset.l === l;
    btn.classList.toggle('active', active);
    btn.style.background = active ? '#a51616' : '#17110e';
    btn.style.borderColor = active ? '#a51616' : '#731010';
    btn.style.color = active ? '#fff' : '#f3ead7';
  }});

  document.documentElement.lang = (l === 'ur' ? 'ur' : (l === 'en' ? 'en' : 'hi'));
  document.documentElement.dir = (l === 'ur' ? 'rtl' : 'ltr');

  try{{
    localStorage.setItem('bs_lang', l);
  }}catch(e){{}}
}}

document.addEventListener('DOMContentLoaded', function(){{
  var s = 'hi';

  try{{
    s = localStorage.getItem('bs_lang') || 'hi';
  }}catch(e){{}}

  if(!['hi','en','ur'].includes(s)){{
    s = 'hi';
  }}

  setLang(s);
}});
</script>
</body>
</html>"""


# Split DAYS into recent (top RECENT_LIMIT) for the homepage,
# and everything older for the archive page.
recent_days = DAYS[:RECENT_LIMIT]
older_days  = DAYS[RECENT_LIMIT:]

home_doc = build_doc(
    recent_days,
    "home",
    "भारत संवाद · Bharat Samwad · بھارت سنواد",
    with_ticker=True,
)
Path("index.html").write_text(home_doc, encoding="utf-8")
print(f"wrote index.html (recent {len(recent_days)} day(s))")

archive_doc = build_doc(
    older_days,
    "archive",
    "पुरालेख · Archive · آرکائیو — भारत संवाद",
)
Path("archive.html").write_text(archive_doc, encoding="utf-8")
print(f"wrote archive.html ({len(older_days)} older day(s))")
