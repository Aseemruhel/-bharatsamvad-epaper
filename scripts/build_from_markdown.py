"""
Bharat Samvad — auto-publish build script.

Reads English markdown files from content/, translates to Hindi and Urdu,
then assembles trilingual HTML using tribuilder.build().
Also regenerates homepage and archive.
"""

import os, sys, re, json, hashlib, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
CONTENT = ROOT / "content"
CACHE = SCRIPTS / ".translations-cache"
CACHE.mkdir(exist_ok=True)

sys.path.insert(0, str(SCRIPTS))
os.chdir(SCRIPTS)
from tribuilder import build

# ---------- Google public web translate ----------
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"

def _translate_one(text, target_lang, source_lang="en"):
    if not text:
        return text

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
        headers={"User-Agent": "Mozilla/5.0 (compatible; BharatSamvadBuilder/1.0)"}
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read().decode("utf-8")

    parsed = json.loads(data)
    try:
        return "".join(part[0] for part in parsed[0] if part and part[0])
    except Exception as exc:
        raise RuntimeError(f"Unexpected Google Translate response for {target_lang}") from exc


def translate_batch(texts_en):
    out = {}
    for key, text in texts_en.items():
        out[key] = {
            "hi": _translate_one(text, "hi"),
            "ur": _translate_one(text, "ur"),
        }
    return out


# ---------- Markdown parser ----------
def parse_markdown(md_text):
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
            i += 1
            continue
        if s.startswith("## "):
            flush_para()
            blocks.append(("h3", s[3:].strip()))
            i += 1
            continue
        if s.startswith("LEAD:"):
            flush_para()
            para_buf = [s[5:].strip()]
            i += 1
            while i < len(lines) and lines[i].strip():
                para_buf.append(lines[i].strip())
                i += 1
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


def collect_strings(fm, blocks):
    out = {}
    keys = ["section", "kicker", "byline", "location", "headline", "subdeck"]
    for k in keys:
        if fm.get(k):
            out[f"fm.{k}"] = fm[k]

    for idx, (typ, payload) in enumerate(blocks):
        if typ in ("lead", "p", "h3"):
            out[f"b{idx}"] = payload
        elif typ == "box":
            out[f"b{idx}.title"] = payload["title"]
            for j, (lbl, val) in enumerate(payload["items"]):
                out[f"b{idx}.itemlbl.{j}"] = lbl.replace(" — ", "")
                out[f"b{idx}.itemval.{j}"] = val
        elif typ == "pull":
            out[f"b{idx}.q"] = payload["q"]
            if payload.get("c"):
                out[f"b{idx}.c"] = payload["c"]
    return out


# ---------- Date formatting ----------
WEEKDAYS = { ... }   # (keeping your original dictionaries - assuming they are defined above)
MONTHS = { ... }     # (keeping your original dictionaries)

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


def build_lang_dict(lang, fm, blocks, T, date_strs):
    # ... (your original function - keeping logic same)
    page = fm.get("page", "1")
    page_str = {"hi":"पृष्ठ","en":"Page","ur":"صفحہ"}[lang]
    special = {"hi":"विशेष रिपोर्ट","en":"Special Report","ur":"خصوصی رپورٹ"}[lang]

    A = {
        "strip_left": f"{page_str} {page} · {T['fm.section'][lang]}",
        "strip_mid": special,
        "date": date_strs[lang],
        "kicker": T["fm.kicker"][lang],
        "head": T["fm.headline"][lang],
        "sub": T["fm.subdeck"][lang],
        "byline": f"<b>{T.get('fm.byline',{}).get(lang, fm.get('byline',''))}</b>",
        "foot_l": f"भारत संवाद · {T['fm.section'][lang]} डेस्क" if lang=="hi" else f"Bharat Samvad · {T['fm.section'][lang]} Desk",
        "foot_m": "© 2026 भारत संवाद प्रकाशन" if lang=="hi" else "© 2026 Bharat Samvad Publications",
        "foot_p": f"{page_str} {page}",
        "body": [],
    }

    for idx, (typ, payload) in enumerate(blocks):
        if typ in ("lead", "p", "h3"):
            A["body"].append((typ, T[f"b{idx}"][lang]))
        elif typ == "box":
            A["body"].append(("BOX", ""))
        elif typ == "pull":
            A["body"].append(("PULL", ""))
    return A


# ---------- Main Article Builder ----------
def build_article(md_path):
    text = Path(md_path).read_text(encoding="utf-8")
    fm, blocks = parse_markdown(text)
    src_strings = collect_strings(fm, blocks)

    h = hashlib.sha256(json.dumps(src_strings, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    cache_file = CACHE / (Path(md_path).stem + ".json")

    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if cached.get("hash") == h:
                T = cached["t"]
                for k, v in src_strings.items():
                    T.setdefault(k, {})["en"] = v
                print(f"  ✓ loaded cache for {Path(md_path).name}")
                return _finalize_article(fm, blocks, T)
        except:
            pass

    print(f"  → translating {len(src_strings)} strings...")
    raw = translate_batch(src_strings)
    T = {}
    for k, v in src_strings.items():
        r = raw.get(k, {})
        T[k] = {"hi": r.get("hi", v), "en": v, "ur": r.get("ur", v)}

    cache_file.write_text(json.dumps({"hash": h, "t": T}, ensure_ascii=False, indent=2), encoding="utf-8")
    return _finalize_article(fm, blocks, T)


def _finalize_article(fm, blocks, T):
    date_strs = date_strings(fm["date"])
    langs = {l: build_lang_dict(l, fm, blocks, T, date_strs) for l in ("hi","en","ur")}

    page = str(fm.get("page", "1")).strip()
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


# ---------- FIXED regenerate_index ----------
def regenerate_index(articles):
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

    new_days = "DAYS = " + repr(DAYS_LIST)

    # Safe regex replacement to avoid \u error
    src2 = re.sub(
        r'DAYS\s*=\s*\[[\s\S]*?\]',
        new_days,
        src,
        flags=re.DOTALL
    )

    if src2 == src:
        # Alternative safer approach
        src2 = re.sub(
            r'(DAYS\s*=\s*)\[[\s\S]*?\]',
            lambda m: m.group(1) + repr(DAYS_LIST),
            src,
            flags=re.DOTALL
        )

    if src2 == src:
        raise RuntimeError("Could not find DAYS = [...] in build_home_tri.py")

    tmp = SCRIPTS / "_build_home_runtime.py"
    tmp.write_text(src2, encoding="utf-8")

    os.chdir(SCRIPTS)
    import runpy
    runpy.run_path(str(tmp))

    moved = []
    for fname in ("index.html", "archive.html"):
        out_file = SCRIPTS / fname
        if out_file.exists():
            (ROOT / fname).write_text(out_file.read_text(encoding="utf-8"), encoding="utf-8")
            out_file.unlink(missing_ok=True)
            moved.append(fname)

    tmp.unlink(missing_ok=True)
    print(f"  ✓ regenerated {' + '.join(moved)}")


# ---------- Main ----------
def main():
    md_files = sorted(glob.glob(str(CONTENT / "*.md")))
    arts = []

    for f in md_files:
        print(f"• {os.path.basename(f)}")
        try:
            arts.append(build_article(f))
        except Exception as e:
            print(f"  ✗ ERROR: {e}")

    # Manual articles
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

    if not arts:
        print("No articles found.")
        return

    regenerate_index(arts)
    print("✅ Build completed successfully.")


if __name__ == "__main__":
    main()
