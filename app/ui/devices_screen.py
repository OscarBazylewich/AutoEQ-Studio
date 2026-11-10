"""The Devices screen of AutoEQ Studio's window (ui\\window.py): your playback devices (connected ones first, then A to
Z by the name shown; the one playing has the green dot), and
for the one chosen: its profiles, the one on (or Off), adding and taking off profiles, whether Equalizer APO is
installed on it, your name for it (Rename…), and a line saying whether its EQ really plays (Equalizer APO asked by
itself, switcher\\check.py; again when something changes; check_line() gives that line its words).
DevicesScreen is one part of the window's class (Window, in ui\\window.py, is made of it, ProfilesScreen and
SettingsScreen): a plain class whose methods work on the window, so they use the window's own things (sw, app,
status(), the answers kept in _checks) and the Profiles part's import_files."""
import os
import re
import subprocess

from PySide6.QtCore import QEvent, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFrame, QGroupBox, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton, QRadioButton, QScrollArea,
                               QSizePolicy, QSplitter, QStyle, QStyledItemDelegate, QStyleOptionButton,
                               QStyleOptionViewItem, QStylePainter, QToolButton, QVBoxLayout, QWidget)

from switcher.core import shown
from ui import bubble, icons, theme, theme_tokens
from ui.window_parts import EmptyText, muted, profile_line, warning_card


DOT = Qt.UserRole + 1  # (a device row's dot: "playing", "connected" or "away", ui\\icons.py's DOTS)


class DeviceRows(QStyledItemDelegate):
    """The device list's rows as Windows 11 lists devices: the device's name, and under it where it is and its EQ, a
    little smaller in the secondary colour (each line cut with "…" when the list is narrow; the row's tooltip has both
    whole). The row's own background (pointed at, chosen, the accent's bar beside it) is the list's, as the theme draws
    any list; the colours, the dot's too (green playing, the accent connected, grey not), are the theme's when the row
    is drawn, so they follow light and dark, Windows' accent and its contrast themes. On the chosen row a dot keeps
    3:1 on the row's fill, as on the list: one that wouldn't (a contrast theme's) is in the chosen row's text colour."""

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        widget = opt.widget
        style = widget.style() if widget is not None else QApplication.style()
        margin = style.pixelMetric(QStyle.PM_FocusFrameHMargin, None, widget) + 1  # (as Qt's own rows have it)
        text_rect = style.subElementRect(QStyle.SE_ItemViewItemText, opt, widget).adjusted(margin, 0, -margin, 0)
        icon_rect = style.subElementRect(QStyle.SE_ItemViewItemDecoration, opt, widget)
        name, _, rest = opt.text.replace("\u2028", "\n").partition("\n")  # (Qt hands the line break as U+2028)
        icon = QIcon(opt.icon)  # (a copy: the option's own is emptied next)
        opt.text, opt.icon = "", QIcon()
        style.drawControl(QStyle.CE_ItemViewItem, opt, painter, widget)  # (the background only)
        t = theme.tokens()
        first = t["sel_ink"] if opt.state & QStyle.State_Selected else t["ink"]
        second = t["ink2"] if t["ink2"] != t["ink"] else first  # (a contrast theme: one colour for text)
        big = QFont(opt.font)
        small = QFont(opt.font)
        if big.pointSizeF() > 0:  # (Fluent's caption under its body text: 12 px under 14)
            small.setPointSizeF(big.pointSizeF() * 12 / 14)
        else:
            small.setPixelSize(max(1, round(big.pixelSize() * 12 / 14)))
        m1, m2 = QFontMetrics(big), QFontMetrics(small)
        gap = 2 if rest else 0
        height = m1.height() + (gap + m2.height() if rest else 0)
        top = text_rect.top() + (text_rect.height() - height) // 2
        painter.save()
        kind = index.data(DOT)
        if kind in icons.DOTS:  # (an 8 px dot in the middle of the icon's place, in the theme's colour for it)
            colour = icons.dot_colour(kind, t)
            if opt.state & QStyle.State_Selected and theme_tokens.contrast(colour, t["sel"]) < 3:
                # (on the chosen row, a dot that would melt into its fill is in the row's text colour: in a contrast
                # theme the playing dot is Windows' highlight colour, the chosen row's fill too, and the device
                # playing is the one chosen when Devices opens, so its dot went; its words still say it)
                colour = t["sel_ink"]
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(colour))
            c = QRectF(icon_rect).center()
            painter.drawEllipse(QRectF(c.x() - 4, c.y() - 4, 8, 8))
        elif not icon.isNull():
            icon.paint(painter, icon_rect, Qt.AlignCenter)
        painter.setFont(big)
        painter.setPen(QColor(first))
        painter.drawText(QRect(text_rect.left(), top, text_rect.width(), m1.height()), Qt.AlignLeft | Qt.AlignVCenter,
                         m1.elidedText(name, Qt.ElideRight, text_rect.width()))
        if rest:
            painter.setFont(small)
            painter.setPen(QColor(second))
            painter.drawText(QRect(text_rect.left(), top + m1.height() + gap, text_rect.width(), m2.height()),
                             Qt.AlignLeft | Qt.AlignVCenter, m2.elidedText(rest, Qt.ElideRight, text_rect.width()))
        painter.restore()


class ElidedRadio(QRadioButton):
    """A round button whose words end in "…" when its row is too narrow for them (a long profile name), so the row's ✕
    and the card's Rename… stay whole and in view (a name of 60 letters made the panel wider than the window at its
    smallest width, and cut them). text() and the name a screen reader reads stay whole; the tooltip has the whole
    name while it is cut."""

    def __init__(self, text):
        super().__init__(text)
        policy = self.sizePolicy()
        policy.setHorizontalPolicy(QSizePolicy.Preferred)  # (Qt's round button never becomes narrower than its words)
        self.setSizePolicy(policy)

    def minimumSizeHint(self):
        hint = super().sizeHint()
        fm = self.fontMetrics()
        cut = max(0, fm.horizontalAdvance(self.text()) - fm.horizontalAdvance(self.text()[:3] + "…"))
        return QSize(hint.width() - cut, hint.height())

    def _room(self, opt):
        return self.style().subElementRect(QStyle.SE_RadioButtonContents, opt, self).width()

    def is_cut(self):
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        return self.fontMetrics().horizontalAdvance(self.text()) > self._room(opt)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.setToolTip(self.text() if self.is_cut() else "")

    def paintEvent(self, _e):
        p = QStylePainter(self)
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        opt.text = self.fontMetrics().elidedText(self.text(), Qt.ElideRight, self._room(opt))
        p.drawControl(QStyle.CE_RadioButton, opt)


class ScreenArea(QScrollArea):
    """A part that scrolls up and down only (the Settings screen, a device's card): its smallest width is the one its
    content needs, so the window's smallest width, or the line between the device list and the card, never cuts it.
    side: the space at the content's right that its scroll bar goes in (Settings' 14 px: window_parts.
    scroll_bar_in_margin; 0: the bar beside the content). Without it, the Settings cards were cut 17 px at the window's
    smallest width, and a device's Rename… and ✕ when the line was dragged to the right. Measured again when its
    content changes size, or shows. Hidden (Settings while another screen shows), it keeps the width it had: Qt
    measures a hidden screen's rows again only when it shows (its APO row had all four buttons then, 962 px)."""

    def __init__(self, side=0):
        super().__init__()
        self.side, self._need = side, 0

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        inner = self.widget()
        if inner is not None and inner.layout() is not None and self.isVisible():
            m = inner.layout().contentsMargins()
            bar = self.verticalScrollBar().sizeHint().width()  # (the theme's is 12 px; another style's can be wider)
            self._need = inner.minimumSizeHint().width() - m.right() + max(self.side, bar + 2) + 2 * self.frameWidth()
        return hint.expandedTo(QSize(self._need, 0))

    def showEvent(self, e):
        super().showEvent(e)
        self.updateGeometry()

    def eventFilter(self, obj, e):
        if obj is self.widget() and e.type() == QEvent.LayoutRequest:
            self.updateGeometry()  # (its content's smallest width may have changed)
        return super().eventFilter(obj, e)


def check_line(ok, text):
    """The device's one-line answer from Equalizer APO's check (switcher\\check.explain's words; all of it in the
    tooltip): the first sentence up to its ": " and without a closing "(…)" remark. A profile's name in “ ” is kept
    whole, brackets and all ("Truthear GATe (Diffuse field)" was cut to “Truthear GATe, 2026-10-21)."""
    if ok is None:  # (couldn't ask: "Couldn't ask Equalizer APO: why")
        return text.split(": ")[0]
    names = re.findall(r"“[^”]*”", text)
    masked = re.sub(r"“[^”]*”", "\x00", text)
    first = masked.split(". ")[0].split(": ")[0]
    first = re.sub(r"\s*\([^()]*\)\.?$", "", first).rstrip(".") + "."
    for n in names:
        first = first.replace("\x00", n, 1)
    return first


class DevicesScreen:
    """The Devices screen's part of the window: the list of devices, the chosen one's panel, Rename…, and the line
    saying whether its EQ plays. A plain class (no __init__, no signals): what it keeps (_checks, _checking,
    _check_after, check_label) is made in Window.__init__."""

    # ---------------------------------------------------------------- Devices
    def _devices_tab(self):
        split = QSplitter()
        self.dev_list = QListWidget()
        self.dev_list.setAccessibleName("Devices")
        self.dev_list.setMinimumWidth(260)
        self.dev_list.setTextElideMode(Qt.ElideRight)  # (a long name ends in "…": its tooltip has it whole)
        self.dev_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dev_list.setItemDelegate(DeviceRows(self.dev_list))
        self.dev_list.currentItemChanged.connect(self._pick_device)
        # (no devices: one gray line in the list that tells the next step, as every empty list: UI-RULES 21)
        self.dev_empty = EmptyText(self.dev_list, "No playback devices. Connect a playback device to this PC.")
        split.addWidget(self.dev_list)
        self.dev_panel = QWidget()
        self.dev_lay = QVBoxLayout(self.dev_panel)
        # (its title level with the list's top, as every screen's content: Qt's 9 px put it lower, .claude/notes/
        # UI-RULES.md 5; a gap kept from the list beside it)
        self.dev_lay.setContentsMargins(16, 0, 0, 0)
        scroll = ScreenArea()  # (many profiles on a device, or a small window: the panel scrolls, never squeezed)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(self.dev_panel)
        split.addWidget(scroll)
        split.setStretchFactor(1, 1)
        split.setSizes([316, 540])
        return split

    def _device_state(self, key):
        d, rec = self.sw.device(key), self.sw.record(key)
        where = "Active" if key == self.sw.playing_key else "Connected" if d and d.connected else "Not connected"
        if self.sw.compare and self.sw.compare["key"] == key:
            return where, "EQ off, to compare"
        if self.sw.trial and self.sw.trial["key"] == key:
            return where, f"For 5 minutes: {self.sw.trial['name']}"
        name = self.sw.profile_name(rec["active"]) if rec else None
        return where, f"EQ: {name}" if name else "EQ off"

    def render_devices(self):
        self.dev_list.blockSignals(True)
        self.dev_list.clear()
        keys = [d.key for d in self.sw.devices]
        keys += [k for k in self.sw.s["devices"] if k not in keys and self.sw.record(k)["profiles"]]  # (gone, but set)
        keys.sort(key=self.sw.device_sort_key)  # (connected ones first, then A to Z by the name shown)
        for key in keys:
            rec, d = self.sw.record(key), self.sw.device(key)
            where, eq = self._device_state(key)
            item = QListWidgetItem(f"{shown(rec)}\n{where} · {eq}")
            kind = "playing" if key == self.sw.playing_key else "connected" if d and d.connected else "away"
            item.setIcon(icons.dot(kind))  # (its place in the row; DeviceRows draws it in the colours of the moment)
            item.setData(DOT, kind)
            item.setData(Qt.UserRole, key)
            item.setToolTip(f"{shown(rec)}\n{where} · {eq}" + (f"\nWindows name: {rec['label']}"
                                                                     if rec.get("nickname") else ""))
            self.dev_list.addItem(item)
            if key == self.selected:
                self.dev_list.setCurrentItem(item)
        if self.dev_list.currentItem() is None and self.dev_list.count():
            self.dev_list.setCurrentRow(0)
            self.selected = self.dev_list.currentItem().data(Qt.UserRole)
        self.dev_list.blockSignals(False)
        self.render_device_panel()

    def _pick_device(self, item, _old=None):
        if item:
            self.selected = item.data(Qt.UserRole)
            self.render_device_panel()

    def render_device_panel(self):
        while self.dev_lay.count():  # (the old panel's parts go at once: deleteLater alone waits for the event loop)
            w = self.dev_lay.takeAt(0).widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        key, lay = self.selected, self.dev_lay
        rec = self.sw.record(key) if key else None
        if not rec:  # (no devices: the list says so, in its middle)
            lay.addStretch(1)
            return
        d = self.sw.device(key)
        head = QFrame()
        theme.mark(head, card=True)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(4, 0, 4, 0)  # (a card frame's padding and these: its words start at a card's inset)
        words = QVBoxLayout()
        words.setSpacing(2)
        title = QLabel(shown(rec))
        theme.mark(title, role="heading")  # (a card's title: 16 px bold)
        title.setWordWrap(True)
        words.addWidget(title)
        where, _ = self._device_state(key)
        words.addWidget(muted(where + ("" if d else " (it is not in the Windows list)")
                              + (f" · Windows name: {rec['label']}" if rec.get("nickname") else "")))
        hl.addLayout(words, 1)
        ren = QPushButton("Rename…")
        icons.put(ren, "rename")
        ren.setToolTip("Your name for this device (for example, the IEM that you use on it)")
        ren.clicked.connect(lambda: self.rename_device(key))
        from ui import help_window
        help_window.tag(ren, "#dev-rename")
        hl.addWidget(ren, 0, Qt.AlignVCenter)
        lay.addWidget(head)

        if d and not d.apo:
            b = None
            if self.sw.apo.configurator:
                b = QPushButton("Open APO's Configurator")
                icons.put(b, "open_new")
                b.clicked.connect(self.open_configurator)
            warn, _ = warning_card("Equalizer APO is not installed on this device. Thus, no EQ operates on it. "
                                   "In APO's Configurator, select this device. Then restart Windows.", b)
            lay.addWidget(warn)

        box = QGroupBox("EQ for this device")
        bl = QVBoxLayout(box)
        # (its EQ off for now, to compare: a bar at the window's top, as a trial's, says so and brings it back,
        # UI-RULES 23; a yellow card here pushed the choices down)
        c = self.sw.compare if self.sw.compare and self.sw.compare["key"] == key else None
        trying = self.sw.trial if self.sw.trial and self.sw.trial["key"] == key else None
        group = QButtonGroup(box)
        off = QRadioButton("Off")
        off.setChecked(rec["active"] is None and not trying)
        off.toggled.connect(lambda on: on and self.sw.set_active(key, None))
        group.addButton(off)
        bl.addWidget(off)

        def two_lines(rb, data):
            """A row's words: its name (the round button), and under the name its data in small gray text."""
            col = QVBoxLayout()
            col.setSpacing(0)
            col.addWidget(rb)
            note = muted(data)
            theme.mark(note, small=True)
            note.setContentsMargins(26, 0, 0, 2)  # (under the name, not under the round button)
            col.addWidget(note)
            return col
        if trying:  # (selecting a profile ends the 5 minutes, as in the tray menu: switcher's set_active)
            rb = ElidedRadio(f"For 5 minutes: {trying['name']}")
            rb.setChecked(True)
            group.addButton(rb)
            holder = QWidget()
            tr = QHBoxLayout(holder)
            tr.setContentsMargins(0, 0, 0, 0)
            tr.addLayout(two_lines(rb, "The bar at the top has the time, Keep it and Do not keep it"), 1)
            bl.addWidget(holder)
        for pid in rec["profiles"]:
            p = self.sw.profiles().get(pid)
            row = QHBoxLayout()
            rb = ElidedRadio(p["name"])
            rb.setChecked(rec["active"] == pid and not trying)
            rb.toggled.connect(lambda on, pid=pid: on and self.sw.set_active(key, pid))
            group.addButton(rb)
            row.addLayout(two_lines(rb, profile_line(p) + ("  (its file is missing from APO's folder)" if
                                                           self.sw.profile_missing(pid) else "")), 1)
            x = QToolButton()
            theme.mark(x, quiet=True)  # (a row's ✕: every list's one look, UI-RULES 18)
            x.setText("✕")
            x.setToolTip("Remove it from this device (it stays in Profiles)")  # (✕ = Remove: UI-RULES 10, 16)
            x.setAccessibleName(f"Remove {p['name']} from this device")
            x.clicked.connect(lambda _=False, pid=pid: self.remove_profile_from_device(key, pid))
            row.addWidget(x, 0, Qt.AlignVCenter)
            holder = QWidget()
            holder.setLayout(row)
            row.setContentsMargins(0, 0, 0, 0)
            bl.addWidget(holder)
        add = QPushButton("Add a profile")  # (its menu's chevron: every menu button's, the theme's buttons part)
        icons.put(add, "add")
        menu = QMenu(add)
        others = [(pid, p) for pid, p in self.sw.profiles().items() if pid not in rec["profiles"]]
        for pid, p in sorted(others, key=lambda x: x[1]["name"].lower()):
            menu.addAction(p["name"], lambda pid=pid: self.sw.add_to_device(key, pid))
        if others:
            menu.addSeparator()
        menu.addAction("Import EQ files…", lambda: self.import_files(for_device=key))  # (Profiles' words: one act)
        make = menu.addAction("Make an EQ", lambda: self.show_page("eq"))  # (there, Use on device adds it to a device)
        make.setToolTip("Make an EQ on the Make an EQ screen. Then click Use on device, and select this device.")
        menu.setToolTipsVisible(True)
        add.setMenu(menu)
        bl.addWidget(add, 0, Qt.AlignLeft)
        lay.addWidget(box)
        self.check_label = self.check_row = self.check_warn = None
        if self.sw.apo.found and d and not c:  # (off for now, APO plays the flat file: asked again once it's back)
            row = QHBoxLayout()
            self.check_label = QLabel()
            self.check_label.setWordWrap(True)
            help_window.tag(self.check_label, "#dev-check")
            row.addWidget(self.check_label, 1)
            chk = QPushButton("Examine again")
            icons.put(chk, "refresh")
            chk.setToolTip("Examine again with the Benchmark tool of Equalizer APO (it only reads), and show all "
                           "the results")
            chk.clicked.connect(lambda: self.check_device(key))
            help_window.tag(chk, "#dev-check")
            row.addWidget(chk, 0, Qt.AlignTop)
            holder = QWidget()
            holder.setLayout(row)
            row.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(holder)
            self.check_row = holder
            # (a bad answer: Windows 11's warning bar in the line's place, with its symbol, and Examine again in it;
            # the ✕ before it was the symbol of Remove, UI-RULES 10)
            again = QPushButton("Examine again")
            icons.put(again, "refresh")
            again.setToolTip(chk.toolTip())
            again.clicked.connect(lambda: self.check_device(key))
            help_window.tag(again, "#dev-check")
            self.check_warn, self.check_warn_text = warning_card("", again)
            help_window.tag(self.check_warn_text, "#dev-check")
            self.check_warn.hide()
            lay.addWidget(self.check_warn)
            self._auto_check(key)
        hk, onoff = self.sw.s.get("hotkey"), self.sw.s.get("onoff_hotkey")
        lay.addWidget(muted("Select a profile in the tray icon menu" + (f", or with {hk} while this device is active."
                                                                         if hk else ".")
                            + (f" {onoff} disables its EQ and enables it again, to compare." if onoff else "")))
        lay.addStretch(1)

    def remove_profile_from_device(self, key, pid):
        """A profile's ✕: off this device (it stays in Profiles), with Undo in the window's line (UI-RULES 20): back in
        its place in the device's list (the hotkey's order), on only if it was."""
        rec = self.sw.record(key)
        if not rec or pid not in rec["profiles"]:  # (taken off already: a second click before the panel was redrawn)
            return
        was_on, at, was_last = rec["active"] == pid, rec["profiles"].index(pid), rec.get("last") == pid
        name = self.sw.profile_name(pid)
        self.sw.remove_from_device(key, pid)

        def undo():
            if pid not in self.sw.profiles():  # (deleted in Profiles meanwhile)
                self.status(f"You deleted “{name}” in Profiles: Undo is not possible.")
                return
            self.sw.add_to_device(key, pid, switch_on=was_on, at=at, last=was_last)
        self.status(f"Removed “{name}” from this device.", undo=undo)

    def rename_device(self, key):
        from ui.window_parts import ask_text  # (looked up here: the tests answer it)
        rec = self.sw.record(key)
        name, ok = ask_text(self, "Rename the device", "Your name for this device", rec.get("nickname", ""), "Rename",
                            placeholder=rec["label"], note="If the box is empty, AutoEQ Studio uses the Windows name.")
        if ok:
            self.sw.set_nickname(key, name)
            self.render_all()

    def _check_job(self, key):
        """What asking APO about a device needs: (the work, a function giving (ok, text) from its answer), or None
        when Windows doesn't list the device now."""
        from switcher import check
        from switcher import devices as D
        d, rec = self.sw.device(key), self.sw.record(key)
        if not d or not d.guids:
            return None
        main = [e for e in d.endpoints if not e.conn.endswith(D.HANDS_FREE)] or d.endpoints
        guid = next((e.guid for e in main if e.state == D.ACTIVE), main[0].guid)
        t = self.sw.trial if self.sw.trial and self.sw.trial["key"] == key else None
        p = self.sw.profiles().get(rec["active"]) if rec["active"] else None
        name = t["name"] if t else p and p["name"]
        pfile = self.sw.trial_path() if t else os.path.join(self.sw.apo.profiles, p["file"]) if p else None
        apo, on_device = self.sw.apo, d.apo

        def work():  # (an answer APO's tool couldn't give is said, not logged as a crash)
            try:
                return check.run(apo, guid)
            except (OSError, subprocess.SubprocessError) as e:
                return {"error": str(e) or type(e).__name__}

        def explain(found):
            if found.get("error"):
                return None, f"AutoEQ Studio cannot get data from Equalizer APO: {found['error']}"
            return check.explain(apo, found, name, pfile, on_device)
        return work, explain

    def _check_sig(self, key):
        """What the answer depends on: when any of it changes, APO is asked again."""
        rec, d = self.sw.record(key), self.sw.device(key)
        files = (self.sw.apo.config_txt, os.path.join(self.sw.apo.own, "switcher.txt"))
        return (rec["active"], bool(self.sw.trial and self.sw.trial["key"] == key), d and d.apo,
                d and d.connected, tuple(os.path.getmtime(f) if os.path.exists(f) else 0 for f in files))

    def _show_check(self, key):
        lab, got = self.check_label, self._checks.get(key)
        if lab is None or key != self.selected:
            return
        try:
            if key in self._checking and not got:
                lab.setText("Wait for Equalizer APO: does it use this EQ?")
                lab.setToolTip("")
                # (a usual wait, in a note's gray: it kept the colour of the answer before, a warning's after a bad
                # one, while Examine again asked)
                theme.mark(lab, role="muted")
            elif got:
                ok, text = got[1], got[2]
                lab.setText(("✓ " if ok else "") + check_line(ok, text))
                lab.setToolTip(text + "\nF1 opens Help.")
                theme.mark(lab, role="good" if ok else "warn" if ok is False else "muted")
            bad = bool(got) and got[1] is False
            if self.check_warn is not None:
                self.check_warn_text.setText(lab.text())
                self.check_warn_text.setToolTip(lab.toolTip())
                self.check_row.setVisible(not bad)
                self.check_warn.setVisible(bad)
        except RuntimeError:  # (the panel was drawn again meanwhile)
            pass

    def _auto_check(self, key, force=False, then=None):
        """The line saying whether the device's EQ plays: Equalizer APO asked in the background when something it
        depends on changed (the EQ, a trial, config.txt or switcher.txt written, plugged in), else the last answer."""
        from ui import tasks
        sig = self._check_sig(key)
        got = self._checks.get(key)
        if got and got[0] == sig and not force:
            self._show_check(key)
            if then:
                then(got)
            return
        job = self._check_job(key)
        if job is None:
            self._checks[key] = (sig, None, "Not connected: connect the device to examine its EQ.")
            self._show_check(key)
            return
        if key in self._checking:  # (asked already: a forced ask goes again after it, with its answer said)
            if force or then:
                self._check_after[key] = then
            return
        self._checking.add(key)
        self._checks.pop(key, None)
        self._show_check(key)
        work, explain = job

        def done(found, err):
            self._checking.discard(key)
            if err is not None:
                self._checks[key] = (sig, None, f"AutoEQ Studio cannot get data from Equalizer APO: {err}")
            else:
                ok, text = explain(found)
                self._checks[key] = (sig, ok, text)
            # (the EQ changed while APO was asked: that answer is about the one before, so it's asked again and the
            # old answer never shown; a change during an ask was dropped and the line named the previous EQ)
            if key not in self._check_after and self.sw.record(key) and self._check_sig(key) != sig:
                self._checks.pop(key, None)
                self._auto_check(key, then=then)
                return
            self._show_check(key)
            if then:
                then(self._checks[key])
            if key in self._check_after:
                self._auto_check(key, force=True, then=self._check_after.pop(key))
        tasks.background(work, done)

    def check_device(self, key):
        """Check again: APO asked now, and all it found said (switcher\\check.py)."""
        rec = self.sw.record(key)
        if self._check_job(key) is None:
            bubble.tell(None, "This device is not in the Windows list: connect it first.", near=self)
            return
        self.status("Wait for Equalizer APO…", 4000)

        def said(got):
            (QMessageBox.information if got[1] else QMessageBox.warning)(self, f"Examine: {shown(rec)}", got[2])
        self._auto_check(key, force=True, then=said)
