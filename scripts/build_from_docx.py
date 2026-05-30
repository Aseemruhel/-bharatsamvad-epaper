"""
Bharat Samvad — auto-publish from .docx (Word) files.

Reads English Word documents from content/, parses them via pandoc, then:
  • translates strings to Hindi + Urdu using free googletrans (no API key, no cost)
  • assembles a trilingual HTML file via tribuilder.build()
  • regenerates the homepage index.html
  • caches translations so unchanged articles aren't re-translated

WHAT THE WORD DOC MUST LOOK LIKE
================================
Use the template (Bharat-Samvad-Article-Template.docx). The first part is a
small set of metadata lines, each of the form "Key: value", then the body.

Required metadata (one per line):
    Date:     2026-05-30          (ISO format)
    Page:     1
    Section:  Foreign Policy
    Kicker:   Diplomacy · Security
    Byline:   Special Correspondent
    Location: New Delhi
    Headline: India and Russia sign new defence pact
    Subdeck:  One-line summary appears here.

Then the body. Supported markers:
    LEAD: First paragraph (gets the drop cap).
    A regular paragraph.
    ## A sub-heading
    BOX: At a Glance               (followed by lines starting with "- Label — value")
    PULL: "A striking quote."
    — Source name                  (must follow PULL line)

Usage (from repo root):
    python scripts/build_from_docx.py
"""
import os, sys, re, json, hashlib, glob, time, subprocess
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
CONTENT = ROOT / "content"
CACHE = SCRIPTS / ".translations-cache"
CACHE.mkdir(exist_ok=True)

sys.path.insert(0, str(SCRIPTS))
os.chdir(SCRIPTS)
from tribuilder import build  # noqa

# ---------- docx → plain text (via pandoc) ----------
def docx_to_text(docx_path):
    """Use pandoc to convert .docx to plain markdown-style text."""
    result = subprocess.run(
        ["pandoc", "-f", "docx", "-t", "markdown", "--wrap=none", str(docx_path)],
        capture_output=True, text=True, check=True,
    )
    text = result.stdout
    # Normalise: drop pandoc's {.class} annotations
    text = re.sub(r"\{[^{}]*\}", "", text)
    # Un-escape markdown punctuation (pandoc adds backslashes before #, -, ., *, ", ', etc.)
    text = re.sub(r"""\\([#\-.*_+`(){}\[\]<>!"'])""", r"\1", text)
    # Pandoc renders em-dash as "---". Convert back to a real em-dash.
    text = text.replace(" --- ", " — ")
    # Also handle when ---  appears at end/start with no spaces (rare in body but safe)
    text = text.replace("---", "—")
    # Drop lines that are entirely italic (pandoc *…*) — those are template instructions.
    cleaned = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("*") and s.endswith("*") and len(s) >= 2 and not s.startswith("**"):
            continue
        cleaned.append(ln)
    return "\n".join(cleaned)

# ---------- parse our template format from the extracted text ----------
KNOWN_META = ["date","page","section","kicker","byline","location","headline","subdeck"]

def parse_article_text(text):
    """Return (frontmatter dict, body blocks list)."""
    lines = [l.rstrip() for l in text.splitlines()]
    fm = {}
    i = 0
    # Walk to collect metadata. Pandoc puts blank lines between paragraphs,
    # so blank lines do NOT terminate metadata. We stop only when we hit a
    # non-blank line that isn't a known metadata key (after we've found
    # at least one), or run out of lines.
    body_start = None
    while i < len(lines):
        s = lines[i].strip()
        s_clean = re.sub(r"^\*\*|\*\*$", "", s).strip()
        if not s_clean:
            i += 1; continue
        m = re.match(r"^([A-Za-z][A-Za-z ]*):\s*(.+?)\s*$", s_clean)
        if m and m.group(1).strip().lower() in KNOWN_META:
            fm[m.group(1).strip().lower()] = m.group(2).strip()
            i += 1; continue
        # not a metadata line
        if fm:
            body_start = i
            break
        # haven't found any metadata yet — skip (title, headers, intro text)
        i += 1
    if body_start is None:
        body_start = i

    # ensure required fields
    for req in ("date","page","section","headline"):
        if req not in fm:
            raise ValueError(f"Missing required field in Word doc: {req}")

    # body parsing starts from body_start
    i = body_start

    # body
    blocks, buf = [], []
    def flush(typ="p"):
        nonlocal buf
        if buf:
            t = " ".join(s.strip() for s in buf if s.strip())
            if t: blocks.append((typ, t))
            buf = []

    while i < len(lines):
        ln = lines[i].rstrip()
        # strip pandoc's **bold** wrapping on header-style lines
        s = re.sub(r"^\*\*|\*\*$", "", ln.strip()).strip()
        if not s:
            flush(); i += 1; continue
        # Skip lines that look like pandoc's "BODY ---" or "METADATA ---" labels
        if re.match(r"^(BODY|METADATA)\b", s, re.IGNORECASE):
            i += 1; continue
        if s.startswith("## "):
            flush(); blocks.append(("h3", s[3:].strip())); i += 1; continue
        if s.startswith("LEAD:"):
            flush(); buf = [s[5:].strip()]; i += 1
            while i < len(lines) and lines[i].strip():
                buf.append(lines[i].strip()); i += 1
            flush("lead"); continue
        if s.startswith("BOX:"):
            flush(); title = s[4:].strip(); i += 1; items = []
            # Collect "- label — value" items; tolerate blank lines between them
            while i < len(lines):
                bs = lines[i].strip()
                if not bs:
                    i += 1; continue
                if not (bs.startswith("- ") or bs.startswith("* ")):
                    break
                line = re.sub(r"^[-*]\s+", "", bs)
                sep = " — " if " — " in line else (" - " if " - " in line else None)
                if sep:
                    lbl, val = line.split(sep, 1)
                else:
                    lbl, val = line, ""
                items.append((lbl.strip(), val.strip())); i += 1
            blocks.append(("box", {"title": title, "items": items})); continue
        if s.startswith("PULL:"):
            flush(); quote = s[5:].strip(); i += 1
            cite = ""
            # Look for the citation line (starts with em-dash); tolerate blanks
            while i < len(lines):
                bs = lines[i].strip()
                if not bs:
                    i += 1; continue
                if bs.startswith("—") or bs.startswith("--"):
                    cite = bs; i += 1
                break
            blocks.append(("pull", {"q": quote, "c": cite})); continue
        buf.append(ln); i += 1
    flush()
    return fm, blocks

# ---------- Free translator (googletrans) ----------
def get_translator():
    from googletrans import Translator
    return Translator()

def translate_one(translator, text, target):
    for attempt in range(3):
        try:
            r = translator.translate(text, src="en", dest=target)
            return r.text
        except Exception as e:
            if attempt < 2:
                time.sleep(1.5*(attempt+1)); continue
            print(f"    ! translation failed for ({target}): {e}")
            return text

def translate_batch(texts_en):
    translator = get_translator()
    out = {}
    for i, (key, text) in enumerate(texts_en.items(), 1):
        hi = translate_one(translator, text, "hi")
        ur = translate_one(translator, text, "ur")
        out[key] = {"hi": hi, "en": text, "ur": ur}
        if i % 5 == 0: print(f"    … {i}/{len(texts_en)} translated")
    return out

def collect_strings(fm, blocks):
    out = {}
    for k in ("section","kicker","byline","location","headline","subdeck"):
        if fm.get(k): out[f"fm.{k}"] = fm[k]
    for idx,(typ,payload) in enumerate(blocks):
        if typ in ("lead","p","h3"):
            out[f"b{idx}"] = payload
        elif typ == "box":
            out[f"b{idx}.title"] = payload["title"]
            for j,(lbl,val) in enumerate(payload["items"]):
                out[f"b{idx}.il.{j}"] = lbl
                out[f"b{idx}.iv.{j}"] = val
        elif typ == "pull":
            out[f"b{idx}.q"] = payload["q"]
            if payload["c"]: out[f"b{idx}.c"] = payload["c"]
    return out

# ---------- dates ----------
WEEKDAYS = {
 "Monday":{"hi":"सोमवार","en":"Monday","ur":"پیر"},
 "Tuesday":{"hi":"मंगलवार","en":"Tuesday","ur":"منگل"},
 "Wednesday":{"hi":"बुधवार","en":"Wednesday","ur":"بدھ"},
 "Thursday":{"hi":"गुरुवार","en":"Thursday","ur":"جمعرات"},
 "Friday":{"hi":"शुक्रवार","en":"Friday","ur":"جمعہ"},
 "Saturday":{"hi":"शनिवार","en":"Saturday","ur":"ہفتہ"},
 "Sunday":{"hi":"रविवार","en":"Sunday","ur":"اتوار"},
}
MONTHS = {
 1:{"hi":"जनवरी","en":"January","ur":"جنوری"},
 2:{"hi":"फ़रवरी","en":"February","ur":"فروری"},
 3:{"hi":"मार्च","en":"March","ur":"مارچ"},
 4:{"hi":"अप्रैल","en":"April","ur":"اپریل"},
 5:{"hi":"मई","en":"May","ur":"مئی"},
 6:{"hi":"जून","en":"June","ur":"جون"},
 7:{"hi":"जुलाई","en":"July","ur":"جولائی"},
 8:{"hi":"अगस्त","en":"August","ur":"اگست"},
 9:{"hi":"सितंबर","en":"September","ur":"ستمبر"},
 10:{"hi":"अक्टूबर","en":"October","ur":"اکتوبر"},
 11:{"hi":"नवंबर","en":"November","ur":"نومبر"},
 12:{"hi":"दिसंबर","en":"December","ur":"دسمبر"},
}
def date_strings(iso):
    y,m,d = map(int, iso.split("-")); dt = date(y,m,d); wd = dt.strftime("%A")
    return {
      "hi": f"{WEEKDAYS[wd]['hi']}, {d} {MONTHS[m]['hi']} {y}",
      "en": f"{WEEKDAYS[wd]['en']}, {d} {MONTHS[m]['en']} {y}",
      "ur": f"{WEEKDAYS[wd]['ur']}، {d} {MONTHS[m]['ur']} {y}",
    }

PAGE_WORD = {"hi":"पृष्ठ","en":"Page","ur":"صفحہ"}
SPECIAL   = {"hi":"विशेष रिपोर्ट","en":"Special Report","ur":"خصوصی رپورٹ"}
FOOT_M    = {"hi":"© 2026 भारत संवाद प्रकाशन","en":"© 2026 Bharat Samvad Publications","ur":"© 2026 بھارت سنواد پبلیکیشنز"}

def build_lang_dict(lang, fm, blocks, T, date_strs):
    page = str(fm.get("page","1")).strip()
    location = T.get("fm.location", {}).get(lang, fm.get("location",""))
    byline   = T.get("fm.byline",   {}).get(lang, fm.get("byline",""))
    A = {
      "strip_left": f"{PAGE_WORD[lang]} {page} · {T['fm.section'][lang]}",
      "strip_mid":  SPECIAL[lang],
      "date":       date_strs[lang],
      "kicker":     T["fm.kicker"][lang] if "fm.kicker" in T else "",
      "head":       T["fm.headline"][lang],
      "sub":        T["fm.subdeck"][lang] if "fm.subdeck" in T else "",
      "byline":     f"<b>{byline}</b> · {location}" if location else f"<b>{byline}</b>",
      "foot_l":     {"hi":f"भारत संवाद · {T['fm.section']['hi']} डेस्क",
                     "en":f"Bharat Samvad · {T['fm.section']['en']} Desk",
                     "ur":f"بھارت سنواد · {T['fm.section']['ur']} ڈیسک"}[lang],
      "foot_m":     FOOT_M[lang],
      "foot_p":     f"{PAGE_WORD[lang]} {page}",
      "box_title":"", "box_items":[], "pull_q":"", "pull_c":"",
      "body": [],
    }
    for idx,(typ,payload) in enumerate(blocks):
        if typ in ("lead","p","h3"):
            A["body"].append((typ, T[f"b{idx}"][lang]))
        elif typ == "box":
            A["box_title"] = T[f"b{idx}.title"][lang]
            A["box_items"] = [(T[f"b{idx}.il.{j}"][lang] + " — ", T[f"b{idx}.iv.{j}"][lang])
                              for j in range(len(payload["items"]))]
            A["body"].append(("BOX",""))
        elif typ == "pull":
            A["pull_q"] = T[f"b{idx}.q"][lang]
            A["pull_c"] = T.get(f"b{idx}.c", {}).get(lang, payload.get("c",""))
            A["body"].append(("PULL",""))
    return A

def build_article(docx_path):
    print(f"  → reading docx via pandoc …")
    text = docx_to_text(docx_path)
    fm, blocks = parse_article_text(text)
    src = collect_strings(fm, blocks)
    h = hashlib.sha256(json.dumps(src, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    cache_file = CACHE / (Path(docx_path).stem + ".json")
    T = None
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if cached.get("hash") == h:
                T = cached["t"]
                for k,v in src.items():
                    if k in T: T[k]["en"] = v
        except Exception:
            T = None
    if T is None:
        print(f"  → translating {len(src)} strings via googletrans (free) …")
        T = translate_batch(src)
        cache_file.write_text(json.dumps({"hash": h, "t": T}, ensure_ascii=False, indent=2), encoding="utf-8")
    date_strs = date_strings(fm["date"])
    langs = {l: build_lang_dict(l, fm, blocks, T, date_strs) for l in ("hi","en","ur")}
    page = str(fm.get("page","1")).strip()
    out_name = f"bharatsamvad-{fm['date']}-page{page}.html"
    out_path = ROOT / out_name
    build(str(out_path), "भारत संवाद · Bharat Samvad · بھارت سنواد", langs)
    print(f"  ✓ wrote {out_name}")
    return {
      "href": out_name, "date": date_strs, "page": page,
      "section": {l: T["fm.section"][l] for l in ("hi","en","ur")},
      "headline": {l: T["fm.headline"][l] for l in ("hi","en","ur")},
      "date_iso": fm["date"],
    }

def regenerate_index(articles):
    by_date = {}
    for a in articles: by_date.setdefault(a["date_iso"], []).append(a)
    sorted_dates = sorted(by_date.keys(), reverse=True)
    DAYS_LIST = []
    for i, d in enumerate(sorted_dates):
        items = sorted(by_date[d], key=lambda x: int(x["page"]))
        DAYS_LIST.append({
          "latest": (i == 0),
          "date": items[0]["date"],
          "cards": [
            {"href": a["href"],
             "label": {l: f"{PAGE_WORD[l]} {a['page']} · {a['section'][l]}" for l in ("hi","en","ur")},
             "title": a["headline"]}
            for a in items
          ],
        })
    home_src = (SCRIPTS / "build_home_tri.py").read_text(encoding="utf-8")
    new_days = "DAYS = " + json.dumps(DAYS_LIST, ensure_ascii=False, indent=1)
    home_src = re.sub(r"DAYS = \[.*?^\]", new_days, home_src, flags=re.DOTALL|re.MULTILINE)
    tmp = SCRIPTS / "_run_home.py"
    tmp.write_text(home_src, encoding="utf-8")
    os.chdir(SCRIPTS)
    import runpy; runpy.run_path(str(tmp))
    src = SCRIPTS / "index.html"
    (ROOT / "index.html").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    tmp.unlink(missing_ok=True); src.unlink(missing_ok=True)
    print(f"  ✓ regenerated index.html ({len(articles)} articles, {len(sorted_dates)} day(s))")

def main():
    docx_files = sorted(glob.glob(str(CONTENT / "*.docx")))
    if not docx_files:
        print("No .docx files found in content/."); return
    print(f"Found {len(docx_files)} article(s).")
    arts = []
    for f in docx_files:
        print(f"• {os.path.basename(f)}")
        try: arts.append(build_article(f))
        except Exception as e: print(f"  ✗ ERROR: {e}")
    if arts: regenerate_index(arts)
    print("Done.")

if __name__ == "__main__":
    main()
