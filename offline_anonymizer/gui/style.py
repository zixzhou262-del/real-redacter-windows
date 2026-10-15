from __future__ import annotations

from offline_anonymizer.app_environment import resource_path


def get_stylesheet(theme: str = "dark") -> str:
    stylesheet = LIGHT_STYLESHEET if theme == "light" else DARK_STYLESHEET
    # Qt style-sheet URLs need URI form on Windows. A raw ``C:\\...`` path
    # can make the checked indicator invisible even though the checkbox state
    # changed correctly.
    checkmark_path = resource_path("checkmark.svg").resolve()
    try:
        checkmark_url = checkmark_path.as_uri()
    except ValueError:
        checkmark_url = checkmark_path.as_posix()
    return stylesheet.replace("__CHECKMARK_ICON__", checkmark_url)


DARK_STYLESHEET = """
QMainWindow {
    background: #07090b;
    color: #eef2f4;
}

QWidget#appRoot, QWidget#mainContainer, QWidget#mainScrollViewport,
QWidget#redactPage, QWidget#restorePage, QWidget#helpPage, QWidget#settingsPage,
QStackedWidget#pageStack, QStackedWidget#actionStack {
    background: #07090b;
}

QScrollArea#mainScroll, QScrollArea#mainScroll > QWidget, QScrollArea#mainScroll > QWidget > QWidget {
    background: #07090b;
}

QWidget {
    font-family: "Helvetica Neue", Arial;
    font-size: 13px;
    color: #eef2f4;
}

QFrame#sidebar {
    background: #090c0f;
    border-right: 1px solid #181e23;
}

QFrame#card, QFrame#actionBar {
    background: #0d1115;
    border: 1px solid #1c252c;
    border-radius: 8px;
}

QFrame#previewPane {
    background: #090d11;
    border: 1px solid #1c252c;
    border-radius: 8px;
}

QLabel#appTitle {
    font-size: 22px;
    font-weight: 700;
    color: #ffffff;
}

QLabel#sideTitle {
    font-size: 17px;
    font-weight: 800;
    color: #ffffff;
}

QLabel#appSubtitle {
    color: #7d8a93;
    font-size: 12px;
}

QLabel#sectionTitle {
    font-size: 14px;
    font-weight: 700;
    color: #ffffff;
}

QLabel#mutedText {
    color: #87939b;
}

QLabel#tokenPill {
    background: #111111;
    border-left: 3px solid #ef3f3a;
    border-radius: 4px;
    color: #f6f1e8;
    padding: 4px 8px;
}

QPushButton {
    background: #151b20;
    border: 1px solid #29333b;
    border-radius: 6px;
    color: #f4f7f8;
    padding: 8px 12px;
}

QPushButton:hover {
    background: #1d252c;
    border-color: #414c55;
}

QPushButton:disabled {
    color: #505b63;
    background: #0f1418;
    border-color: #1b2329;
}

QPushButton#primaryButton {
    background: #ef3f3a;
    border: 1px solid #ff5a54;
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
    padding: 11px 18px;
}

QPushButton#primaryButton:hover {
    background: #ff504b;
}

QPushButton#navButton {
    text-align: left;
    border: 0;
    border-radius: 6px;
    background: transparent;
    padding: 12px 14px;
    color: #b8c3ca;
    font-size: 15px;
}

QPushButton#navButton:hover {
    background: #151b20;
    color: #ffffff;
}

QPushButton#navButtonActive {
    text-align: left;
    border: 0;
    border-left: 4px solid #ef3f3a;
    border-radius: 6px;
    background: #171d22;
    padding: 12px 14px;
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
}

QCheckBox {
    spacing: 8px;
    color: #dce4e8;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #3a444c;
    background: #080b0e;
}

QCheckBox::indicator:checked {
    background: #25c7c7;
    border: 1px solid #25c7c7;
    image: url("__CHECKMARK_ICON__");
}

QPlainTextEdit, QComboBox {
    background: #080b0e;
    border: 1px solid #222c33;
    border-radius: 6px;
    color: #eef2f4;
    padding: 6px;
    selection-background-color: #ef3f3a;
    selection-color: #ffffff;
}

QPlainTextEdit#customKeywordsEdit {
    background: #080b0e;
    color: #eef2f4;
}

QTableWidget {
    background: #080b0e;
    alternate-background-color: #0c1115;
    gridline-color: #1c252c;
    border: 1px solid #1c252c;
    border-radius: 6px;
    color: #dce4e8;
}

QHeaderView::section {
    background: #11171c;
    color: #b6c0c7;
    border: 0;
    border-right: 1px solid #32404a;
    padding: 7px;
}

QScrollArea {
    border: 0;
    background: #07090b;
}

QScrollBar:vertical {
    background: #080b0e;
    width: 10px;
}

QScrollBar::handle:vertical {
    background: #29333b;
    border-radius: 5px;
}

QStatusBar {
    background: #07090b;
    color: #7d8a93;
}
"""


LIGHT_STYLESHEET = """
QMainWindow {
    background: #f4f5f7;
    color: #1f2328;
}

QWidget#appRoot, QWidget#mainContainer, QWidget#mainScrollViewport,
QWidget#redactPage, QWidget#restorePage, QWidget#helpPage, QWidget#settingsPage,
QStackedWidget#pageStack, QStackedWidget#actionStack {
    background: #f4f5f7;
}

QScrollArea#mainScroll, QScrollArea#mainScroll > QWidget, QScrollArea#mainScroll > QWidget > QWidget {
    background: #f4f5f7;
}

QWidget {
    font-family: "Helvetica Neue", Arial;
    font-size: 13px;
    color: #1f2328;
}

QFrame#sidebar {
    background: #ffffff;
    border-right: 1px solid #d8dde3;
}

QFrame#card, QFrame#actionBar, QFrame#previewPane {
    background: #ffffff;
    border: 1px solid #d8dde3;
    border-radius: 8px;
}

QLabel#appTitle {
    font-size: 22px;
    font-weight: 700;
    color: #101418;
}

QLabel#sideTitle {
    font-size: 17px;
    font-weight: 800;
    color: #101418;
}

QLabel#appSubtitle, QLabel#mutedText {
    color: #68727d;
    font-size: 12px;
}

QLabel#sectionTitle {
    font-size: 14px;
    font-weight: 700;
    color: #101418;
}

QLabel#tokenPill {
    background: #101418;
    border-left: 3px solid #ef3f3a;
    border-radius: 4px;
    color: #ffffff;
    padding: 4px 8px;
}

QPushButton {
    background: #f1f3f5;
    border: 1px solid #cfd6dd;
    border-radius: 6px;
    color: #1f2328;
    padding: 8px 12px;
}

QPushButton:hover {
    background: #e8ecef;
    border-color: #b8c0c8;
}

QPushButton:disabled {
    color: #9aa3ab;
    background: #f6f7f8;
    border-color: #e2e6ea;
}

QPushButton#primaryButton {
    background: #ef3f3a;
    border: 1px solid #d93430;
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
    padding: 11px 18px;
}

QPushButton#primaryButton:hover {
    background: #d93430;
}

QPushButton#navButton {
    text-align: left;
    border: 0;
    border-radius: 6px;
    background: transparent;
    padding: 12px 14px;
    color: #4c5963;
    font-size: 15px;
}

QPushButton#navButton:hover {
    background: #f1f3f5;
    color: #101418;
}

QPushButton#navButtonActive {
    text-align: left;
    border: 0;
    border-left: 4px solid #ef3f3a;
    border-radius: 6px;
    background: #f1f3f5;
    padding: 12px 14px;
    color: #101418;
    font-size: 15px;
    font-weight: 700;
}

QCheckBox {
    spacing: 8px;
    color: #1f2328;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #aeb8c2;
    background: #ffffff;
}

QCheckBox::indicator:checked {
    background: #25aeb0;
    border: 1px solid #25aeb0;
    image: url("__CHECKMARK_ICON__");
}

QPlainTextEdit, QComboBox {
    background: #ffffff;
    border: 1px solid #cfd6dd;
    border-radius: 6px;
    color: #1f2328;
    padding: 6px;
    selection-background-color: #ef3f3a;
    selection-color: #ffffff;
}

QPlainTextEdit#customKeywordsEdit {
    background: #ffffff;
    color: #1f2328;
}

QTableWidget {
    background: #ffffff;
    alternate-background-color: #f6f7f8;
    gridline-color: #d8dde3;
    border: 1px solid #d8dde3;
    border-radius: 6px;
    color: #1f2328;
}

QHeaderView::section {
    background: #f1f3f5;
    color: #4c5963;
    border: 0;
    border-right: 1px solid #d8dde3;
    padding: 7px;
}

QScrollArea {
    border: 0;
    background: #f4f5f7;
}

QScrollBar:vertical {
    background: #eef1f3;
    width: 10px;
}

QScrollBar::handle:vertical {
    background: #c2cad2;
    border-radius: 5px;
}

QStatusBar {
    background: #f4f5f7;
    color: #68727d;
    border-top: 1px solid #d8dde3;
}

QStatusBar {
    background: #ffffff;
    color: #4c5963;
}

QStatusBar::item {
    border: 0;
}
"""


APP_STYLESHEET = DARK_STYLESHEET
