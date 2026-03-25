"""
pipeline.py
-----------
Orchestrates the full PDF-to-clean-Markdown transformation pipeline.

Pipeline steps
--------------
  Step 1   figure_extractor    Crop figure images from PDF → img_dir/*.png
  Step 2   cover_replacer      Parse cover-page table     → clean key/value Markdown
  Step 3   cover_replacer      Parse revision table       → clean minimal HTML table
  Step 4   toc_builder         Rebuild TOC                → styled anchor-linked table
  Step 5   boilerplate_remover Strip per-page noise lines
  Step 6   symbol_normaliser   Fix OCR symbol artefacts   (☒/🔘 → 〇)
  Step 7   heading_fixer       Correct heading depths     (# levels by content pattern)
  Step 8   image_rewriter      Rewrite figure references  (figures/N.M → img_dir/fig_N_M.png)
  Step 9   table_cleaner       Fix page-break artefacts inside <table> blocks
  Step 10  whitespace_cleaner  Final cosmetic normalisation

CLI usage
---------
    python pipeline.py --pdf source.pdf --md input.md --out output.md
    python pipeline.py --pdf source.pdf --md input.md --out output.md --img-dir assets/figures

Python API
----------
    from pipeline import run
    run(pdf_path="source.pdf", md_path="input.md", out_path="output.md")
    run(pdf_path="source.pdf", md_path="input.md", out_path="output.md", img_dir="assets")
"""

from __future__ import annotations

import argparse
from pathlib import Path

from boilerplate_remover import remove_boilerplate
from config import DEFAULT_IMG_DIR
from cover_replacer import replace_cover, replace_revision_table
from figure_extractor import extract_figures
from heading_fixer import fix_headings
from image_rewriter import rewrite_images
from symbol_normaliser import normalise_symbols
from table_cleaner import clean_tables
from toc_builder import replace_toc
from whitespace_cleaner import clean_whitespace


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run(
    pdf_path: str | Path,
    md_path:  str | Path,
    out_path: str | Path,
    img_dir:  str | Path | None = None,
) -> None:
    """
    Execute the full transformation pipeline.

    Parameters
    ----------
    pdf_path : str | Path
        Source PDF file.  Used only for figure extraction (step 1).
    md_path : str | Path
        Raw input Markdown file produced by a PDF-to-Markdown tool.
    out_path : str | Path
        Destination for the cleaned Markdown output.
    img_dir : str | Path | None
        Directory where cropped figure PNGs are saved.
        Defaults to a ``figures/`` sub-directory next to *out_path*.
    """
    pdf_path = Path(pdf_path)
    md_path  = Path(md_path)
    out_path = Path(out_path)

    # Resolve figure output directory
    if img_dir is None:
        img_dir_path = out_path.parent / DEFAULT_IMG_DIR
    else:
        img_dir_path = Path(img_dir)

    # ── Step 1: Extract figures from PDF ──────────────────────────────────
    #_log(1, "Extracting figures from PDF …")
    #extract_figures(pdf_path, img_dir_path)

    # ── Load input Markdown ───────────────────────────────────────────────
    _log("–", f"Reading {md_path} …")
    text = md_path.read_text(encoding="utf-8")

    # ── Step 2: Replace cover page ────────────────────────────────────────
    _log(2, "Replacing cover page …")
    text = replace_cover(text)

    # ── Step 3: Replace revision table ───────────────────────────────────
    #_log(3, "Replacing revision table …")
    #text = replace_revision_table(text)

    # ── Step 4: Rebuild Table of Contents ────────────────────────────────
    #_log(4, "Rebuilding Table of Contents …")
    #text = replace_toc(text)

    # ── Step 5: Remove boilerplate lines ─────────────────────────────────
    #_log(5, "Removing boilerplate lines …")
    #text = remove_boilerplate(text)

    # ── Step 6: Normalise symbol characters ──────────────────────────────
    #_log(6, "Normalising symbols (☒ / 🔘 → 〇) …")
    #text = normalise_symbols(text)

    # ── Step 7: Fix heading levels ────────────────────────────────────────
    #_log(7, "Fixing heading levels …")
    #text = fix_headings(text)

    # ── Step 8: Rewrite image references ─────────────────────────────────
    #_log(8, "Rewriting image references …")
    # Compute a path relative to the output file for portability.
    try:
        rel_img_dir = str(img_dir_path.relative_to(out_path.parent))
    except ValueError:
        rel_img_dir = img_dir_path.name
    text = rewrite_images(text, rel_img_dir)

    # ── Step 9: Clean table artefacts ─────────────────────────────────────
    #_log(9, "Cleaning table page-break artefacts …")
    #text = clean_tables(text)

    # ── Step 10: Final whitespace cleanup ─────────────────────────────────
    #_log(10, "Final whitespace cleanup …")
    #text = clean_whitespace(text)

    # ── Write output ──────────────────────────────────────────────────────
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    _log("✓", f"Done → {out_path}  ({out_path.stat().st_size:,} bytes)")


# ── Internal helper ───────────────────────────────────────────────────────────

def _log(step: int | str, message: str) -> None:
    print(f"[step {step:>2}] {message}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pipeline",
        description="Transform a raw PDF-extracted Markdown into a clean spec document.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python pipeline.py --pdf source.pdf --md input.md --out output.md\n"
            "  python pipeline.py --pdf source.pdf --md input.md --out output.md "
            "--img-dir assets/figures\n"
        ),
    )
    p.add_argument("--pdf",     required=True,  metavar="PATH", help="Source PDF file")
    p.add_argument("--md",      required=True,  metavar="PATH", help="Raw input Markdown file")
    p.add_argument("--out",     required=True,  metavar="PATH", help="Output Markdown file")
    p.add_argument(
        "--img-dir",
        default=None,
        metavar="PATH",
        help=(
            f"Directory for extracted figure PNGs "
            f"(default: '{DEFAULT_IMG_DIR}/' next to --out)"
        ),
    )
    return p


if __name__ == "__main__":
    args = _build_parser().parse_args()
    run(
        pdf_path=args.pdf,
        md_path=args.md,
        out_path=args.out,
        img_dir=args.img_dir,
    )
