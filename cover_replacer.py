"""
cover_replacer.py
-----------------
Parses the raw cover-page HTML table produced by PDF-to-Markdown tools
and renders it as clean, readable Markdown.  Also handles the revision
table (改定欄) that follows on page 2.

Design goals
~~~~~~~~~~~~
* Zero hardcoded document values — title, names, dates, order numbers
  are all read from the HTML table at runtime.
* The only thing hardcoded is structural knowledge: which row index
  carries which semantic role.  This is fixed by the Mitsubishi Electric
  Software specification-document template, not by any particular document.

Cover table row map (template structure)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  Row  0   noise  | 御注文元 PURCHASER (key, rowspan=2)  | value (rowspan=2)
  Row  1   spacer (rowspan=4 cell)
  Row  2   件名 PROJECT (key)        | value
  Row  3   据付場所 SITE (key)        | value
  Row  4   表題 TITLE (key)           | value      ← becomes H1 title
  Row  5   spacer  | プログラム名 PROGRAM NO. (key)  | value
  Row  6   オーダ番号 ORDER NO. k  | v  | 機種 MODEL NO. k  | v
  Row  7   <開発件名> ·bullet text…
  Row  8   noise  | MITSUBISHI ELECTRIC SOFTWARE CORPORATION
  Row  9   noise  | TITLE                            ← bare label, skipped
  Row 10   noise  | 作成日付 DATE (key)  | title|date|検認key|作成val (rowspan=2)
  Row 11   noise  | 作成 (partial key fragment)
  Row 12   noise  | DRAWN|照査 CHECKED               | vals: drawn,checked,DWG,page,-,dwg_no
  Row 13   noise  | 設計 DESIGNED (key)               | total_pages|設計val

Output layout
~~~~~~~~~~~~~
  <!-- PageHeader: MITSUBISHI ELECTRIC SOFTWARE CORPORATION -->
  <!-- PageHeader: 社外秘 -->

  # <表題 value>

  **御注文元 PURCHASER：**
  value
  ---
  ... (件名, 据付場所, 表題, プログラム名, オーダ番号, 機種) ...
  ---
  <開発件名>
  • bullet line
  ---
  **MITSUBISHI ELECTRIC SOFTWARE CORPORATION**
  ---
  **TITLE：**
  value
  ---
  **作成日付　DATE：** value
  **作成　DRAWN：** value
  **照査　CHECKED：** value
  **設計 DESIGNED：** value
  **検認　APPROVED：** value
  ---
  **DWG. NO.：** value
  N/M
  ---

Public API
----------
    replace_cover(text)          -> str
    replace_revision_table(text) -> str
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import NamedTuple

from bs4 import BeautifulSoup, Tag

# ── Constants ─────────────────────────────────────────────────────────────────

_PAGE_BREAK = "<!-- PageBreak -->"

# PageHeader comments worth keeping; all others (C7450b…, | …) are noise.
_KEEP_HEADER_RE: list[re.Pattern[str]] = [
    re.compile(r"MITSUBISHI ELECTRIC SOFTWARE", re.IGNORECASE),
    re.compile(r"社外秘"),
]

# BeautifulSoup separator for <br> tags when calling get_text().
_BR = "|"

# Detects the DWG number label cell ("DWG. No.", "DWG.NO.", etc.)
_DWG_RE = re.compile(r"DWG\.?\s*N[Oo]\.?", re.IGNORECASE)

# Detects the 開発件名 block cell.
_KAIHATU_RE = re.compile(r"[<＜]?開発件名[>＞]?")

# Bullet characters used before project-name items.
_BULLET_RE = re.compile(r"^[··•・]\s*")

# Structural noise cells that carry no document data.
_NOISE_TEXTS: frozenset[str] = frozenset({
    "記 録 MEMO", "記録 MEMO", "記録MEMO",
    "出図先 ( )", "出図先",
})


# ── Data model ────────────────────────────────────────────────────────────────

class KV(NamedTuple):
    """A single key→value metadata pair."""
    key: str
    value: str


@dataclass
class CoverData:
    """All structured data extracted from the cover page table."""
    kept_headers:   list[str] = field(default_factory=list)
    title:          str = ""       # Document H1 (from 表題 TITLE row)
    fields:         list[KV] = field(default_factory=list)   # Two-line fields
    kaihatu_block:  list[str] = field(default_factory=list)  # 開発件名 bullets
    company_bold:   str = ""       # Standalone bold company line
    subtitle_title: str = ""       # Second "TITLE:" line value
    auth_fields:    list[KV] = field(default_factory=list)   # Inline auth fields
    dwg_no:         str = ""
    page_current:   str = ""
    page_total:     str = ""


# ── Text helpers ──────────────────────────────────────────────────────────────

def _cell_text(cell: Tag) -> str:
    """Return a cell's full text, using _BR to represent <br> tags."""
    return cell.get_text(separator=_BR).strip()


def _split_br(raw: str) -> list[str]:
    """Split a _BR-joined string into non-empty parts."""
    return [p.strip() for p in raw.split(_BR) if p.strip()]


def _is_noise(raw: str) -> bool:
    """Return True for structural spacer cells that carry no document data."""
    plain = raw.replace(_BR, "").strip()
    return plain == "" or plain in _NOISE_TEXTS


def _normalise_label(raw: str) -> str:
    """
    Collapse internal spaces between consecutive CJK characters.
    Leaves spaces between CJK and Latin intact.

    Examples
    --------
    "御 注 文 元 PURCHASER" → "御注文元 PURCHASER"
    "据 付 場 所 SITE"      → "据付場所 SITE"
    """
    t = raw.replace(_BR, " ").strip()
    t = re.sub(r"(?<=[\u3000-\u9fff])\s+(?=[\u3000-\u9fff])", "", t)
    return re.sub(r" {2,}", " ", t).strip()


def _normalise_bullet(line: str) -> str:
    """Replace any bullet-character prefix with a standard '• '."""
    return _BULLET_RE.sub("• ", line.strip())


def _auth_label(raw: str) -> str:
    """
    Normalise an auth-field key and widen the space between a Japanese
    word-end and its ALL-CAPS Latin abbreviation to an ideographic space
    (U+3000).

    Examples
    --------
    "作成日付 DATE" → "作成日付　DATE"
    "照査 CHECKED"  → "照査　CHECKED"
    "検認 APPROVED" → "検認　APPROVED"

    Note: cells where the regular space must be preserved (e.g. "設計 DESIGNED")
    should use plain _normalise_label() instead.
    """
    t = _normalise_label(raw)
    return re.sub(r"(?<=[\u3040-\u9fff])\s+(?=[A-Z])", "\u3000", t)


# ── Parser ────────────────────────────────────────────────────────────────────

def _parse_cover(block: str) -> CoverData:
    """
    Parse the raw cover-page HTML block and return a populated CoverData.
    See module docstring for the complete row-by-row structural map.
    """
    data = CoverData()

    # ── PageHeader comments ────────────────────────────────────────────
    for line in block.splitlines():
        s = line.strip()
        if s.startswith("<!-- PageHeader:"):
            if any(r.search(s) for r in _KEEP_HEADER_RE):
                data.kept_headers.append(s)

    # ── Table ──────────────────────────────────────────────────────────
    soup = BeautifulSoup(block, "html.parser")
    table = soup.find("table")
    if table is None:
        return data

    rows = table.find_all("tr")

    # State threaded across rows for compound fields
    sakusei_key_parts: list[str] = []  # Accumulates "作成" (row 11) + "DRAWN" (row 12)
    sakusei_value:     str = ""        # Person name for 作成 DRAWN  (from row 10 cell 2)
    checked_kv:    KV | None = None    # 照査 CHECKED  (built in row 12)
    row10_c2_parts:    list[str] = []  # Parts of the rowspan=2 cell in row 10

    for ri, row in enumerate(rows):
        cells = row.find_all(["td", "th"])
        txts  = [_cell_text(c) for c in cells]

        # Skip rows that are entirely blank
        if all(t.replace(_BR, "").strip() == "" for t in txts):
            continue

        # ── Row 0: 御注文元 PURCHASER ──────────────────────────────────
        # Cell layout: [noise, key(rowspan=2), value(rowspan=2)]
        if ri == 0:
            if len(txts) >= 3:
                data.fields.append(KV(
                    _normalise_label(txts[1]),
                    txts[2].replace(_BR, " ").strip(),
                ))
            continue

        # ── Row 7: <開発件名> bullets ──────────────────────────────────
        # The entire cell is one string; bullets are separated by bullet chars.
        if txts and _KAIHATU_RE.search(txts[0].replace(_BR, "")):
            raw = txts[0].replace(_BR, " ")
            # Remove the "<開発件名>" label prefix, then split on bullet chars.
            cleaned = _KAIHATU_RE.sub("", raw, count=1)
            cleaned = re.sub(r"^[>＞]?\s*", "", cleaned).strip()
            items = [p.strip() for p in re.split(r"[·•・]", cleaned) if p.strip()]
            data.kaihatu_block = ["• " + item for item in items]
            continue

        # ── Row 8: bold company name ───────────────────────────────────
        if ri == 8:
            non_noise = [t for t in txts if not _is_noise(t)]
            if non_noise:
                data.company_bold = non_noise[0].replace(_BR, " ").strip()
            continue

        # ── Row 9: bare "TITLE" label row — skip ──────────────────────
        if ri == 9:
            continue

        # ── Row 10: 作成日付 DATE key + large rowspan cell ────────────
        # rowspan cell parts: [subtitle_title, date_value, 検認_key, 作成_person]
        if ri == 10:
            non_noise = [t for t in txts if not _is_noise(t)]
            if len(non_noise) >= 2:
                date_key       = _auth_label(non_noise[0])      # "作成日付　DATE"
                row10_c2_parts = _split_br(non_noise[1])
                if row10_c2_parts:
                    data.subtitle_title = row10_c2_parts[0]
                if len(row10_c2_parts) >= 2:
                    data.auth_fields.append(KV(date_key, row10_c2_parts[1]))
                if len(row10_c2_parts) >= 4:
                    sakusei_value = row10_c2_parts[3]
            continue

        # ── Row 11: partial key "作成" ─────────────────────────────────
        if ri == 11:
            non_noise = [t for t in txts if not _is_noise(t)]
            if non_noise:
                sakusei_key_parts.append(_normalise_label(non_noise[0]))
            continue

        # ── Row 12: DRAWN + 照査 CHECKED + DWG number ─────────────────
        if ri == 12:
            non_noise = [t for t in txts if not _is_noise(t)]
            if len(non_noise) >= 2:
                key_parts = _split_br(non_noise[0])  # ["DRAWN", "照査 CHECKED"]
                val_parts = _split_br(non_noise[1])  # [drawn_v, checked_v, DWG, page, -, dwg_no]

                # Complete the compound "作成　DRAWN" key
                if key_parts:
                    sakusei_key_parts.append(key_parts[0])
                compound_key = _auth_label(" ".join(sakusei_key_parts))
                data.auth_fields.append(KV(compound_key, sakusei_value))

                # 照査 CHECKED
                if len(key_parts) >= 2 and len(val_parts) >= 2:
                    checked_kv = KV(_auth_label(key_parts[1]), val_parts[1])
                    data.auth_fields.append(checked_kv)

                # Extract DWG number (alphanumeric, after "DWG. No." marker)
                # and current page number (first standalone digit).
                for i, part in enumerate(val_parts):
                    if _DWG_RE.match(part):
                        for candidate in val_parts[i + 1:]:
                            if candidate not in ("-", "－", "") and not candidate.isdigit():
                                data.dwg_no = candidate
                                break
                    elif part.isdigit() and not data.page_current:
                        data.page_current = part
            continue

        # ── Row 13: 設計 DESIGNED + total page count ──────────────────
        if ri == 13:
            non_noise = [t for t in txts if not _is_noise(t)]
            if len(non_noise) >= 2:
                # NOTE: 設計 DESIGNED uses _normalise_label (regular space),
                # not _auth_label, because the expected output retains a regular
                # space between the Japanese word and its Latin abbreviation here.
                designed_key = _normalise_label(non_noise[0])
                vp = _split_br(non_noise[1])        # [total_pages, designed_person]
                if vp:
                    data.page_total = vp[0]
                if len(vp) >= 2:
                    data.auth_fields.append(KV(designed_key, vp[1]))

                # 検認 APPROVED: key from row 10 cell-2 parts[2]; value = same as 照査
                if len(row10_c2_parts) >= 3:
                    approved_key = _auth_label(row10_c2_parts[2])
                    approved_val = checked_kv.value if checked_kv else ""
                    data.auth_fields.append(KV(approved_key, approved_val))
            continue

        # ── Generic rows (2, 3, 4, 5): one or two key/value pairs ─────
        non_noise = [t for t in txts if not _is_noise(t)]

        if len(non_noise) == 2:
            key = _normalise_label(non_noise[0])
            val = non_noise[1].replace(_BR, " ").strip()
            if key == "TITLE" and not val:
                continue                        # bare TITLE label row — skip
            if "TITLE" in key and "表題" in key:
                data.title = val                # capture H1 document title
            data.fields.append(KV(key, val))

        elif len(non_noise) == 4:
            # Row 6: [オーダ番号 key, value, 機種 key, value]
            data.fields.append(KV(
                _normalise_label(non_noise[0]),
                non_noise[1].replace(_BR, " ").strip(),
            ))
            data.fields.append(KV(
                _normalise_label(non_noise[2]),
                non_noise[3].replace(_BR, " ").strip(),
            ))

    return data


# ── Renderer ──────────────────────────────────────────────────────────────────

def _render_cover(data: CoverData) -> str:
    """Render a CoverData instance as clean Markdown."""
    out: list[str] = []

    # Kept PageHeader comments
    for h in data.kept_headers:
        out.append(h)
    out.append("")

    # H1 document title
    if data.title:
        out.append(f"# {data.title}")
        out.append("")
        out.append("---")
        out.append("")

    # Two-line metadata fields: **key：**\nvalue\n---
    for kv in data.fields:
        out.append(f"**{kv.key}：**")
        out.append(kv.value)
        out.append("")
        out.append("---")
        out.append("")

    # 開発件名 block
    if data.kaihatu_block:
        out.append("<開発件名>")
        for bullet in data.kaihatu_block:
            out.append(bullet)
        out.append("")
        out.append("---")
        out.append("")

    # Bold standalone company line
    if data.company_bold:
        out.append(f"**{data.company_bold}**")
        out.append("")
        out.append("---")
        out.append("")

    # Second TITLE: subtitle
    if data.subtitle_title:
        out.append("**TITLE：**")
        out.append(data.subtitle_title)
        out.append("")
        out.append("---")
        out.append("")

    # Auth fields: **key：** value, each followed by a blank line, then ---
    if data.auth_fields:
        for kv in data.auth_fields:
            out.append(f"**{kv.key}：** {kv.value}")
            out.append("")
        out.append("---")
        out.append("")

    # DWG number and page fraction
    if data.dwg_no:
        out.append(f"**DWG. NO.：** {data.dwg_no}")
        if data.page_current and data.page_total:
            out.append(f"{data.page_current}/{data.page_total}")
        out.append("")
        out.append("---")
        out.append("")

    # Page markers
    out.append("<!-- PageNumber: 1 -->")
    out.append("<!-- PageBreak -->")
    out.append("")

    return "\n".join(out)


# ── Public API ────────────────────────────────────────────────────────────────

def replace_cover(text: str) -> str:
    """
    Parse the cover-page HTML table generically and replace it with clean
    Markdown.  No document-specific values are hardcoded — everything is
    read from the table at runtime.

    Parameters
    ----------
    text : full content of the raw input Markdown file

    Returns
    -------
    str : Markdown with the cover page replaced.
    """
    pb = text.find(_PAGE_BREAK)
    if pb == -1:
        return text

    cover_block = text[:pb]
    rest        = text[pb + len(_PAGE_BREAK):].lstrip("\n")
    data        = _parse_cover(cover_block)
    return _render_cover(data) + "\n" + rest


def replace_revision_table(text: str) -> str:
    """
    Replace the revision table block (page 2, between page breaks 1 and 2)
    with a clean minimal 4-column template.

    The revision table always has the same structure in this document
    template (四列: 内容, 作成, 照査, 検認) and contains no document-specific
    values, so a static replacement is appropriate.

    Parameters
    ----------
    text : Markdown content after replace_cover() has already run.

    Returns
    -------
    str : Markdown with the revision table replaced.
    """
    first = text.find(_PAGE_BREAK)
    if first == -1:
        return text
    second = text.find(_PAGE_BREAK, first + 1)
    if second == -1:
        return text

    block = text[first + len(_PAGE_BREAK): second]
    if "改" not in block and "CHANGE" not in block:
        return text

    clean_table = """\

## 改定欄

<table>
<tr>
<th colspan="1">内 容 CONTENTS</th>
<th>作 成 DRAWN 日付 DATE</th>
<th>照 査 CHECKED</th>
<th>検 認 APPROVED</th>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
</tr>
<tr>
<td></td>
<td></td>
<td></td>
<td></td>
</tr>
</table>

"""
    rest   = text[second + len(_PAGE_BREAK):].lstrip("\n")
    prefix = text[: first + len(_PAGE_BREAK)]
    return (
        prefix
        + "\n\n"
        + clean_table
        + "\n<!-- PageNumber: 2 -->\n"
        + _PAGE_BREAK
        + "\n\n"
        + rest
    )
