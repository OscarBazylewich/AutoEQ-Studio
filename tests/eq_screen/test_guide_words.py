"""The words of the Guide of Make an EQ (ui\\guide_eq.py), read from its source: each sentence of each step's text and
of the words of each demo (api.say, api.note, "say") has 25 words or fewer, and each step's text 6 sentences or fewer
(ASD-STE100 rules 6.1 and 7.3; 2026-11-11: step 22 had a sentence of 29 words). The fixed parts of an f-string count;
its values count as one word. The source of the module that the page (the eq_screen fixture) loaded is read."""
import ast
import inspect
import re


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


def _texts(path):
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            out += [(node.lineno, k.value, _text(v)) for k, v in zip(node.keys, node.values)
                    if isinstance(k, ast.Constant) and k.value in ("text", "say")]
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in ("say", "note") and node.args:
                out.append((node.lineno, node.func.attr, _text(node.args[0])))
            out += [(node.lineno, "say", _text(kw.value)) for kw in node.keywords if kw.arg == "say"]
    return [(n, kind, t) for n, kind, t in out if t]


def _sentences(text):
    text = re.sub(r"\(Demo:[^)]*\)", "", text)  # (a demo's own note: said apart)
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z“(])", text.strip()) if s.strip()]


def _words(sentence):
    return len(re.findall(r"[A-Za-z0-9][\w'’.,+×/-]*", sentence))


def test_guide_sentences_are_short(eq_screen, check):
    from ui import guide_eq
    texts = _texts(inspect.getsourcefile(guide_eq))
    long = [(n, _words(s), s) for n, _, t in texts for s in _sentences(t) if _words(s) > 25]
    many = [(n, len(_sentences(t))) for n, kind, t in texts if kind == "text" and len(_sentences(t)) > 6]
    check("guide: each sentence of the steps and the demos of Make an EQ has 25 words or fewer",
          len(texts) > 100 and not long, long)
    check("guide: each step text of Make an EQ has 6 sentences or fewer", not many, many)
