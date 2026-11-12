"""A modern PyQt6 interface for the Gemini desktop agent.

The window launches ``main.py`` as a child process, streams its logs in real
time, and turns every tool call into a short lesson that explains what the
agent is doing, why it is doing it, and how the mechanism works.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
import time
from typing import Any

from PyQt6.QtCore import (
    QEasingCurve,
    QProcess,
    QProcessEnvironment,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    QUrl,
    pyqtProperty,
)
from PyQt6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QKeySequence,
    QPainter,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from action_guide import (
    Guide,
    describe_action,
    failure,
    overview,
    paused,
    resumed,
    thinking,
)
from config import (
    DEFAULT_MODEL,
    KNOWN_MODELS,
    PROJECT_ROOT,
    config_path,
    load_config,
    resolve_api_key,
    save_config,
)

APP_TITLE = "Gemini PC Use"
ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
LOG_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})"
    r" - (?P<level>[A-Z]+) - (?P<message>.*)$"
)
ACTION_RE = re.compile(r"^\[ACTION\]\s+([A-Za-z_][\w]*)\s*(\{.*\})\s*$")
STEP_RE = re.compile(r"^\[STEP\]\s+(\d+)\s*$")
DONE_RE = re.compile(r"^\[DONE\]\s*(.*)$")
PAUSED_RE = re.compile(r"^\[PAUSED\]\s*(.*)$")
RESUMED_RE = re.compile(r"^\[RESUMED\]\s*(.*)$")

EXAMPLES = [
    ("Open Notepad", "Open Notepad and type a short welcome message."),
    (
        "Create a folder",
        "Create a new folder named Reports on the Desktop.",
    ),
    (
        "Browse the web",
        "Open a browser and search for the current weather in Warsaw.",
    ),
    (
        "Find a file",
        "Open File Explorer and show the Downloads folder.",
    ),
]

BADGE_TEXT = {
    "click_at": "CLK",
    "double_click_at": "DBL",
    "type_text_at": "TYP",
    "type_text": "TYP",
    "press_key": "KEY",
    "hotkey": "HK",
    "move_mouse": "MOV",
    "done": "OK",
}

TONES = {
    "info": ("#6d6cff", "#22d3ee"),
    "success": ("#10b981", "#34d399"),
    "warn": ("#f59e0b", "#fbbf24"),
    "error": ("#e11d48", "#fb7185"),
}

STYLESHEET = """
QWidget {
    color: #e8edf7;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QWidget#root {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #060a14, stop:0.55 #0a1020, stop:1 #0b1428);
}
QFrame#header {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #17224a, stop:0.55 #111a36, stop:1 #0d1730);
    border: 1px solid #26345c;
    border-radius: 18px;
}
QFrame#card {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #111a2d, stop:1 #0d1626);
    border: 1px solid #213052;
    border-radius: 16px;
}
QFrame#footer {
    background-color: transparent;
}
QLabel#appTitle {
    font-size: 20pt;
    font-weight: 700;
    color: #ffffff;
}
QLabel#appSubtitle {
    font-size: 9pt;
    color: #93a5c8;
}
QLabel#logo {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #6d6cff, stop:1 #22d3ee);
    color: #ffffff;
    border-radius: 14px;
    font-size: 16pt;
    font-weight: 800;
}
QLabel#statusPill {
    background-color: #1a2644;
    color: #9fb3d9;
    border: 1px solid #2b3a60;
    border-radius: 13px;
    padding: 6px 14px;
    font-size: 9pt;
    font-weight: 600;
}
QLabel#statusPill[state="running"] {
    background-color: rgba(52, 211, 153, 0.12);
    color: #34d399;
    border: 1px solid rgba(52, 211, 153, 0.40);
}
QLabel#statusPill[state="success"] {
    background-color: rgba(34, 211, 238, 0.12);
    color: #22d3ee;
    border: 1px solid rgba(34, 211, 238, 0.40);
}
QLabel#statusPill[state="error"] {
    background-color: rgba(251, 113, 133, 0.12);
    color: #fb7185;
    border: 1px solid rgba(251, 113, 133, 0.40);
}
QLabel#statusPill[state="stopping"] {
    background-color: rgba(251, 191, 36, 0.12);
    color: #fbbf24;
    border: 1px solid rgba(251, 191, 36, 0.40);
}
QLabel#statusPill[state="paused"] {
    background-color: rgba(251, 191, 36, 0.12);
    color: #fbbf24;
    border: 1px solid rgba(251, 191, 36, 0.40);
}
QLabel#headerStat {
    color: #7f92b6;
    font-size: 9pt;
}
QLabel#headerStatValue {
    color: #d7e2f7;
    font-size: 9pt;
    font-weight: 600;
}
QLabel#cardTitle {
    color: #ffffff;
    font-size: 12pt;
    font-weight: 700;
}
QLabel#cardHint {
    color: #7f92b6;
    font-size: 8.5pt;
}
QLabel#sectionLabel {
    color: #7185aa;
    font-size: 7.5pt;
    font-weight: 700;
}
QLabel#sectionBody {
    color: #d2ddf0;
    font-size: 9pt;
}
QLabel#guideTitle {
    color: #ffffff;
    font-size: 14pt;
    font-weight: 700;
}
QLabel#guideMeta {
    color: #7f92b6;
    font-size: 8pt;
}
QLabel#tipBody {
    color: #9fb3d9;
    font-size: 8.5pt;
}
QLabel#storageHint {
    color: #66789b;
    font-size: 8pt;
}
QLabel#commandPreview {
    color: #8ea2c8;
    font-family: "Consolas";
    font-size: 8.5pt;
}
QLabel#footerLabel {
    color: #5f7195;
    font-size: 8pt;
}
QPlainTextEdit#promptEdit {
    background-color: #0b1322;
    border: 1px solid #243356;
    border-radius: 12px;
    padding: 10px;
    color: #eaf0fb;
    selection-background-color: #3b3f9e;
    font-size: 10pt;
}
QPlainTextEdit#promptEdit:focus {
    border: 1px solid #6d6cff;
}
QLineEdit#keyEdit {
    background-color: #0b1322;
    border: 1px solid #243356;
    border-radius: 10px;
    padding: 9px 11px;
    color: #eaf0fb;
    selection-background-color: #3b3f9e;
}
QLineEdit#keyEdit:focus {
    border: 1px solid #6d6cff;
}
QComboBox#modelCombo {
    background-color: #0b1322;
    border: 1px solid #243356;
    border-radius: 10px;
    padding: 8px 11px;
    color: #eaf0fb;
}
QComboBox#modelCombo:focus {
    border: 1px solid #6d6cff;
}
QComboBox#modelCombo::drop-down {
    border: 0;
    width: 26px;
}
QComboBox#modelCombo::down-arrow {
    width: 0;
    height: 0;
}
QComboBox QAbstractItemView {
    background-color: #101829;
    border: 1px solid #2b3a60;
    border-radius: 8px;
    color: #e8edf7;
    selection-background-color: #2a2f6b;
    outline: 0;
    padding: 4px;
}
QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6d6cff, stop:1 #4f8cff);
    color: #ffffff;
    border: 0;
    border-radius: 11px;
    padding: 12px 18px;
    font-size: 10.5pt;
    font-weight: 700;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7d7cff, stop:1 #63a0ff);
}
QPushButton#primary:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5a59e6, stop:1 #3f7ae6);
}
QPushButton#primary:disabled {
    background-color: #1b2440;
    color: #5d6d90;
}
QPushButton#danger {
    background-color: #241726;
    color: #fb7185;
    border: 1px solid #5c2a3b;
    border-radius: 11px;
    padding: 12px 16px;
    font-size: 10pt;
    font-weight: 600;
}
QPushButton#danger:hover {
    background-color: #321b30;
    border: 1px solid #8a3a52;
}
QPushButton#danger:disabled {
    background-color: #141a29;
    color: #4d5a74;
    border: 1px solid #202b45;
}
QPushButton#ghost {
    background-color: #131d33;
    color: #9fb3d9;
    border: 1px solid #27365b;
    border-radius: 9px;
    padding: 7px 12px;
    font-size: 8.5pt;
    font-weight: 600;
}
QPushButton#ghost:hover {
    background-color: #1a2846;
    color: #d7e2f7;
    border: 1px solid #36497a;
}
QPushButton#pause {
    background-color: #1a2439;
    color: #fbbf24;
    border: 1px solid #4a3d24;
    border-radius: 11px;
    padding: 12px 16px;
    font-size: 10pt;
    font-weight: 600;
}
QPushButton#pause:hover {
    background-color: #24304a;
    border: 1px solid #6b5730;
}
QPushButton#pause:disabled {
    background-color: #141a29;
    color: #4d5a74;
    border: 1px solid #202b45;
}
QPushButton#chip {
    background-color: #111b30;
    color: #93a5c8;
    border: 1px solid #243356;
    border-radius: 14px;
    padding: 6px 12px;
    font-size: 8.5pt;
}
QPushButton#chip:hover {
    background-color: #1a2744;
    color: #e8edf7;
    border: 1px solid #3b4f80;
}
QPlainTextEdit#logView {
    background-color: #070c17;
    border: 1px solid #1c2947;
    border-radius: 12px;
    padding: 8px;
    color: #b9c8e2;
    font-family: "Consolas";
    font-size: 8.5pt;
    selection-background-color: #2a2f6b;
}
QProgressBar#activity {
    background-color: #0b1322;
    border: 0;
    border-radius: 2px;
    max-height: 4px;
    min-height: 4px;
}
QProgressBar#activity::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6d6cff, stop:1 #22d3ee);
    border-radius: 2px;
}
QScrollArea {
    background: transparent;
    border: 0;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #293858;
    min-height: 28px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #3a4d77;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
"""


def _add_shadow(widget: QWidget, blur: int = 34, y_offset: int = 10) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y_offset)
    effect.setColor(QColor(0, 0, 0, 110))
    widget.setGraphicsEffect(effect)


class Switch(QCheckBox):
    """A small animated toggle switch."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(48, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._offset = 3.0
        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(140)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, checked: bool) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._offset)
        self._animation.setEndValue(25.0 if checked else 3.0)
        self._animation.start()

    @pyqtProperty(float)
    def offset(self) -> float:  # noqa: D401 - property getter
        return self._offset

    @offset.setter
    def offset(self, value: float) -> None:
        self._offset = value
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#6d6cff") if self.isChecked() else QColor("#2a3654"))
        painter.drawRoundedRect(QRectF(0, 0, 48, 26), 13, 13)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(QRectF(self._offset, 3, 20, 20))


class Card(QFrame):
    """A rounded surface with a title row."""

    def __init__(
        self,
        title: str,
        hint: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        _add_shadow(self)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(18, 15, 18, 17)
        self.body.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        header.addWidget(title_label)
        header.addStretch(1)

        self.actions = QHBoxLayout()
        self.actions.setSpacing(6)
        header.addLayout(self.actions)

        self.body.addLayout(header)
        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("cardHint")
            hint_label.setWordWrap(True)
            self.body.addWidget(hint_label)


class GuidePanel(Card):
    """Explains the current action to the user."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("What is happening", parent=parent)
        header = QHBoxLayout()
        header.setSpacing(12)

        self.badge = QLabel("AI")
        self.badge.setFixedSize(46, 46)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.badge)

        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        self.title_label = QLabel("Ready when you are")
        self.title_label.setObjectName("guideTitle")
        self.title_label.setWordWrap(True)
        self.meta_label = QLabel("The agent's next move will be explained here")
        self.meta_label.setObjectName("guideMeta")
        self.meta_label.setWordWrap(True)
        title_column.addWidget(self.title_label)
        title_column.addWidget(self.meta_label)
        header.addLayout(title_column, 1)
        self.body.addLayout(header)

        self.what_widget, self.what_body = self._section("WHAT HAPPENED")
        self.why_widget, self.why_body = self._section("WHY IT MATTERS")
        self.how_widget, self.how_body = self._section("HOW IT WORKS")
        self.tip_widget, self.tip_body = self._section("TRY THIS")
        for widget in (
            self.what_widget,
            self.why_widget,
            self.how_widget,
            self.tip_widget,
        ):
            self.body.addWidget(widget)

        self.show_guide(overview())

    def _section(self, heading: str) -> tuple[QWidget, QLabel]:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        heading_label = QLabel(heading)
        heading_label.setObjectName("sectionLabel")
        body = QLabel()
        body.setObjectName("sectionBody")
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(heading_label)
        layout.addWidget(body)
        return wrapper, body

    def show_guide(
        self,
        guide: Guide,
        *,
        action: str | None = None,
        step: int | None = None,
    ) -> None:
        start, end = TONES.get(guide.tone, TONES["info"])
        self.badge.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            f"stop:0 {start}, stop:1 {end});"
            "color: #ffffff; border-radius: 14px; font-size: 8pt; "
            "font-weight: 800;"
        )
        self.badge.setText(BADGE_TEXT.get(action or "", "AI"))
        self.title_label.setText(guide.title)

        bits: list[str] = []
        if action:
            bits.append(action)
        if step:
            bits.append(f"Step {step}")
        bits.append(guide.tone.capitalize())
        self.meta_label.setText("  ·  ".join(bits))

        self.what_body.setText(guide.what)
        self.why_body.setText(guide.why)
        self.how_body.setText(guide.how)
        self.tip_body.setText(guide.tip)
        self.tip_widget.setVisible(bool(guide.tip))


class MainWindow(QMainWindow):
    def __init__(
        self,
        initial_prompt: str = "",
        initial_model: str | None = None,
        initial_instant_click: bool | None = None,
    ) -> None:
        super().__init__()
        self._config = load_config()
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._read_output)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_process_error)

        self._buffer = ""
        self._running = False
        self._paused = False
        self._user_stopped = False
        self._final_state = ""
        self._started_at = 0.0
        self._paused_at = 0.0
        self._paused_total = 0.0
        self._step = 0

        self._clock = QTimer(self)
        self._clock.setInterval(500)
        self._clock.timeout.connect(self._tick_clock)

        self.setWindowTitle(f"{APP_TITLE} — Desktop Agent")
        self.setMinimumSize(1080, 720)
        self.resize(1240, 800)
        self._build_ui()
        self._load_settings(initial_model, initial_instant_click)
        if initial_prompt:
            self.prompt_edit.setPlainText(initial_prompt)
        self._update_command_preview()
        self._set_status("idle", "Idle")
        self._center_on_screen()

        QShortcut(QKeySequence("Ctrl+Return"), self, self.start_task)
        QShortcut(QKeySequence("Ctrl+Enter"), self, self.start_task)
        QShortcut(QKeySequence("Esc"), self, self.stop_task)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        root.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 18, 18, 10)
        outer.setSpacing(12)

        outer.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self._build_left_column(), 0)
        body.addLayout(self._build_right_column(), 1)
        outer.addLayout(body, 1)

        outer.addWidget(self._build_footer())

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("header")
        _add_shadow(header, blur=40, y_offset=12)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 13, 18, 13)
        layout.setSpacing(14)

        logo = QLabel("G")
        logo.setObjectName("logo")
        logo.setFixedSize(48, 48)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(1)
        app_title = QLabel(APP_TITLE)
        app_title.setObjectName("appTitle")
        subtitle = QLabel("A vision agent that can see your screen and operate your desktop")
        subtitle.setObjectName("appSubtitle")
        subtitle.setWordWrap(True)
        titles.addWidget(app_title)
        titles.addWidget(subtitle)
        layout.addLayout(titles, 1)

        stats = QHBoxLayout()
        stats.setSpacing(18)
        stats.addLayout(self._stat("STEPS", "0", "step"))
        stats.addLayout(self._stat("ELAPSED", "0:00", "elapsed"))
        layout.addLayout(stats)

        self.status_pill = QLabel("●  Idle")
        self.status_pill.setObjectName("statusPill")
        self.status_pill.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.status_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_pill.setFixedHeight(32)
        layout.addWidget(self.status_pill)
        return header

    def _stat(self, caption: str, value: str, key: str) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(0)
        caption_label = QLabel(caption)
        caption_label.setObjectName("headerStat")
        value_label = QLabel(value)
        value_label.setObjectName("headerStatValue")
        layout.addWidget(caption_label)
        layout.addWidget(value_label)
        if key == "step":
            self.step_value = value_label
        elif key == "elapsed":
            self.elapsed_value = value_label
        return layout

    def _build_left_column(self) -> QWidget:
        container = QWidget()
        column = QVBoxLayout(container)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)

        task_card = Card(
            "Describe your task",
            "State the result you want; the agent handles the clicks.",
        )
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setObjectName("promptEdit")
        self.prompt_edit.setPlaceholderText(
            "Example: Open Notepad and type a short welcome message."
        )
        self.prompt_edit.setFixedHeight(105)
        self.prompt_edit.textChanged.connect(self._update_command_preview)
        task_card.body.addWidget(self.prompt_edit)

        examples_row = QHBoxLayout()
        examples_row.setSpacing(6)
        for label, prompt in EXAMPLES[:2]:
            button = QPushButton(label)
            button.setObjectName("chip")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, p=prompt: self.prompt_edit.setPlainText(p))
            examples_row.addWidget(button)
        examples_row.addStretch(1)
        task_card.body.addLayout(examples_row)

        more_row = QHBoxLayout()
        more_row.setSpacing(6)
        for label, prompt in EXAMPLES[2:]:
            button = QPushButton(label)
            button.setObjectName("chip")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, p=prompt: self.prompt_edit.setPlainText(p))
            more_row.addWidget(button)
        more_row.addStretch(1)
        task_card.body.addLayout(more_row)

        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(12)
        toggle_text = QVBoxLayout()
        toggle_text.setSpacing(1)
        toggle_title = QLabel("Instant click")
        toggle_title.setStyleSheet("color: #e8edf7; font-weight: 600;")
        toggle_hint = QLabel("Skip pointer travel and click the target instantly")
        toggle_hint.setObjectName("cardHint")
        toggle_hint.setWordWrap(True)
        toggle_text.addWidget(toggle_title)
        toggle_text.addWidget(toggle_hint)
        toggle_row.addLayout(toggle_text, 1)
        self.instant_switch = Switch()
        self.instant_switch.toggled.connect(self._update_command_preview)
        toggle_row.addWidget(self.instant_switch, 0, Qt.AlignmentFlag.AlignVCenter)
        task_card.body.addLayout(toggle_row)
        column.addWidget(task_card)

        settings_card = Card("Model and key")
        settings_card.body.addWidget(self._field_label("Gemini model"))
        self.model_combo = QComboBox()
        self.model_combo.setObjectName("modelCombo")
        self.model_combo.setEditable(True)
        self.model_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.model_combo.addItems(KNOWN_MODELS)
        self.model_combo.currentTextChanged.connect(self._update_command_preview)
        settings_card.body.addWidget(self.model_combo)

        settings_card.body.addWidget(self._field_label("Gemini API key"))
        key_row = QHBoxLayout()
        key_row.setSpacing(6)
        self.key_edit = QLineEdit()
        self.key_edit.setObjectName("keyEdit")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("Paste your API key")
        self.key_edit.textChanged.connect(self._update_command_preview)
        key_row.addWidget(self.key_edit, 1)
        self.reveal_button = QPushButton("Show")
        self.reveal_button.setObjectName("ghost")
        self.reveal_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reveal_button.clicked.connect(self._toggle_key_visibility)
        key_row.addWidget(self.reveal_button)
        settings_card.body.addLayout(key_row)

        self.storage_hint = QLabel("")
        self.storage_hint.setObjectName("storageHint")
        self.storage_hint.setWordWrap(True)

        self.remember_check = QCheckBox("Remember this key")
        self.remember_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remember_check.setChecked(True)
        settings_card.body.addWidget(self.remember_check)

        settings_card.body.addWidget(self.storage_hint)
        column.addWidget(settings_card)
        column.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        wrapper = QWidget()
        wrapper.setFixedWidth(418)
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(10)
        wrapper_layout.addWidget(scroll, 1)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.start_button = QPushButton("▶   Start task")
        self.start_button.setObjectName("primary")
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.setMinimumHeight(44)
        self.start_button.clicked.connect(self.start_task)
        actions.addWidget(self.start_button, 1)

        self.pause_button = QPushButton("❚❚   Pause")
        self.pause_button.setObjectName("pause")
        self.pause_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_button.setMinimumHeight(44)
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.toggle_pause)
        actions.addWidget(self.pause_button)

        self.stop_button = QPushButton("■   Stop")
        self.stop_button.setObjectName("danger")
        self.stop_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_button.setMinimumHeight(44)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_task)
        actions.addWidget(self.stop_button)
        wrapper_layout.addLayout(actions)

        pause_hint = QLabel(
            "Global hotkey: Alt+F10 pauses or resumes this run anywhere in Windows."
        )
        pause_hint.setObjectName("cardHint")
        pause_hint.setWordWrap(True)
        wrapper_layout.addWidget(pause_hint)
        return wrapper

    def _build_right_column(self) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setSpacing(12)

        self.guide_panel = GuidePanel()
        self.guide_panel.setMinimumHeight(350)
        column.addWidget(self.guide_panel, 0)

        log_card = Card("Live log", "Streamed directly from the agent process.")
        self.copy_button = QPushButton("Copy")
        self.copy_button.setObjectName("ghost")
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_button.clicked.connect(self._copy_log)
        self.clear_button = QPushButton("Clear")
        self.clear_button.setObjectName("ghost")
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.clicked.connect(self._clear_log)
        log_card.actions.addWidget(self.copy_button)
        log_card.actions.addWidget(self.clear_button)

        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(6000)
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        log_card.body.addWidget(self.log_view, 1)

        self.activity = QProgressBar()
        self.activity.setObjectName("activity")
        self.activity.setRange(0, 0)
        self.activity.setTextVisible(False)
        self.activity.setVisible(False)
        log_card.body.addWidget(self.activity)

        column.addWidget(log_card, 1)
        return column

    def _build_footer(self) -> QWidget:
        footer = QFrame()
        footer.setObjectName("footer")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(10)

        command_column = QVBoxLayout()
        command_column.setSpacing(1)
        command_caption = QLabel("COMMAND")
        command_caption.setObjectName("footerLabel")
        self.command_preview = QLabel("")
        self.command_preview.setObjectName("commandPreview")
        self.command_preview.setWordWrap(True)
        self.command_preview.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        command_column.addWidget(command_caption)
        command_column.addWidget(self.command_preview)
        layout.addLayout(command_column, 1)

        self.config_button = QPushButton("Config folder")
        self.config_button.setObjectName("ghost")
        self.config_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.config_button.clicked.connect(self._open_config_folder)
        layout.addWidget(self.config_button)
        return footer

    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("cardHint")
        label.setStyleSheet("color: #8ea2c8; font-size: 8.5pt; font-weight: 600;")
        return label

    def _center_on_screen(self) -> None:
        screen = self.screen()
        if screen is None:
            return
        geometry = self.frameGeometry()
        geometry.moveCenter(screen.availableGeometry().center())
        self.move(geometry.topLeft())

    # ------------------------------------------------------------- settings
    def _load_settings(
        self,
        initial_model: str | None,
        initial_instant_click: bool | None,
    ) -> None:
        model = initial_model or self._config.get("model", DEFAULT_MODEL)
        if model not in [self.model_combo.itemText(i) for i in range(self.model_combo.count())]:
            self.model_combo.addItem(model)
        self.model_combo.setCurrentText(model)

        key = resolve_api_key(self._config)
        self.key_edit.setText(key)
        self.remember_check.setChecked(bool(self._config.get("remember_api_key", True)))

        instant = (
            bool(initial_instant_click)
            if initial_instant_click is not None
            else bool(self._config.get("instant_click", False))
        )
        self.instant_switch.setChecked(instant)
        self.storage_hint.setText(
            "Saved only on this computer. Use “Config folder” to open it."
        )
        self.storage_hint.setToolTip(str(config_path()))

    def _collect_settings(self) -> dict[str, Any]:
        config = dict(self._config)
        config["api_key"] = self.key_edit.text().strip()
        config["model"] = self.model_combo.currentText().strip() or DEFAULT_MODEL
        config["instant_click"] = self.instant_switch.isChecked()
        config["remember_api_key"] = self.remember_check.isChecked()
        return config

    def _persist_settings(self) -> None:
        config = self._collect_settings()
        try:
            path = save_config(config)
            self._config = load_config()
            self.storage_hint.setText(
                "Saved only on this computer. Use “Config folder” to open it."
            )
            self.storage_hint.setToolTip(str(path))
        except OSError as error:
            self._append_plain(
                f"Could not save settings: {error}",
                "#fb7185",
            )

    def _toggle_key_visibility(self) -> None:
        if self.key_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.reveal_button.setText("Hide")
        else:
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.reveal_button.setText("Show")

    def _open_config_folder(self) -> None:
        path = config_path().parent
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    # -------------------------------------------------------------- running
    def _build_command(self, prompt: str) -> tuple[str, list[str], str]:
        if shutil.which("py"):
            program = "py"
            launcher = ["-3.13"]
        else:
            program = sys.executable
            launcher = []

        arguments = launcher + ["main.py", prompt]
        model = self.model_combo.currentText().strip() or DEFAULT_MODEL
        arguments += ["--model", model]
        arguments.append("--instant-click" if self.instant_switch.isChecked() else "--no-instant-click")
        preview = subprocess.list2cmdline([program, *arguments])
        return program, arguments, preview

    def _update_command_preview(self) -> None:
        prompt = self.prompt_edit.toPlainText().strip() or "some action to do"
        _, _, preview = self._build_command(prompt)
        self.command_preview.setText(preview)
        if hasattr(self, "start_button"):
            self.start_button.setEnabled(not self._running)

    def start_task(self) -> None:
        if self._running:
            return
        prompt = self.prompt_edit.toPlainText().strip()
        key = self.key_edit.text().strip()
        if not prompt:
            self.guide_panel.show_guide(
                Guide(
                    title="Describe a goal first",
                    what="The task field is empty.",
                    why="The agent needs a concrete result to aim for; without one it cannot decide what to click.",
                    how="Type a short instruction such as “Open Notepad and write a haiku”, or pick one of the examples.",
                    tip="Start small. A single clear outcome is easier to verify than a long list.",
                    tone="warn",
                )
            )
            self.prompt_edit.setFocus()
            return
        if not key:
            self.guide_panel.show_guide(
                Guide(
                    title="Add your Gemini API key",
                    what="No API key was found in the field, the environment, or the saved configuration.",
                    why="Every decision is made by Gemini, so the agent cannot run without an authenticated request.",
                    how="Create a key in Google AI Studio, paste it above, and press Start. It is stored only on this computer.",
                    tip="You can also set GEMINI_API_KEY in your environment or in a .env file.",
                    tone="error",
                )
            )
            self.key_edit.setFocus()
            return

        self._persist_settings()
        program, arguments, preview = self._build_command(prompt)

        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("GEMINI_API_KEY", key)
        environment.insert("PYTHONUNBUFFERED", "1")
        environment.insert("PYTHONIOENCODING", "utf-8")
        environment.insert("GEMINI_PC_USE_STDIN_CONTROL", "1")
        self._process.setProcessEnvironment(environment)
        self._process.setWorkingDirectory(str(PROJECT_ROOT))

        self.log_view.clear()
        self._buffer = ""
        self._paused = False
        self.pause_button.setText("❚❚   Pause")
        self._user_stopped = False
        self._final_state = ""
        self._step = 0
        self.step_value.setText("0")
        self._started_at = time.monotonic()
        self._paused_at = 0.0
        self._paused_total = 0.0
        self.elapsed_value.setText("0:00")
        self._clock.start()

        self._append_plain(f"$ {preview}", "#7dd3fc")
        self._append_plain("Starting the agent process…", "#93a5c8")
        self.guide_panel.show_guide(thinking(1))
        self._set_running(True)
        self._set_status("running", "Running")

        self._process.start(program, arguments)

    def toggle_pause(self) -> None:
        """Ask the child process to pause or resume at its next safe point."""
        if not self._running:
            return
        if self._process.state() == QProcess.ProcessState.NotRunning:
            return
        if self._process.write(b"toggle\n") < 0:
            self._append_plain(
                "Could not send the pause command to the agent process.",
                "#fb7185",
            )

    def stop_task(self) -> None:
        if not self._running:
            return
        self._user_stopped = True
        self._set_status("stopping", "Stopping")
        self._append_plain("Stopping the agent…", "#fbbf24")
        self._kill_process_tree()

    def _kill_process_tree(self) -> None:
        """Stop the agent, including child processes spawned by the py launcher."""
        if self._process.state() == QProcess.ProcessState.NotRunning:
            return
        if sys.platform == "win32":
            pid = int(self._process.processId())
            if pid:
                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        capture_output=True,
                        check=False,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                except OSError:
                    pass
        self._process.kill()

    def _set_running(self, running: bool) -> None:
        self._running = running
        for widget in (
            self.prompt_edit,
            self.key_edit,
            self.model_combo,
            self.instant_switch,
            self.remember_check,
            self.reveal_button,
        ):
            widget.setEnabled(not running)
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.pause_button.setEnabled(running)
        self.activity.setVisible(running)
        self._update_command_preview()

    def _set_status(self, state: str, text: str) -> None:
        self.status_pill.setText(f"●  {text}")
        self.status_pill.setProperty("state", state)
        style = self.status_pill.style()
        style.unpolish(self.status_pill)
        style.polish(self.status_pill)
        self.status_pill.update()

    def _tick_clock(self) -> None:
        if not self._started_at:
            return
        now = time.monotonic()
        paused = self._paused_total
        if self._paused_at:
            paused += now - self._paused_at
        elapsed = max(0, int(now - self._started_at - paused))
        self.elapsed_value.setText(f"{elapsed // 60}:{elapsed % 60:02d}")

    # ----------------------------------------------------------------- logs
    def _read_output(self) -> None:
        data = bytes(self._process.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        self._buffer += data.replace("\r\n", "\n").replace("\r", "\n")
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._process_line(line)

    def _process_line(self, raw_line: str) -> None:
        line = ANSI_RE.sub("", raw_line).rstrip()
        if not line:
            return

        match = STEP_RE.match(self._message_of(line))
        if match:
            self._step = int(match.group(1))
            self.step_value.setText(str(self._step))
            self.guide_panel.show_guide(thinking(self._step), step=self._step)

        action_match = ACTION_RE.match(self._message_of(line))
        if action_match:
            name = action_match.group(1)
            try:
                args = json.loads(action_match.group(2))
            except ValueError:
                args = {}
            if not isinstance(args, dict):
                args = {}
            guide = describe_action(
                name, args, instant_click=self.instant_switch.isChecked()
            )
            self.guide_panel.show_guide(
                guide, action=name, step=self._step or None
            )

        done_match = DONE_RE.match(self._message_of(line))
        if done_match:
            message = done_match.group(1).strip()
            if "complete" in message.lower():
                self._final_state = "success"
                self._set_status("success", "Complete")
            elif "cancel" in message.lower():
                self._final_state = "cancelled"
                self.guide_panel.show_guide(
                    Guide(
                        title="Run cancelled",
                        what="The agent process was stopped before it reported success.",
                        why="Stopping is always safe. The agent only sends input; it does not delete files on its own.",
                        how="The child process was terminated and its keyboard and mouse control was released.",
                        tip="Start again with a narrower task if you are unsure what went wrong.",
                        tone="warn",
                    )
                )
            elif "step limit" in message.lower():
                self._final_state = "limit"
                self.guide_panel.show_guide(
                    Guide(
                        title="Step limit reached",
                        what=f"The agent used all {self._step} allowed steps without finishing.",
                        why="The limit prevents a confused model from running forever.",
                        how="Each screenshot plus model answer counts as one step. You can raise the limit in the configuration file.",
                        tip="Try a more specific goal, or split the work into smaller tasks.",
                        tone="warn",
                    )
                )

        if PAUSED_RE.match(self._message_of(line)):
            if not self._paused:
                self._paused_at = time.monotonic()
            self._paused = True
            self.pause_button.setText("▶   Resume")
            self._set_status("paused", "Paused")
            self.guide_panel.show_guide(paused(), step=self._step or None)
        elif RESUMED_RE.match(self._message_of(line)):
            if self._paused_at:
                self._paused_total += time.monotonic() - self._paused_at
                self._paused_at = 0.0
            self._paused = False
            self.pause_button.setText("❚❚   Pause")
            self._set_status("running", "Running")
            self.guide_panel.show_guide(resumed(self._step), step=self._step or None)

        self._append_log_line(line)

    @staticmethod
    def _message_of(line: str) -> str:
        match = LOG_RE.match(line)
        return match.group("message") if match else line

    def _append_log_line(self, line: str) -> None:
        match = LOG_RE.match(line)
        if not match:
            self._append_plain(line, "#aab8d4")
            return

        timestamp = match.group("timestamp")
        level = match.group("level")
        message = match.group("message")
        colors = {
            "INFO": "#9fc0ff",
            "WARNING": "#fbbf24",
            "ERROR": "#fb7185",
            "CRITICAL": "#fb7185",
            "DEBUG": "#6b7a99",
        }
        message_colors = {
            "INFO": "#c6d4ec",
            "WARNING": "#f7d38a",
            "ERROR": "#ffb3c0",
            "CRITICAL": "#ffb3c0",
            "DEBUG": "#7b89a8",
        }
        color = colors.get(level, "#9fc0ff")
        message_color = message_colors.get(level, "#c6d4ec")
        if message.startswith("[ACTION]"):
            message_color = "#7dd3fc"
        elif message.startswith("[STEP]"):
            message_color = "#a78bfa"
        elif message.startswith("[DONE]"):
            message_color = "#34d399"
        elif message.startswith("[PAUSED]"):
            message_color = "#fbbf24"
        elif message.startswith("[RESUMED]"):
            message_color = "#34d399"

        self.log_view.appendHtml(
            f'<span style="color:#536382;">{html.escape(timestamp)}</span> '
            f'<span style="color:{color}; font-weight:600;">{level.ljust(7)}</span> '
            f'<span style="color:{message_color};">{html.escape(message)}</span>'
        )
        self._scroll_log()

    def _append_plain(self, text: str, color: str = "#c6d4ec") -> None:
        self.log_view.appendHtml(
            f'<span style="color:{color};">{html.escape(text)}</span>'
        )
        self._scroll_log()

    def _scroll_log(self) -> None:
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _copy_log(self) -> None:
        QApplication.clipboard().setText(self.log_view.toPlainText())
        self.copy_button.setText("Copied")
        QTimer.singleShot(1200, lambda: self.copy_button.setText("Copy"))

    def _clear_log(self) -> None:
        self.log_view.clear()

    # ------------------------------------------------------------- lifecycle
    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        if self._buffer:
            self._process_line(self._buffer)
            self._buffer = ""

        self._clock.stop()
        self._tick_clock()
        self._paused = False
        self._paused_at = 0.0
        self.pause_button.setText("❚❚   Pause")
        self._set_running(False)

        if self._user_stopped or self._final_state == "cancelled":
            self._set_status("error", "Stopped")
            if not self._final_state:
                self.guide_panel.show_guide(
                    Guide(
                        title="Run stopped",
                        what="You stopped the agent before it finished.",
                        why="You always stay in control; the process is terminated immediately.",
                        how="The child process was killed and the desktop was returned to you.",
                        tip="Run the same task again and watch the first few steps to see where it went.",
                        tone="warn",
                    )
                )
        elif exit_status != QProcess.ExitStatus.NormalExit:
            self._final_state = "error"
            self._set_status("error", "Crashed")
            self.guide_panel.show_guide(
                failure("The agent process crashed before it could finish.")
            )
        elif exit_code == 0:
            self._final_state = "success"
            self._set_status("success", "Complete")
        elif self._final_state == "limit":
            self._set_status("error", "Incomplete")
        else:
            self._final_state = "error"
            self._set_status("error", "Failed")
            self.guide_panel.show_guide(
                failure(f"The agent exited with code {exit_code}.")
            )

        self._append_plain(
            f"Process finished with exit code {exit_code}.",
            "#93a5c8",
        )

    def _on_process_error(self, error: QProcess.ProcessError) -> None:
        self._append_plain(f"Process error: {error.name}", "#fb7185")
        if error == QProcess.ProcessError.FailedToStart:
            self._clock.stop()
            self._paused = False
            self.pause_button.setText("❚❚   Pause")
            self._set_running(False)
            self._set_status("error", "Failed")
            self.guide_panel.show_guide(
                failure("Could not start the agent process. Check the Python installation.")
            )
        elif not self._running:
            self._set_status("error", "Failed")

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if self._process.state() != QProcess.ProcessState.NotRunning:
            self._kill_process_tree()
            self._process.waitForFinished(1500)
        event.accept()


def launch_gui(
    initial_prompt: str = "",
    initial_model: str | None = None,
    initial_instant_click: bool | None = None,
) -> int:
    """Create the application and run the Qt event loop."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName("GeminiPCUse")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLESHEET)

    window = MainWindow(
        initial_prompt=initial_prompt,
        initial_model=initial_model,
        initial_instant_click=initial_instant_click,
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(launch_gui())
