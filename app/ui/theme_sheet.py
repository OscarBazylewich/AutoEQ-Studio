"""The app's stylesheet (Qt's style rules for every kind of control) in small named parts, in the order they
apply (when two rules style the same thing, the later one wins: the order matters). sheet(t, tick) joins them
into the one text theme.apply() gives the whole app, exactly as it was written in one piece before: t is the
colours in use (theme.tokens()), tick the path of the check box's tick picture (theme.py draws it). Each part
styles one kind of control, so a new look for one kind changes one part. Nothing is imported here.
"""


def base_and_tooltips(t, tick):
    """The windows' background, the text, tooltips."""
    return f"""\
    QMainWindow, QDialog {{ background: {t['bg']}; }}
    QWidget {{ color: {t['ink']}; font-size: 10pt; }}
    QToolTip {{ background: {t['card']}; color: {t['ink']}; border: 1px solid {t['line']}; padding: 4px; }}
"""


def cards_and_group_boxes(t, tick):
    """Cards: a QGroupBox (its title the card's heading) or a frame with card=true; a warning card (card="warn");
    the labels on them."""
    return f"""\
    QGroupBox, QFrame[card="true"] {{
        background: {t['card']}; border: 1px solid {t['line']}; border-radius: 10px; }}
    QGroupBox {{ margin-top: 0px; padding: 34px 12px 12px 12px; font-weight: 600; }}
    QGroupBox::title {{ subcontrol-origin: padding; subcontrol-position: top left; left: 12px; top: 10px;
        color: {t['ink']}; font-size: 10.5pt; font-weight: 600; }}
    QFrame[card="true"] {{ padding: 10px; }}
    QFrame[card="warn"] {{ background: {t['card']}; border: 1px solid {t['warn']}; border-left: 4px solid {t['warn']};
        border-radius: 10px; padding: 8px; }}
    QGroupBox QLabel, QFrame[card] QLabel {{ background: transparent; font-weight: 400; }}
"""


def text_roles(t, tick):
    """Text roles (QLabel's role): a screen's title, muted, warn, good, a chip, the brand."""
    return f"""\
    QLabel[role="title"] {{ font-size: 15pt; font-weight: 700; }}
    QLabel[role="muted"] {{ color: {t['muted']}; }}
    QLabel[role="warn"] {{ color: {t['warn']}; }}
    QLabel[role="good"] {{ color: {t['good']}; }}
    QLabel[role="chip"] {{ background: {t['shade']}; border: 1px solid {t['line']}; border-radius: 9px;
        padding: 2px 8px; }}
    QLabel[role="brand"] {{ font-size: 12pt; font-weight: 700; }}
"""


def buttons(t, tick):
    """Buttons: plain, pointed at, unavailable, checked, and the one main action of a card (primary=true)."""
    return f"""\
    QPushButton, QToolButton {{ background: {t['field']}; border: 1px solid {t['line']}; border-radius: 7px;
        padding: 5px 12px; }}
    QPushButton:hover, QToolButton:hover {{ border-color: {t['c1']}; }}
    QPushButton:disabled {{ color: {t['muted']}; }}
    QPushButton:checked {{ background: {t['sel']}; border-color: {t['c1']}; color: {t['sel_accent']}; font-weight: 600; }}
    QPushButton[primary="true"] {{ background: {t['btn']}; color: {t['on_btn']}; border: 1px solid {t['btn']}; font-weight: 600; }}
    QPushButton[primary="true"]:disabled {{ background: {t['line']}; border-color: {t['line']}; color: {t['muted']}; }}
"""


def top_bar(t, tick):
    """The top bar: its screens' buttons (nav=true), Online / Offline (online=true), the bar itself."""
    return f"""\
    QPushButton[nav="true"] {{ background: transparent; border: none; border-radius: 7px; padding: 6px 12px;
        color: {t['ink2']}; font-weight: 600; }}
    QPushButton[nav="true"]:checked {{ background: {t['sel']}; color: {t['sel_ink']}; }}
    QPushButton[nav="true"]:hover {{ color: {t['ink']}; }}
    QPushButton[online="true"] {{ border-radius: 12px; padding: 4px 12px; font-weight: 600; }}
    QPushButton[online="true"]:checked {{ background: {t['pill']}; color: {t['good']}; border-color: {t['good']}; }}
    QFrame[topbar="true"] {{ background: {t['card']}; border-bottom: 1px solid {t['line']}; }}
"""


def inputs(t, tick):
    """Drop-downs, text and number boxes, the hotkey box, and a drop-down's open list."""
    return f"""\
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QKeySequenceEdit {{ background: {t['field']};
        border: 1px solid {t['line']}; border-radius: 7px; padding: 4px 8px; }}
    QComboBox:hover, QLineEdit:focus {{ border-color: {t['c1']}; }}
    QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{ background: {t['shade']};
        color: {t['muted']}; border-color: {t['line']}; }}
    QComboBox QAbstractItemView {{ background: {t['card']}; border: 1px solid {t['line']};
        selection-background-color: {t['sel']}; selection-color: {t['sel_ink']}; }}
"""


def lists_and_tables(t, tick):
    """Lists and tables, their rows, and a table's column headings."""
    return f"""\
    QListWidget, QTableWidget {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: 8px;
        alternate-background-color: {t['field']}; gridline-color: {t['line']}; }}
    QListWidget::item {{ padding: 6px 4px; border-radius: 6px; }}
    QListWidget::item:selected, QTableWidget::item:selected {{ background: {t['sel']}; color: {t['sel_ink']}; }}
    QHeaderView::section {{ background: {t['shade']}; color: {t['ink2']}; border: none;
        border-bottom: 1px solid {t['line']}; padding: 5px 8px; font-weight: 600; }}
"""


def progress_and_sliders(t, tick):
    """Progress bars and sliders (across and up)."""
    return f"""\
    QProgressBar {{ background: {t['shade']}; border: none; border-radius: 4px; height: 8px; text-align: center; }}
    QProgressBar::chunk {{ background: {t['c1']}; border-radius: 4px; }}
    QSlider::groove:horizontal {{ height: 6px; background: {t['line']}; border-radius: 3px; }}
    QSlider::sub-page:horizontal {{ background: {t['c1']}; border-radius: 3px; }}
    QSlider::handle:horizontal {{ background: {t['card']}; border: 2px solid {t['c1']}; width: 14px; height: 14px;
        margin: -6px 0; border-radius: 9px; }}
    QSlider::groove:vertical {{ width: 6px; background: {t['line']}; border-radius: 3px; }}
    QSlider::sub-page:vertical, QSlider::add-page:vertical {{ background: {t['line']}; border-radius: 3px; }}
    QSlider::handle:vertical {{ background: {t['card']}; border: 2px solid {t['c1']}; width: 14px; height: 14px;
        margin: 0 -6px; border-radius: 9px; }}
    QSlider::handle:vertical:disabled {{ border-color: {t['muted']}; }}
"""


def scroll_areas_and_menus(t, tick):
    """Scroll areas, splitters, the status bar and menus."""
    return f"""\
    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QSplitter::handle {{ background: transparent; }}
    QStatusBar {{ color: {t['ink2']}; }}
    QMenu {{ background: {t['card']}; border: 1px solid {t['line']}; padding: 4px; }}
    QMenu::item {{ padding: 5px 18px; border-radius: 5px; }}
    QMenu::item:selected {{ background: {t['sel']}; color: {t['sel_ink']}; }}
    QMenu::item:disabled {{ color: {t['muted']}; }}
"""


def settings_boxes(t, tick):
    """Settings boxes: a value that isn't one (bad=true), the many-line text box, a setting's “auto” / “yours ↺” tag
    (tag=true), section headings, folds (fold=true)."""
    return f"""\
    QLineEdit[bad="true"], QPlainTextEdit[bad="true"] {{ border: 1px solid {t['err']}; background: {t['field']}; }}
    QPlainTextEdit {{ background: {t['field']}; border: 1px solid {t['line']}; border-radius: 7px; padding: 4px; }}
    QToolButton[tag="true"] {{ background: {t['shade']}; color: {t['muted']}; border: 1px solid {t['line']};
        border-radius: 9px; padding: 1px 8px; font-size: 8.5pt; }}
    QToolButton[tag="true"]:enabled {{ background: {t['sel']}; color: {t['sel_accent']}; border-color: {t['c1']}; }}
    QLabel[role="section"] {{ color: {t['muted']}; font-size: 8.5pt; font-weight: 700; letter-spacing: 1px;
        text-transform: uppercase; padding-top: 4px; }}
    QToolButton[fold="true"] {{ background: transparent; border: none; font-size: 10.5pt; font-weight: 600;
        padding: 6px 4px; }}
"""


def check_boxes(t, tick):
    """Check boxes and round choice buttons, and the tick boxes in lists and trees."""
    return f"""\
    QCheckBox, QRadioButton {{ background: transparent; spacing: 8px; }}
    QRadioButton::indicator, QCheckBox::indicator {{ width: 14px; height: 14px; background: {t['field']};
        border: 2px solid {t['muted']}; }}
    QRadioButton::indicator {{ border-radius: 9px; }}
    QCheckBox::indicator {{ border-radius: 4px; }}
    QRadioButton::indicator:hover, QCheckBox::indicator:hover {{ border-color: {t['c1']}; }}
    QRadioButton::indicator:checked {{ border: 2px solid {t['c1']};
        background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 {t['c1']}, stop:0.45 {t['c1']},
        stop:0.55 {t['field']}, stop:1 {t['field']}); }}
    QCheckBox::indicator:checked {{ background: {t['c1']}; border-color: {t['c1']}; image: url({tick}); }}
    QTreeView::indicator, QListView::indicator {{ width: 12px; height: 12px; background: {t['field']};
        border: 2px solid {t['muted']}; border-radius: 4px; }}
    QTreeView::indicator:checked, QListView::indicator:checked {{ background: {t['c1']}; border-color: {t['c1']};
        image: url({tick}); }}
    QTreeView::indicator:indeterminate {{ background: {t['sel']}; border-color: {t['c1']}; }}
    QRadioButton:disabled, QCheckBox:disabled {{ color: {t['muted']}; }}
"""


PARTS = [base_and_tooltips, cards_and_group_boxes, text_roles, buttons, top_bar, inputs, lists_and_tables,
         progress_and_sliders, scroll_areas_and_menus, settings_boxes, check_boxes]


def sheet(t, tick):
    """The whole stylesheet: every part in order, as one text (a line break first and four spaces last, as
    the one-piece text had)."""
    return "\n" + "".join(part(t, tick) for part in PARTS) + "    "
