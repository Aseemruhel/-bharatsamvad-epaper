"""
Bharat Samvad — auto-publish build script.
"""

import os, sys, re, json, hashlib, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
CONTENT = ROOT / "content"
ARTICLES = ROOT / "articles"
ARTICLES.mkdir(exist_ok=True)
CACHE = SCRIPTS / ".translations-cache"
CACHE.mkdir(exist_ok=True)

sys.path.insert(0, str(SCRIPTS))
os.chdir(SCRIPTS)
from tribuilder import build

# ---------- IndicTrans2 ----------
from IndicTransToolkit import IndicProcessor
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE = 4

# Hugging Face auth token for gated ai4bharat/indictrans2-* models.
# Set as a GitHub Actions secret named HF_TOKEN and exposed via `env:` in the workflow.
HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
if not HF_TOKEN:
    print("  ⚠ HF_TOKEN not set — gated IndicTrans2 model access will fail with 401.")
    print("    See: https://huggingface.co/ai4bharat/indictrans2-en-indic-1B")

def _load_model(src_lang_code):
    ckpt = "ai4bharat/indictrans2-en-indic-1B"
    tokenizer = AutoTokenizer.from_pretrained(
        ckpt,
        trust_remote_code=True,
        token=HF_TOKEN,
    )
    model = AutoModelForSeq2SeqLM.from_pretrained(
        ckpt,
        trust_remote_code=True,
        token=HF_TOKEN,
    ).to(DEVICE)
    processor = IndicProcessor(inference=True)
    return tokenizer, model, processor

_MODEL_CACHE = {}

def _get_model():
    if "en-indic" not in _MODEL_CACHE:
        print("  → loading IndicTrans2 model (en → Indic)...")
        _MODEL_CACHE["en-indic"] = _load_model("eng_Latn")
    return _MODEL_CACHE["en-indic"]

LANG_CODE = {
    "hi": "hin_Deva",
    "ur": "urd_Arab",
}

def _translate_list(texts, tgt_lang_code):
    tokenizer, model, processor = _get_model()
    results = []
    for i in range(0, len(texts), BATCH_SIZE):
        chunk = texts[i:i + BATCH_SIZE]
        batch = processor.preprocess_batch(chunk, src_lang="eng_Latn", tgt_lang=tgt_lang_code)
        inputs = tokenizer(
            batch,
            truncation=True,
            padding="longest",
            return_tensors="pt",
            return_attention_mask=True,
        ).to(DEVICE)
        with torch.no_grad():
            generated = model.generate(
                **inputs,
                num_beams=5,
                num_return_sequences=1,
                max_length=256,
            )
        decoded = tokenizer.batch_decode(generated, skip_special_tokens=True)
        results.extend(processor.postprocess_batch(decoded, lang=tgt_lang_code))
    return results

def translate_batch(texts_en):
    keys = list(texts_en.keys())
    texts = list(texts_en.values())
    hi_translations = _translate_list(texts, LANG_CODE["hi"])
    ur_translations = _translate_list(texts, LANG_CODE["ur"])
    return {
        key: {"hi": hi_translations[i], "ur": ur_translations[i]}
        for i, key in enumerate(keys)
    }
# ---------- Markdown Parser ----------
def parse_markdown(md_text):
    if not md_text.startswith("---"):
        raise ValueError("Article must start with ---")
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
    for k in ["section", "kicker", "byline", "location", "headline", "subdeck"]:
        if fm.get(k):
            out[f"fm.{k}"] = fm[k]

    for idx, (typ, payload) in enumerate(blocks):
        if typ in ("lead", "p", "h3"):
            out[f"b{idx}"] = payload
        elif typ == "box":
            out[f"b{idx}.title"] = payload["title"]
            for j, (lbl, val) in enumerate(payload.get("items", [])):
                out[f"b{idx}.itemlbl.{j}"] = lbl.replace(" — ", "")
                out[f"b{idx}.itemval.{j}"] = val
        elif typ == "pull":
            out[f"b{idx}.q"] = payload["q"]
            if payload.get("c"):
                out[f"b{idx}.c"] = payload["c"]
    return out


# ---------- Date Dictionaries ----------
WEEKDAYS = {
    "Monday":    {"hi":"सोमवार", "en":"Monday",    "ur":"پیر"},
    "Tuesday":   {"hi":"मंगलवार","en":"Tuesday",   "ur":"منگل"},
    "Wednesday": {"hi":"बुधवार", "en":"Wednesday", "ur":"بدھ"},
    "Thursday":  {"hi":"गुरुवार","en":"Thursday",  "ur":"جمعرات"},
    "Friday":    {"hi":"शुक्रवार","en":"Friday",    "ur":"جمعہ"},
    "Saturday":  {"hi":"शनिवार", "en":"Saturday",  "ur":"ہفتہ"},
    "Sunday":    {"hi":"रविवार", "en":"Sunday",    "ur":"اتوار"},
}

MONTHS = {
    1: {"hi":"जनवरी", "en":"January", "ur":"جنوری"},
    2: {"hi":"फरवरी", "en":"February","ur":"فروری"},
    3: {"hi":"मार्च",  "en":"March",    "ur":"مارچ"},
    4: {"hi":"अप्रैल", "en":"April",    "ur":"اپریل"},
    5: {"hi":"मई",     "en":"May",      "ur":"مئی"},
    6: {"hi":"जून",    "en":"June",     "ur":"جون"},
    7: {"hi":"जुलाई",  "en":"July",     "ur":"جولائی"},
    8: {"hi":"अगस्त",  "en":"August",   "ur":"اگست"},
    9: {"hi":"सितंबर","en":"September","ur":"ستمبر"},
    10:{"hi":"अक्टूबर","en":"October",  "ur":"اکتوبر"},
    11:{"hi":"नवंबर", "en":"November", "ur":"نومبر"},
    12:{"hi":"दिसंबर","en":"December", "ur":"دسمبر"},
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


# ---------- This Day in Indian History ----------
def load_this_day():
    """
    Load today's entries from content/this_day.md (based on IST).
    Format per line: MM-DD: YEAR — HI text || EN text || UR text
    Returns a list of dicts: [{"year": "1969", "hi": "...", "en": "...", "ur": "..."}, ...]
    Returns [] if no entries for today (sidebar hides itself gracefully).
    """
    try:
        from datetime import datetime
        try:
            from zoneinfo import ZoneInfo
            ist = ZoneInfo("Asia/Kolkata")
        except Exception:
            # Fallback if zoneinfo unavailable — use UTC + fixed offset for IST
            from datetime import timezone, timedelta
            ist = timezone(timedelta(hours=5, minutes=30))
        today = datetime.now(ist)
    except Exception as e:
        print(f"  ⚠ this_day: could not determine IST date: {e}")
        from datetime import datetime
        today = datetime.now()
    
    key = today.strftime("%m-%d")
    
    this_day_file = CONTENT / "this_day.md"
    if not this_day_file.exists():
        print(f"  ⚠ this_day: content/this_day.md not found; sidebar will hide")
        return []
    
    entries = []
    for line in this_day_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Match "MM-DD: rest" where MM-DD is today's key
        if not line.startswith(key + ":"):
            continue
        try:
            # Strip "MM-DD: " prefix (6 chars: "07-16:" + space)
            rest = line[len(key) + 1:].strip()
            # Split year from event text at first em-dash
            if "—" in rest:
                year, texts = rest.split("—", 1)
            elif " - " in rest:
                year, texts = rest.split(" - ", 1)
            else:
                print(f"  ⚠ this_day: no year separator in: {line[:60]}...")
                continue
            year = year.strip()
            texts = texts.strip()
            # Split trilingual by ||
            parts = [p.strip() for p in texts.split("||")]
            if len(parts) != 3:
                print(f"  ⚠ this_day: expected 3 lang parts (HI || EN || UR), got {len(parts)}: {line[:60]}...")
                continue
            entries.append({
                "year": year,
                "hi": parts[0],
                "en": parts[1],
                "ur": parts[2],
            })
        except Exception as e:
            print(f"  ⚠ this_day: could not parse: {line[:60]}... ({e})")
    
    if entries:
        print(f"  ✓ loaded {len(entries)} 'this day' entry/entries for {key} (IST)")
    else:
        print(f"  ℹ this_day: no entries for {key} (IST); sidebar will hide")
    return entries


# ---------- Build Language Dict ----------
def build_lang_dict(lang, fm, blocks, T, date_strs):
    page = fm.get("page", "1")
    page_str = {"hi":"पृष्ठ","en":"Page","ur":"صفحہ"}[lang]
    special = {"hi":"विशेष रिपोर्ट","en":"Special Report","ur":"خصوصی رپورٹ"}[lang]

    A = {
        "strip_left": f"{page_str} {page} · {T['fm.section'][lang]}",
        "strip_mid":  special,
        "date":       date_strs[lang],
        "kicker":     T.get("fm.kicker", {}).get(lang, fm.get("kicker", "")),
        "head":       T.get("fm.headline", {}).get(lang, fm.get("headline", "")),
        "sub":        T.get("fm.subdeck", {}).get(lang, fm.get("subdeck", "")),
        "byline":     f"<b>{T.get('fm.byline',{}).get(lang, fm.get('byline',''))}</b> · {T.get('fm.location',{}).get(lang, fm.get('location',''))}",
        "foot_l":     f"भारत संवाद · {T['fm.section'][lang]} डेस्क" if lang == "hi" else f"Bharat Samvad · {T['fm.section'][lang]} Desk",
        "foot_m":     "© 2026 भारत संवाद प्रकाशन" if lang == "hi" else "© 2026 Bharat Samvad Publications",
        "foot_p":     f"{page_str} {page}",
        "body":       [],
        "box_title":  "",
        "box_items":  [],
        "pull_q":     "",
        "pull_c":     "",
    }

    for idx, (typ, payload) in enumerate(blocks):
        if typ in ("lead", "p", "h3"):
            A["body"].append((typ, T[f"b{idx}"][lang]))
        elif typ == "box":
            A["box_title"] = T.get(f"b{idx}.title", {}).get(lang, "")
            A["box_items"] = [
                (T.get(f"b{idx}.itemlbl.{j}", {}).get(lang, lbl), 
                 T.get(f"b{idx}.itemval.{j}", {}).get(lang, val))
                for j, (lbl, val) in enumerate(payload.get("items", []))
            ]
            A["body"].append(("BOX", ""))
        elif typ == "pull":
            A["pull_q"] = T.get(f"b{idx}.q", {}).get(lang, "")
            A["pull_c"] = T.get(f"b{idx}.c", {}).get(lang, "")
            A["body"].append(("PULL", ""))
    return A


# ---------- Build Article ----------
def build_article(md_path):
    text = Path(md_path).read_text(encoding="utf-8")
    fm, blocks = parse_markdown(text)
    src_strings = collect_strings(fm, blocks)

    h = hashlib.sha256(json.dumps(src_strings, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    cache_file = CACHE / (Path(md_path).stem + ".json")

    T = None
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if cached.get("hash") == h:
                T = cached["t"]
                print(f"  ✓ loaded cache for {Path(md_path).name}")
        except:
            pass

    if T is None:
        print(f"  → translating {len(src_strings)} strings...")
        raw = translate_batch(src_strings)
        T = {}
        for k, v in src_strings.items():
            r = raw.get(k, {})
            T[k] = {"hi": r.get("hi", v), "en": v, "ur": r.get("ur", v)}
        cache_file.write_text(json.dumps({"hash": h, "t": T}, ensure_ascii=False, indent=2), encoding="utf-8")

    date_strs = date_strings(fm["date"])
    langs = {l: build_lang_dict(l, fm, blocks, T, date_strs) for l in ("hi","en","ur")}

    page = str(fm.get("page", "1"))
    out_name = f"bharatsamvad-{fm['date']}-page{page}.html"
    out_path = ARTICLES / out_name

    build(str(out_path), "भारत संवाद", langs)

    # Post-process: tribuilder.py writes URLs and links assuming the article is at
    # the repo root. Since we now write under /articles/, fix up the URLs so social
    # cards and the back-home button work correctly.
    try:
        html = out_path.read_text(encoding="utf-8")
        # Fix OG / Twitter / canonical URLs to include /articles/ in the path
        html = re.sub(
            r'(content="https?://[^/"]+)/(bharatsamvad-\d{4}-\d{2}-\d{2}-page\d+\.html")',
            r'\1/articles/\2',
            html,
        )
        html = re.sub(
            r'(href="https?://[^/"]+)/(bharatsamvad-\d{4}-\d{2}-\d{2}-page\d+\.html")',
            r'\1/articles/\2',
            html,
        )
        # Fix back-home / masthead links: from inside /articles/, index.html resolves
        # to /articles/index.html (which doesn't exist). Change to relative parent.
        html = re.sub(
            r'href="index\.html"',
            r'href="../index.html"',
            html,
        )
        out_path.write_text(html, encoding="utf-8")
    except Exception as e:
        print(f"  ⚠ post-process URL fix failed for {out_name}: {e}")

    print(f"  ✓ wrote articles/{out_name}")

    return {
        "href": f"articles/{out_name}",
        "date": date_strs,
        "page": page,
        "section": {l: T["fm.section"][l] for l in ("hi","en","ur")},
        "headline": {l: T["fm.headline"][l] for l in ("hi","en","ur")},
        "date_iso": fm["date"],
    }


# ---------- Regenerate Index ----------
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

    # Read ticker items from content/ticker.md (optional)
    ticker_items = []
    ticker_file = CONTENT / "ticker.md"
    if ticker_file.exists():
        for line in ticker_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            ticker_items.append(line)
        print(f"  ✓ loaded {len(ticker_items)} ticker item(s) from content/ticker.md")

    # Load "This Day in Indian History" entries for today (IST)
    this_day_items = load_this_day()

    new_days = "DAYS = " + repr(DAYS_LIST)
    new_ticker = "TICKER_ITEMS = " + repr(ticker_items)
    new_this_day = "THIS_DAY_ITEMS = " + repr(this_day_items)

    # Inject DAYS list
    src2 = re.sub(
        r'DAYS\s*=\s*\[[\s\S]*?\]',
        lambda match: new_days,
        src,
        flags=re.DOTALL
    )

    # Fallback if first pattern didn't match
    if src2 == src:
        src2 = re.sub(
            r'(DAYS\s*=\s*)\[[\s\S]*?\]',
            lambda match: match.group(1) + repr(DAYS_LIST),
            src,
            flags=re.DOTALL
        )

    if src2 == src:
        raise RuntimeError("Could not find 'DAYS = [...]' in build_home_tri.py. Please check the file.")

    # Inject TICKER_ITEMS (line-anchored pattern)
    src2 = re.sub(
        r"^TICKER_ITEMS\s*=\s*\[.*?\]",
        lambda m: new_ticker,
        src2,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )

    # Inject THIS_DAY_ITEMS (line-anchored pattern)
    src2 = re.sub(
        r"^THIS_DAY_ITEMS\s*=\s*\[.*?\]",
        lambda m: new_this_day,
        src2,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )

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
    print(f"  ✓ regenerated {' + '.join(moved)} with {len(articles)} articles")


# ---------- Auto-discover hand-uploaded HTML articles ----------
def discover_html_articles(existing_hrefs):
    """
    Scan ROOT for hand-uploaded bharatsamvad-YYYY-MM-DD-pageN.html files.
    Skip any that are already in existing_hrefs (built from markdown / manual JSON).
    Extract headline + section from the article's langblocks; fall back to <title>
    for Word-saved HTML that lacks the langblock structure.
    Returns a list of article dicts in the same shape as build_article() output.
    """
    discovered = []
    pattern = re.compile(r"^bharatsamvad-(\d{4}-\d{2}-\d{2})-page(\d+)\.html$")
    scan_locations = [
        (ARTICLES, "articles/"),
        (ROOT,     ""),
    ]
    for scan_dir, href_prefix in scan_locations:
        if not scan_dir.is_dir():
            continue
        for fname in sorted(os.listdir(scan_dir)):
            m = pattern.match(fname)
            if not m:
                continue
            href = href_prefix + fname
            if href in existing_hrefs or fname in existing_hrefs:
                continue
            if href_prefix == "" and (ARTICLES / fname).exists():
                continue
            date_iso = m.group(1)
            page = m.group(2)
            try:
                html = (scan_dir / fname).read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                print(f"  ✗ could not read {href}: {e}")
                continue

            headline = {"hi": "", "en": "", "ur": ""}
            section  = {"hi": "", "en": "", "ur": ""}
            lang_starts = {}
            for lang in ("hi", "en", "ur"):
                m_start = re.search(
                    rf'<div class="langblock"\s+data-lang="{lang}"[^>]*>',
                    html,
                )
                if m_start:
                    lang_starts[lang] = m_start.end()
            all_block_starts = sorted([m.start() for m in re.finditer(r'<div class="langblock"\s+data-lang="(?:hi|en|ur)"', html)])
            for lang, start_pos in lang_starts.items():
                next_starts = [p for p in all_block_starts if p > start_pos]
                end_pos = next_starts[0] if next_starts else len(html)
                scope = html[start_pos:end_pos]
                h_m = re.search(r'<h\d[^>]*class="headline"[^>]*>(.*?)</h\d>', scope, re.DOTALL)
                if h_m:
                    headline[lang] = re.sub(r"<[^>]+>", "", h_m.group(1)).strip()
                s_m = re.search(r'<span[^>]*>([^<]+)</span>\s*<span class="mid"', scope)
                if s_m:
                    left = s_m.group(1).strip()
                    section[lang] = re.sub(r"^\S+\s+\d+\s*·\s*", "", left).strip()

            if not any(headline.values()):
                t_m = re.search(r"<title>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
                if t_m:
                    title_txt = re.sub(r"<[^>]+>", "", t_m.group(1)).strip()
                    headline = {"hi": title_txt, "en": title_txt, "ur": title_txt}
            if not any(section.values()):
                section = {"hi": "लेख", "en": "Article", "ur": "مضمون"}
            for lang in ("hi", "ur"):
                if not headline[lang]: headline[lang] = headline["en"]
                if not section[lang]:  section[lang]  = section["en"]

            date_strs = date_strings(date_iso)
            discovered.append({
                "href": href,
                "date": date_strs,
                "page": page,
                "section": section,
                "headline": headline,
                "date_iso": date_iso,
            })
            print(f"  ✓ discovered {href}")
    return discovered


# ---------- Main ----------
def main():
    md_files = sorted(f for f in glob.glob(str(CONTENT / "*.md")) if os.path.basename(f) not in ("ticker.md", "this_day.md"))
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
        try:
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
        except Exception as e:
            print(f"  ✗ manual_articles error: {e}")

    # Auto-discover hand-uploaded HTML articles in repo root
    existing_hrefs = {a["href"] for a in arts}
    discovered = discover_html_articles(existing_hrefs)
    if discovered:
        print(f"• auto-discovered {len(discovered)} hand-uploaded HTML article(s)")
        arts.extend(discovered)

    if not arts:
        print("No articles found.")
        return

    regenerate_index(arts)
    print("✅ Build completed successfully.")


if __name__ == "__main__":
    main()
