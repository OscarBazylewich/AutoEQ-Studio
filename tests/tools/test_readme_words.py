"""README.txt in ASD-STE100 (2026-11-11: the block about Adjust… had 9 sentences, and 25 sentences had more than 25
words): each paragraph has 6 sentences or fewer, and each sentence 25 words or fewer. A paragraph: the lines between
blank lines; a list item ("- ", "1. "), a table row ("Name   words"), a line with less indent than the line before,
or a line that the author started (the line before ends a sentence, and the first word had room on it) starts a new
one. The rows of a table are names and their words, not sentences: not counted. Only the text of the file is read."""
import os
import re

from helpers import paths

WIDTH = 117  # (the lines of README.txt: 120 characters at most, with room for a word of 3 more)
_ITEM = re.compile(r"^\s*(-|\d+\.|[a-z]\.|•)\s")
_TABLE = re.compile(r"^\s*\S.*?\S\s{2,}\S")


def _paragraphs(text):
    out, cur, indent_before, before = [], None, 0, ""
    for line in text.split("\n"):
        indent = len(line) - len(line.lstrip(" "))
        if not line.strip() or set(line.strip()) <= set("-="):
            cur, before = None, ""
            continue
        broke = before.rstrip().endswith((".", ":", ")")) and len(before.rstrip()) + 1 + len(line.split()[0]) <= WIDTH
        table = bool(_TABLE.match(line)) and indent <= 4
        if cur is None or _ITEM.match(line) or table or indent < indent_before or broke or line.strip().isupper():
            cur = {"table": table, "lines": []}
            out.append(cur)
        cur["lines"].append(line.strip())
        indent_before, before = indent, line
    return out


def _sentences(text):
    text = re.sub(r"^(-|\d+\.|[a-z]\.|•)\s+", "", text)
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"“(])", text) if s.strip()]


def _words(sentence):
    return len(re.findall(r"[A-Za-z0-9…][\w'’.,+×/%-]*", sentence))


def test_readme_paragraphs_and_sentences(check):
    with open(os.path.join(paths.PROJECT, "README.txt"), encoding="utf-8") as fh:
        paras = [p for p in _paragraphs(fh.read()) if not p["table"] and not p["lines"][0].isupper()]
    many = [(p["lines"][0][:50], len(_sentences(" ".join(p["lines"])))) for p in paras
            if len(_sentences(" ".join(p["lines"]))) > 6]
    long = [(_words(s), s) for p in paras for s in _sentences(" ".join(p["lines"])) if _words(s) > 25]
    check("readme: each paragraph of README.txt has 6 sentences or fewer", len(paras) > 100 and not many, many)
    check("readme: each sentence of README.txt has 25 words or fewer", not long, long)
