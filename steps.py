import re

from cover_replacer import replace_cover, replace_revision_table
from toc_builder import replace_toc
from boilerplate_remover import remove_boilerplate
from footer_table_remover import remove_footer_tables
from symbol_normaliser import normalise_symbols
from heading_fixer import fix_headings
from image_rewriter import rewrite_images
from table_cleaner import clean_tables
from whitespace_cleaner import clean_whitespace


def step_replace_cover(text, ctx):
    return replace_cover(text)


def step_replace_revision(text, ctx):
    return replace_revision_table(text)


def step_replace_toc(text, ctx):
    toc_entries = ctx.get("toc_entries", [])

    if not toc_entries:
        return text

    # ✅ REMOVE old "# 目 次" completely
    text = re.sub(r'#\s*目\s*次', '', text)

    return replace_toc(text, toc_entries)


def step_remove_boilerplate(text, ctx):
    return remove_boilerplate(text)


def step_remove_footer_tables(text, ctx):
    return remove_footer_tables(text)


def step_remove_memo(text, ctx):
    return re.sub(
        r'<t[dh][^>]*>[^<]*MEMO[^<]*</t[dh]>',
        '',
        text,
        flags=re.IGNORECASE
    )


def step_remove_empty_rows(text, ctx):
    text = re.sub(r'<tr>\s*(<td[^>]*>\s*</td>\s*)+\s*</tr>', '', text)
    text = re.sub(r'<tr>\s*</tr>', '', text)
    return text


def step_normalise_symbols(text, ctx):
    return normalise_symbols(text)


def step_fix_headings(text, ctx):
    return fix_headings(text)


def step_rewrite_images(text, ctx):
    img_dir = ctx["img_dir"]
    out_path = ctx["out_path"]

    try:
        rel = str(img_dir.relative_to(out_path.parent))
    except:
        rel = img_dir.name

    return rewrite_images(text, rel)


def step_clean_tables(text, ctx):
    return clean_tables(text)


def step_clean_whitespace(text, ctx):
    return clean_whitespace(text)

def step_add_heading_ids(text, ctx):
    def repl(match):
        hashes = match.group(1)
        title = match.group(2).strip()

        anchor = re.sub(r'[^\w一-龥ぁ-んァ-ン]+', '-', title).strip('-')

        return f'{hashes} <a id="{anchor}"></a>{title}'

    return re.sub(r'^(#{1,6})\s+(.*)', repl, text, flags=re.MULTILINE)