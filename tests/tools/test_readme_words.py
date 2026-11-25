"""The words of README.txt about the On tick box of a filter, the message after Update, a graph from a website and
Remove for a device: the facts that each must tell. Its lines: 120 characters or fewer, with LF line ends. Only the
text of the file is read."""
import os

from helpers import paths


def test_readme_words_of_update_and_the_filters(check):
    # (2026-11-12: the message after Update names a maximum of 3 devices for each group; a device with an EQ for 5
    # minutes or its EQ off to compare uses a change only after that)
    with open(os.path.join(paths.PROJECT, "README.txt"), encoding="utf-8") as fh:
        text = " ".join(fh.read().split())
    check("readme: the On tick box disables a filter, and the message of Update has its rule",
          "the On tick box of the table disables a filter" in text
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
    # (2026-11-25, the owner: steps 1 and 2 have the words of the wait window's two steps, ui\picture_wait.py)
    check("readme: steps 1 and 2 of a graph from a website have the words of the wait window, and step 3 tells "
          "that the measurement does not include the part out of the grid",
          # (2026-11-12: then what to do when the graph does not show the entry: the share link of an entry is not
          # verified on each website)
          "1. Maximize your browser for better accuracy, and close any popups over the graph. If this entry isn't "
          "shown, select it from the site's list. For an entry of a target, show only the target on the graph of the "
          "website. 2. Press Win+Shift+S and drag over the graph. Or click Screenshot on the site to save it to "
          "Downloads." in text
          and "Site target adjustments (like tilt or bass) are captured in the screenshot." in text
          and "If a curve goes above or below the grid near an end of the frequency axis, the measurement does not "
          "include that part. The text on 3 Save gives the frequencies." in text
          and "starts or stops at that frequency" not in text
          and not any(w in text for w in ("in front of the graph", "Windows + Shift + S", "list of the website",
                                          "If they agree", "Compare the curve")), text[:0])
    # (2026-11-13: the tracer of a target from a website traces the target line when the graph shows only the target.
    # The instruction to show only the target is in step 1, before the picture; step 4 tells Add as target one time)
    check("readme: step 1 tells to show only the target for an entry of a target, and step 4 tells Add as target "
          "for an entry of a target or from Find a target, one time",
          "4. Verify the curve against the picture, then click Add as measurement. For an entry of a target or an "
          "entry from Find a target, the tracer tells you to click Add as target. If the tracer cannot trace the "
          "picture, it shows the step that you must correct." in text and text.count("show only the target") == 1
          and text.count("click Add as target") == 1, text[:0])
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
