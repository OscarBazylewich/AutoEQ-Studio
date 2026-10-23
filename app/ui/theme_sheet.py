"""The app's stylesheet (Qt's style rules for every kind of control) in small named parts, in the order they
apply (when two rules style the same thing, the later one wins: the order matters). sheet(t, img) joins them into
the one text theme.apply() gives the whole app: t is the colours in use (theme.tokens()), img the paths of the
pictures a stylesheet needs as files (theme.py draws them in t's colours: "tick", Windows 11's chevrons "chevron"
(down), "chevron_up" and "chevron_right", and the accent's small bars that mark what's chosen, "pill_h" under a
screen's name, "pill_v" beside a row). Each part styles one kind of control, so a new look for one kind changes one
part. Nothing is imported here.

The look is Windows 11's (Fluent, 2026-10-23, the user's choice from pictures): its type sizes (10.5 pt text),
4 px corners on controls and 8 px on cards, thin borders with a slightly darker bottom edge, fills that change when
pointed at, the accent (Windows' own colour) on the main action, ticks and what's chosen.
"""

FONT = 10.5   # (pt: Fluent's body text, 14 px)
PAD = (5, 11)  # (a control's padding, up and down / sideways: 32 px tall with the text)
CARD = 16     # (a card's inset: its title and its content start this far inside its border, as Windows 11's cards)
LAYOUT = 9    # (the margin Qt's own layouts keep inside a widget when the code doesn't set one: a card's padding is
#               CARD less this, so its content starts at CARD too)


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
    the labels on them. A QGroupBox's title and content start CARD inside its border (its padding is CARD less the
    margin Qt's layout adds; Qt centres the title in a place a space wider than its words: half a space less); its
    title is drawn in the box's own font (Qt doesn't size ::title), 11 pt as a fold's title, while what's on it keeps
    10.5 pt (the QWidget rule). A card frame's padding leaves 4 px for its code's own layout margin (the trial bar's, a
    fold's)."""
    return f"""
    QGroupBox, QFrame[card="true"] {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: 8px; }}
    QGroupBox {{ margin-top: 0px; padding: {CARD + 24}px {CARD - LAYOUT}px {CARD}px {CARD - LAYOUT}px;
        font-size: {FONT + 0.5}pt; font-weight: 600; }}
    QGroupBox::title {{ subcontrol-origin: padding; subcontrol-position: top left; left: {CARD - 2}px;
        top: {CARD - 3}px; color: {t['ink']}; }}
    QFrame[card="true"] {{ padding: {CARD - 4}px; }}
    QFrame[card="warn"] {{ background: {t['warn_bg']}; border: 1px solid {t['line']}; border-radius: 8px;
        padding: 8px; }}
    QGroupBox QLabel, QFrame[card] QLabel {{ background: transparent; font-weight: 400; }}
"""


def text_roles(t, img):
    """Text roles (QLabel's role): a screen's title, muted, warn, good, a chip, the brand. A label with padding gets
    no indent of Qt's own (half an "x" more at its left: a chip's words sat off its middle)."""
    return f"""
    QLabel[role="title"] {{ font-family: "Segoe UI Variable Display"; font-size: 20pt; font-weight: 600; }}
    QLabel[role="muted"] {{ color: {t['muted']}; }}
    QLabel[role="warn"] {{ color: {t['warn']}; }}
    QLabel[role="good"] {{ color: {t['good']}; }}
    QLabel[role="chip"] {{ background: {t['subtle']}; border: 1px solid {t['stroke']}; border-radius: 4px;
        padding: 2px 8px; qproperty-indent: 0; }}
    QLabel[role="brand"] {{ font-family: "Segoe UI Variable Display"; font-size: 12pt; font-weight: 600; }}
"""


def buttons(t, img):
    """Buttons: plain, pointed at, pressed, unavailable, checked (the accent), the one main action of a card
    (primary=true: the accent), a quiet one (quiet=true: no fill until pointed at, as a row's ✕), and a button with a
    menu (Use on device, Add a profile …: Windows 11's chevron at its right, with room before it; Qt gives the
    button that much more width)."""
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
    QPushButton[quiet="true"], QToolButton[quiet="true"] {{ background: transparent; border: 1px solid transparent;
        color: {t['ink2']}; }}
    QPushButton[quiet="true"]:hover, QToolButton[quiet="true"]:hover {{ background: {t['subtle_hover']};
        color: {t['ink']}; }}
    QPushButton[quiet="true"]:pressed, QToolButton[quiet="true"]:pressed {{ background: {t['subtle_press']};
        color: {t['ink2']}; }}
    QPushButton[quiet="true"]:disabled, QToolButton[quiet="true"]:disabled {{ background: transparent;
        color: {t['disabled']}; }}
    QPushButton::menu-indicator {{ image: url({img['chevron']}); subcontrol-origin: padding;
        subcontrol-position: center right; width: 16px; height: 12px; right: 6px; }}
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
    under it, the accent's when typing in it. A drop-down's list has one look, short or long (one with its search box,
    #searchPopup: ui\\search_combo.py): on the menus' colour in a thin border with 8 px corners (the short list draws
    it itself; the long one's list inside its frame is without one), its rows as the lists' (filled when pointed at;
    the chosen one filled, the accent's bar beside it), and both open under the drop-down (combobox-popup: 0, Qt's
    list rather than Fusion's menu-like one, which drew a frame of its own around the list)."""
    return f"""
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QKeySequenceEdit {{ background: {t['field']};
        border: 1px solid {t['stroke']}; border-radius: 4px; padding: {PAD[0]}px {PAD[1] - 3}px; }}
    QLineEdit, QSpinBox, QDoubleSpinBox, QKeySequenceEdit {{ border-bottom: 1px solid {t['strong']}; }}
    QComboBox {{ border-bottom-color: {t['stroke_bottom']}; padding-right: 26px; combobox-popup: 0; }}
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
    QComboBox QAbstractItemView, QWidget#searchPopup {{ background: {t['menu']}; border: 1px solid {t['stroke']};
        border-radius: 8px; }}
    QComboBox QAbstractItemView {{ padding: 4px; selection-background-color: {t['sel']};
        selection-color: {t['sel_ink']}; outline: none; }}
    QComboBox QAbstractItemView::item {{ padding: 7px 8px; border-radius: 4px; }}
    QComboBox QAbstractItemView::item:hover {{ background: {t['subtle_hover']}; }}
    QComboBox QAbstractItemView::item:selected {{ background: {t['sel']}; color: {t['sel_ink']};
        background-image: url({img['pill_v']}); background-position: center left; background-repeat: no-repeat; }}
    QWidget#searchPopup QListWidget {{ background: transparent; border: none; padding: 0px; }}
"""


def lists_and_tables(t, img):
    """Lists and tables, their rows (pointed at, chosen: a quiet fill, and in lists the accent's bar beside the chosen
    row, as Windows 11's), and a table's column headings. A list whose rows hold controls of their own (setItemWidget:
    Find…'s) sets its rows' padding itself: Qt puts those controls inside this 7 px padding, which cuts them."""
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
    """Scroll areas and their thin scroll bars, splitters, the status bar and menus. A menu's item that can't be
    chosen is a note in this app ("No presets yet: …", "Run first", the tray's device playing): in the muted colour,
    readable (4.5:1), not the unavailable grey. A submenu's arrow is Windows 11's chevron."""
    return f"""
    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QSplitter::handle {{ background: transparent; }}
    QStatusBar {{ color: {t['ink2']}; }}
    QMenu {{ background: {t['menu']}; border: 1px solid {t['stroke']}; padding: 4px; }}
    QMenu::item {{ padding: 6px 28px 6px 12px; border-radius: 4px; }}
    QMenu::item:selected {{ background: {t['sel']}; color: {t['sel_ink']}; }}
    QMenu::item:disabled {{ color: {t['muted']}; }}
    QMenu::right-arrow {{ image: url({img['chevron_right']}); width: 12px; height: 12px; right: 8px; }}
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
    (tag=true), section headings (in line with the labels under them: no indent of Qt's own), folds (fold=true:
    ui\\forms.py's Fold, the Target card's Adjust; Windows 11's chevron, right when closed and down when open, its
    place starting where the button does, so in line with the card's content, and a fill when pointed at, as Windows
    11's expanders)."""
    return f"""
    QLineEdit[bad="true"], QPlainTextEdit[bad="true"] {{ border: 1px solid {t['err']}; border-bottom: 2px solid {t['err']};
        background: {t['field']}; }}
    QPlainTextEdit {{ background: {t['field']}; border: 1px solid {t['stroke']}; border-bottom: 1px solid {t['strong']};
        border-radius: 4px; padding: 4px; }}
    QToolButton[tag="true"] {{ background: {t['subtle']}; color: {t['muted']}; border: 1px solid {t['stroke']};
        border-radius: 10px; padding: 1px 8px; font-size: {FONT - 1.5}pt; }}
    QToolButton[tag="true"]:enabled {{ background: {t['accent_soft']}; color: {t['accent_text']};
        border-color: {t['accent_soft_line']}; }}
    QLabel[role="section"] {{ color: {t['ink']}; font-size: {FONT}pt; font-weight: 600; padding-top: 6px;
        qproperty-indent: 0; }}
    QToolButton[fold="true"] {{ background: transparent; border: none; border-radius: 4px; font-size: {FONT + 0.5}pt;
        font-weight: 600; padding: 6px 8px 6px 0px; }}
    QToolButton[fold="true"]:hover {{ background: {t['subtle_hover']}; }}
    QToolButton[fold="true"]:pressed {{ background: {t['subtle_press']}; }}
    QToolButton[fold="true"]::right-arrow {{ image: url({img['chevron_right']}); padding-right: 6px; }}
    QToolButton[fold="true"]::down-arrow {{ image: url({img['chevron']}); padding-right: 6px; }}
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
    - Devices: a profile's ✕ (#takeOff: a quiet button, filled when pointed at); Add a profile's chevron is every
      menu button's (buttons()), the tray menu's headings every menu's notes (scroll_areas_and_menus())
    - Profiles: the table's words under their headings (#profileTable)
    - Set up (#setUp): the words on the card colour, the buttons on a band in the window's colour (#dialogFooter)
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
    QDialog#setUp {{ background: {t['card']}; }}
    QDialog#setUp QListWidget::item {{ padding: 3px 8px; }}
    QFrame#dialogFooter {{ background: {t['bg']}; border: none; border-top: 1px solid {t['line']}; }}
    QMessageBox QPushButton, QInputDialog QPushButton {{ padding-left: 24px; padding-right: 24px; }}
    QMessageBox QPushButton:default, QInputDialog QPushButton:default {{ {default} }}
    QMessageBox QPushButton:default:hover, QInputDialog QPushButton:default:hover {{ background: {t['accent_hover']}; }}
    QMessageBox QPushButton:default:pressed, QInputDialog QPushButton:default:pressed {{
        background: {t['accent_press']}; }}
"""


def eq_screen(t, img):
    """Make an EQ: its cards, settings folds, result card, notices. Its own properties: eqtitle (the graph's title,
    the result's name: a little bigger than a card's heading, in Windows 11's display type), eqsub (a fold inside a
    card, the Target card's Adjust: body text, quieter than the card's title, as Windows 11's expanders), eqsubtle (a
    button with no fill until it's pointed at: the notice's ✕, as the close button of Windows 11's information bar).
    And in its Guide (ui\\guide_eq.py), a submenu's arrow in a menu the demos draw (#eqMockArrow): the picture the
    app's menus draw for one (Windows 11's chevron, scroll_areas_and_menus()), not a typed ▸."""
    return f"""
    QLabel[eqtitle="true"] {{ font-family: "Segoe UI Variable Display"; font-size: {FONT + 1.5}pt; font-weight: 600; }}
    QToolButton[eqsub="true"] {{ font-size: {FONT}pt; font-weight: 400; }}
    QPushButton[eqsubtle="true"] {{ background: transparent; border-color: transparent; }}
    QPushButton[eqsubtle="true"]:hover {{ background: {t['subtle_hover']}; }}
    QPushButton[eqsubtle="true"]:pressed {{ background: {t['subtle_press']}; color: {t['ink2']}; }}
    QFrame#tourMock QLabel#eqMockArrow {{ image: url({img['chevron_right']}); padding: 0px; border: none;
        background: transparent; }}
"""


def eq_windows(t, img):
    """Make an EQ's own windows: the filter editor, All results, Compare, Run several, History. Their controls by
    object names of their own (eqw…): the filter table's boxes a little apart (the table has no grid lines) and its
    headings 3 px further in, so Type's (at the left) starts where its drop-downs' words do, inside their border and
    padding (the centred ones stay centred over their values); ✕ (delete a filter, take an EQ out of History) as
    Windows 11's subtle buttons, without a fill until pointed at; a switched-off filter's slider with its thumb's ring
    and a grey dot (Windows 11's), not a flat square; the pre-amp's bar as a slider's empty track; the error grid's
    corner as its headings; room at the left of the tables' cells, so their words start under their headings (Run
    several's, All results' grid and table, Compare's numbers and filters: Windows 11's table look, no grid lines)."""
    return f"""
    QTableWidget#eqwFilters QLineEdit, QTableWidget#eqwFilters QComboBox {{ margin: 1px 2px; }}
    QTableWidget#eqwFilters QHeaderView::section {{ padding-left: 11px; padding-right: 11px; }}
    QToolButton#eqwDelete, QPushButton#eqwDelete {{ background: transparent; border: 1px solid transparent;
        color: {t['ink2']}; }}
    QToolButton#eqwDelete:hover, QPushButton#eqwDelete:hover {{ background: {t['subtle_hover']}; color: {t['ink']}; }}
    QToolButton#eqwDelete:pressed, QPushButton#eqwDelete:pressed {{ background: {t['subtle_press']};
        color: {t['ink2']}; }}
    QToolButton#eqwDelete:disabled, QPushButton#eqwDelete:disabled {{ background: transparent; color: {t['disabled']}; }}
    QSlider#eqwGain::handle:vertical:disabled {{ border: 1px solid {t['stroke']}; background: qradialgradient(cx:0.5,
        cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 {t['disabled']}, stop:0.48 {t['disabled']}, stop:0.56 {t['thumb']},
        stop:1 {t['thumb']}); }}
    QFrame#eqwPreamp {{ background: {t['track']}; border: none; border-radius: 2px; }}
    QTableWidget#eqwGrid QTableCornerButton::section {{ background: {t['card']}; border: none;
        border-bottom: 1px solid {t['line']}; }}
    QTableWidget#eqwQueue::item, QTableWidget#eqwNumbers::item, QTableWidget#eqwGrid::item,
    QTableWidget#eqwResults::item, QTableWidget#eqwCmpFilters::item {{ padding: 0px 5px; }}
"""


def find_windows(t, img):
    """Find…, Sources and Which measurement (ui\\picker.py, sources_window.py, compare_window.py). Find…: its list's
    rows without padding (Qt puts a row's widgets inside it: the lists' 7 px cut its buttons and names; headings and
    notes keep a little at the sides), a result's name (semibold) and its download mark (Windows 11's symbol, from its
    icon font; Segoe MDL2 Assets on Windows 10); a row's quiet ✕, pointed at or pressed, as Windows 11 fills a quiet
    button: the text's colour at 6 % (4 % pressed) laid over the row's own fill under the mouse (the quiet buttons'
    usual fill is the same colour as a pointed-at row's, so on a row it showed nothing; a contrast theme keeps it in
    sight too).
    Sources: its tree of databases as the lists (a card with rounded corners, whole rows filled when pointed at or
    chosen; their ticks say which are on). Which measurement: the rank, a measurement's name, its reasons (+ good,
    − not), the warning symbol of a note to heed, its chart's card, and a box filled while the mouse is over it (its
    curve is the one on top)."""
    veil = lambda alpha: f"#{alpha}{t['ink'][1:]}"  # (the text's colour, see-through: #AARRGGBB)
    return f"""
    QListWidget#findList::item {{ padding: 0px; }}
    QListWidget#findList::item:disabled {{ padding: 0px 8px; }}
    QListWidget#findList::item:disabled:hover {{ background: transparent; }}
    QListWidget#findList QPushButton[quiet="true"]:hover {{ background: {veil("0f")}; }}
    QListWidget#findList QPushButton[quiet="true"]:pressed {{ background: {veil("0a")}; }}
    QLabel#findRowName {{ font-weight: 600; }}
    QLabel#findMark, QLabel#whichNoteMark {{ font-family: "Segoe Fluent Icons", "Segoe MDL2 Assets"; font-size: 12pt;
        color: {t['muted']}; padding: 0px 2px; }}
    QLabel#whichNoteMark {{ color: {t['warn']}; padding: 1px 4px 0px 0px; }}
    QTreeWidget#sourcesTree {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: 8px;
        outline: none; padding: 2px; show-decoration-selected: 1; }}
    QTreeWidget#sourcesTree QHeaderView, QTreeWidget#sourcesTree QHeaderView::section {{ background: transparent; }}
    QTreeWidget#sourcesTree::item {{ padding: 4px 2px; }}
    QTreeWidget#sourcesTree::item:hover {{ background: {t['subtle_hover']}; }}
    QTreeWidget#sourcesTree::item:selected {{ background: {t['sel']}; color: {t['sel_ink']}; }}
    QLabel#whichRank {{ font-family: "Segoe UI Variable Display"; font-size: 15pt; font-weight: 600; }}
    QLabel#whichName {{ font-weight: 600; }}
    QLabel[reason="plus"] {{ color: {t['good']}; }}
    QLabel[reason="minus"] {{ color: {t['err']}; }}
    QFrame#whichRow:hover, QFrame#whichAverage:hover {{ background: {t['subtle']}; }}
    QFrame#whichChart {{ padding: 0px; }}
"""


def listen(t, img):
    """Listen's card (ui\\listen.py): each version's button marked on its left in its curve's colour on the graph
    (EQ off: the measurement's; the selected EQ: "with the EQ"'s; your EQs to compare: their own), and the same
    colour on the ■ beside each EQ to compare. listen_mark=<the colour's name> on the button or the ■."""
    return "".join(f"""
    QPushButton[listen_mark="{k}"] {{ border-left: 4px solid {t[k]}; }}
    QLabel[listen_mark="{k}"] {{ color: {t[k]}; }}""" for k in ("meas", "with_eq", "c3", "c5", "c4", "c2")) + "\n"


def tracer(t, img):
    """The tracer's window (ui\\trace_window.py, by its objectNames and its own tr* properties): its title and the
    empty picture's heading (Fluent's subtitle sizes), the Automatic settings switch (the card's heading) and its
    Why these settings fold (flat inside that card), the tools as one group (trTool: only the group's two ends rounded),
    the zoom bar's buttons and a curve's dot and ✕ a little smaller than other buttons (trCompact: they're the shared
    quiet buttons, quiet=true; trIcon: a symbol without words, centred), the chosen curve's row (trRow="chosen": as a
    chosen list row, the accent's bar beside it, its words in a chosen row's text colour, which a contrast theme
    needs), the traced colour's frame, the zoom bar floating on the picture (as Windows 11's flyouts; its words in the
    text colour, as its symbols: a quiet button's are greyer). The picture's card itself is drawn by the window in the
    same colours (trace_window.Stage)."""
    return f"""
    QLabel#trTitle {{ font-family: "Segoe UI Variable Display"; font-size: 15pt; font-weight: 600; }}
    QLabel#trDropHead {{ font-family: "Segoe UI Variable Display"; font-size: 13.5pt; font-weight: 600; }}
    QCheckBox#trAutoOn {{ font-weight: 600; }}
    QFrame#trWhy {{ background: transparent; border: none; padding: 0px; }}
    QFrame#trWhy QToolButton[fold="true"] {{ font-size: {FONT}pt; padding: 4px 0px; }}
    QPushButton[trTool="first"] {{ border-top-right-radius: 0px; border-bottom-right-radius: 0px; }}
    QPushButton[trTool="mid"] {{ border-radius: 0px; border-left-width: 0px; }}
    QPushButton[trTool="last"] {{ border-top-left-radius: 0px; border-bottom-left-radius: 0px;
        border-left-width: 0px; }}
    QPushButton[trCompact="true"] {{ padding: 4px 8px; }}
    QPushButton[trIcon="true"] {{ padding-left: 10px; padding-right: 4px; }}
    QFrame#trZoom QPushButton:enabled {{ color: {t['ink']}; }}
    QFrame[trRow="chosen"] {{ background-color: {t['subtle_sel']}; border-radius: 4px;
        background-image: url({img['pill_v']}); background-position: center left; background-repeat: no-repeat; }}
    QFrame[trRow="chosen"] QLabel, QFrame[trRow="chosen"] QPushButton {{ color: {t['sel_ink']}; }}
    QLabel#trSwatch {{ border: 1px solid {t['stroke']}; border-radius: 4px; }}
    QFrame#trZoom {{ background: {t['menu']}; border: 1px solid {t['stroke']}; border-radius: 8px; }}
"""


def guide_and_help(t, img):
    """The Guide's layer and card, and the Help window. The Guide (ui\\tour.py): its card (#tourCard: the step list's
    button, the “Demo” tag as the settings' tags, the step's title, link-like buttons with link=true), and what a demo
    shows inside it: a drop-down's list or a menu (#tourMock, as the app's lists), a message (#tourNote), a key
    (#tourKey), a window or a question with its title bar (#tourWin), the step list (#tourSteps, as a menu), the graph
    kept in sight (#tourPin). Help (ui\\help_window.py): its contents (#helpContents) and its page (#helpPage) as cards."""
    return f"""
    QFrame#tourCard {{ padding: 0px; }}
    QFrame#tourCard QToolButton#tourCount {{ background: transparent; border: none; border-radius: 4px; padding: 3px 6px;
        color: {t['ink2']}; }}
    QFrame#tourCard QToolButton#tourCount:hover {{ background: {t['subtle_hover']}; color: {t['ink']}; }}
    QFrame#tourCard QToolButton#tourCount:pressed {{ background: {t['subtle_press']}; }}
    QFrame#tourCard QLabel#tourBadge {{ background: {t['accent_soft']}; color: {t['accent_text']};
        border: 1px solid {t['accent_soft_line']}; border-radius: 10px; padding: 1px 8px; font-size: {FONT - 1.5}pt; }}
    QFrame#tourCard QLabel#tourTitle {{ font-size: {FONT + 1.5}pt; font-weight: 600; }}
    QFrame#tourCard QPushButton[link="true"] {{ background: transparent; border: none; border-radius: 4px;
        color: {t['accent_text']}; padding: {PAD[0]}px 8px; }}
    QFrame#tourCard QPushButton[link="true"]:hover {{ background: {t['subtle_hover']}; }}
    QFrame#tourCard QPushButton[link="true"]:pressed {{ background: {t['subtle_press']}; }}
    QFrame#tourMock {{ background: {t['menu']}; border: 1px solid {t['stroke']}; border-radius: 8px; }}
    QFrame#tourMock QLabel {{ padding: 6px 10px; border-radius: 4px; background: transparent; color: {t['ink']}; }}
    QFrame#tourMock QLabel[cur="true"] {{ font-weight: 600; }}
    QFrame#tourMock QLabel[hover="true"] {{ background: {t['sel']}; color: {t['sel_ink']}; }}
    QFrame#tourMock QLabel[off="true"] {{ color: {t['muted']}; }}
    QFrame#tourMock QFrame#tourSep {{ background: {t['stroke']}; border: none; max-height: 1px; min-height: 1px; }}
    QLabel#tourNote {{ background: {t['card']}; color: {t['ink']}; border: 1px solid {t['accent']}; border-radius: 8px;
        padding: 7px 10px; }}
    QLabel#tourKey {{ background: {t['field']}; color: {t['ink']}; border: 1px solid {t['strong']};
        border-bottom-width: 3px; border-radius: 4px; padding: 3px 10px; font-weight: 600; }}
    QFrame#tourWin {{ background: {t['bg']}; border: 1px solid {t['stroke']}; border-radius: 8px; }}
    QFrame#tourWin QFrame#tourWinBar {{ background: transparent; border: none; }}
    QFrame#tourWin QLabel#tourWinTitle {{ background: transparent; font-size: {FONT - 1.5}pt; }}
    QFrame#tourWin QLabel#tourWinClose {{ background: transparent; }}
    QFrame#tourSteps {{ background: {t['menu']}; border: 1px solid {t['stroke']}; border-radius: 8px; }}
    QFrame#tourSteps QListWidget {{ background: transparent; border: none; }}
    QFrame#tourSteps QListWidget::item {{ padding: 5px 8px; }}
    QLabel#tourPin {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: 8px; }}
    QListWidget#helpContents::item {{ padding: 6px 8px; }}
    QTextBrowser#helpPage {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: 8px; }}
"""


PARTS = [base_and_tooltips, cards_and_group_boxes, text_roles, buttons, top_bar, inputs, lists_and_tables,
         progress_and_sliders, scroll_areas_and_menus, settings_boxes, check_boxes,
         window_screens, eq_screen, eq_windows, find_windows, listen, tracer, guide_and_help]


def sheet(t, img):
    """The whole stylesheet: every part in order, as one text."""
    return "".join(part(t, img) for part in PARTS)
