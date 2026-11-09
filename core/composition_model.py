"""Composition geometry and undoable editing commands."""
from dataclasses import dataclass, replace
from math import floor, ceil
from uuid import uuid4
from PySide6.QtCore import QObject, Signal, QRectF
from PySide6.QtGui import QTransform
from core.selection_manager import SelectionItem

@dataclass(frozen=True)
class CompositionEntry:
    id: str
    selection: SelectionItem
    x: float
    y: float
    rotation: float
    z: int

    @property
    def rect(self):
        return QRectF(0, 0, self.selection.image.width(), self.selection.image.height())

    def transform(self):
        w, h = self.rect.width(), self.rect.height()
        transform = QTransform()
        transform.translate(self.x + w / 2, self.y + h / 2)
        transform.rotate(self.rotation)
        transform.translate(-w / 2, -h / 2)
        return transform

    def bounds(self):
        return self.transform().mapRect(self.rect)

@dataclass(frozen=True)
class CompositionState:
    entries: tuple[CompositionEntry, ...]
    background_mode: str
    background_color: tuple[int, int, int]
    padding: int

@dataclass(frozen=True)
class CompositionCommand:
    label: str
    before: CompositionState
    after: CompositionState

class CompositionModel(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.entries = ()
        self.background_mode = 'transparent'
        self.background_color = (248, 254, 255)
        self.padding = 16
        self.undo_stack = []
        self.redo_stack = []

    def snapshot(self):
        return CompositionState(self.entries, self.background_mode, self.background_color, self.padding)

    def export_rect(self):
        bounds = QRectF()
        for entry in self.entries:
            bounds = bounds.united(entry.bounds())
        return pixel_envelope(bounds, self.padding)

    def _finish(self, label, before):
        after = self.snapshot()
        if before == after:
            return
        self.undo_stack.append(CompositionCommand(label, before, after))
        self.redo_stack.clear()
        self.changed.emit()

    def _restore(self, state):
        self.entries = state.entries
        self.background_mode = state.background_mode
        self.background_color = state.background_color
        self.padding = state.padding
        self.changed.emit()

    def add(self, selection, x, y):
        before = self.snapshot()
        entry = CompositionEntry(uuid4().hex, selection, x, y, 0.0,
                                 max((e.z for e in self.entries), default=0) + 1)
        self.entries += (entry,)
        self._finish('添加选区', before)
        return entry.id

    def remove(self, ids):
        before = self.snapshot()
        self.entries = tuple(e for e in self.entries if e.id not in ids)
        self._finish('删除选区', before)

    def clear(self):
        before = self.snapshot()
        self.entries = ()
        self._finish('清空画布', before)

    def move(self, positions):
        before = self.snapshot()
        self.entries = tuple(replace(e, x=positions[e.id][0], y=positions[e.id][1])
                             if e.id in positions else e for e in self.entries)
        self._finish('移动选区', before)

    def rotate(self, entry_id, angle):
        before = self.snapshot()
        self.entries = tuple(replace(e, rotation=angle) if e.id == entry_id else e
                             for e in self.entries)
        self._finish('旋转选区', before)

    def change_layer(self, ids, mode):
        before = self.snapshot()
        ordered = sorted(self.entries, key=lambda e: e.z)
        if mode == 'top':
            ordered = [e for e in ordered if e.id not in ids] + [e for e in ordered if e.id in ids]
        elif mode == 'bottom':
            ordered = [e for e in ordered if e.id in ids] + [e for e in ordered if e.id not in ids]
        elif mode == 'up':
            for i in range(len(ordered) - 2, -1, -1):
                if ordered[i].id in ids and ordered[i + 1].id not in ids:
                    ordered[i], ordered[i + 1] = ordered[i + 1], ordered[i]
        elif mode == 'down':
            for i in range(1, len(ordered)):
                if ordered[i].id in ids and ordered[i - 1].id not in ids:
                    ordered[i], ordered[i - 1] = ordered[i - 1], ordered[i]
        self.entries = tuple(replace(e, z=i) for i, e in enumerate(ordered))
        self._finish('调整层级', before)

    def set_background(self, mode, color):
        before = self.snapshot()
        self.background_mode, self.background_color = mode, color
        self._finish('背景设置', before)

    def set_padding(self, value):
        before = self.snapshot()
        self.padding = value
        self._finish('导出边距', before)

    def undo(self):
        command = self.undo_stack.pop()
        self.redo_stack.append(command)
        self._restore(command.before)
        return command.label

    def redo(self):
        command = self.redo_stack.pop()
        self.undo_stack.append(command)
        self._restore(command.after)
        return command.label

    def clear_history_and_content(self):
        self.entries = ()
        self.undo_stack.clear()
        self.redo_stack.clear()


def pixel_envelope(bounds, padding):
    left, top = floor(bounds.left()) - padding, floor(bounds.top()) - padding
    right, bottom = ceil(bounds.right()) + padding, ceil(bounds.bottom()) + padding
    return QRectF(left, top, right - left, bottom - top)
