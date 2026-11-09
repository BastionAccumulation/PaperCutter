"""Shared export destination, overwrite decision and file write."""
from pathlib import Path
from PySide6.QtGui import QImageWriter
from core.export_naming import build_export_stem

class ExportService:
    def __init__(self, session, resolve_conflict):
        self.session = session
        self.resolve_conflict = resolve_conflict

    def export(self, render, output_dir, mode, question_num, custom_prefix):
        directory = Path(output_dir) / self.session.path.stem
        path = directory / (build_export_stem(mode, question_num, custom_prefix) + '.png')
        if path.exists():
            decision = self.session.overwrite_decision
            if decision is None:
                decision, remember = self.resolve_conflict(path)
                if remember:
                    self.session.overwrite_decision = decision
            if not decision:
                return None
        image = render()
        directory.mkdir(parents=True, exist_ok=True)
        writer = QImageWriter(str(path), b'png')
        if not writer.write(image):
            raise OSError(f'{path}\n{writer.errorString()}')
        return str(path)
