"""Document navigation and zoom controls in the Aero toolbar."""
from PySide6.QtWidgets import QToolBar, QWidget, QSpinBox, QAbstractSpinBox, QLabel, QHBoxLayout, QSizePolicy
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QSize, Signal, QSignalBlocker
from config.settings import Settings
from config.resources import resource_path
from ui.glass_effect import GlassEffect


def _spinbox_style():
    s = Settings
    up = resource_path('assets', 'controls', 'spin-up.png').as_posix()
    down = resource_path('assets', 'controls', 'spin-down.png').as_posix()
    up_disabled = resource_path('assets', 'controls', 'spin-up-disabled.png').as_posix()
    down_disabled = resource_path('assets', 'controls', 'spin-down-disabled.png').as_posix()
    return f"""
        QSpinBox {{
            background: {s.SURFACE['input']};
            border: 1px solid {s.BORDER['input']};
            border-radius: {s.RADIUS['small']}px;
            padding: 0px 34px 0px 8px;
            color: {s.TEXT['primary']};
            font-family: {s.FONTS['family']};
            font-size: {s.FONTS['size_caption']}pt;
            selection-background-color: {s.SURFACE['list_sel']};
            selection-color: {s.TEXT['selection']};
        }}
        QSpinBox:hover {{
            background: {s.SURFACE['input_focus']};
            border-color: {s.BORDER['strong']};
        }}
        QSpinBox:focus {{
            background: {s.SURFACE['input_focus']};
            border-color: {s.BORDER['focus']};
        }}
        QSpinBox:disabled {{
            background: {s.SURFACE['button_dsb']};
            border-color: {s.BORDER['subtle']};
            color: {s.TEXT['disabled']};
        }}
        QSpinBox QLineEdit {{
            background: transparent;
            border: none;
            padding: 0px;
            color: {s.TEXT['primary']};
            font-size: {s.FONTS['size_caption']}pt;
            selection-background-color: {s.SURFACE['list_sel']};
            selection-color: {s.TEXT['selection']};
        }}
        QSpinBox QLineEdit:disabled {{
            color: {s.TEXT['disabled']};
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            subcontrol-origin: border;
            width: 26px;
            height: 18px;
            background: {s.SURFACE['button']};
            border: none;
            border-left: 1px solid {s.BORDER['input']};
        }}
        QSpinBox::up-button {{
            subcontrol-position: top right;
            border-bottom: 1px solid {s.BORDER['subtle']};
            border-top: 1px solid {s.BORDER['highlight']};
            border-top-right-radius: {s.RADIUS['small']}px;
        }}
        QSpinBox::down-button {{
            subcontrol-position: bottom right;
            border-bottom-right-radius: {s.RADIUS['small']}px;
        }}
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background: {s.SURFACE['button_hov']};
        }}
        QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{
            background: {s.SURFACE['button_prs']};
        }}
        QSpinBox::up-button:disabled, QSpinBox::down-button:disabled,
        QSpinBox::up-button:off, QSpinBox::down-button:off {{
            background: {s.SURFACE['button_dsb']};
            border-left-color: {s.BORDER['subtle']};
        }}
        QSpinBox::up-arrow {{
            image: url("{up}");
            width: 10px;
            height: 6px;
        }}
        QSpinBox::down-arrow {{
            image: url("{down}");
            width: 10px;
            height: 6px;
        }}
        QSpinBox::up-arrow:disabled, QSpinBox::up-arrow:off {{
            image: url("{up_disabled}");
        }}
        QSpinBox::down-arrow:disabled, QSpinBox::down-arrow:off {{
            image: url("{down_disabled}");
        }}
    """


class PageSpinBox(QSpinBox):
    def stepBy(self, steps):
        super().stepBy(-steps)

    def stepEnabled(self):
        native = super().stepEnabled()
        flags = QAbstractSpinBox.StepEnabledFlag
        enabled = flags.StepNone
        if native & flags.StepDownEnabled:
            enabled |= flags.StepUpEnabled
        if native & flags.StepUpEnabled:
            enabled |= flags.StepDownEnabled
        return enabled


class ToolBar(QToolBar):
    zoom_changed = Signal(float)
    page_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(False)
        self.setIconSize(QSize(20, 20))
        self._create_actions()
        self._create_widgets()
        for action in (self.zoom_in_action, self.zoom_out_action,
                       self.fit_width_action, self.fit_page_action):
            action.setEnabled(False)
        self.zoom_input.setEnabled(False)
        GlassEffect.apply_glass_effect(self, 'toolbar')

    def _create_actions(self):
        self.open_action = QAction("打开", self)
        self.open_action.setShortcut("Ctrl+O")
        self.addAction(self.open_action)
        self.addSeparator()

        self.prev_page_action = QAction("上一页", self)
        self.prev_page_action.setShortcut("Ctrl+Left")
        self.prev_page_action.setEnabled(False)
        self.addAction(self.prev_page_action)

        self.next_page_action = QAction("下一页", self)
        self.next_page_action.setShortcut("Ctrl+Right")
        self.next_page_action.setEnabled(False)
        self.addAction(self.next_page_action)
        self.addSeparator()

        self.zoom_in_action = QAction("放大", self)
        self.zoom_in_action.setShortcut("Ctrl++")
        self.addAction(self.zoom_in_action)

        self.zoom_out_action = QAction("缩小", self)
        self.zoom_out_action.setShortcut("Ctrl+-")
        self.addAction(self.zoom_out_action)

        self.fit_width_action = QAction("适应宽度", self)
        self.addAction(self.fit_width_action)

        self.fit_page_action = QAction("适应页面", self)
        self.addAction(self.fit_page_action)

    def _control_group(self):
        group = QWidget(self)
        group.setObjectName('toolbarControlGroup')
        group.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        s = Settings
        group.setStyleSheet(f"""
            QWidget#toolbarControlGroup {{
                background: {s.SURFACE['bg_base']};
                border: 1px solid {s.BORDER['subtle']};
                border-top: 1px solid {s.BORDER['highlight']};
                border-radius: {s.RADIUS['normal']}px;
            }}
            QWidget#toolbarControlGroup QLabel {{
                background: transparent;
                border: none;
                padding: 0px;
                color: {s.TEXT['primary']};
                font-family: {s.FONTS['family']};
                font-size: {s.FONTS['size_caption']}pt;
            }}
            QWidget#toolbarControlGroup QLabel:disabled {{
                color: {s.TEXT['disabled']};
            }}
        """)
        layout = QHBoxLayout(group)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(8)
        return group, layout

    def _configure_spinbox(self, spinbox, minimum_width):
        spinbox.setMinimumWidth(minimum_width)
        spinbox.setFixedHeight(38)
        spinbox.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spinbox.setSingleStep(1)
        spinbox.setKeyboardTracking(False)
        spinbox.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        spinbox.setStyleSheet(_spinbox_style())
        return spinbox

    def _create_widgets(self):
        self.addSeparator()
        self.page_group, page_layout = self._control_group()
        self.page_input = self._configure_spinbox(PageSpinBox(self.page_group), 96)
        self.page_input.setSpecialValueText('—')
        self.page_input.setRange(0, 0)
        self.page_input.setAccessibleName('页码')
        self.page_input.setToolTip('输入页码后按回车或离开输入框跳转；↑ 上一页，↓ 下一页')
        page_caption = QLabel('页码', self.page_group)
        page_caption.setBuddy(self.page_input)
        self.page_total_label = QLabel('/ —', self.page_group)
        page_layout.addWidget(page_caption)
        page_layout.addWidget(self.page_input)
        page_layout.addWidget(self.page_total_label)
        self.page_group.setEnabled(False)
        self.page_input.valueChanged.connect(self._on_page_input_changed)
        self.addWidget(self.page_group)

        self.addSeparator()
        self.zoom_group, zoom_layout = self._control_group()
        self.zoom_input = self._configure_spinbox(QSpinBox(self.zoom_group), 112)
        self.zoom_input.setRange(10, 500)
        self.zoom_input.setSuffix('%')
        self.zoom_input.setValue(100)
        self.zoom_input.setAccessibleName('缩放百分比')
        self.zoom_input.setToolTip('输入百分比后按回车或离开输入框应用；上下箭头立即增减 1%')
        zoom_caption = QLabel('缩放', self.zoom_group)
        zoom_caption.setBuddy(self.zoom_input)
        zoom_layout.addWidget(zoom_caption)
        zoom_layout.addWidget(self.zoom_input)
        self.zoom_input.valueChanged.connect(self._on_zoom_input_changed)
        self.addWidget(self.zoom_group)

    def _on_page_input_changed(self, value):
        self.page_changed.emit(value - 1)

    def _on_zoom_input_changed(self, value):
        self.zoom_changed.emit(value / 100.0)

    def set_page_info(self, current, total):
        has_pages = total > 0
        with QSignalBlocker(self.page_input):
            if has_pages:
                self.page_input.setSpecialValueText('')
                self.page_input.setRange(1, total)
                self.page_input.setValue(current + 1)
                self.page_total_label.setText(f'/ {total}')
            else:
                self.page_input.setRange(0, 0)
                self.page_input.setSpecialValueText('—')
                self.page_total_label.setText('/ —')
        self.page_group.setEnabled(has_pages)
        self.page_input.setEnabled(has_pages)
        self.prev_page_action.setEnabled(has_pages and current > 0)
        self.next_page_action.setEnabled(has_pages and current < total - 1)

    def set_zoom_info(self, zoom):
        with QSignalBlocker(self.zoom_input):
            self.zoom_input.setValue(int(zoom * 100))

    def enable_pdf_controls(self, enabled):
        self.prev_page_action.setEnabled(enabled)
        self.next_page_action.setEnabled(enabled)
        self.page_group.setEnabled(enabled)
        self.page_input.setEnabled(enabled)
