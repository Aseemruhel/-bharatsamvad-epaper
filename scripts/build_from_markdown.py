"""
Bharat Samvad — auto-publish build script.

Reads English markdown files from content/, uses Google's public web translate
endpoint to translate each article's strings to Hindi and Urdu, then assembles
a trilingual HTML file using tribuilder.build(). Also regenerates the homepage
index.

Caches translations per-file so unchanged articles are not re-translated.

Usage (from repo root):
  python scripts/build_from_markdown.py
Env: requires internet access. No API key is required
"""
import os, sys, re, json, hashlib, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repo root
SCRIPTS = ROOT / "scripts"
CONTENT = ROOT / "content"
CACHE = SCRIPTS / ".translations-cache"
CACHE.mkdir(exist_ok=True)

sys.path.insert(0, str(SCRIPTS))
os.chdir(SCRIPTS)  # so tribuilder finds _style.tmp / _urdu.tmp
from tribuilder import build  # noqa

# ---------- Google public web translate ----------
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"

def _translate_one(text, target_lang, source_lang="en"):
    """Translate one string with Google's public web translate endpoint."""
    if not text:
        return text

    # Google Translate can occasionally be sensitive to very long strings.
    # The article format normally sends headline/paragraph-sized strings, so
    # translating one collected string at a time keeps requests small and cacheable.
    import urllib.parse
    import urllib.request

    params = {
        "client": "gtx",
        "sl": source_lang,
        "tl": target_lang,
        "dt": "t",
        "q": text,
    }
    url = GOOGLE_TRANSLATE_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; BharatSamvadBuilder/1.0)"
        },
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read().decode("utf-8")

    parsed = json.loads(data)

    # Response shape is typically:
    # [[["translated part","source part",...], ...], ...]
    try:
        return "".join(part[0] for part in parsed[0] if part and part[0])
    except Exception as exc:
        raise RuntimeError(f"Unexpected Google Translate response for {target_lang}: {data[:300]}") from exc

def translate_batch(texts_en):
    """texts_en: dict[str, str]. Returns dict[str, {hi, ur}]."""
    out = {}
    for key, text in texts_en.items():
        out[key] = {
            "hi": _translate_one(text, "hi"),
            "ur": _translate_one(text, "ur"),
        }
    return out

# ---------- Markdown parser ----------
def parse_markdown(md_text):
    """Parses our simple article format → (frontmatter dict, body blocks list).
    Body blocks are (typ, payload) where typ in {lead, p, h3, box, pull}."""
    if not md_text.startswith("---"):
        raise ValueError("Article must start with --- frontmatter ---")
    _, fm_text, body_text = md_text.split("---", 2)
    fm = {}
    for line in fm_text.strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()

    blocks = []
    lines = body_text.strip().splitlines()
    i = 0
    para_buf = []

    def flush_para(typ_default="p"):
        nonlocal para_buf
        if para_buf:
            text = " ".join(s.strip() for s in para_buf if s.strip())
            if text:
                blocks.append((typ_default, text))
            para_buf = []

    while i < len(lines):
        ln = lines[i].rstrip()
        s = ln.strip()
        if not s:
            flush_para()
            i += 1; continue
        if s.startswith("## "):
            flush_para()
            blocks.append(("h3", s[3:].strip()))
            i += 1; continue
        if s.startswith("LEAD:"):
            flush_para()
            para_buf = [s[5:].strip()]
            i += 1
            while i < len(lines) and lines[i].strip():
                para_buf.append(lines[i].strip()); i += 1
            flush_para("lead")
            continue
        if s.startswith("BOX:"):
            flush_para()
            title = s[4:].strip()
            i += 1
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                line = lines[i].strip()[2:]
                if " — " in line:
                    lbl, val = line.split(" — ", 1)
                elif " - " in line:
                    lbl, val = line.split(" - ", 1)
                else:
                    lbl, val = line, ""
                items.append((lbl.strip() + " — ", val.strip()))
                i += 1
            blocks.append(("box", {"title": title, "items": items}))
            continue
        if s.startswith("PULL:"):
            flush_para()
            quote = s[5:].strip()
            i += 1
            cite = ""
            if i < len(lines) and lines[i].strip().startswith("—"):
                cite = lines[i].strip()
                i += 1
            blocks.append(("pull", {"q": quote, "c": cite}))
            continue
        para_buf.append(ln)
        i += 1
    flush_para()
    return fm, blocks

# ---------- collect strings for translation ----------
def collect_strings(fm, blocks):
    out = {}
    keys_to_translate = ["section", "kicker", "byline", "location", "headline", "subdeck"]
    for k in keys_to_translate:
        if fm.get(k):
            out[f"fm.{k}"] = fm[k]
    for idx, (typ, payload) in enumerate(blocks):
        if typ in ("lead", "p", "h3"):
            out[f"b{idx}"] = payload
        elif typ == "box":
            out[f"b{idx}.title"] = payload["title"]
            for j, (lbl, val) in enumerate(payload["items"]):
                # translate just the label without trailing " — "
                out[f"b{idx}.itemlbl.{j}"] = lbl.replace(" — ", "")
                out[f"b{idx}.itemval.{j}"] = val
        elif typ == "pull":
            out[f"b{idx}.q"] = payload["q"]
            if payload["c"]:
                out[f"b{idx}.c"] = payload["c"]
    return out

# ---------- date formatting per language ----------
WEEKDAYS = {
    "Monday":   {"hi":"सोमवार",  "en":"Monday",    "ur":"پیر"},
    "Tuesday":  {"hi":"मंगलवार", "en":"Tuesday",   "ur":"منگل"},
    "Wednesday":{"hi":"बुधवार",  "en":"Wednesday", "ur":"بدھ"},
    "Thursday": {"hi":"गुरुवार", "en":"Thursday",  "ur":"جمعرات"},
    "Friday":   {"hi":"शुक्रवार","en":"Friday",    "ur":"جمعہ"},
    "Saturday": {"hi":"शनिवार",  "en":"Saturday",  "ur":"ہفتہ"},
    "Sunday":   {"hi":"रविवार",  "en":"Sunday",    "ur":"اتوار"},
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
def date_strings(date_iso):
    from datetime import date
    y, m, d = map(int, date_iso.split("-"))
    dt = date(y, m, d)
    wd = dt.strftime("%A")
    return {
      "hi": f"{WEEKDAYS[wd]['hi']}, {d} {MONTHS[m]['hi']} {y}",
      "en": f"{WEEKDAYS[wd]['en']}, {d} {MONTHS[m]['en']} {y}",
      "ur": f"{WEEKDAYS[wd]['ur']}، {d} {MONTHS[m]['ur']} {y}",
    }

# ---------- assemble per-language content dicts for tribuilder ----------
def build_lang_dict(lang, fm, blocks, T, date_strs):
    page = fm.get("page", "1")
    page_str = {"hi":"पृष्ठ","en":"Page","ur":"صفحہ"}[lang]
    special = {"hi":"विशेष रिपोर्ट","en":"Special Report","ur":"خصوصی رپورٹ"}[lang]
    foot_l_map = {
      "hi": f"भारत संवाद · {T['fm.section']['hi']} डेस्क",
      "en": f"Bharat Samvad · {T['fm.section']['en']} Desk",
      "ur": f"بھارت سنواد · {T['fm.section']['ur']} ڈیسک",
    }
    foot_m_map = {
      "hi":"© 2026 भारत संवाद प्रकाशन",
      "en":"© 2026 Bharat Samvad Publications",
      "ur":"© 2026 بھارت سنواد پبلیکیشنز",
    }
    location = T.get("fm.location", {}).get(lang, fm.get("location",""))
    byline = T.get("fm.byline", {}).get(lang, fm.get("byline",""))

    A = {
      "strip_left": f"{page_str} {page} · {T['fm.section'][lang]}",
      "strip_mid":  special,
      "date":       date_strs[lang],
      "kicker":     T["fm.kicker"][lang],
      "head":       T["fm.headline"][lang],
      "sub":        T["fm.subdeck"][lang],
      "byline":     f"<b>{byline}</b> · {location}" if location else f"<b>{byline}</b>",
      "foot_l":     foot_l_map[lang],
      "foot_m":     foot_m_map[lang],
      "foot_p":     f"{page_str} {page}",
      "body":       [],
      "box_title":  "",
      "box_items":  [],
      "pull_q":     "",
      "pull_c":     "",
    }
    for idx, (typ, payload) in enumerate(blocks):
        if typ in ("lead","p","h3"):
            A["body"].append((typ, T[f"b{idx}"][lang]))
        elif typ == "box":
            A["box_title"] = T[f"b{idx}.title"][lang]
            A["box_items"] = [
              (T[f"b{idx}.itemlbl.{j}"][lang] + " — ", T[f"b{idx}.itemval.{j}"][lang])
              for j in range(len(payload["items"]))
            ]
            A["body"].append(("BOX",""))
        elif typ == "pull":
            A["pull_q"] = T[f"b{idx}.q"][lang]
            A["pull_c"] = T.get(f"b{idx}.c", {}).get(lang, payload.get("c",""))
            A["body"].append(("PULL",""))
    return A

# ---------- single article build with translation caching ----------
def build_article(md_path):
    text = Path(md_path).read_text(encoding="utf-8")
    fm, blocks = parse_markdown(text)
    src_strings = collect_strings(fm, blocks)

    # cache by content hash
    h = hashlib.sha256(json.dumps(src_strings, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    cache_file = CACHE / (Path(md_path).stem + ".json")
    T = None
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if cached.get("hash") == h:
                T = cached["t"]
                # add identity-mapped English to each entry
                for k, v in src_strings.items():
                    T[k]["en"] = v
        except Exception:
            T = None
    if T is None:
        print(f"  → translating {len(src_strings)} strings via Google public web translate…")
        raw = translate_batch(src_strings)
        # ensure each value has hi+ur, and add the original English
        T = {}
        for k, v in src_strings.items():
            r = raw.get(k, {})
            T[k] = {"hi": r.get("hi", v), "en": v, "ur": r.get("ur", v)}
        cache_file.write_text(json.dumps({"hash": h, "t": T}, ensure_ascii=False, indent=2), encoding="utf-8")

    # dates
    date_strs = date_strings(fm["date"])
    # per-lang dicts
    langs = {l: build_lang_dict(l, fm, blocks, T, date_strs) for l in ("hi","en","ur")}

    # output file name based on date + page
    page = str(fm.get("page","1")).strip()
    out_name = f"bharatsamvad-{fm['date']}-page{page}.html"
    out_path = ROOT / out_name
    title = "भारत संवाद · Bharat Samvad · بھارت سنواد"
    build(str(out_path), title, langs)
    print(f"  ✓ wrote {out_name}")
    return {
        "href": out_name,
        "date": date_strs,
        "page": page,
        "section": {l: T["fm.section"][l] for l in ("hi","en","ur")},
        "headline": {l: T["fm.headline"][l] for l in ("hi","en","ur")},
        "date_iso": fm["date"],
    }

# ---------- regenerate homepage ----------
# ---------- regenerate homepage ----------
def regenerate_index(articles):
    # group by date_iso desc
    by_date = {}
    for a in articles:
        by_date.setdefault(a["date_iso"], []).append(a)

    sorted_dates = sorted(by_date.keys(), reverse=True)

    DAYS_LIST = []
    for i, d in enumerate(sorted_dates):
        items = sorted(by_date[d], key=lambda x: int(x["page"]))
        DAYS_LIST.append({
            "latest": (i == 0),
            "date": items[0]["date"],
            "cards": [
                {
                    "href": a["href"],
                    "label": {
                        l: f"{ {'hi':'पृष्ठ','en':'Page','ur':'صفحہ'}[l] } {a['page']} · {a['section'][l]}"
                        for l in ("hi", "en", "ur")
                    },
                    "title": a["headline"]
                }
                for a in items
            ],
        })

    home_path = SCRIPTS / "build_home_tri.py"
    src = home_path.read_text(encoding="utf-8")

    new_days = new_days = "DAYS = " + repr(DAYS_LIST)

    src2 = re.sub(
        r"^DAYS\s*=\s*.*$",
        new_days,
        src,
        count=1,
        flags=re.MULTILINE
    )

    if src2 == src:
        raise RuntimeError("Could not inject article list into build_home_tri.py. Check the DAYS = [] line.")

    tmp = SCRIPTS / "_build_home_runtime.py"
    tmp.write_text(src2, encoding="utf-8")

    # the homepage generator writes index.html into its CWD (scripts/), so we move it after
    os.chdir(SCRIPTS)
    import runpy
    runpy.run_path(str(tmp))
    # move/copy result to repo root
    out_index = SCRIPTS / "index.html"
    final = ROOT / "index.html"
    final.write_text(out_index.read_text(encoding="utf-8"), encoding="utf-8")

    tmp.unlink(missing_ok=True)
    out_index.unlink(missing_ok=True)

    print(f"  ✓ regenerated index.html with {len(articles)} articles across {len(sorted_dates)} day(s)")
# ---------- main ----------
def main():
    md_files = sorted(glob.glob(str(CONTENT / "*.md")))
    if not md_files:
        print("No markdown files found in content/. Nothing to build.")
        return
    print(f"Found {len(md_files)} article(s).")
    arts = []
    for f in md_files:
        print(f"• {os.path.basename(f)}")
        try:
            arts.append(build_article(f))
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
          manual_file = CONTENT / "manual_articles.json"

if manual_file.exists():
    print("• manual_articles.json")
    manual_articles = json.loads(manual_file.read_text(encoding="utf-8"))

    for a in manual_articles:
        date_strs = date_strings(a["date_iso"])
        arts.append({
            "href": a["href"],
            "date": date_strs,
            "page": str(a.get("page", "1")),
            "section": a["section"],
            "headline": a["headline"],
            "date_iso": a["date_iso"],
        })
    regenerate_index(arts)
    print("Done.")

if __name__ == "__main__":
    main()
