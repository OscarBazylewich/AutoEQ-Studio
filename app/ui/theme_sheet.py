"""The app's stylesheet (Qt's style rules for every kind of control) in small named parts, in the order they
apply (when two rules style the same thing, the later one wins: the order matters). sheet(t, img) joins them into
the one text theme.apply() gives the whole app: t is the colours in use (theme.tokens()), img the paths of the
pictures a stylesheet needs as files (theme.py draws them in t's colours: "tick", "chevron", "chevron_up", and the
accent's small bars that mark what's chosen, "pill_h" under a screen's name, "pill_v" beside a row). Each part
styles one kind of control, so a new look for one kind changes one part. Nothing is imported here.

The look is Windows 11's (Fluent, 2026-10-23, the user's choice from pictures): its type sizes (10.5 pt text),
4 px corners on controls and 8 px on cards, thin borders with a slightly darker bottom edge, fills that change when
pointed at, the accent (Windows' own colour) on the main action, ticks and what's chosen.
"""

FONT = 10.5   # (pt: Fluent's body text, 14 px)
PAD = (5, 11)  # (a control's padding, up and down / sideways: 32 px tall with the text)
CARD = 16     # (a card's padding)


def base_and_tooltips(t, img):
    """The windows' background, the text, tooltips."""
    return f"""
    QMainWindow, QDialog {{ background: {t['bg']}; }}
    QWidget {{ color: {t['ink']}; font-size: {FONT}pt; }}
    QToolTip {{ background: {t['menu']}; color: {t['ink']}; border: 1px solid {t['stroke']}; border-radius: 4px;
        padding: 5px 8px; }}
"""


def cards_and_group_boxes(t, img):
    """Cards: a QGroupBox (its title the card's heading) or a frame with card=true; a warning card (card="warn");
    the labels on them."""
    return f"""
    QGroupBox, QFrame[card="true"] {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: 8px; }}
    QGroupBox {{ margin-top: 0px; padding: {CARD + 24}px {CARD}px {CARD}px {CARD}px; font-weight: 600; }}
    QGroupBox::title {{ subcontrol-origin: padding; subcontrol-position: top left; left: {CARD}px; top: {CARD - 3}px;
        color: {t['ink']}; font-size: {FONT + 0.5}pt; font-weight: 600; }}
    QFrame[card="true"] {{ padding: {CARD - 4}px; }}
    QFrame[card="warn"] {{ background: {t['warn_bg']}; border: 1px solid {t['line']}; border-radius: 8px;
        padding: 8px; }}
    QGroupBox QLabel, QFrame[card] QLabel {{ background: transparent; font-weight: 400; }}
"""


def text_roles(t, img):
    """Text roles (QLabel's role): a screen's title, muted, warn, good, a chip, the brand."""
    return f"""
    QLabel[role="title"] {{ font-family: "Segoe UI Variable Display"; font-size: 20pt; font-weight: 600; }}
    QLabel[role="muted"] {{ color: {t['muted']}; }}
    QLabel[role="warn"] {{ color: {t['warn']}; }}
    QLabel[role="good"] {{ color: {t['good']}; }}
    QLabel[role="chip"] {{ background: {t['subtle']}; border: 1px solid {t['stroke']}; border-radius: 4px;
        padding: 2px 8px; }}
    QLabel[role="brand"] {{ font-family: "Segoe UI Variable Display"; font-size: 12pt; font-weight: 600; }}
"""


def buttons(t, img):
    """Buttons: plain, pointed at, pressed, unavailable, checked (the accent), and the one main action of a card
    (primary=true: the accent)."""
    return f"""
    QPushButton, QToolButton {{ background: {t['field']}; border: 1px solid {t['stroke']};
        border-bottom-color: {t['stroke_bottom']}; border-radius: 4px; padding: {PAD[0]}px {PAD[1]}px; }}
    QPushButton:hover, QToolButton:hover {{ background: {t['field_hover']}; }}
    QPushButton:pressed, QToolButton:pressed {{ background: {t['field_press']}; color: {t['ink2']};
        border-bottom-color: {t['stroke']}; }}
    QPushButton:disabled, QToolButton:disabled {{ background: {t['field_disabled']}; color: {t['disabled']};
        border-color: {t['stroke']}; }}
    QPushButton:checked {{ background: {t['accent']}; color: {t['on_accent']}; border-color: {t['accent']};
        border-bottom-color: {t['accent_bottom']}; }}
    QPushButton:checked:hover {{ background: {t['accent_hover']}; }}
    QPushButton[primary="true"] {{ background: {t['accent']}; color: {t['on_accent']}; border: 1px solid {t['accent']};
        border-bottom-color: {t['accent_bottom']}; }}
    QPushButton[primary="true"]:hover {{ background: {t['accent_hover']}; }}
    QPushButton[primary="true"]:pressed {{ background: {t['accent_press']}; }}
    QPushButton[primary="true"]:disabled {{ background: {t['accent_disabled']}; border-color: {t['accent_disabled']};
        color: {t['on_accent_disabled']}; }}
"""


def top_bar(t, img):
    """The top bar: its screens' buttons (nav=true: the one shown has the accent's bar under it), Online / Offline
    (online=true), the bar itself (on the window's background, as Windows 11's own)."""
    return f"""
    QPushButton[nav="true"] {{ background-color: transparent; border: none; border-radius: 4px;
        padding: 6px 12px 8px 12px; color: {t['ink2']}; }}
    QPushButton[nav="true"]:hover {{ background-color: {t['subtle_hover']}; color: {t['ink']}; }}
    QPushButton[nav="true"]:pressed {{ background-color: {t['subtle_press']}; }}
    QPushButton[nav="true"]:checked {{ color: {t['ink']}; background-color: transparent;
        background-image: url({img['pill_h']}); background-position: bottom center; background-repeat: no-repeat; }}
    QPushButton[nav="true"]:checked:hover {{ background-color: {t['subtle_hover']}; }}
    QPushButton[online="true"] {{ border-radius: 14px; padding: 4px 12px; }}
    QPushButton[online="true"]:checked {{ background: {t['pill']}; color: {t['good']}; border-color: {t['good']}; }}
    QFrame[topbar="true"] {{ background: {t['bg']}; border: none; }}
"""


def inputs(t, img):
    """Drop-downs, text and number boxes, the hotkey box, and a drop-down's open list. A text box has a darker line
    under it, the accent's when typing in it."""
    return f"""
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QKeySequenceEdit {{ background: {t['field']};
        border: 1px solid {t['stroke']}; border-radius: 4px; padding: {PAD[0]}px {PAD[1] - 3}px; }}
    QLineEdit, QSpinBox, QDoubleSpinBox, QKeySequenceEdit {{ border-bottom: 1px solid {t['strong']}; }}
    QComboBox {{ border-bottom-color: {t['stroke_bottom']}; padding-right: 26px; }}
    QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{ background: {t['field_hover']}; }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QKeySequenceEdit:focus {{ background: {t['field_focus']};
        border-bottom: 2px solid {t['accent']}; padding-bottom: {PAD[0] - 1}px; }}
    QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right; width: 26px; border: none; }}
    QComboBox::down-arrow {{ image: url({img['chevron']}); width: 12px; height: 12px; }}
    QSpinBox::up-button, QDoubleSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right;
        width: 22px; border: none; background: transparent; }}
    QSpinBox::down-button, QDoubleSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right;
        width: 22px; border: none; background: transparent; }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url({img['chevron_up']}); width: 9px; height: 9px; }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url({img['chevron']}); width: 9px; height: 9px; }}
    QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
        background: {t['field_disabled']}; color: {t['disabled']}; border-color: {t['stroke']}; }}
    QComboBox QAbstractItemView {{ background: {t['menu']}; border: 1px solid {t['stroke']}; padding: 4px;
        selection-background-color: {t['sel']}; selection-color: {t['sel_ink']}; outline: none; }}
"""


def lists_and_tables(t, img):
    """Lists and tables, their rows (pointed at, chosen: a quiet fill, and in lists the accent's bar beside the chosen
    row, as Windows 11's), and a table's column headings."""
    return f"""
    QListWidget, QTableWidget {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: 8px;
        alternate-background-color: {t['alt_row']}; gridline-color: {t['line']}; outline: none; }}
    QListWidget::item {{ padding: 7px 8px; border-radius: 4px; }}
    QListWidget::item:hover {{ background: {t['subtle_hover']}; }}
    QListWidget::item:selected, QTableWidget::item:selected {{ background: {t['sel']}; color: {t['sel_ink']}; }}
    QListWidget::item:selected {{ background-image: url({img['pill_v']}); background-position: center left;
        background-repeat: no-repeat; }}
    QHeaderView::section {{ background: {t['card']}; color: {t['ink2']}; border: none;
        border-bottom: 1px solid {t['line']}; padding: 6px 8px; font-weight: 600; }}
"""


def progress_and_sliders(t, img):
    """Progress bars (Windows 11's thin line) and sliders (across and up: a round thumb with the accent inside)."""
    groove = f"background: {t['strong']}; border-radius: 2px;"
    thumb = (f"border: 1px solid {t['stroke']}; border-radius: 10px; background: qradialgradient(cx:0.5, cy:0.5, "
             f"radius:0.5, fx:0.5, fy:0.5, stop:0 {t['accent']}, stop:0.48 {t['accent']}, stop:0.56 {t['thumb']}, "
             f"stop:1 {t['thumb']});")
    return f"""
    QProgressBar {{ background: {t['track']}; border: none; border-radius: 2px; max-height: 4px; min-height: 4px; }}
    QProgressBar::chunk {{ background: {t['accent']}; border-radius: 2px; }}
    QSlider::groove:horizontal {{ height: 4px; {groove} }}
    QSlider::sub-page:horizontal {{ background: {t['accent']}; border-radius: 2px; }}
    QSlider::handle:horizontal {{ width: 18px; height: 18px; margin: -8px 0; {thumb} }}
    QSlider::groove:vertical {{ width: 4px; {groove} }}
    QSlider::sub-page:vertical, QSlider::add-page:vertical {{ {groove} }}
    QSlider::handle:vertical {{ width: 18px; height: 18px; margin: 0 -8px; {thumb} }}
    QSlider::handle:horizontal:disabled, QSlider::handle:vertical:disabled {{ background: {t['field_disabled']}; }}
"""


def scroll_areas_and_menus(t, img):
    """Scroll areas and their thin scroll bars, splitters, the status bar and menus."""
    return f"""
    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QSplitter::handle {{ background: transparent; }}
    QStatusBar {{ color: {t['ink2']}; }}
    QMenu {{ background: {t['menu']}; border: 1px solid {t['stroke']}; padding: 4px; }}
    QMenu::item {{ padding: 6px 28px 6px 12px; border-radius: 4px; }}
    QMenu::item:selected {{ background: {t['sel']}; color: {t['sel_ink']}; }}
    QMenu::item:disabled {{ color: {t['disabled']}; }}
    QMenu::separator {{ height: 1px; background: {t['stroke']}; margin: 4px 0; }}
    QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {t['scroll']}; border-radius: 3px; min-height: 32px; margin: 2px 3px; }}
    QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 0; }}
    QScrollBar::handle:horizontal {{ background: {t['scroll']}; border-radius: 3px; min-width: 32px; margin: 3px 2px; }}
    QScrollBar::handle:hover {{ background: {t['scroll_hover']}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0px; height: 0px; border: none; background: none; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
"""


def settings_boxes(t, img):
    """Settings boxes: a value that isn't one (bad=true), the many-line text box, a setting's “auto” / “yours ↺” tag
    (tag=true), section headings, folds (fold=true)."""
    return f"""
    QLineEdit[bad="true"], QPlainTextEdit[bad="true"] {{ border: 1px solid {t['err']}; border-bottom: 2px solid {t['err']};
        background: {t['field']}; }}
    QPlainTextEdit {{ background: {t['field']}; border: 1px solid {t['stroke']}; border-bottom: 1px solid {t['strong']};
        border-radius: 4px; padding: 4px; }}
    QToolButton[tag="true"] {{ background: {t['subtle']}; color: {t['muted']}; border: 1px solid {t['stroke']};
        border-radius: 10px; padding: 1px 8px; font-size: {FONT - 1.5}pt; }}
    QToolButton[tag="true"]:enabled {{ background: {t['accent_soft']}; color: {t['accent_text']};
        border-color: {t['accent_soft_line']}; }}
    QLabel[role="section"] {{ color: {t['ink']}; font-size: {FONT}pt; font-weight: 600; padding-top: 6px; }}
    QToolButton[fold="true"] {{ background: transparent; border: none; font-size: {FONT + 0.5}pt; font-weight: 600;
        padding: 6px 4px; }}
"""


def check_boxes(t, img):
    """Check boxes and round choice buttons (the accent when ticked), and the tick boxes in lists and trees."""
    return f"""
    QCheckBox, QRadioButton {{ background: transparent; spacing: 8px; }}
    QCheckBox::indicator, QRadioButton::indicator {{ width: 18px; height: 18px; background: {t['check_fill']};
        border: 1px solid {t['strong']}; }}
    QCheckBox::indicator {{ border-radius: 4px; }}
    QRadioButton::indicator {{ border-radius: 10px; }}
    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ background: {t['check_hover']}; }}
    QCheckBox::indicator:checked {{ background: {t['accent']}; border-color: {t['accent']}; image: url({img['tick']}); }}
    QCheckBox::indicator:checked:hover {{ background: {t['accent_hover']}; border-color: {t['accent_hover']}; }}
    QRadioButton::indicator:checked {{ border: 1px solid {t['accent']}; background: qradialgradient(cx:0.5, cy:0.5,
        radius:0.5, fx:0.5, fy:0.5, stop:0 {t['on_accent']}, stop:0.36 {t['on_accent']}, stop:0.46 {t['accent']},
        stop:1 {t['accent']}); }}
    QTreeView::indicator, QListView::indicator {{ width: 16px; height: 16px; background: {t['check_fill']};
        border: 1px solid {t['strong']}; border-radius: 4px; }}
    QTreeView::indicator:checked, QListView::indicator:checked {{ background: {t['accent']}; border-color: {t['accent']};
        image: url({img['tick']}); }}
    QTreeView::indicator:indeterminate {{ background: {t['accent']}; border-color: {t['accent']}; }}
    QRadioButton:disabled, QCheckBox:disabled {{ color: {t['disabled']}; }}
"""


# ---------------------------------------------------------------- each screen's own rules (after the shared ones,
# so a screen's rule wins over them): its controls by objectName (#name) or a property of its own, for what used to
# be a style set in the screen's code. Each belongs to that screen's area (the restyle's stage 2, 2026-10-23).
def window_screens(t, img):
    """The window around the screens and the device screens: the banner, the trial bar, Devices, Profiles,
    Settings, Set up, the tray menu, and the app's message boxes and input boxes (Windows 11's dialogs: the answer
    Enter gives in the accent).
    - a symbol in front of words (glyph=true: the warning sign on the banner, the trial's clock), in its role's colour
    - the status line, its words lined up with the screens'
    - Devices: a profile's ✕ (#takeOff: a quiet button, filled when pointed at), Add a profile's chevron (#addProfile)
    - Profiles: the table's words under their headings (#profileTable)
    - Set up (#setUp): the words on the card colour, the buttons on a band in the window's colour (#dialogFooter)
    - the tray menu (#tray): its headings (the device playing, the EQ being tried) readable, not greyed
    - message boxes' buttons made wider by their padding (a min-width is a fixed minimum in Qt: a message box then
      squeezed its long buttons below their words)"""
    default = (f"background: {t['accent']}; color: {t['on_accent']}; border: 1px solid {t['accent']}; "
               f"border-bottom-color: {t['accent_bottom']};")
    return f"""
    QLabel[glyph="true"] {{ font-size: 12pt; }}
    QLabel#trialGlyph {{ color: {t['accent_text']}; }}
    QStatusBar#windowStatus::item {{ border: none; }}
    QStatusBar#windowStatus QLabel {{ color: {t['ink2']}; padding-left: 8px; }}
    QToolButton#takeOff {{ background: transparent; border: 1px solid transparent; color: {t['ink2']};
        padding: 4px 9px; }}
    QToolButton#takeOff:hover {{ background: {t['subtle_hover']}; color: {t['ink']}; }}
    QToolButton#takeOff:pressed {{ background: {t['subtle_press']}; }}
    QTableWidget#profileTable::item {{ padding: 0px 5px; }}
    QPushButton#addProfile {{ padding-right: 30px; }}
    QPushButton#addProfile::menu-indicator {{ image: url({img['chevron']}); subcontrol-origin: padding;
        subcontrol-position: center right; right: 10px; width: 12px; height: 12px; }}
    QDialog#setUp {{ background: {t['card']}; }}
    QDialog#setUp QListWidget::item {{ padding: 3px 8px; }}
    QFrame#dialogFooter {{ background: {t['bg']}; border: none; border-top: 1px solid {t['line']}; }}
    QMessageBox QPushButton, QInputDialog QPushButton {{ padding-left: 24px; padding-right: 24px; }}
    QMessageBox QPushButton:default, QInputDialog QPushButton:default {{ {default} }}
    QMessageBox QPushButton:default:hover, QInputDialog QPushButton:default:hover {{ background: {t['accent_hover']}; }}
    QMessageBox QPushButton:default:pressed, QInputDialog QPushButton:default:pressed {{
        background: {t['accent_press']}; }}
    QMenu#tray::item:disabled {{ color: {t['muted']}; }}
"""


def eq_screen(t, img):
    """Make an EQ: its cards, settings folds, result card, notices. Its own properties: eqtitle (the graph's title,
    the result's name: a little bigger than a card's heading, in Windows 11's display type), eqsub (a fold inside a
    card, the Target card's Adjust: body text, quieter than the card's title, as Windows 11's expanders), eqsubtle (a
    button with no fill until it's pointed at: the notice's ✕, as the close button of Windows 11's information bar)."""
    return f"""
    QLabel[eqtitle="true"] {{ font-family: "Segoe UI Variable Display"; font-size: {FONT + 1.5}pt; font-weight: 600; }}
    QToolButton[eqsub="true"] {{ font-size: {FONT}pt; font-weight: 400; }}
    QPushButton[eqsubtle="true"] {{ background: transparent; border-color: transparent; }}
    QPushButton[eqsubtle="true"]:hover {{ background: {t['subtle_hover']}; }}
    QPushButton[eqsubtle="true"]:pressed {{ background: {t['subtle_press']}; color: {t['ink2']}; }}
"""


def eq_windows(t, img):
    """Make an EQ's own windows: the filter editor, All results, Compare, Run several, History."""
    return ""


def find_windows(t, img):
    """Find…, Sources and Which measurement."""
    return ""


def listen(t, img):
    """Listen's card."""
    return ""


def tracer(t, img):
    """The tracer's window."""
    return ""


def guide_and_help(t, img):
    """The Guide's layer and card, and the Help window."""
    return ""


PARTS = [base_and_tooltips, cards_and_group_boxes, text_roles, buttons, top_bar, inputs, lists_and_tables,
         progress_and_sliders, scroll_areas_and_menus, settings_boxes, check_boxes,
         window_screens, eq_screen, eq_windows, find_windows, listen, tracer, guide_and_help]


def sheet(t, img):
    """The whole stylesheet: every part in order, as one text."""
    return "".join(part(t, img) for part in PARTS)
