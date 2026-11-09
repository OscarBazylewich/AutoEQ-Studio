"""Help: terms and questions (AutoEQ Local's Help page, natively): how an EQ job goes, the questions that come up most,
every term the app uses in groups, and every setting in full (ui/help_texts.py WIKI), with the contents beside them.
The UI audit (2026-11-08, the user's selections): the contents are groups that open and close (Windows 11's chevron,
as every fold of the app), so the list starts with its few groups; the page shows one entry at a time (or a group's
list of entries), and its "Related" links open the others.
- the search box keeps only the entries with every word typed in the contents, each group with a result open
- open_at(id) opens the window at an entry (F1 on a setting: its entry), its group open and the entry selected
One window for the whole app: opened again, it's brought back. Its look is Windows 11's, as the rest of the app: the
contents and the page as cards (theme_sheet.py's guide_and_help: #helpContents, #helpPage), the page's own words
in the theme's colours (links in the accent's text colour; the entry asked for on a quiet fill with the accent's bar
beside it, as a chosen row), drawn again when the theme changes.
"""
import html
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QTextBrowser, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from ui import theme
from ui.help_texts import HELP, WIKI
from ui.theme_sheet import CARD
from ui.window_parts import fit_to_screen

_window = None


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
    out = [("Frequent problems", "questions", [dict(e, title=e["q"]) for e in WIKI["questions"]])]
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
        _window.show_entry(entry_id)
    return _window


class HelpWindow(QWidget):
    def __init__(self):
        super().__init__(None, Qt.Window)
        self.setWindowTitle("Help - AutoEQ Studio")  # (a window of its own: Windows' " - " and the app's name, UI-RULES 3)
        fit_to_screen(self, (1000, 760))  # (within the screen's room: 760 high was under a laptop's taskbar at 150 %)
        self.sections = _entries()
        self.lit = None
        h = QHBoxLayout(self)
        h.setContentsMargins(CARD, CARD, CARD, CARD)  # (as every window's: Qt's own 11 px, UI-RULES 5)
        side = QVBoxLayout()
        side.setContentsMargins(0, 0, 0, 0)  # (its column lined up with the page beside it: Qt's 9 px put it lower)
        self.q = QLineEdit()
        self.q.setPlaceholderText("Search Help…")
        self.q.setClearButtonEnabled(True)
        self.q.textChanged.connect(self.render)
        side.addWidget(self.q)
        self.toc = QTreeWidget()
        self.toc.setObjectName("helpContents")
        self.toc.setAccessibleName("Contents")
        self.toc.setHeaderHidden(True)
        self.toc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.toc.setWordWrap(True)
        self.toc.setIndentation(18)
        self.toc.itemClicked.connect(lambda it, _c=0: it.data(0, Qt.UserRole) and self.show_entry(it.data(0, Qt.UserRole)))
        side.addWidget(self.toc, 1)
        holder = QWidget()
        holder.setLayout(side)
        holder.setFixedWidth(280)
        h.addWidget(holder)
        self.view = QTextBrowser()
        self.view.setObjectName("helpPage")
        self.view.setAccessibleName("Help page")  # (a screen reader said nothing for it)
        self.view.document().setDocumentMargin(14)
        self.view.setOpenLinks(False)
        self.view.anchorClicked.connect(lambda url: self.show_entry(url.fragment() or url.toString().lstrip("#")))
        h.addWidget(self.view, 1)
        self.items = {}  # (an anchor: its item in the contents)
        self._make_contents()
        theme.on_change(self._retheme)
        self.render()
        self.show_page("start")

    # ---------------------------------------------------------------- the contents: groups that open and close
    def _make_contents(self):
        bold = QFont(self.toc.font())
        bold.setBold(True)

        def item(parent, text, anchor, head=False):
            it = QTreeWidgetItem([text])
            it.setData(0, Qt.UserRole, anchor)
            it.setToolTip(0, text)
            if head:
                it.setFont(0, bold)
            (parent.addChild if isinstance(parent, QTreeWidgetItem) else parent.addTopLevelItem)(it)
            self.items[anchor] = it
            return it
        item(self.toc, "How to make an EQ", "start", True)
        settings = None
        for i, (title, sid, entries) in enumerate(self.sections):
            if i == len(WIKI["groups"]) + 1:  # (the groups of settings: in one group, All settings)
                settings = item(self.toc, "All settings", "settings", True)
            g = item(settings if settings is not None else self.toc, title, sid, True)
            for e in entries:
                item(g, e["title"], e["id"])

    def _matches(self, e, words):
        text = " ".join([e["title"], *[x for b in e["body"] for x in (b if isinstance(b, list) else [b])]]).lower()
        return all(w in text for w in words)

    def _retheme(self):
        self.render(keep=True)
        self.show_page(getattr(self, "page_now", "start"), keep=True)

    def render(self, *_, keep=False):
        """The contents with only the entries that have every word typed (each group with one open), or all of them
        (the groups closed, but the one with the entry shown)."""
        words = self.q.text().lower().split()
        found = 0
        for _title, sid, entries in self.sections:
            g = self.items[sid]
            shown = 0
            for e in entries:
                on = self._matches(e, words) if words else True
                self.items[e["id"]].setHidden(not on)
                shown += on
            found += shown if words else 0
            g.setHidden(bool(words) and not shown)
            g.setExpanded(bool(words) and bool(shown))
        self.items["start"].setHidden(bool(words))
        self.items["settings"].setHidden(bool(words) and all(self.items[sid].isHidden() for _t, sid, _e in
                                                              self.sections[len(WIKI["groups"]) + 1:]))
        self.items["settings"].setExpanded(bool(words))
        self.found = found
        if words and not found:
            self.view.setHtml(self._css() + "<p class='muted'>No results with all of these words. Type a smaller number "
                              "of words.</p>")
        elif not words and not keep and getattr(self, "page_now", None):
            self.show_page(self.page_now, keep=True)

    def _css(self):
        t = theme.tokens()
        return (f"<style>body {{ color: {t['ink']}; }} "
                f"h2 {{ color: {t['ink']}; font-size: 15pt; font-weight: 600; margin-top: 4px; }} "
                f"h3 {{ color: {t['ink']}; font-size: 12pt; font-weight: 600; margin-bottom: 2px; }} "
                f"p, li {{ line-height: 140%; }} a {{ color: {t['accent_text']}; }} .muted {{ color: {t['muted']}; }}"
                "</style>")

    # ---------------------------------------------------------------- the page: one entry at a time
    def show_page(self, anchor, keep=False):
        """The page for one item of the contents: the start (how to make an EQ), a group (its entries as links), All
        settings, or one entry (its words and its Related links)."""
        esc = html.escape
        by_id = _by_id()
        parts = [self._css()]
        groups = {sid: (title, entries) for title, sid, entries in self.sections}
        if anchor == "start":
            parts.append(f"<h2>How to make an EQ</h2><p class='muted'>{esc(WIKI['intro'])}</p><ol>"
                         + "".join(f"<li>{esc(st)}</li>" for st in WIKI["steps"]) + "</ol>")
        elif anchor == "settings":
            parts.append("<h2>All settings</h2><p class='muted'>The function of each setting, in full. The tooltip of a "
                         "setting gives a short line about it, and F1 on a setting opens it here.</p><ul>"
                         + "".join(f"<li><a href='#{sid}'>{esc(title)}</a></li>"
                                   for title, sid, _e in self.sections[len(WIKI["groups"]) + 1:]) + "</ul>")
        elif anchor in groups:
            title, entries = groups[anchor]
            if anchor.startswith("sg-"):  # (a group of settings: all of them, in full)
                parts.append(f"<h2>{esc(title)}</h2>" + "".join(self._entry_html(e, by_id) for e in entries))
            else:
                parts.append(f"<h2>{esc(title)}</h2><ul>" + "".join(f"<li><a href='#{e['id']}'>{esc(e['title'])}</a></li>"
                                                                  for e in entries) + "</ul>")
        elif anchor in by_id:
            parts.append(self._entry_html(by_id[anchor], by_id))
        else:
            return
        self.page_now = anchor
        bar = self.view.verticalScrollBar().value()
        self.view.setHtml("".join(parts))
        self.view.verticalScrollBar().setValue(bar if keep else 0)

    @staticmethod
    def _entry_html(e, by_id):
        esc = html.escape
        body = "".join("<ul>" + "".join(f"<li>{esc(x)}</li>" for x in b) + "</ul>" if isinstance(b, list)
                       else f"<p>{esc(b)}</p>" for b in e["body"])
        see = [x for x in e.get("see") or [] if x in by_id]
        if see:
            body += "<p class='muted'>Related: " + ", ".join(
                f"<a href='#{x}'>{esc(by_id[x]['title'])}</a>" for x in see) + "</p>"
        return f"<a name='{e['id']}'></a><h3>{esc(e['title'])}</h3>{body}"

    def show_entry(self, entry_id):
        """An entry (or a group) shown on the page, selected in the contents with its group open (the search cleared
        if it hid it)."""
        it = self.items.get(entry_id)
        if it is None:
            return
        self.lit = entry_id
        if it.isHidden() and self.q.text():
            self.q.blockSignals(True)
            self.q.clear()
            self.q.blockSignals(False)
            self.render()
        p = it.parent()
        while p is not None:
            p.setExpanded(True)
            p = p.parent()
        self.toc.setCurrentItem(it)
        self.toc.scrollToItem(it)
        self.show_page(entry_id)


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
        widget.setToolTip(widget.toolTip() + "\nF1 opens Help.")
    return widget


def entry_of_widget(w):
    """The Help entry for the setting a widget belongs to (its box or a parent with a "help_key"), or None."""
    while w is not None:
        k = w.property("help_key")
        if k:
            return entry_for(k)
        w = w.parentWidget()
    return None

