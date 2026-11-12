"""Help: terms and questions (AutoEQ Local's Help page, natively): how an EQ job goes, the questions that come up most,
every term the app uses in groups, and every setting in full (ui/help_texts.py WIKI), with the contents beside them.
The UI audit (2026-11-08, the user's selections): the contents are groups that open and close (Windows 11's chevron,
as every fold of the app), so the list starts with its few groups; the page shows one entry at a time (or a group's
list of entries), and its "Related" links open the others.
- the search box keeps only the entries with every word typed in the contents, each group with a result open, and
  one result on the page
- a row of the contents opens its entry when it becomes the current row (a click, the arrow keys) and on Enter; a
  long row goes on to more lines (WrappedRows)
- open_at(id) opens the window at an entry (F1 on a setting: its entry), its group open and the entry selected
One window for the whole app: opened again, it's brought back (opened from a window that blocks the others, as Find…,
it blocks them too until it closes: _modal_over_modal). Its look is Windows 11's, as the rest of the app: the
contents and the page as cards (theme_sheet.py's guide_and_help: #helpContents, #helpPage), the page's own words
in the theme's colours (links in the accent's text colour; the entry asked for on a quiet fill with the accent's bar
beside it, as a chosen row), drawn again when the theme changes.
"""
import html
import re

from PySide6.QtCore import QEvent, QObject, QRect, QSize, Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (QHBoxLayout, QLineEdit, QStyle, QStyledItemDelegate, QStyleOptionViewItem, QTextBrowser,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

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
    """The Help window (made once), at an entry, in front. A minimized Help comes back as it was (maximized or not):
    show(), raise_() and activateWindow() kept it minimized, so F1 and the Help button seemed to do nothing (the same
    fault as the tracer's, eq_page_files.EqFiles.open_trace, 2026-11-12)."""
    global _window
    if _window is None:
        _window = HelpWindow()
    _modal_over_modal(_window)
    _window.show()
    _window.setWindowState(_window.windowState() & ~Qt.WindowMinimized)
    _window.raise_()
    _window.activateWindow()
    if entry_id:
        _window.show_entry(entry_id)
    return _window


def _modal_over_modal(win):
    """Help opened while a window that blocks the others is open (Find…, Which measurement, Sources, History, the
    wait for a picture): Qt gives no input to a window outside that one, so Help showed but took no click or key.
    Then Help blocks the others itself until it closes (in front, with input; the window under it stays open, and
    takes input again when Help closes). Opened from a window that blocks nothing: a window of its own, as before.
    Qt takes a window's modality only when it shows, so a Help that is open is shown again. The window under Help
    can close by itself (the wait gets a picture): then Help goes back to a window of its own (_under_gone)."""
    from PySide6.QtWidgets import QApplication
    over = QApplication.activeModalWidget()
    if over is win:  # (F1 in Help itself, while it blocks the others: it stays so, over the same window)
        return
    want = Qt.ApplicationModal if over is not None else Qt.NonModal
    if win.windowModality() != want:
        win.hide()
        win.setWindowModality(want)
    _watch_under(win, over)


_under = []  # (the window under a Help that blocks the others: [its QWindow, the slot on its visibleChanged])


def _watch_under(win, over):
    """Help told when `over` (the window under it, or None) closes."""
    while _under:
        handle, slot = _under.pop()
        try:
            handle.visibleChanged.disconnect(slot)
        except (RuntimeError, TypeError):  # (the window is gone already)
            pass
    handle = over.windowHandle() if over is not None else None
    if handle is None:
        return

    def slot(visible):
        if not visible:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: _under_gone(win))  # (once Qt has taken it out of the windows that block)
    handle.visibleChanged.connect(slot)
    _under.append((handle, slot))


def _under_gone(win):
    """The window under Help closed by itself while Help blocks the others: Help is shown again over the next window
    that blocks the others, or as a window of its own when there is none (then each window takes input again). A
    Help that you minimized stays minimized as a window of its own (nothing asked for it); over a window that it
    blocks, it comes back (else that window takes no input, and nothing on the screen tells why)."""
    import shiboken6
    from PySide6.QtWidgets import QApplication
    if not shiboken6.isValid(win) or not win.isVisible() or win.windowModality() == Qt.NonModal:
        _watch_under(win, None)
        return
    win.hide()  # (also out of the windows that block: the one under it shows)
    over = QApplication.activeModalWidget()
    win.setWindowModality(Qt.ApplicationModal if over is not None else Qt.NonModal)
    _watch_under(win, over)
    win.show()
    if over is not None:
        win.setWindowState(win.windowState() & ~Qt.WindowMinimized)
    win.raise_()
    win.activateWindow()


class WrappedRows(QStyledItemDelegate):
    """The contents' rows as high as their words need: a long question goes on to a second line, never cut with "…"
    (Qt's setWordWrap alone wraps a row's words but keeps it one line high). The room for the words: the list's width
    less its frame, its scroll bar (counted always, so a scroll bar that comes and goes never changes the rows) and
    the row's indent, less the style's own margins."""

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        tree = self.parent()
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        depth, p = 1 if tree.rootIsDecorated() else 0, index.parent()
        while p.isValid():
            depth, p = depth + 1, p.parent()
        style = tree.style()
        width = (tree.width() - 2 * tree.frameWidth() - style.pixelMetric(QStyle.PM_ScrollBarExtent, None, tree)
                 - tree.indentation() * depth)
        opt.rect = QRect(0, 0, max(width, 1), size.height())
        room = style.subElementRect(QStyle.SE_ItemViewItemText, opt, tree).width()
        room -= 2 * (style.pixelMetric(QStyle.PM_FocusFrameHMargin, None, tree) + 1)  # (Qt's margin inside it)
        fm = QFontMetrics(opt.font)
        need = fm.boundingRect(QRect(0, 0, max(room, 1), 100000), Qt.TextWordWrap, opt.text).height()
        return QSize(size.width(), max(size.height(), need + size.height() - fm.height()))


class _Relayout(QObject):
    """The contents' rows measured again when the list's width changes (as the window first shows)."""

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Resize and ev.size().width() != ev.oldSize().width():
            obj.doItemsLayout()
        return False


class HelpWindow(QWidget):
    def __init__(self):
        super().__init__(None, Qt.Window)
        self.setWindowTitle("Help - AutoEQ Studio")  # (a window of its own: Windows' " - " and the app's name, UI-RULES 3)
        # (within the screen's room: 760 high was under a laptop's taskbar at 150 %; at its smallest, the page keeps
        # room for its words beside the contents, and a few rows of the contents show)
        fit_to_screen(self, (1000, 760), (680, 420))
        self.sections = _entries()
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
        self.toc.setUniformRowHeights(False)
        self.toc.setItemDelegate(WrappedRows(self.toc))
        self._relayout = _Relayout(self.toc)
        self.toc.installEventFilter(self._relayout)
        self.toc.setIndentation(18)
        # (the page shows one entry at a time, so the row that becomes current opens its entry: a click, the arrow
        # keys, Home, End; Enter too. A group row's chevron and the Left and Right keys open and close it, as before)
        self.toc.currentItemChanged.connect(lambda it, _old=None: self._item_chosen(it))
        self.toc.itemClicked.connect(lambda it, _c=0: self._item_chosen(it))
        self.toc.itemActivated.connect(lambda it, _c=0: self._item_chosen(it))
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

    def _item_chosen(self, it):
        anchor = it.data(0, Qt.UserRole) if it is not None else None
        if anchor and anchor != getattr(self, "page_now", None):
            self.show_entry(anchor)

    def _select(self, it):
        """A row made the current one without opening it again (the page is already done)."""
        self.toc.blockSignals(True)
        try:
            self.toc.setCurrentItem(it)
        finally:
            self.toc.blockSignals(False)
        self.toc.scrollToItem(it)

    def _matches(self, e, words):
        text = " ".join([e["title"], *[x for b in e["body"] for x in (b if isinstance(b, list) else [b])]]).lower()
        return all(w in text for w in words)

    def _retheme(self):
        self.render(keep=True)
        if not (self.q.text().split() and not self.found):  # (render drew the "No results" words again)
            self.show_page(getattr(self, "page_now", "start"), keep=True)

    def render(self, *_, keep=False):
        """The contents with only the entries that have every word typed (each group with one open), or all of them
        (the groups closed, but the one with the entry shown). A search with results shows one on the page: the entry
        that was open if it is one of them, else the first; a search without, the words "No results"."""
        words = self.q.text().lower().split()
        now = getattr(self, "page_now", None)
        found, first = 0, None
        self.toc.blockSignals(True)  # (rows hidden and groups closed here never open an entry)
        try:
            for _title, sid, entries in self.sections:
                g = self.items[sid]
                shown = 0
                for e in entries:
                    on = self._matches(e, words) if words else True
                    self.items[e["id"]].setHidden(not on)
                    shown += on
                    if words and on and first is None:
                        first = e["id"]
                found += shown if words else 0
                g.setHidden(bool(words) and not shown)
                g.setExpanded(bool(words) and bool(shown))
            self.items["start"].setHidden(bool(words))
            self.items["settings"].setHidden(bool(words) and all(self.items[sid].isHidden() for _t, sid, _e in
                                                                  self.sections[len(WIKI["groups"]) + 1:]))
            self.items["settings"].setExpanded(bool(words))
            if not words and now in self.items:  # (the entry shown keeps its group open)
                p = self.items[now].parent()
                while p is not None:
                    p.setExpanded(True)
                    p = p.parent()
        finally:
            self.toc.blockSignals(False)
        self.found = found
        if words and not found:
            self.view.setHtml(self._css() + "<p class='muted'>No results with all of these words. Type a smaller number "
                              "of words.</p>")
        elif words:
            show = now if now in _by_id() and not self.items[now].isHidden() else first
            self.show_page(show, keep=keep or show == now)
            self._select(self.items[show])
        elif not keep and now:
            self.show_page(now, keep=True)

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
        if it.isHidden() and self.q.text():
            self.q.blockSignals(True)
            self.q.clear()
            self.q.blockSignals(False)
            self.render()
        p = it.parent()
        while p is not None:
            p.setExpanded(True)
            p = p.parent()
        self.show_page(entry_id)
        self._select(it)


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

