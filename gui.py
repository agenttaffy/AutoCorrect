import sys
import random
import time
import json
import os
import datetime
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QRect, QRectF, QEasingCurve, 
    Signal, QObject, Property, QSequentialAnimationGroup, QPoint
)
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QPainterPath,
    QIcon, QPixmap, QAction
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFrame, QStackedWidget,
    QSizePolicy, QGridLayout, QSpacerItem, QGraphicsOpacityEffect,
    QSystemTrayIcon, QMenu, QListWidget, QLineEdit
)

import AutoCorrect

# =====================================================================
# Neural Constants
# =====================================================================
FONT_STACK = "Geist, Segoe UI, sans-serif"

# --- TRAY ICON CONFIGURATION ---
# Change this path to point to your own .ico or .png file.
# If the file does not exist, a default pink square will be generated.
TRAY_ICON_PATH = "icon.png" 

C_BASE_BG = QColor("#0a0a0b")
C_SURFACE = QColor("#111113")
C_ACCENT = QColor("#ff57a0")

C_ACCENT_HOVER = QColor(255, 87, 160, 89)
C_ACCENT_FAINT = QColor(255, 87, 160, 25)
C_BORDER = QColor(255, 87, 160, 82)

C_TEXT_PRI = QColor("#ededf0")
C_TEXT_SEC = QColor("#8b8b94")
C_TEXT_MUT = QColor("#55555e")

GLOBAL_QSS = f"""
QMainWindow {{ background-color: {C_BASE_BG.name()}; }}
"""


# =====================================================================
# Matrix Layer
# =====================================================================
class MatrixLayer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_drops)
        self.timer.start(40)
        
        self.columns = 0
        self.drops = []
        self.char_size = 16
        # Heavily weighted with Japanese Half-width Katakana for Matrix feel
        self.chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ" * 3

    def resizeEvent(self, event):
        self.columns = self.width() // self.char_size + 1
        if len(self.drops) < self.columns:
            for _ in range(self.columns - len(self.drops)):
                self.drops.append(random.randint(-100, 0))

    def update_drops(self):
        for i in range(len(self.drops)):
            if self.drops[i] * self.char_size > self.height() and random.random() > 0.95:
                self.drops[i] = 0
            self.drops[i] += 1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), C_BASE_BG)
        painter.setFont(QFont("Courier New", 10, QFont.Bold))
        
        for i in range(len(self.drops)):
            x = i * self.char_size
            y = self.drops[i] * self.char_size

            for j in range(20):
                trail_y = y - (j * self.char_size)
                if trail_y < 0 or trail_y > self.height():
                    continue
                
                char = random.choice(self.chars)
                alpha = max(0, 255 - (j * 12))
                color = QColor(C_ACCENT)
                color.setAlpha(alpha)
                
                painter.setPen(color)
                painter.drawText(x, trail_y, char)


# =====================================================================
# Glassmorphic Containers
# =====================================================================
class GlassFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            GlassFrame {{
                background-color: rgba(17, 17, 19, 200);
                border: 1px solid rgba(255, 87, 160, 82);
                border-radius: 8px;
            }}
        """)


class NeuralInput(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont(FONT_STACK, 12))
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: rgba(10, 10, 11, 220);
                color: {C_TEXT_PRI.name()};
                border: 1px solid rgba(255, 87, 160, 50);
                border-radius: 4px;
                padding: 10px;
            }}
            QTextEdit:focus {{
                border: 1px solid {C_ACCENT.name()};
            }}
        """)

class NeuralLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont(FONT_STACK, 11))
        self.setFixedHeight(36)
        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(10, 10, 11, 220);
                color: {C_TEXT_PRI.name()};
                border: 1px solid rgba(255, 87, 160, 50);
                border-radius: 4px;
                padding: 5px 10px;
            }}
            QLineEdit:focus {{
                border: 1px solid {C_ACCENT.name()};
            }}
        """)

# =====================================================================
# Animated Custom Controls
# =====================================================================
class NeuralButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(36)
        self.setFont(QFont(FONT_STACK, 10, QFont.Bold))
        
        self.bg_color = QColor(0, 0, 0, 0)
        self.anim = QPropertyAnimation(self, b"hover_color")
        self.anim.setDuration(200)
        
    @Property(QColor)
    def hover_color(self):
        return self.bg_color
        
    @hover_color.setter
    def hover_color(self, color):
        self.bg_color = color
        self.update()

    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setEndValue(C_ACCENT_HOVER)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setEndValue(QColor(0, 0, 0, 0))
        self.anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 4, 4)
        painter.fillPath(path, self.bg_color)
        
        painter.setPen(QPen(C_BORDER, 1))
        painter.drawPath(path)
        
        painter.setPen(C_TEXT_PRI)
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())


class NeuralToggle(QWidget):
    toggled = Signal(bool)
    
    def __init__(self, parent=None, checked=True):
        super().__init__(parent)
        self.setFixedSize(40, 20)
        self.setCursor(Qt.PointingHandCursor)
        self._checked = checked
        self._thumb_pos = 20 if checked else 2
        
        self.anim = QPropertyAnimation(self, b"thumb_pos")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutExpo)
        
    @Property(float)
    def thumb_pos(self):
        return self._thumb_pos
        
    @thumb_pos.setter
    def thumb_pos(self, pos):
        self._thumb_pos = pos
        self.update()
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._checked = not self._checked
            self.anim.stop()
            self.anim.setEndValue(20 if self._checked else 2)
            self.anim.start()
            self.toggled.emit(self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        track_rect = QRectF(0, 0, self.width(), self.height())
        bg_color = C_ACCENT_HOVER if self._checked else QColor(30, 30, 35)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(C_BORDER, 1))
        painter.drawRoundedRect(track_rect, 10, 10)
        
        thumb_rect = QRectF(self._thumb_pos, 2, 16, 16)
        painter.setBrush(QBrush(C_ACCENT if self._checked else C_TEXT_MUT))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(thumb_rect)


# =====================================================================
# Custom Frameless Title Bar
# =====================================================================
class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(30)
        self.setStyleSheet(f"background-color: {C_BASE_BG.name()};")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        
        title = QLabel("SYS_AUTOCORRECT")
        title.setFont(QFont(FONT_STACK, 9, QFont.Bold))
        title.setStyleSheet(f"color: {C_TEXT_SEC.name()};")
        
        btn_min = QPushButton("─")
        btn_min.setFixedSize(20, 20)
        btn_min.setStyleSheet(f"color: {C_TEXT_SEC.name()}; background: transparent; border: none;")
        btn_min.clicked.connect(self.parent.showMinimized)
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(20, 20)
        btn_close.setStyleSheet(f"color: {C_TEXT_SEC.name()}; background: transparent; border: none;")
        btn_close.clicked.connect(self.parent.close_to_tray)
        
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(btn_min)
        layout.addWidget(btn_close)

        self.drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            self.parent.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None


# =====================================================================
# Backend Bridge
# =====================================================================
class BackendSignals(QObject):
    stats_updated = Signal()
    log_added = Signal(str, str)
    toggled_by_hotkey = Signal(bool)


# =====================================================================
# Main Application
# =====================================================================
class AutoCorrectGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoCorrect_Neural")
        self.resize(1000, 700)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setStyleSheet(GLOBAL_QSS)
        
        # Tray Icon setup
        self.setup_tray()
        
        self.signals = BackendSignals()
        self.signals.stats_updated.connect(self.update_stats_ui)
        self.signals.log_added.connect(self.append_log)
        self.signals.toggled_by_hotkey.connect(self.sync_toggle_state)

        AutoCorrect.GUI_CALLBACKS["on_stats_update"] = self.signals.stats_updated.emit
        AutoCorrect.GUI_CALLBACKS["on_log"] = self.signals.log_added.emit
        AutoCorrect.GUI_CALLBACKS["on_toggle"] = self.signals.toggled_by_hotkey.emit

        self.setup_ui()
        AutoCorrect.start_in_background()
        self.update_stats_ui()
        
        self.run_startup_animation()

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # Load icon from path if it exists, otherwise generate fallback
        if os.path.exists(TRAY_ICON_PATH):
            icon = QIcon(TRAY_ICON_PATH)
        else:
            # Create a simple pink square icon as fallback
            pixmap = QPixmap(32, 32)
            pixmap.fill(C_ACCENT)
            icon = QIcon(pixmap)
        
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("SYS_AUTOCORRECT Daemon")
        
        menu = QMenu()
        show_action = QAction("Show Interface", self)
        show_action.triggered.connect(self.showNormal)
        quit_action = QAction("Quit Daemon", self)
        quit_action.triggered.connect(self.quit_app)
        
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()
        
        self.tray_icon.activated.connect(self.tray_activated)

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.showNormal()
            self.activateWindow()

    def sync_toggle_state(self, enabled):
        """Sync the UI toggle and show the window when enabled via hotkey."""
        self.btn_master._checked = enabled
        self.btn_master.anim.stop()
        self.btn_master.anim.setEndValue(20 if enabled else 2)
        self.btn_master.anim.start()
        
        if enabled:
            self.showNormal()
            self.activateWindow()
            self.tray_icon.showMessage(
                "AutoCorrect Activated",
                "Engine is now ONLINE.",
                QSystemTrayIcon.Information,
                1000
            )

    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.close_to_tray()
            event.ignore()

    def close_to_tray(self):
        self.hide()
        self.tray_icon.showMessage(
            "AutoCorrect Running",
            "The daemon is still running in the background. Double click the tray icon to restore.",
            QSystemTrayIcon.Information,
            2000
        )

    def quit_app(self):
        self.tray_icon.hide()
        QApplication.quit()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        grid = QGridLayout(central)
        grid.setContentsMargins(0, 0, 0, 0)
        
        self.bg = MatrixLayer(central)
        grid.addWidget(self.bg, 0, 0)
        
        ui_container = QWidget()
        ui_layout = QVBoxLayout(ui_container)
        ui_layout.setContentsMargins(0, 0, 0, 0)
        ui_layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(self)
        ui_layout.addWidget(self.title_bar)
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(30, 20, 30, 30)
        main_layout.setSpacing(20)
        
        # --- LEFT RAIL ---
        left_col = QFrame()
        left_col.setFixedWidth(200)
        l_layout = QVBoxLayout(left_col)
        l_layout.setContentsMargins(0, 0, 0, 0)
        
        self.logo_label = QLabel("A C")
        self.logo_label.setFont(QFont(FONT_STACK, 32, QFont.Bold))
        self.logo_label.setStyleSheet(f"color: {C_TEXT_PRI.name()};")
        
        l_layout.addWidget(self.logo_label)
        l_layout.addSpacing(40)
        
        self.nav_container = QWidget()
        nav_vbox = QVBoxLayout(self.nav_container)
        nav_vbox.setContentsMargins(15, 0, 0, 0)
        
        self.btn_stats = QPushButton("STATISTICS")
        self.btn_unknown = QPushButton("UNKNOWN WORDS")
        self.btn_dict = QPushButton("DICTIONARY")
        self.btn_logs = QPushButton("SYS_LOGS")
        
        self.nav_btns = [self.btn_stats, self.btn_unknown, self.btn_dict, self.btn_logs]
        
        for idx, btn in enumerate(self.nav_btns):
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"color: {C_TEXT_SEC.name()}; background: transparent; border: none; text-align: left;")
            btn.setFont(QFont(FONT_STACK, 11, QFont.Bold))
            nav_vbox.addWidget(btn)
            btn.clicked.connect(lambda checked, i=idx, b=btn: self.switch_view(i, b))
            
        l_layout.addWidget(self.nav_container)
        l_layout.addStretch()
        
        self.indicator = QWidget(self.nav_container)
        self.indicator.setStyleSheet(f"background-color: {C_ACCENT.name()};")
        self.indicator.setFixedSize(3, 20)
        self.indicator.move(0, 0)
        
        self.ind_anim = QPropertyAnimation(self.indicator, b"geometry")
        self.ind_anim.setDuration(300)
        self.ind_anim.setEasingCurve(QEasingCurve.OutExpo)
        
        # --- CENTER ---
        self.stack = QStackedWidget()
        self.page_stats = self.build_statistics()
        self.page_unknown = self.build_unknown_words()
        self.page_dict = self.build_dictionary()
        self.page_logs = self.build_logs()
        
        self.stack.addWidget(self.page_stats)
        self.stack.addWidget(self.page_unknown)
        self.stack.addWidget(self.page_dict)
        self.stack.addWidget(self.page_logs)
        
        # --- RIGHT (Diagnostics) ---
        self.diag_panel = self.build_diagnostics()
        
        main_layout.addWidget(left_col)
        main_layout.addWidget(self.stack, stretch=1)
        main_layout.addWidget(self.diag_panel)
        
        ui_layout.addLayout(main_layout)
        grid.addWidget(ui_container, 0, 0)
        
        QTimer.singleShot(50, lambda: self.switch_view(0, self.btn_stats))

    def switch_view(self, index, button):
        self.stack.setCurrentIndex(index)
        
        for btn in self.nav_btns:
            btn.setStyleSheet(f"color: {C_TEXT_SEC.name()}; background: transparent; border: none; text-align: left;")
        button.setStyleSheet(f"color: {C_TEXT_PRI.name()}; background: transparent; border: none; text-align: left;")
        
        target_y = button.y() + (button.height() - 20) // 2
        self.ind_anim.stop()
        self.ind_anim.setEndValue(QRect(0, target_y, 3, 20))
        self.ind_anim.start()

    def run_startup_animation(self):
        self.logo_op = QGraphicsOpacityEffect(self.logo_label)
        self.logo_label.setGraphicsEffect(self.logo_op)
        
        group = QSequentialAnimationGroup()
        for val in [0.0, 1.0, 0.4, 1.0]:
            anim = QPropertyAnimation(self.logo_op, b"opacity")
            anim.setDuration(50)
            anim.setEndValue(val)
            group.addAnimation(anim)
            
        group.start()

    # ========================== VIEW BUILDERS ==========================
    def build_statistics(self):
        panel = GlassFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        lbl = QLabel("LIFETIME METRICS")
        lbl.setFont(QFont(FONT_STACK, 12, QFont.Bold))
        lbl.setStyleSheet(f"color: {C_TEXT_PRI.name()};")
        layout.addWidget(lbl)
        
        # Scroll area for stats
        self.stats_text = NeuralInput()
        self.stats_text.setReadOnly(True)
        self.refresh_stats_view()
        layout.addWidget(self.stats_text)
        
        btn = NeuralButton("Refresh Data")
        btn.clicked.connect(self.refresh_stats_view)
        layout.addWidget(btn)
        
        return panel
        
    def refresh_stats_view(self):
        stats = AutoCorrect.load_stats()
        if not stats:
            self.stats_text.setText("No data recorded yet.")
            return
            
        today = datetime.date.today()
        
        periods = {
            "Day": lambda d: d == today,
            "Week": lambda d: (today - d).days <= 7,
            "Month": lambda d: (today - d).days <= 30,
            "Lifetime": lambda d: True
        }
        
        res = []
        for period_name, condition in periods.items():
            scanned = 0
            corrected = 0
            total_time = 0.0
            
            for date_str, data in stats.items():
                try:
                    d = datetime.date.fromisoformat(date_str)
                    if condition(d):
                        scanned += data.get("scanned", 0)
                        corrected += data.get("corrected", 0)
                        total_time += data.get("time_ms", 0.0)
                except:
                    pass
            
            avg_time = (total_time / scanned) if scanned > 0 else 0.0
            
            res.append(f"[{period_name.upper()}]")
            res.append(f"  Words Scanned : {scanned:,}")
            res.append(f"  Corrections   : {corrected:,}")
            res.append(f"  Avg Latency   : {avg_time:.2f} ms\n")
            
        self.stats_text.setText("\n".join(res))

    def build_unknown_words(self):
        panel = GlassFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        lbl = QLabel("UNKNOWN TOKENS")
        lbl.setFont(QFont(FONT_STACK, 12, QFont.Bold))
        lbl.setStyleSheet(f"color: {C_TEXT_PRI.name()};")
        layout.addWidget(lbl)
        
        self.unknown_text = NeuralInput()
        self.unknown_text.setReadOnly(True)
        self.refresh_unknown_view()
        layout.addWidget(self.unknown_text)
        
        btn = NeuralButton("Refresh List")
        btn.clicked.connect(self.refresh_unknown_view)
        layout.addWidget(btn)
        
        return panel
        
    def refresh_unknown_view(self):
        if os.path.exists(AutoCorrect.UNKNOWN_FILE):
            with open(AutoCorrect.UNKNOWN_FILE, "r") as f:
                content = f.read()
                self.unknown_text.setText(content if content else "No unknown words logged.")
        else:
            self.unknown_text.setText("No unknown words logged.")

    def build_dictionary(self):
        panel = GlassFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        lbl = QLabel("CUSTOM DICTIONARY")
        lbl.setFont(QFont(FONT_STACK, 12, QFont.Bold))
        lbl.setStyleSheet(f"color: {C_TEXT_PRI.name()};")
        layout.addWidget(lbl)
        
        self.dict_search = NeuralLineEdit()
        self.dict_search.setPlaceholderText("Search dictionary...")
        self.dict_search.textChanged.connect(self.filter_dict)
        layout.addWidget(self.dict_search)
        
        self.dict_list = QListWidget()
        self.dict_list.setStyleSheet(f"""
            QListWidget {{
                background-color: rgba(10, 10, 11, 220);
                color: {C_TEXT_PRI.name()};
                border: 1px solid rgba(255, 87, 160, 50);
                border-radius: 4px;
                padding: 5px;
                font-family: '{FONT_STACK}';
                font-size: 13px;
            }}
            QListWidget::item:selected {{
                background-color: {C_ACCENT_HOVER.name()};
                color: {C_TEXT_PRI.name()};
            }}
        """)
        layout.addWidget(self.dict_list)
        self.refresh_dict_view()
        
        add_layout = QHBoxLayout()
        self.dict_input = NeuralLineEdit()
        self.dict_input.setPlaceholderText("New word...")
        btn_add = NeuralButton("Add Word")
        btn_add.clicked.connect(self.add_to_dict)
        add_layout.addWidget(self.dict_input, stretch=1)
        add_layout.addWidget(btn_add)
        
        layout.addLayout(add_layout)
        
        btn_remove = NeuralButton("Remove Selected")
        btn_remove.clicked.connect(self.remove_from_dict)
        layout.addWidget(btn_remove)
        
        return panel
        
    def refresh_dict_view(self):
        self.dict_list.clear()
        if os.path.exists(AutoCorrect.CUSTOM_DICT_FILE):
            with open(AutoCorrect.CUSTOM_DICT_FILE, "r") as f:
                words = f.read().splitlines()
                self.dict_list.addItems(sorted(words))

    def filter_dict(self, text):
        for i in range(self.dict_list.count()):
            item = self.dict_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def add_to_dict(self):
        word = self.dict_input.text().strip()
        if word:
            AutoCorrect.add_custom_word(word)
            self.dict_input.clear()
            self.refresh_dict_view()

    def remove_from_dict(self):
        selected = self.dict_list.selectedItems()
        if selected:
            for item in selected:
                AutoCorrect.remove_custom_word(item.text())
            self.refresh_dict_view()

    def build_logs(self):
        panel = GlassFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        
        lbl = QLabel("SYSTEM_LOGS")
        lbl.setFont(QFont(FONT_STACK, 12, QFont.Bold))
        lbl.setStyleSheet(f"color: {C_TEXT_PRI.name()};")
        layout.addWidget(lbl)
        
        self.log_area = NeuralInput()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        
        return panel

    def build_diagnostics(self):
        panel = GlassFrame()
        panel.setFixedWidth(280)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        lbl = QLabel("DIAGNOSTICS")
        lbl.setFont(QFont(FONT_STACK, 12, QFont.Bold))
        lbl.setStyleSheet(f"color: {C_TEXT_PRI.name()};")
        layout.addWidget(lbl)
        
        self.s_scanned, self.v_scanned = self.build_stat_row("Words Scanned", "0")
        self.s_applied, self.v_applied = self.build_stat_row("Corrections", "0")
        self.s_unknown, self.v_unknown = self.build_stat_row("Unknown", "0")
        
        layout.addLayout(self.s_scanned)
        layout.addLayout(self.s_applied)
        layout.addLayout(self.s_unknown)
        
        layout.addSpacing(20)
        
        # Master Toggle
        m_layout = QHBoxLayout()
        m_lbl = QLabel("AutoCorrect On")
        m_lbl.setFont(QFont(FONT_STACK, 10))
        m_lbl.setStyleSheet(f"color: {C_TEXT_SEC.name()};")
        
        self.btn_master = NeuralToggle(checked=AutoCorrect.MASTER_ENABLE)
        self.btn_master.toggled.connect(self.on_master_toggle)
        
        m_layout.addWidget(m_lbl)
        m_layout.addStretch()
        m_layout.addWidget(self.btn_master)
        layout.addLayout(m_layout)
        
        # Context Engine Toggle
        t_layout = QHBoxLayout()
        t_lbl = QLabel("Context Engine")
        t_lbl.setFont(QFont(FONT_STACK, 10))
        t_lbl.setStyleSheet(f"color: {C_TEXT_SEC.name()};")
        
        self.btn_toggle = NeuralToggle(checked=AutoCorrect.ENABLE_BIGRAMS)
        self.btn_toggle.toggled.connect(self.on_bigram_toggle)
        
        t_layout.addWidget(t_lbl)
        t_layout.addStretch()
        t_layout.addWidget(self.btn_toggle)
        layout.addLayout(t_layout)

        # Auto-Capitalization Toggle
        c_layout = QHBoxLayout()
        c_lbl = QLabel("Auto-Capitalization")
        c_lbl.setFont(QFont(FONT_STACK, 10))
        c_lbl.setStyleSheet(f"color: {C_TEXT_SEC.name()};")
        
        self.btn_caps = NeuralToggle(checked=AutoCorrect.ENABLE_CAPITALIZATION)
        self.btn_caps.toggled.connect(self.on_caps_toggle)
        
        c_layout.addWidget(c_lbl)
        c_layout.addStretch()
        c_layout.addWidget(self.btn_caps)
        layout.addLayout(c_layout)

        layout.addSpacing(10)

        # Undo Window
        u_layout = QVBoxLayout()
        u_lbl = QLabel("Undo Window (seconds)")
        u_lbl.setFont(QFont(FONT_STACK, 10))
        u_lbl.setStyleSheet(f"color: {C_TEXT_SEC.name()};")
        
        self.undo_input = QLineEdit(str(AutoCorrect.UNDO_WINDOW))
        self.undo_input.setFixedWidth(80)
        self.undo_input.setStyleSheet(f"""
            background: {C_SURFACE.name()};
            border: 1px solid {C_BORDER.name()};
            color: {C_TEXT_PRI.name()};
            padding: 5px;
            border-radius: 4px;
        """)
        self.undo_input.textChanged.connect(self.on_undo_change)
        
        u_layout.addWidget(u_lbl)
        u_layout.addWidget(self.undo_input)
        layout.addLayout(u_layout)

        layout.addStretch()
        
        # Quit Button
        self.btn_quit = QPushButton("EXIT DAEMON")
        self.btn_quit.setFixedHeight(40)
        self.btn_quit.setCursor(Qt.PointingHandCursor)
        self.btn_quit.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 87, 160, 40);
                color: {C_ACCENT.name()};
                border: 1px solid rgba(255, 87, 160, 80);
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 87, 160, 80);
            }}
        """)
        self.btn_quit.clicked.connect(self.quit_app)
        layout.addWidget(self.btn_quit)

        return panel

    def build_stat_row(self, label, value, val_color=C_TEXT_PRI):
        lay = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFont(QFont(FONT_STACK, 10))
        lbl.setStyleSheet(f"color: {C_TEXT_SEC.name()};")
        
        val = QLabel(value)
        val.setFont(QFont(FONT_STACK, 12, QFont.Bold))
        val.setStyleSheet(f"color: {val_color.name()};")
        
        lay.addWidget(lbl)
        lay.addStretch()
        lay.addWidget(val)
        return lay, val

    def on_master_toggle(self, checked):
        AutoCorrect.MASTER_ENABLE = checked
        AutoCorrect.save_config()

    def on_bigram_toggle(self, checked):
        AutoCorrect.ENABLE_BIGRAMS = checked
        AutoCorrect.save_config()

    def on_caps_toggle(self, checked):
        AutoCorrect.ENABLE_CAPITALIZATION = checked
        AutoCorrect.save_config()

    def on_undo_change(self, text):
        try:
            val = float(text)
            if 0 < val < 5:
                AutoCorrect.UNDO_WINDOW = val
                AutoCorrect.save_config()
        except ValueError:
            pass

    def update_stats_ui(self):
        self.v_scanned.setText(str(AutoCorrect.GUI_WORDS_SCANNED))
        self.v_applied.setText(str(AutoCorrect.GUI_CORRECTIONS_APPLIED))
        self.v_unknown.setText(str(AutoCorrect.GUI_UNKNOWN_TOKENS))

    def append_log(self, original, corrected):
        ts = time.strftime("%H:%M:%S")
        msg = f"[{ts}] <span style='color:{C_TEXT_MUT.name()};'>{original}</span> → <span style='color:{C_ACCENT.name()};'>{corrected}</span>"
        self.log_area.append(msg)


def launch():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Needed so minimizing to tray doesn't quit
    
    font = app.font()
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)
    
    window = AutoCorrectGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch()
