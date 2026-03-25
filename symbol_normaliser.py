"""
symbol_normaliser.py
--------------------
Corrects symbol characters that the PDF-to-Markdown extractor renders
incorrectly:

  ☒  (U+2612, ballot box with X)  →  〇  (U+3007, used as ○ "applicable")
  🔘 (U+1F518, radio button emoji) →  〇

Also fixes mixed artefact combinations such as:
  "△ ☒" → "△"   (conditional marker followed by stray checkbox)
  "一 ☒" → "一"  (not-applicable marker followed by stray checkbox)

All substitutions are configured in config.SYMBOL_REPLACEMENTS and
config.SYMBOL_REGEX_REPLACEMENTS.

Public API
----------
    normalise_symbols(text) -> str
"""

from __future__ import annotations

import re

from config import SYMBOL_REGEX_REPLACEMENTS, SYMBOL_REPLACEMENTS


def normalise_symbols(text: str) -> str:
    """
    Apply all symbol substitutions defined in config.py.

    Plain string replacements are applied first (order matters when the
    same character appears in multiple patterns), followed by regex
    substitutions for combined artefact patterns.

    Parameters
    ----------
    text : Markdown content

    Returns
    -------
    str : Markdown with corrected symbols.
    """
    for find, replace in SYMBOL_REPLACEMENTS:
        text = text.replace(find, replace)

    for pattern, replacement in SYMBOL_REGEX_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)

    return text
