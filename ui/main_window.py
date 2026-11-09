"""Main-window coordination for the active document session."""
import sys
from pathlib import Path
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QMessageBox,
                               QFileDialog, QSplitter, QVBoxLayout, QCheckBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from ui.document_canvas import ScrollableCanvas
from ui.toolbar import ToolBar
from ui.mode_panel import ModePanel
from ui.status_bar import StatusBar
from ui.selection_list import SelectionListWidget
from ui.composition_window import CompositionWindow
from ui.particle_background import ParticleBackground
from ui.glass_effect import GlassEffect
from config import persist
from core.document_session import DocumentSession, PDFSource
from core.selection_exporter import SelectionExporter
from core.selection_merger import SelectionMerger
from core.composition_merger import CompositionMerger
from core.export_service import ExportService

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.session = None
        self._cfg = persist.load()
        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self._execute_render)
        self._init_ui()
        self._connect_signals()
        self.mode_panel.start_selection_btn.setEnabled(False)
        self.toolbar.enable_pdf_controls(False)
        self.toolbar.set_page_info(0, 0)

    def _get_icon_path(self):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = Path(__file__).parent.parent
        return str(Path(base_path) / 'app_icon.ico')

    def _init_ui(self):
        self.setWindowTitle("切题辅助应用")
        self.setGeometry(100, 100, 1400, 800)
        self.setWindowIcon(QIcon(self._get_icon_path()))
        
        self.particle_background = ParticleBackground(self)
        self.particle_background.setGeometry(0, 0, 1400, 800)
        self.particle_background.lower()
        
        self.toolbar = ToolBar()
        self.addToolBar(self.toolbar)
        
        last_output = self._cfg.get('output_dir')
        self.mode_panel = ModePanel(
            last_output,
            self._cfg.get('export_prefix', ''),
            self._cfg.get('auto_increment_enabled', False),
        )
        self.selection_list = SelectionListWidget()
        self.scrollable_canvas = ScrollableCanvas()
        self.canvas = self.scrollable_canvas.get_canvas()
        
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        left_splitter.addWidget(self.mode_panel)
        left_splitter.addWidget(self.selection_list)
        left_splitter.setStretchFactor(0, 1)
        left_splitter.setStretchFactor(1, 1)
        left_splitter.setMinimumWidth(328)
        left_splitter.setMaximumWidth(390)
        left_splitter.setSizes([430, 370])
        
        central_widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        layout.addWidget(left_splitter)
        layout.addWidget(self.scrollable_canvas, stretch=1)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        self.status_bar = StatusBar()
        self.setStatusBar(self.status_bar)
        
        self._apply_glass_effects()

    def _connect_signals(self):
        self.toolbar.open_action.triggered.connect(self._open_file)
        self.toolbar.prev_page_action.triggered.connect(self._prev_page)
        self.toolbar.next_page_action.triggered.connect(self._next_page)
        self.toolbar.zoom_in_action.triggered.connect(self._zoom_in)
        self.toolbar.zoom_out_action.triggered.connect(self._zoom_out)
        self.toolbar.fit_width_action.triggered.connect(self._fit_width)
        self.toolbar.fit_page_action.triggered.connect(self._fit_page)
        self.toolbar.zoom_changed.connect(self._set_zoom)
        self.toolbar.page_changed.connect(self._change_page)
        self.mode_panel.mode_changed.connect(self.status_bar.set_mode_info)
        self.mode_panel.start_selection.connect(self._on_start_selection)
        self.mode_panel.selection_tool_changed.connect(self.canvas.set_selection_tool)
        self.mode_panel.confirm_cut.connect(self._on_confirm_cut)
        self.mode_panel.add_selection.connect(self._on_add_selection)
        self.mode_panel.open_composition.connect(self._on_open_composition)
        self.canvas.selection_changed.connect(self._on_selection_changed)
        self.selection_list.export_merged.connect(self._on_export_merged)
        self.selection_list.clear_all.connect(self._on_clear_all_selections)

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '打开文件', self._cfg.get('last_open_dir', ''),
            '支持的文件 (*.png *.jpg *.jpeg *.bmp *.pdf);;图片文件 (*.png *.jpg *.jpeg *.bmp);;PDF文件 (*.pdf)')
        if path:
            try:
                opened = self._load_file(path)
            except (OSError, ValueError, RuntimeError) as error:
                QMessageBox.critical(self, '打开失败', str(error))
                return
            if opened:
                directory = str(self.session.path.parent)
                self._cfg['last_open_dir'] = directory
                try:
                    persist.update({'last_open_dir': directory})
                except OSError as error:
                    QMessageBox.critical(self, '保存打开位置失败', str(error))

    def _load_file(self, path):
        candidate = DocumentSession.open(path)
        if self.session is not None and self.session.has_content:
            answer = QMessageBox.question(
                self, '切换文档', '当前文档有草稿、暂存选区或编排内容，是否丢弃并打开新文档？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                candidate.close()
                return False
        self.render_timer.stop()
        previous = self.session
        if previous is not None:
            previous.selections.changed.disconnect(self._refresh_actions)
            previous.composition.changed.disconnect(self._refresh_actions)
        self.session = candidate
        self.selection_list.bind_model(candidate.selections)
        self.canvas.bind_session(candidate)
        candidate.selections.changed.connect(self._refresh_actions)
        candidate.composition.changed.connect(self._refresh_actions)
        if previous is not None:
            previous.close()
            previous.deleteLater()
        self.mode_panel.cancel_selection()
        self.canvas.set_selection_mode(False)
        self.mode_panel.start_selection_btn.setEnabled(True)
        self.toolbar.zoom_in_action.setEnabled(True)
        self.toolbar.zoom_out_action.setEnabled(True)
        self.toolbar.fit_width_action.setEnabled(True)
        self.toolbar.fit_page_action.setEnabled(True)
        self.toolbar.zoom_input.setEnabled(True)
        self.status_bar.set_file_info(candidate.path.stem)
        self._sync_page_info()
        self._sync_zoom_info()
        self._refresh_actions()
        return True

    def _refresh_actions(self):
        available = bool(self.session.selections.items or self.session.composition.entries)
        self.mode_panel.composition_btn.setEnabled(available)

    def _sync_page_info(self):
        session = self.session
        is_pdf = isinstance(session.source, PDFSource)
        self.toolbar.enable_pdf_controls(is_pdf)
        count = session.source.page_count if is_pdf else 0
        self.toolbar.set_page_info(session.page_num, count)
        self.status_bar.set_page_info(session.page_num, count)

    def _sync_zoom_info(self):
        self.toolbar.set_zoom_info(self.session.zoom)
        self.status_bar.set_zoom_info(self.session.zoom)

    def _prev_page(self):
        self._change_page(self.session.page_num - 1)

    def _next_page(self):
        self._change_page(self.session.page_num + 1)

    def _change_page(self, page_num):
        session = self.session
        try:
            image = session.source.render(page_num, session.zoom)
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.critical(self, '翻页失败', str(error))
            self._sync_page_info()
            return
        self.render_timer.stop()
        session.page_num = page_num
        session.preview = image
        self.mode_panel.cancel_selection()
        self.canvas.set_selection_mode(False)
        self.canvas.page_changed()
        self._sync_page_info()

    def _set_zoom(self, zoom):
        self.session.zoom = max(0.1, min(zoom, 5.0))
        self.canvas.update_transform()
        self._sync_zoom_info()
        self.render_timer.start(100)

    def _execute_render(self):
        session = self.session
        try:
            image = session.source.render(session.page_num, session.zoom)
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.critical(self, '显示失败', str(error))
            return
        session.preview = image
        self.canvas.set_image(image)

    def _zoom_in(self):
        self._set_zoom(self.session.zoom * 1.2)

    def _zoom_out(self):
        self._set_zoom(self.session.zoom / 1.2)

    def _fit_width(self):
        width, _ = self.session.source.page_size(self.session.page_num)
        self._set_zoom(self.scrollable_canvas.viewport().width() /
                       (width * self.session.source.display_base))

    def _fit_page(self):
        width, height = self.session.source.page_size(self.session.page_num)
        viewport = self.scrollable_canvas.viewport()
        base = self.session.source.display_base
        self._set_zoom(min(viewport.width() / (width * base), viewport.height() / (height * base)))

    def _on_start_selection(self):
        enabled = self.mode_panel.start_selection_btn.isChecked()
        self.canvas.set_selection_tool(self.mode_panel.get_selection_tool())
        self.canvas.set_selection_mode(enabled)
        if not enabled:
            self.session.set_draft(None)

    def _on_selection_changed(self, available):
        self.mode_panel.set_selection_active(available)
        if available:
            geometry = self.session.draft
            self.canvas.selection_tool = geometry.shape_type
            self.mode_panel.set_selection_tool(geometry.shape_type)
            self.status_bar.set_selection_info(geometry.rect, geometry.shape_type)
        else:
            self.status_bar.set_selection_info(None)

    def _finish_selection(self):
        self.session.set_draft(None)
        self.mode_panel.cancel_selection()
        self.canvas.set_selection_mode(False)

    def _on_add_selection(self):
        try:
            self.session.commit_draft()
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.critical(self, '添加失败', str(error))
            return
        self._finish_selection()

    def _on_clear_all_selections(self):
        answer = QMessageBox.question(
            self, '清除选区', '确定要清除所有暂存选区吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.session.selections.clear()

    def _on_open_composition(self):
        if self.session.composition_window is None:
            dialog = CompositionWindow(self.session, self)
            dialog.export_requested.connect(self._on_export_composition)
            self.session.composition_window = dialog
        dialog = self.session.composition_window
        if dialog.isMinimized():
            dialog.setWindowState(dialog.windowState() ^ Qt.WindowState.WindowMinimized)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _resolve_conflict(self, path):
        dialog = QMessageBox(self)
        dialog.setWindowTitle('文件已存在')
        dialog.setText(f'是否替换已有图片？\n{path}')
        replace_button = dialog.addButton('替换', QMessageBox.ButtonRole.AcceptRole)
        skip_button = dialog.addButton('跳过', QMessageBox.ButtonRole.NoRole)
        cancel_button = dialog.addButton('取消', QMessageBox.ButtonRole.RejectRole)
        dialog.setDefaultButton(skip_button)
        dialog.setEscapeButton(cancel_button)
        checkbox = QCheckBox('将此选择应用于当前文档后续所有同名文件', dialog)
        dialog.setCheckBox(checkbox)
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked == cancel_button:
            return None, False
        return clicked == replace_button, checkbox.isChecked()

    def _export(self, kind):
        question_num = self.mode_panel.get_question_num()
        output_dir = self.mode_panel.get_output_dir()
        if not question_num:
            QMessageBox.information(self, '导出', '请输入题号')
            return
        if output_dir is None:
            QMessageBox.information(self, '导出', '请选择输出文件夹')
            return
        session = self.session
        if kind == 'selection':
            geometry = session.draft
            outside = (self.mode_panel.get_selection_outside_mode()
                       if geometry.shape_type == 'free' else 'transparent')
            render = lambda: SelectionExporter.render(session.source.crop(geometry), outside)
        elif kind == 'merged':
            render = lambda: SelectionMerger.render(session.selections.items)
        else:
            render = lambda: CompositionMerger.render(session.composition)
        try:
            path = ExportService(session, self._resolve_conflict).export(
                render, output_dir, self.mode_panel.get_mode(), question_num,
                self.mode_panel.get_export_prefix())
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.critical(self, '导出失败', str(error))
            return
        if path is None:
            return
        if kind == 'selection':
            self._finish_selection()
        elif kind == 'merged':
            session.selections.clear()
        if self.mode_panel.is_auto_increment_enabled():
            self.mode_panel.increment_question_num()
        self.status_bar.showMessage(f'已导出：{path}', 5000)
        if kind == 'composition':
            session.composition_window.notify_export(path)

    def _on_confirm_cut(self):
        self._export('selection')

    def _on_export_merged(self):
        self._export('merged')

    def _on_export_composition(self):
        self._export('composition')

    def closeEvent(self, event):
        self.render_timer.stop()
        if self.session is not None:
            self.session.selections.changed.disconnect(self._refresh_actions)
            self.session.composition.changed.disconnect(self._refresh_actions)
            self.selection_list.model.changed.disconnect(self.selection_list._refresh)
            self.canvas.session.draft_changed.disconnect(self.canvas._draft_changed)
            self.session.close()
        event.accept()

    def _apply_glass_effects(self):
        GlassEffect.apply_glass_effect(self.toolbar, 'toolbar')
        GlassEffect.apply_glass_effect(self.mode_panel, 'panel')
        GlassEffect.apply_glass_effect(self.selection_list, 'list')
        GlassEffect.apply_glass_effect(self.status_bar, 'statusbar')
        GlassEffect.apply_glass_effect(self.scrollable_canvas, 'canvas')

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'particle_background'):
            self.particle_background.setGeometry(0, 0, self.width(), self.height())
