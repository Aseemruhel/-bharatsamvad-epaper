# -*- coding: utf-8 -*-
# ===================================================================
#  भारत संवाद — NEW ARTICLE RECIPE (trilingual, with optional poll)
# ===================================================================
#  HOW TO USE:
#   1. Copy this file, rename it (e.g. build_2026-05-28-page1.py).
#   2. Fill in the hi / en / ur dictionaries below.
#   3. (Optional) keep the POLL block to add a language-aware poll,
#      or delete it and remove the ("POLL","") line from each body.
#   4. Run:  python3 <yourfile>.py
#   It writes the finished HTML at the OUTFILE name you set.
#   Fonts + language toggle + poll engine are added automatically.
#
#  BODY tokens you can use in the "body" list, in any order:
#     ("lead", "first paragraph (gets the big drop-cap)")
#     ("p",    "a normal paragraph")
#     ("h3",   "a sub-heading")
#     ("BOX",  "")     -> inserts the 'At a Glance' box (uses box_title/box_items)
#     ("PULL", "")     -> inserts the pull-quote (uses pull_q/pull_c)
#     ("POLL", "")     -> inserts the poll (uses the "poll" dict; see below)
# ===================================================================
from tribuilder import build

OUTFILE = "bharatsamvad-2026-05-28-page1.html"      # <-- date-based name
TITLE   = "भारत संवाद · Bharat Samvad · بھارت سنواد — पृष्ठ 01"

# ---- OPTIONAL POLL (shared across all 3 languages; delete if not needed) ----
POLL = {
 "id":"unique-poll-id-here",          # MUST be unique per poll
 "q":{"hi":"प्रश्न हिंदी में?","en":"Question in English?","ur":"سوال اردو میں؟"},
 "options":[
   {"opt":"a","hi":"विकल्प 1","en":"Option 1","ur":"آپشن 1"},
   {"opt":"b","hi":"विकल्प 2","en":"Option 2","ur":"آپشن 2"},
   {"opt":"c","hi":"विकल्प 3","en":"Option 3","ur":"آپشن 3"},
 ],
}

hi = {
 "strip_left":"पृष्ठ 01 · खंड","strip_mid":"विशेष रिपोर्ट","date":"<वार>, <दिनांक> 2026",
 "kicker":"श्रेणी · उपश्रेणी",
 "head":"यहाँ मुख्य शीर्षक",
 "sub":"यहाँ एक-दो पंक्ति का सारांश।",
 "byline":"<b>विशेष संवाददाता</b> · स्थान",
 "box_title":"एक नज़र में",
 "box_items":[("बिंदु — ","विवरण"),("बिंदु — ","विवरण")],
 "pull_q":'"यहाँ एक प्रभावशाली उद्धरण।"',
 "pull_c":"— स्रोत (आशय)",
 "foot_l":"भारत संवाद · डेस्क","foot_m":"© 2026 भारत संवाद प्रकाशन","foot_p":"पृष्ठ 01",
 "poll":POLL,
 "body":[
   ("lead","पहला अनुच्छेद।"),
   ("p","दूसरा अनुच्छेद।"),
   ("h3","उपशीर्षक"),
   ("p","अनुच्छेद।"),
   ("BOX",""),
   ("PULL",""),
   ("POLL",""),         # <-- poll appears here; delete this line if no poll
   ("h3","आगे की राह"),
   ("p","समापन अनुच्छेद।"),
 ],
}

en = {
 "strip_left":"Page 01 · Section","strip_mid":"Special Report","date":"<Day>, <Date> 2026",
 "kicker":"Category · Subcategory",
 "head":"Main headline here",
 "sub":"One- or two-line summary here.",
 "byline":"<b>Special Correspondent</b> · Place",
 "box_title":"At a Glance",
 "box_items":[("Point — ","detail"),("Point — ","detail")],
 "pull_q":'"A striking quote here."',
 "pull_c":"— Source (paraphrased)",
 "foot_l":"Bharat Samvad · Desk","foot_m":"© 2026 Bharat Samvad Publications","foot_p":"Page 01",
 "poll":POLL,
 "body":[
   ("lead","First paragraph."),
   ("p","Second paragraph."),
   ("h3","Sub-heading"),
   ("p","Paragraph."),
   ("BOX",""),
   ("PULL",""),
   ("POLL",""),
   ("h3","The road ahead"),
   ("p","Closing paragraph."),
 ],
}

ur = {
 "strip_left":"صفحہ 1 · سیکشن","strip_mid":"خصوصی رپورٹ","date":"<دن>، <تاریخ> 2026",
 "kicker":"زمرہ · ذیلی زمرہ",
 "head":"یہاں مرکزی سرخی",
 "sub":"یہاں ایک یا دو سطری خلاصہ۔",
 "byline":"<b>خصوصی نامہ نگار</b> · مقام",
 "box_title":"ایک نظر میں",
 "box_items":[("نکتہ — ","تفصیل"),("نکتہ — ","تفصیل")],
 "pull_q":'"یہاں ایک مؤثر اقتباس۔"',
 "pull_c":"— ماخذ (مفہوم)",
 "foot_l":"بھارت سنواد · ڈیسک","foot_m":"© 2026 بھارت سنواد پبلیکیشنز","foot_p":"صفحہ 1",
 "poll":POLL,
 "body":[
   ("lead","پہلا پیراگراف۔"),
   ("p","دوسرا پیراگراف۔"),
   ("h3","ذیلی سرخی"),
   ("p","پیراگراف۔"),
   ("BOX",""),
   ("PULL",""),
   ("POLL",""),
   ("h3","آگے کا راستہ"),
   ("p","اختتامی پیراگراف۔"),
 ],
}

# To add a photo: pass photo_b64="...base64..." to build(...)
build(OUTFILE, TITLE, {"hi":hi,"en":en,"ur":ur})
print("written:", OUTFILE)
