"""
figure_extractor.py
-------------------
Extracts figure images from a PDF and saves them as PNG files.

Strategy
--------
The PDF may contain figures as either embedded raster images or as
vector/composite graphics with no single large raster.  Both cases are
handled:

  Raster figures   — pdfplumber detects a single large embedded image on
                     the page.  Its bounding box is converted from PDF
                     coordinates to PIL pixel coordinates and cropped.

  Vector figures   — pdfplumber finds no large raster.  The page is
                     rendered at full resolution and a region is cropped
                     using the figure caption's y-position as the lower
                     boundary.

Figure captions are detected by scanning for the pattern「図 N-N」using
pdfplumber's word extraction.

Public API
----------
    extract_figures(pdf_path, out_dir) -> dict[str, Path]
        Returns {figure_id: saved_path}, e.g. {"4-1": Path("figures/fig_4_1.png")}
"""

from __future__ import annotations

import re
from pathlib import Path

import pdf2image
import pdfplumber
from PIL import Image

from config import (
    DEFAULT_IMG_PREFIX,
    MIN_FIGURE_HEIGHT_PT,
    MIN_FIGURE_WIDTH_PT,
    PAGE_HEADER_HEIGHT_PT,
    PAGE_LEFT_MARGIN_PT,
    PAGE_RIGHT_MARGIN_PT,
    PDF_DPI,
    PDF_POINTS_PER_INCH,
)

# ── Module-level constants ────────────────────────────────────────────────────

# Pixel scale: one PDF point equals this many pixels at PDF_DPI.
_SCALE: float = PDF_DPI / PDF_POINTS_PER_INCH

# Matches figure captions: 「図 3-1」「図4-1」「図 4-1」(optional spaces, full-width dash)
_CAPTION_RE = re.compile(r"図\s*([\d]+[-－][\d]+)")


# ── Coordinate conversion ─────────────────────────────────────────────────────

def _pdf_box_to_pil(
    x0: float,
    y0_pdf: float,
    x1: float,
    y1_pdf: float,
    page_height: float,
) -> tuple[int, int, int, int]:
    """
    Convert a rectangle from PDF space (origin bottom-left, units = points)
    to PIL space (origin top-left, units = pixels at PDF_DPI).
    """
    pil_x0 = int(x0 * _SCALE)
    pil_y0 = int((page_height - y1_pdf) * _SCALE)
    pil_x1 = int(x1 * _SCALE)
    pil_y1 = int((page_height - y0_pdf) * _SCALE)
    return (pil_x0, pil_y0, pil_x1, pil_y1)


# ── Caption detection ─────────────────────────────────────────────────────────

def _find_captions(page: pdfplumber.page.Page) -> list[tuple[str, float]]:
    """
    Return [(figure_id, y_top), …] for every figure caption on *page*.
    y_top is measured from the top of the page in PDF points.
    Only the first occurrence of each figure_id is kept.
    """
    found: list[tuple[str, float]] = []
    seen: set[str] = set()
    words = page.extract_words()

    for i, word in enumerate(words):
        if word["text"] != "図":
            continue
        snippet = " ".join(w["text"] for w in words[i: i + 4])
        m = _CAPTION_RE.search(snippet)
        if m:
            fig_id = m.group(1).replace("－", "-")
            if fig_id not in seen:
                seen.add(fig_id)
                found.append((fig_id, word["top"]))

    return found


# ── Cropping strategies ───────────────────────────────────────────────────────

def _crop_raster(
    page: pdfplumber.page.Page,
    page_img: Image.Image,
) -> Image.Image | None:
    """
    If exactly one large raster image is embedded on *page*, crop and return
    it.  Returns None when zero or multiple large rasters are found.
    """
    large = [
        img for img in page.images
        if img["width"] >= MIN_FIGURE_WIDTH_PT
        and img["height"] >= MIN_FIGURE_HEIGHT_PT
    ]
    if len(large) != 1:
        return None

    img = large[0]
    box = _pdf_box_to_pil(img["x0"], img["y0"], img["x1"], img["y1"], page.height)
    return page_img.crop(box)


def _crop_vector(
    page: pdfplumber.page.Page,
    page_img: Image.Image,
    caption_y: float,
) -> Image.Image:
    """
    Crop the page region between the header band and just above the figure
    caption.  Used when the figure is drawn as vector graphics.
    """
    top    = PAGE_HEADER_HEIGHT_PT
    bottom = caption_y - 5.0                    # small gap above caption text
    left   = PAGE_LEFT_MARGIN_PT
    right  = page.width - PAGE_RIGHT_MARGIN_PT

    x0, y0, x1, y1 = _pdf_box_to_pil(left, bottom, right, top, page.height)
    # Ensure y0 < y1 regardless of coordinate orientation
    if y0 > y1:
        y0, y1 = y1, y0

    return page_img.crop((x0, y0, x1, y1))


# ── Public API ────────────────────────────────────────────────────────────────

def extract_figures(
    pdf_path: str | Path,
    out_dir: str | Path,
) -> dict[str, Path]:
    """
    Extract all figures from *pdf_path* and write them as PNGs to *out_dir*.

    Parameters
    ----------
    pdf_path : str | Path
        Path to the source PDF file.
    out_dir : str | Path
        Directory where cropped PNG files will be saved.  Created if absent.

    Returns
    -------
    dict[str, Path]
        Maps figure_id → saved image path.
        Example: {"3-1": PosixPath("figures/fig_3_1.png")}
    """
    pdf_path = Path(pdf_path)
    out_dir  = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[figure_extractor] Rendering PDF at {PDF_DPI} DPI …")
    page_images: list[Image.Image] = pdf2image.convert_from_path(
        str(pdf_path), dpi=PDF_DPI
    )

    saved: dict[str, Path] = {}

    with pdfplumber.open(str(pdf_path)) as pdf:
        for pg_idx, page in enumerate(pdf.pages):
            captions = _find_captions(page)
            if not captions:
                continue

            page_img = page_images[pg_idx]

            for fig_id, caption_y in captions:
                # Try raster extraction first; fall back to vector region crop.
                cropped = _crop_raster(page, page_img)
                if cropped is None:
                    cropped = _crop_vector(page, page_img, caption_y)

                safe_id  = fig_id.replace("-", "_")
                filename = f"{DEFAULT_IMG_PREFIX}_{safe_id}.png"
                dest     = out_dir / filename
                cropped.save(str(dest))
                saved[fig_id] = dest

                print(
                    f"  [figure_extractor] page {pg_idx + 1:>2}  "
                    f"fig {fig_id} → {dest.name}  {cropped.size}"
                )

    print(f"[figure_extractor] {len(saved)} figure(s) saved to '{out_dir}'")
    return saved
