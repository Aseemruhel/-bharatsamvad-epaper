# -*- coding: utf-8 -*-
"""Reusable trilingual (हिंदी/English/اردو) article builder for Bharat Samvad."""
import re

STYLE = open("_style.tmp", encoding="utf-8").read()       # embedded Hindi fonts + design CSS
URDU  = open("_urdu.tmp", encoding="utf-8").read()         # embedded Noto Nastaliq Urdu faces

TOGGLE_CSS = '''
/* ===== language toggle ===== */
.langbar{position:sticky;top:0;z-index:50;display:flex;justify-content:center;
  background:rgba(26,23,20,.92);padding:10px;backdrop-filter:blur(4px);}
.langbar button{font-family:Georgia,'Tiro Devanagari Hindi','Noto Nastaliq Urdu',serif;
  font-size:15px;font-weight:bold;color:#e8dfce;background:transparent;border:1.5px solid #6f1212;
  padding:7px 20px;cursor:pointer;transition:all .15s;}
.langbar button:first-child{border-radius:4px 0 0 4px;}
.langbar button:last-child{border-radius:0 4px 4px 0;border-left:none;}
.langbar button:not(:first-child):not(:last-child){border-left:none;}
.langbar button.active{background:#9a1b1b;color:#fff;border-color:#9a1b1b;}
.langbar button:hover:not(.active){background:#3a342c;}
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
'''

TOGGLE_JS = '''
<script>
/* ===== poll chrome strings per language ===== */
var BS_POLL_T = {
  hi:{eyebrow:"जनमत · आपकी राय", thanks:"आपके मत के लिए धन्यवाद!", votes:"वोट"},
  en:{eyebrow:"Poll · Your Opinion", thanks:"Thanks for your vote!", votes:"votes"},
  ur:{eyebrow:"رائے شماری · آپ کی رائے", thanks:"آپ کی رائے کا شکریہ!", votes:"ووٹ"}
};
var BS_LANG = "hi";

function bsPollPct(n,t){return t?Math.round(n*100/t):0;}
function bsPollRenderOne(box,counts){
  counts=counts||{};
  var opts=box.querySelectorAll(".opt"),total=0;
  opts.forEach(function(o){total+=counts[o.dataset.opt]||0;});
  var voted=box.classList.contains("voted");
  opts.forEach(function(o){
    var lab=o.querySelector(".optlabel");
    if(lab) lab.textContent=o.getAttribute("data-"+BS_LANG)||lab.textContent;
    var n=counts[o.dataset.opt]||0,p=bsPollPct(n,total);
    o.querySelector(".barfill").style.width=voted?p+"%":"0%";
    o.querySelector(".pct").textContent=voted?p+"%":"";
  });
  var t=BS_POLL_T[BS_LANG];
  var eb=box.querySelector(".eyebrow"); if(eb) eb.textContent=t.eyebrow;
  var th=box.querySelector("[data-thanks]"); if(th) th.textContent=t.thanks;
  var tot=box.querySelector("[data-total]"); if(tot) tot.textContent=voted?(total+" "+t.votes):"";
  var q=box.querySelector("h4"); if(q && q.getAttribute("data-"+BS_LANG)) q.textContent=q.getAttribute("data-"+BS_LANG);
}
function bsPollRefreshAll(){document.querySelectorAll(".bs-poll").forEach(function(b){bsPollRenderOne(b);});}

function bsPollInit(box){
  var API="/api/poll", id=box.dataset.pollId, already=false;
  try{already=!!localStorage.getItem("bs_voted_"+id);}catch(e){}
  function localCounts(){try{return JSON.parse(localStorage.getItem("bs_counts_"+id)||"{}");}catch(e){return {};}}
  fetch(API+"?id="+encodeURIComponent(id)).then(function(r){return r.ok?r.json():null;})
    .then(function(d){var c=(d&&d.counts)?d.counts:localCounts(); if(already)box.classList.add("voted"); if(already){var t=box.querySelector("[data-thanks]"); if(t)t.hidden=false;} bsPollRenderOne(box,c);})
    .catch(function(){var c=localCounts(); if(already)box.classList.add("voted"); bsPollRenderOne(box,c);});
  box.querySelectorAll(".opt").forEach(function(btn){
    btn.addEventListener("click",function(){
      if(box.classList.contains("voted"))return;
      var opt=btn.dataset.opt;
      try{localStorage.setItem("bs_voted_"+id,opt);}catch(e){}
      var c=localCounts(); c[opt]=(c[opt]||0)+1; try{localStorage.setItem("bs_counts_"+id,JSON.stringify(c));}catch(e){}
      box.classList.add("voted");
      var th=box.querySelector("[data-thanks]"); if(th)th.hidden=false;
      bsPollRenderOne(box,c);
      fetch(API,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id:id,option:opt})})
        .then(function(r){return r.ok?r.json():null;})
        .then(function(d){if(d&&d.counts)bsPollRenderOne(box,d.counts);}).catch(function(){});
    });
  });
}

function setLang(l){
  BS_LANG=l;
  document.querySelectorAll('.langblock').forEach(b=>b.classList.toggle('show', b.dataset.lang===l));
  document.querySelectorAll('.langbar button').forEach(btn=>btn.classList.toggle('active', btn.dataset.l===l));
  document.documentElement.lang=(l==='ur'?'ur':(l==='en'?'en':'hi'));
  bsPollRefreshAll();
  try{localStorage.setItem('bs_lang',l);}catch(e){}
}
document.addEventListener('DOMContentLoaded',function(){
  document.querySelectorAll(".bs-poll").forEach(bsPollInit);
  var s='hi'; try{s=localStorage.getItem('bs_lang')||'hi';}catch(e){}
  setLang(s);
});
</script>'''

BAR = '''  <div class="langbar">
    <button data-l="hi" onclick="setLang('hi')">हिंदी</button>
    <button data-l="en" onclick="setLang('en')">English</button>
    <button data-l="ur" onclick="setLang('ur')">اردو</button>
  </div>'''

MAST = {"hi":"भारत संवाद","en":"Bharat Samvad","ur":"بھارت سنواد"}

def block(typ, txt):
    if typ=="lead": return f'<p class="lead">{txt}</p>'
    if typ=="h3":   return f'<h3>{txt}</h3>'
    return f'<p>{txt}</p>'

def poll_html(P):
    """P = {id, q:{hi,en,ur}, options:[{opt, hi, en, ur}, ...]}"""
    opts=""
    for o in P["options"]:
        opts+=(f'<button class="opt" data-opt="{o["opt"]}" data-hi="{o["hi"]}" data-en="{o["en"]}" data-ur="{o["ur"]}">'
               f'<span class="lbl"><span class="optlabel">{o["hi"]}</span><span class="pct"></span></span>'
               f'<span class="barfill"></span></button>')
    q=P["q"]
    return (f'<div class="bs-poll" data-poll-id="{P["id"]}">'
            f'<span class="eyebrow"></span>'
            f'<h4 data-hi="{q["hi"]}" data-en="{q["en"]}" data-ur="{q["ur"]}">{q["hi"]}</h4>'
            f'{opts}'
            f'<div class="meta"><span class="thanks" data-thanks hidden></span><span class="total" data-total></span></div>'
            f'</div>')

def render_lang(lang, A, photo_b64=None):
    """A is the article content dict for this language."""
    parts=[]
    # optional photo right after byline (newspaper style)
    figure=""
    if photo_b64 and A.get("caption"):
        figure=(f'<figure class="newsfig"><img src="data:image/jpeg;base64,{photo_b64}" '
                f'alt=""><figcaption>{A["caption"]}</figcaption></figure>')
    # body assembly: list of (typ,txt); special tokens BOX, PULL, POLL inserted by markers
    body=""
    for typ,txt in A["body"]:
        if typ=="BOX":
            items="".join(f'<li><b>{a}</b>{b}</li>' for a,b in A["box_items"])
            body+=f'<div class="box"><h4>{A["box_title"]}</h4><ul>{items}</ul></div>'
        elif typ=="PULL":
            body+=f'<div class="pull">{A["pull_q"]}<cite>{A["pull_c"]}</cite></div>'
        elif typ=="POLL":
            body+=poll_html(A["poll"])
        else:
            body+=block(typ,txt)
    rtl=' dir="rtl"' if lang=="ur" else ''
    mhsize="36px"
    return f'''  <div class="langblock lang-{lang}"{rtl} data-lang="{lang}">
    <div class="masthead" style="border-bottom:2px solid var(--rule);padding:4px 0 6px;">
      <h1 style="font-size:{mhsize};">{MAST[lang]}</h1>
    </div>
    <div class="strip">
      <span>{A["strip_left"]}</span>
      <span class="mid">{A["strip_mid"]}</span>
      <span>{A["date"]} · bharatsamvad-epaper</span>
    </div>
    <span class="kicker">{A["kicker"]}</span>
    <h2 class="headline">{A["head"]}</h2>
    <p class="subdeck">{A["sub"]}</p>
    <div class="byline">{A["byline"]}</div>
    <div class="body">
{figure}{body}
    </div>
    <div class="foot">
      <span>{A["foot_l"]}</span><span>{A["foot_m"]}</span><span>{A["foot_p"]}</span>
    </div>
  </div>'''

def build(outfile, title, langs, photo_b64=None):
    """langs: dict lang->content dict"""
    blocks="\n".join(render_lang(l, langs[l], photo_b64) for l in ("hi","en","ur"))
    html=f'''<!DOCTYPE html>
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
    open(outfile,"w",encoding="utf-8").write(html)
    return html
