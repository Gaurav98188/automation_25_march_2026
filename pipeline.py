from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Callable, List
import re

from config import DEFAULT_IMG_DIR, DEBUG_DIR

from steps import (
    step_replace_cover,
    step_replace_revision,
    step_replace_toc,
    step_remove_boilerplate,
    step_remove_footer_tables,
    step_remove_memo,
    step_remove_empty_rows,
    step_normalise_symbols,
    step_fix_headings,
    step_rewrite_images,
    step_clean_tables,
    step_clean_whitespace,
    step_add_heading_ids
)

# ── Logging ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

Step = Callable[[str, dict], str]


# ── TOC extractor (FINAL STABLE) ─────────────────────────
def extract_toc_entries(md_path):
    text = Path(md_path).read_text(encoding="utf-8")

    # STEP 1: Extract Page 3
    page3_match = re.search(
        r'(.*?<!-- PageNumber:\s*3\s*-->)',
        text,
        flags=re.DOTALL
    )

    if not page3_match:
        return []

    page3 = page3_match.group(1)

    # 🔥 FIX: normalize <br> → newline
    page3 = re.sub(r'<br\s*/?>', '\n', page3)

    # STEP 2: find ALL tables
    tables = re.findall(r'<table.*?>.*?</table>', page3, flags=re.DOTALL)

    if not tables:
        return []

    # STEP 3: pick biggest table
    table = max(tables, key=len)

    # 🔥 FIX: normalize again inside table
    table = re.sub(r'<br\s*/?>', '\n', table)

    rows = re.findall(r'<tr>(.*?)</tr>', table, flags=re.DOTALL)

    entries = []

    for row in rows:

        # ❌ skip header row completely
        if "<th" in row.lower():
            continue

        cols = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, flags=re.DOTALL)
        cols = [re.sub(r'<.*?>', '', c).strip() for c in cols]

        # must have at least title + page
        if len(cols) < 3:
            continue

        title_col = cols[1]
        page_col = cols[2]

        # skip empty rows
        if not title_col.strip() or not page_col.strip():
            continue

        # handle <br>
        titles = title_col.split('\n')
        pages = page_col.split('\n')

        for t, p in zip(titles, pages):

            t = t.strip()
            p = p.strip()

            if not t or not p:
                continue

            clean_title = re.sub(r'\s+', ' ', t)

            # ✅ FIX LEVEL (correct hierarchy)
            level = (clean_title.count('.') - 1) * 20
            if level < 0:
                level = 0

            # ✅ CLEAN ANCHOR
            anchor = re.sub(r'[^\w一-龥ぁ-んァ-ン]+', '-', clean_title).strip('-')

            entries.append((level, anchor, clean_title, p))


# ── Pipeline steps ───────────────────────────────────────
PIPELINE: List[tuple[str, Step]] = [
    ("Replacing cover page", step_replace_cover),
    ("Replacing revision table", step_replace_revision),
    ("Rebuilding TOC", step_replace_toc),
    ("Removing boilerplate", step_remove_boilerplate),
    ("Removing footer tables", step_remove_footer_tables),
    ("Removing MEMO cells", step_remove_memo),
    ("Removing empty rows", step_remove_empty_rows),
    ("Normalising symbols", step_normalise_symbols),
    ("Fixing headings", step_fix_headings),
    ("Adding heading anchors", step_add_heading_ids),
    ("Rewriting images", step_rewrite_images),
    ("Cleaning tables", step_clean_tables),
    ("Cleaning whitespace", step_clean_whitespace),
]


# ── Runner ──────────────────────────────────────────────
def run(pdf_path, md_path, out_path, img_dir=None):

    pdf_path = Path(pdf_path)
    md_path = Path(md_path)
    out_path = Path(out_path)

    img_dir_path = Path(img_dir) if img_dir else out_path.parent / DEFAULT_IMG_DIR

    context = {
        "pdf_path": pdf_path,
        "img_dir": img_dir_path,
        "out_path": out_path,
        "toc_entries": extract_toc_entries(md_path),
    }

    logger.info(f"Reading {md_path}")
    text = md_path.read_text(encoding="utf-8")

    for i, (name, step) in enumerate(PIPELINE, start=1):
        logger.info(f"[step {i:02}] {name}")
        text = step(text, context)

    out_path.write_text(text, encoding="utf-8")
    logger.info(f"Done → {out_path}")


# ── CLI ─────────────────────────────────────────────────
def _build_parser():
    p = argparse.ArgumentParser(description="Markdown Cleaning Pipeline")
    p.add_argument("--pdf", required=True)
    p.add_argument("--md", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--img-dir", default=None)
    return p


if __name__ == "__main__":
    args = _build_parser().parse_args()
    run(args.pdf, args.md, args.out, args.img_dir)