#!/usr/bin/env python3
"""
One-shot migration: move bharatsamvad-YYYY-MM-DD-pageN.html files from
repo root into the articles/ subfolder.

Safe to re-run — only moves files that are actually at the root, and
explicitly leaves per-date index pages alone (those lack the -pageN suffix).

If a file is already present at articles/X.html and ALSO at root, the
root-level copy is removed to clean up the duplicate.
"""

import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
ARTICLES.mkdir(exist_ok=True)

# Matches article files like bharatsamvad-2026-06-09-page2.html
# Deliberately does NOT match per-date index pages like bharatsamvad-2026-06-09.html
pattern = re.compile(r"^bharatsamvad-\d{4}-\d{2}-\d{2}-page\d+\.html$")

moved = []
deduped = []

for fname in sorted(os.listdir(ROOT)):
    if not pattern.match(fname):
        continue

    src = ROOT / fname
    dst = ARTICLES / fname

    if not src.is_file():
        # could be a directory in some odd repo state — skip
        continue

    if dst.exists():
        # Already migrated to articles/, remove the root-level duplicate
        print(f"  ⚠ already in articles/, removing root duplicate: {fname}")
        src.unlink()
        deduped.append(fname)
        continue

    # Standard case: move from root → articles/
    shutil.move(str(src), str(dst))
    print(f"  ✓ moved {fname} → articles/{fname}")
    moved.append(fname)

print()
print("=== Migration Summary ===")
print(f"  Moved into articles/   : {len(moved)} file(s)")
print(f"  Root duplicates removed: {len(deduped)} file(s)")

if not moved and not deduped:
    print()
    print("Nothing to migrate — repo root is already clean.")
