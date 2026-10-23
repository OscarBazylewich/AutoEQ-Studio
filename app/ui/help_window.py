"""Help: terms and questions (AutoEQ Local's Help page, natively): how an EQ job goes, the questions that come up most,
every term the app uses in groups, and every setting in full (ui/help_texts.py WIKI), with the contents beside them.
- the search box keeps only the entries with every word typed (and the groups that still have one)
- an entry's "See also" opens that entry; open_at(id) opens the window at one (F1 on a setting: its entry), lit
One window for the whole app: opened again, it's brought back. Its look is Windows 11's, as the rest of the app: the
contents and the page as cards (theme_sheet.py's guide_and_help: #helpContents, #helpPage), the page's own words
in the theme's colours (links in the accent's text colour; the entry asked for on a quiet fill with the accent's bar
beside it, as a chosen row), drawn again when the theme changes.
"""
import html
import re

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QStyle, QTextBrowser,
                               QVBoxLayout, QWidget)

from ui import theme
from ui.help_texts import HELP, WIKI

_window = None
ROW_PAD = (6, 8)  # (a contents row's padding, up and down / sideways: theme_sheet.py's #helpContents::item)


class _Contents(QListWidget):
    """The contents: each entry as tall as its words need at the list's width, and never wider than the list (Qt's
    own measure leaves out the rows' padding: a long question came out wider than the list, its end cut off)."""

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.fit()

    def fit(self):
        # (the room beside the scroll bar whether it's shown or not: a row's width never changes with it)
        w = self.width() - 2 * self.frameWidth() - self.verticalScrollBar().sizeHint().width()
        if w < 60:  # (not laid out yet: fitted when it is)
            return
        words = self.style().pixelMetric(QStyle.PM_FocusFrameHMargin, None, self) + 1  # (Qt's room each side of them)
        room = w - 2 * ROW_PAD[1] - 2 * words - 1  # (the row's padding, the words' own margins, a pixel to spare)
        for k in range(self.count()):
            it = self.item(k)
            fm = QFontMetrics(it.font() if it.data(Qt.FontRole) is not None else self.font())
            h = fm.boundingRect(QRect(0, 0, room, 100000), Qt.TextWordWrap, it.text()).height()
            it.setSizeHint(QSize(w, h + 2 * ROW_PAD[0] + 2))


def setting_id(key):
    """A setting's entry id (AutoEQ Local's wikiSettingId)."""
    return "set-" + re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", key.lower()))


def help_key(key):
    """The key HELP knows a setting by (a "to" box shares its "from" box's: ".1" -> ".0", "_high" -> "_low", "_max" ->
    "_min"; a list's item, its list's)."""
    for k in (key, re.sub(r"\.1$", ".0", key), re.sub(r"\.\d+$", "", key), re.sub(r"_high$", "_low", key),
              re.sub(r"_max$", "_min", key)):
        if k in HELP:
            return k
    return None


def entry_for(key):
    """The Help entry for a setting's key: its own, or else the first term its help names; None without one."""
    k = help_key(key)
    if not k:
        return None
    if setting_id(k) in _by_id():
        return setting_id(k)
    h = HELP[k]
    return next((s for s in (h[1:] if isinstance(h, list) else []) if s in _by_id()), None)


def _entries():
    """[(section title, section id, [entry…])]; an entry: {id, title, body, see}."""
    out = [("Questions", "questions", [dict(e, title=e["q"]) for e in WIKI["questions"]])]
    for g in WIKI["groups"]:
        out.append((g["title"], "g-" + re.sub(r"[^a-z]+", "-", g["title"].lower()), g["terms"]))
    for g in WIKI["settings"]:
        items = []
        for e in g["items"]:
            h = HELP.get(help_key(e["key"]) or "", [])
            items.append(dict(e, id=setting_id(e["key"]), see=h[1:] if isinstance(h, list) else []))
        out.append((g["title"], "sg-" + re.sub(r"^-|-$", "", re.sub(r"[^a-z]+", "-", g["title"].lower())), items))
    return out


_ids = None


def _by_id():
    global _ids
    if _ids is None:
        _ids = {e["id"]: e for _t, _i, items in _entries() for e in items}
    return _ids


def open_at(entry_id=None):
    """The Help window (made once), at an entry."""
    global _window
    if _window is None:
        _window = HelpWindow()
    _window.show()
    _window.raise_()
    _window.activateWindow()
    if entry_id:
        _window.go(entry_id)
    return _window


class HelpWindow(QWidget):
    def __init__(self):
        super().__init__(None, Qt.Window)
        self.setWindowTitle("Help: terms and questions · AutoEQ Studio")
        self.resize(1000, 760)
        self.sections = _entries()
        self.lit = None
        h = QHBoxLayout(self)
        side = QVBoxLayout()
        self.q = QLineEdit()
        self.q.setPlaceholderText("Search the help…")
        self.q.setClearButtonEnabled(True)
        self.q.textChanged.connect(self.render)
        side.addWidget(self.q)
        self.toc = _Contents()
        self.toc.setObjectName("helpContents")
        self.toc.setAccessibleName("Contents")
        self.toc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.toc.setWordWrap(True)
        self.toc.itemClicked.connect(lambda it: it.data(Qt.UserRole) and self.go(it.data(Qt.UserRole)))
        side.addWidget(self.toc, 1)
        holder = QWidget()
        holder.setLayout(side)
        holder.setFixedWidth(280)
        h.addWidget(holder)
        self.view = QTextBrowser()
        self.view.setObjectName("helpPage")
        self.view.document().setDocumentMargin(14)
        self.view.setOpenLinks(False)
        self.view.anchorClicked.connect(lambda url: self.go(url.fragment() or url.toString().lstrip("#")))
        h.addWidget(self.view, 1)
        theme.on_change(self._retheme)
        self.render()

    def _matches(self, e, words):
        text = " ".join([e["title"], *[x for b in e["body"] for x in (b if isinstance(b, list) else [b])]]).lower()
        return all(w in text for w in words)

    def _retheme(self):
        self.render(keep=True)

    def render(self, *_, keep=False):
        """The entries (only those with every word typed) and the contents beside them, in the theme's colours; the
        contents from their top (a search typed) or where they were (keep: an entry opened, the theme changed)."""
        t = theme.tokens()
        words = self.q.text().lower().split()
        by_id = _by_id()
        esc = html.escape
        css = (f"body {{ color: {t['ink']}; }} "
               f"h2 {{ color: {t['ink']}; font-size: 15pt; font-weight: 600; margin-top: 18px; }} "
               f"h3 {{ color: {t['ink']}; font-size: 12pt; font-weight: 600; margin-bottom: 2px; }} "
               f"p, li {{ line-height: 140%; }} a {{ color: {t['accent_text']}; }} .muted {{ color: {t['muted']}; }} "
               f".lit {{ background: {t['sel']}; color: {t['sel_ink']}; }}")
        parts, toc = [f"<style>{css}</style>"], []
        if not words:
            parts.append(f"<p class='muted'>{esc(WIKI['intro'])}</p><a name='start'></a><h2>How an EQ job goes</h2><ol>"
                         + "".join(f"<li>{esc(s)}</li>" for s in WIKI["steps"]) + "</ol>")
            toc.append(("How an EQ job goes", "start", True))
        any_shown = False
        for i, (title, sid, items) in enumerate(self.sections):
            shown = [e for e in items if self._matches(e, words)]
            if not shown:
                continue
            any_shown = True
            if i == len(WIKI["groups"]) + 1 and not words:  # (the first group of settings: the part's heading)
                parts.append("<a name='settings'></a><h2>Every setting</h2><p class='muted'>What each setting does, in "
                             "full. Pointing at a setting says it in a line; F1 on it opens it here.</p>")
                toc.append(("Every setting", "settings", True))
            parts.append(f"<a name='{sid}'></a><h2>{esc(title)}</h2>")
            toc.append((title, sid, True))
            for e in shown:
                body = "".join("<ul>" + "".join(f"<li>{esc(x)}</li>" for x in b) + "</ul>" if isinstance(b, list)
                               else f"<p>{esc(b)}</p>" for b in e["body"])
                see = [s for s in e.get("see") or [] if s in by_id]
                if see:
                    body += "<p class='muted'>See also: " + ", ".join(
                        f"<a href='#{s}'>{esc(by_id[s]['title'])}</a>" for s in see) + "</p>"
                entry = f"<h3>{esc(e['title'])}</h3>{body}"
                if e["id"] == self.lit:  # (the entry asked for: one quiet block, the accent's bar beside it)
                    entry = (f"<table width='100%' cellspacing='0' cellpadding='0'><tr>"
                             f"<td width='3' style='background: {t['accent']}'></td>"
                             f"<td class='lit' style='padding: 2px 12px 6px 12px'>{entry}</td></tr></table>")
                parts.append(f"<a name='{e['id']}'></a>{entry}")
                if sid in ("questions",) or sid.startswith("g-") or words:
                    toc.append((e["title"], e["id"], False))
        if not any_shown:
            parts.append("<p class='muted'>Nothing matches every word. Try fewer words.</p>")
        bar = self.view.verticalScrollBar().value()
        self.view.setHtml("".join(parts))
        self.view.verticalScrollBar().setValue(bar)
        place = self.toc.verticalScrollBar().value()
        self.toc.clear()
        self.toc.ensurePolished()
        bold = QFont(self.toc.font())  # (the list's own font: an item's font() is the app's smaller default)
        bold.setBold(True)
        for text, anchor, head in toc:
            it = QListWidgetItem(text)
            it.setData(Qt.UserRole, anchor)
            if head:
                it.setFont(bold)
            self.toc.addItem(it)
            if anchor == self.lit:  # (marked as chosen; the list isn't moved: go() brings it into sight)
                it.setSelected(True)
        self.toc.fit()
        self.toc.doItemsLayout()  # (laid out now: else the new list took the old one's place, a search part-way down)
        self.toc.verticalScrollBar().setValue(place if keep else 0)

    def go(self, entry_id):
        """An entry shown (the search cleared if it hid it), brought into sight and lit (and in the contents, chosen
        and in sight)."""
        if entry_id in _by_id():
            self.lit = entry_id
            cleared = bool(self.q.text()) and not self._matches(_by_id()[entry_id], self.q.text().lower().split())
            if cleared:
                self.q.blockSignals(True)
                self.q.clear()
                self.q.blockSignals(False)
            self.render(keep=not cleared)  # (the same contents: left where they were; new ones: from their top)
            row = next((it for it in self.toc.selectedItems() if it.data(Qt.UserRole) == entry_id), None)
            if row is not None:
                self.toc.scrollToItem(row)  # (moved only when it's out of sight)
        self.view.scrollToAnchor(entry_id)


def tag(widget, key):
    """A control belongs to a setting: its line as the tooltip (when it has none), and F1 on it opens the setting's
    entry (the tooltip says so)."""
    widget.setProperty("help_key", key)
    h = HELP.get(help_key(key) or "")
    line = (h[0] if isinstance(h, list) else h) if h else ""
    if h and not widget.toolTip():
        widget.setToolTip(line)
    # (for a screen reader: the setting's name, as Help names it, and its line)
    e = _by_id().get(entry_for(key) or "")
    if not widget.accessibleName() and (e and e.get("title") or line):
        widget.setAccessibleName(e["title"] if e and e.get("title") else line.split(".")[0])
    if line and not widget.accessibleDescription():
        widget.setAccessibleDescription(line)
    if entry_for(key) and widget.toolTip() and "F1" not in widget.toolTip():
        widget.setToolTip(widget.toolTip() + "\nF1: more in Help.")
    return widget


def entry_of_widget(w):
    """The Help entry for the setting a widget belongs to (its box or a parent with a "help_key"), or None."""
    while w is not None:
        k = w.property("help_key")
        if k:
            return entry_for(k)
        w = w.parentWidget()
    return None

