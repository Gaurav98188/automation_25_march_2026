# MD Pipeline

Converts a raw PDF-extracted Markdown file into a clean, readable specification document.  Figure images are cropped directly from the source PDF and saved as PNG files.

---

## Project structure

```
md_pipeline/
├── pipeline.py            # Entry point — orchestrates all 10 steps
├── config.py              # All tuneable constants (single file to edit per document)
├── figure_extractor.py    # Step 1  — crop figures from PDF pages
├── cover_replacer.py      # Steps 2–3 — parse cover page & revision table generically
├── toc_builder.py         # Step 4  — rebuild TOC with anchor hyperlinks
├── boilerplate_remover.py # Step 5  — strip per-page footer/header noise lines
├── symbol_normaliser.py   # Step 6  — fix OCR symbol artefacts (☒ → 〇)
├── heading_fixer.py       # Step 7  — correct Markdown heading depths
├── image_rewriter.py      # Step 8  — rewrite figure refs to real PNG paths
├── table_cleaner.py       # Step 9  — fix page-break artefacts inside HTML tables
├── whitespace_cleaner.py  # Step 10 — final cosmetic normalisation
├── requirements.txt
└── README.md
```

---

## Requirements

### Python packages

```bash
pip install -r requirements.txt
```

| Package | Purpose |
|---|---|
| `pdfplumber` | Extract text, word positions, and embedded images from PDF |
| `pdf2image` | Render PDF pages to raster images for figure cropping |
| `Pillow` | Image cropping and PNG saving |
| `beautifulsoup4` + `lxml` | Parse the cover-page HTML table |

### System dependency

`pdf2image` requires **Poppler**:

| OS | Install command |
|---|---|
| macOS | `brew install poppler` |
| Ubuntu / Debian | `sudo apt-get install poppler-utils` |
| Windows | Download from [oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases) |

---

## Usage

### Command line

```bash
# Basic — figures saved to figures/ next to output.md
python pipeline.py --pdf source.pdf --md input.md --out output.md

# Custom figure directory
python pipeline.py --pdf source.pdf --md input.md --out output.md --img-dir assets/figures
```

### Python API

```python
from pipeline import run

run(
    pdf_path="source.pdf",
    md_path="input.md",
    out_path="output.md",
    img_dir="assets/figures",   # optional; defaults to figures/ next to out_path
)
```

---

## What each step does

| Step | Module | What it fixes |
|---|---|---|
| 1 | `figure_extractor` | Crops figure images from PDF pages using caption y-position as the lower boundary |
| 2 | `cover_replacer` | Parses the cover-page HTML table **generically** — reads all values at runtime, nothing hardcoded |
| 3 | `cover_replacer` | Replaces the noisy revision table with a clean 4-column template |
| 4 | `toc_builder` | Rebuilds the TOC as a styled HTML table with `<a href="…">` anchor links |
| 5 | `boilerplate_remover` | Strips repeated footer/header noise: company name, DWG number, page numbers, etc. |
| 6 | `symbol_normaliser` | Converts `☒` and `🔘` back to the correct `〇` circle symbol |
| 7 | `heading_fixer` | Corrects `#` depth by section-number pattern (`N.N.N` → `####`, `(N).` → `#####`) |
| 8 | `image_rewriter` | Rewrites `figures/15.1` refs to `figures/fig_15_1.png`; preserves OCR alt-text in HTML comment |
| 9 | `table_cleaner` | Moves `<!-- PageBreak -->` comments that landed inside `<table>` blocks to after `</table>` |
| 10 | `whitespace_cleaner` | Normalises line endings, strips trailing spaces, collapses excess blank lines |

---

## Figure extraction strategy

The PDF may contain figures as either embedded raster images or vector/composite graphics.  Both cases are handled automatically:

**Raster figures** — `pdfplumber` detects a single large embedded image on the page.  Its bounding box is converted from PDF coordinates (origin bottom-left) to PIL pixel coordinates (origin top-left) and cropped from the full-resolution page render.

**Vector figures** — no single large raster is present.  The page is rendered at full resolution (`PDF_DPI`) and a region is cropped using the figure caption's y-position as the lower boundary and `PAGE_HEADER_HEIGHT_PT` as the upper boundary.

Figure captions are detected by scanning for the pattern `図 N-N` using `pdfplumber`'s word extraction.

---

## Cover page parsing

The cover-page parser is **fully generalised** — it reads all values from the HTML table at runtime.  The only hardcoded knowledge is *structural*: which row index carries which semantic role (e.g. row 4 = 表題 TITLE, row 7 = 開発件名 block).  This structure is fixed by the document template, not by any particular document's content.

Key design decisions:

- **Compound key "作成　DRAWN"** is assembled across rows 11 and 12 using accumulated key fragments.
- **Ideographic space (U+3000)** is inserted between CJK word-ends and their ALL-CAPS Latin abbreviations for auth field keys (e.g. `作成日付　DATE`), except for `設計 DESIGNED` which retains a regular space to match the source document's formatting.
- **`<開発件名>` block** is parsed by stripping the label prefix and splitting on bullet characters (`·`, `•`, `・`), handling both single-line and multi-line cell content.
- **DWG number** extraction skips pure integers (page numbers) to find the alphanumeric document identifier.

---

## Adapting to a different document

Everything document-specific lives in **`config.py`** only:

| Setting | What to change |
|---|---|
| `BOILERPLATE_LINE_PATTERNS` | Add regex patterns for noise lines in your PDF's footer/header |
| `SYMBOL_REPLACEMENTS` | Add any additional OCR character substitutions |
| `SYMBOL_REGEX_REPLACEMENTS` | Add combined-character artefact fixes |
| `TOC_ENTRIES` | Update the section list to match your document |
| `PDF_DPI` | Increase for sharper figure crops (150 is a good default) |
| `MIN_FIGURE_WIDTH_PT` / `MIN_FIGURE_HEIGHT_PT` | Tune figure detection thresholds |
| `PAGE_HEADER_HEIGHT_PT` | Adjust how much of the page top is skipped when cropping vector figures |

The cover-page and revision-table parsers adapt automatically as long as the source PDF uses the same Mitsubishi Electric Software specification-document template.
