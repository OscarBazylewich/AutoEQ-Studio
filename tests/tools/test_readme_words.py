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


def test_readme_words_of_update_and_the_filters(check):
    # (2026-11-12: "turns a filter off" is a phrasal verb; the message after Update names a maximum of 3 devices for
    # each group; a device with an EQ for 5 minutes or its EQ off to compare uses a change only after that)
    with open(os.path.join(paths.PROJECT, "README.txt"), encoding="utf-8") as fh:
        text = " ".join(fh.read().split())
    check("readme: the On tick box disables a filter (no phrasal verb), and the message of Update has its rule",
          "the On tick box of the table disables a filter" in text and "turns a filter off" not in text
          and "(a maximum of 3 names for each group, and the number of other devices)" in text
          and "If Equalizer APO uses AutoEQ Studio, all other connected devices with Equalizer APO use the change "
          "immediately." in text and "If you do not click Keep it, a device with an EQ for 5 minutes uses the change "
          "when the EQ for 5 minutes stops. A device with its EQ off to compare uses the change when its EQ is on "
          "again." in text
          # (2026-11-12: Keep it makes the EQ for 5 minutes a new profile, so "unless you click Keep it" was said of
          # the compare too. Then "after the 5 minutes" was not exact: Do not keep it stops it before that time, and
          # the condition comes first)
          and "or with its EQ off to compare, uses the change after that" not in text
          and "uses the change after the 5 minutes" not in text, text[:0])


def test_readme_words_of_a_graph_from_a_website(check):
    # (2026-11-12: a window of the website in front of the graph (at the first visit) gave a picture with no graph,
    # and a curve that goes out of the grid near an end of the frequency axis is traced only to a frequency before
    # that end: the measurement does not include that part, and 3 Save's text gives the values)
    with open(os.path.join(paths.PROJECT, "README.txt"), encoding="utf-8") as fh:
        raw = fh.read()
    text = " ".join(raw.split())
    check("readme: step 1 of a graph from a website closes a window in front of the graph first, and step 2 tells "
          "that the measurement does not include the part out of the grid",
          "1. If the website shows a window in front of the graph, close that window. Press Windows + Shift + S. Then "
          "select the area of the graph. Or click Screenshot on the website." in text
          and "If a curve goes above or below the grid near an end of the frequency axis, the measurement does not "
          "include that part. The text on 3 Save gives the frequencies." in text
          and "starts or stops at that frequency" not in text, text[:0])
    check("readme: each line of README.txt has 120 characters or fewer, with LF line ends",
          "\r" not in raw and all(len(line) <= 120 for line in raw.split("\n")),
          [line for line in raw.split("\n") if len(line) > 120])


def test_readme_words_of_remove_for_a_device(check):
    # (2026-11-12: with Remove on the Devices screen, a device does not stay in the list for all time)
    with open(os.path.join(paths.PROJECT, "README.txt"), encoding="utf-8") as fh:
        text = " ".join(fh.read().split())
    check("readme: a device stays in the list of AutoEQ Studio until you remove it, and Remove removes it from Devices",
          "AutoEQ Studio keeps each device in its list after the first time, until you remove it." in text
          and "Remove (after Rename…) removes a device that is not connected from Devices." in text, text[:0])
