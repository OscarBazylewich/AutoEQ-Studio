"""The words of the Guide of Make an EQ (ui\\guide_eq.py), read from its source: the text of the steps tells what On
in the table, Copy and Open the Saved EQs folder do. Of an f-string, its fixed parts are read ("X" for each value).
The source of the module that the page (the eq_screen fixture) loaded is read."""
import ast
import inspect


def _text(node):
    """The words of a string expression (adjacent strings, +, a lambda's or an if's first value), or None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "X" for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = _text(node.left), _text(node.right)
        return (a or "") + (b or "") if (a or b) else None
    if isinstance(node, (ast.IfExp, ast.Lambda)):
        return _text(node.body)
    return None


def _step_texts(path):
    """The text of each step (the "text" of its dict) in a source file."""
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    out = [_text(v) for node in ast.walk(tree) if isinstance(node, ast.Dict)
           for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant) and k.value == "text"]
    return [t for t in out if t]


def test_guide_words_of_the_filters_and_the_files(eq_screen, check):
    # (2026-11-12: step 22 told that Copy opens the folder, which the button Open the Saved EQs folder does)
    from ui import guide_eq
    texts = " ".join(_step_texts(inspect.getsourcefile(guide_eq)))
    check("guide: On in the table disables a filter; Open the Saved EQs folder opens the folder, not Copy",
          "(On in the table disables a filter)" in texts
          and "Copy copies the filters to the clipboard, and Open the Saved EQs folder opens that folder." in texts
          and "and the folder opens" not in texts, texts[:0])


def test_guide_words_of_the_boxes_of_an_eq_app(eq_screen, check):
    # (2026-11-24: Peace bands, Peace max gain and Band counts to try show only for their EQ app, so the steps Your
    # EQ app and Your values tell that they are in Settings, by the names that the app shows)
    from eq import eq_apps
    from ui import guide_eq
    texts = " ".join(_step_texts(inspect.getsourcefile(guide_eq)))
    labels = [it["label"] for a in eq_apps.listing() for it in a["user"]]
    check("guide: the step Your EQ app names the boxes of Peace and of FxSound in Settings by their labels, and the "
          "step Your values tells that they are there",
          "For Peace, Settings has Peace bands and Peace max gain: enter the values that you set in Peace. For "
          "FxSound, Settings has Band counts to try." in texts
          and "With Peace or FxSound, the boxes of that app are also here." in texts
          and labels == ["Peace bands", "Peace max gain (± dB)", "Band counts to try"], labels)
