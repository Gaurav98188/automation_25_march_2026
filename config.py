"""
config.py
---------
Central configuration for the MD pipeline.

All tuneable knobs live here.  No other module contains document-specific
values or magic numbers — change behaviour by editing this file only.

Sections
--------
  PDF rendering       DPI and coordinate system constants
  Figure cropping     Size thresholds and page-margin offsets
  Output paths        Default directory / filename prefix for figures
  Boilerplate         Regex patterns for per-page footer/header noise
  Symbol fixes        Character substitutions for OCR artefacts
  TOC entries         Section list used to rebuild the Table of Contents
"""

from __future__ import annotations

DEFAULT_IMG_DIR = "figures"
DEBUG_DIR = "_debug_steps"

# ── PDF rendering ─────────────────────────────────────────────────────────────
# Dots-per-inch used when rendering PDF pages to raster images for cropping.
# Higher values produce sharper figure crops but use more memory and time.
PDF_DPI: int = 150

# Standard PDF coordinate unit (points per inch).  Do not change.
PDF_POINTS_PER_INCH: float = 72.0


# ── Figure cropping ───────────────────────────────────────────────────────────
# A raster image embedded in the PDF must be at least this large (in PDF
# points) to be treated as a figure rather than an icon or bullet graphic.
MIN_FIGURE_WIDTH_PT: float = 80.0
MIN_FIGURE_HEIGHT_PT: float = 40.0

# When a figure is drawn in vector graphics (no single large embedded raster),
# we crop the page region between the header band and the figure caption.
# These offsets (in PDF points) define that region.
PAGE_HEADER_HEIGHT_PT: float = 80.0   # skip this many points from the top
PAGE_LEFT_MARGIN_PT: float = 60.0    # crop starts this far from the left edge
PAGE_RIGHT_MARGIN_PT: float = 40.0   # crop ends this far from the right edge


# ── Output paths ──────────────────────────────────────────────────────────────
# Default sub-directory for extracted figure PNGs (relative to the output .md).
DEFAULT_IMG_DIR: str = "figures"

# Filename prefix for saved figures.  e.g. "fig" → fig_4_1.png
DEFAULT_IMG_PREFIX: str = "fig"


# ── Boilerplate removal ───────────────────────────────────────────────────────
# Every line in the input Markdown that fully matches one of these patterns
# is removed.  These patterns target the repeated per-page decorative border
# text that PDF-to-Markdown tools extract verbatim.
#
# Add new patterns here when adapting the pipeline to a different PDF template.
BOILERPLATE_LINE_PATTERNS: list[str] = [
    # Page comment artefacts
    r"^<!-- PageFooter:.*-->$",
    r"^<!-- PageHeader: 記 録 MEMO -->$",
    r"^<!-- PageHeader: C7450b.*-->$",
    r"^<!-- PageHeader: \|.*-->$",

    # Company / document footer text
    r"^MITSUBISHI ELECTRIC SOFTWARE\s*$",
    r"^作成[·・]照査\s*$",
    r"^DRAWN\s*$",
    r"^日\s*付\s*$",
    r"^DATE\s*$",
    r"^設計[·・\s]*検認\s*$",
    r"^APPROVED\s*$",
    r"^TITLE\s*$",
    r"^DWG\.NO\.\s*$",
    r"^MCO23-01K0004\s*$",
    r"^記\s*録\s*$",
    r"^MEMO\s*$",
    r"^10071-B\s*$",

    # Bare page numbers (1–99) appearing as standalone lines
    r"^\d{1,2}\s*$",

    # Heading artefacts
    r"^#\s+記\s*録\s+MEMO\s*$",
    r"^#{1,6}\s+MITSUBISHI ELECTRIC SOFTWARE\s*$",
]


# ── Symbol normalisation ──────────────────────────────────────────────────────
# Plain string substitutions applied first (order matters for combined artefacts).
# Each entry is (find_string, replace_string).
SYMBOL_REPLACEMENTS: list[tuple[str, str]] = [
    ("\u2612", "\u3007"),       # ☒  → 〇  (ballot box X → white circle)
    ("\U0001F518", "\u3007"),   # 🔘 → 〇  (radio button emoji → white circle)
]

# Regex substitutions applied after the plain replacements.
# Each entry is (regex_pattern, replacement_string).
SYMBOL_REGEX_REPLACEMENTS: list[tuple[str, str]] = [
    (r"△\s*☒", "△"),   # "△ ☒" → "△"  (conditional + stray checkbox)
    (r"☒\s*△", "△"),   # "☒ △" → "△"
    (r"一\s*☒", "一"),  # "一 ☒" → "一"  (not-applicable + stray checkbox)
]


# ── TOC entries ───────────────────────────────────────────────────────────────
# Defines the Table of Contents structure for the output document.
# Each entry is a tuple of:
#   (indent_px, anchor_id, display_label, page_number)
#
# indent_px   : left-padding in pixels (0 = top-level, 20 = level 2, 40 = level 3)
# anchor_id   : href target, e.g. "1-はじめに"  →  <a href="#1-はじめに">
# display_label : text shown in the TOC
# page_number : page number shown in the right column
#
# Update this list when adapting the pipeline to a different document.

"""
TOC_ENTRIES: list[tuple[int, str, str, str]] = [
    (0,  "1-はじめに",                        "1. はじめに",                         "4"),
    (20, "11-改造内容",                        "1.1. 改造内容",                       "4"),
    (20, "12-関連図書",                        "1.2. 関連図書",                       "4"),
    (0,  "2-構成",                             "2. 構成",                             "4"),
    (20, "21-システム構成",                    "2.1. システム構成",                    "4"),
    (20, "22-ソフトウェア構成",                "2.2. ソフトウェア構成",                "4"),
    (0,  "3-機能仕様",                         "3. 機能仕様",                         "5"),
    (20, "31-機能一覧",                        "3.1. 機能一覧",                       "5"),
    (20, "32-バックアップ機能",                "3.2. バックアップ機能",                "5"),
    (40, "321バックアップの種類と対象データ",   "3.2.1. バックアップの種類と対象データ", "5"),
    (40, "322任意フォルダへのバックアップ",     "3.2.2. 任意フォルダへのバックアップ",  "6"),
    (40, "323-dbへのバックアップ",             "3.2.3. DBへのバックアップ",            "10"),
    (40, "324-クラウドへのバックアップ",        "3.2.4. クラウドへのバックアップ",      "10"),
    (40, "325-エラー処理",                     "3.2.5. エラー処理",                   "11"),
    (20, "33バックアップデータ表示機能",        "3.3. バックアップデータ表示機能",      "14"),
    (40, "331ヒストリカルトレンド表示機能",     "3.3.1. ヒストリカルトレンド表示機能",  "14"),
    (20, "34-データ削除機能",                  "3.4. データ削除機能",                 "14"),
    (0,  "4-画面仕様",                         "4. 画面仕様",                         "15"),
    (20, "41ヒストリカルデータ管理画面",        "4.1. ヒストリカルデータ管理画面",      "15"),
    (40, "411一括操作",                        "4.1.1. 一括操作",                     "15"),
    (40, "412-個別操作",                       "4.1.2. 個別操作",                     "25"),
]
"""