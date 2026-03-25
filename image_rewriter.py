"""
image_rewriter.py
-----------------
Rewrites the figure references produced by the PDF extractor so they
point to the real PNG assets saved by figure_extractor.py.

Input pattern (raw extractor output)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ![alt text from OCR](figures/15.1)

Output pattern
~~~~~~~~~~~~~~
    ![Diagram](figures/fig_15_1.png)
    <!--![alt text from OCR](figures/15.1)
    -->

The original alt-text version is preserved in an HTML comment so no
OCR information is lost and the file remains fully diffable.

Public API
----------
    rewrite_images(text, img_dir) -> str

    img_dir : relative directory name used in the new src attribute,
              e.g. "figures"  →  figures/fig_15_1.png
"""

from __future__ import annotations

import re

from config import DEFAULT_IMG_PREFIX

# Matches the raw extractor format: ![any alt text](figures/N.M)
_RAW_IMG_RE = re.compile(r"!\[([^\]]*)\]\((figures/[\d]+\.[\d]+)\)")


def _make_asset_path(raw_ref: str, img_dir: str) -> str:
    """
    Convert a raw figure reference to a real asset path.

    Parameters
    ----------
    raw_ref : e.g. "figures/15.1"
    img_dir : e.g. "figures"

    Returns
    -------
    str : e.g. "figures/fig_15_1.png"
    """
    number_part = raw_ref.split("/", 1)[1]       # "15.1"
    safe        = number_part.replace(".", "_")   # "15_1"
    return f"{img_dir}/{DEFAULT_IMG_PREFIX}_{safe}.png"


def rewrite_images(text: str, img_dir: str = "figures") -> str:
    """
    Replace every raw figure reference with a real asset link.
    The original alt-text reference is kept in an HTML comment.

    Parameters
    ----------
    text    : Markdown content
    img_dir : directory name for the new image src paths

    Returns
    -------
    str : Markdown with rewritten image references.
    """
    def _replacer(m: re.Match) -> str:
        alt     = m.group(1)
        raw_ref = m.group(2)
        new_src = _make_asset_path(raw_ref, img_dir)
        return (
            f"![Diagram]({new_src})\n"
            f"<!--![{alt}]({raw_ref})\n"
            f"-->"
        )

    return _RAW_IMG_RE.sub(_replacer, text)
