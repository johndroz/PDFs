"""Interactive PDF page canvas for field placement and dragging."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from app.model.field import FieldType, FormField


@dataclass(slots=True)
class PageMetrics:
    width_pt: float
    height_pt: float


class PdfCanvas(QWidget):
    field_selection_changed = Signal(object)
    fields_changed = Signal()
    field_created = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._pixmap: QPixmap | None = None
        self._metrics: PageMetrics | None = None
        self._fields: list[FormField] = []
        self._placement_type: FieldType | None = None
        self._selected_index: int | None = None
        self._drag_offset_px: QPointF | None = None
        self._interaction: str | None = None
        self._resize_start: QPointF | None = None
        self._resize_start_size: tuple[float, float] | None = None

        self.setMouseTracking(True)
        self.setMinimumSize(500, 600)

    def set_page(
        self,
        pixmap: QPixmap,
        fields: list[FormField],
        metrics: PageMetrics,
    ) -> None:
        self._pixmap = pixmap
        self._fields = fields
        self._metrics = metrics
        self._selected_index = None
        self._drag_offset_px = None
        self._interaction = None
        self._resize_start = None
        self._resize_start_size = None
        self.field_selection_changed.emit(None)
        self.resize(pixmap.size())
        self.update()

    def clear_page(self) -> None:
        self._pixmap = None
        self._fields = []
        self._metrics = None
        self._selected_index = None
        self._drag_offset_px = None
        self._interaction = None
        self._resize_start = None
        self._resize_start_size = None
        self.resize(500, 600)
        self.update()

    def set_placement_type(self, field_type: FieldType | None) -> None:
        self._placement_type = field_type

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#e9eaee"))

        if self._pixmap is None or self._metrics is None:
            return

        painter.drawPixmap(0, 0, self._pixmap)
        for index, field in enumerate(self._fields):
            rect_px = self._field_rect_to_pixels(field)
            color = QColor("#c62828") if index == self._selected_index else QColor("#1565c0")
            pen = QPen(color)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(rect_px)
            if index == self._selected_index:
                painter.fillRect(self._resize_handle_rect(rect_px), QColor("#c62828"))

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if self._pixmap is None or self._metrics is None:
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._placement_type is not None:
            self._create_field_at(event.position())
            return

        clicked_index = self._field_index_at(event.position())
        self._selected_index = clicked_index
        selected = self._fields[clicked_index] if clicked_index is not None else None
        self.field_selection_changed.emit(selected)

        if clicked_index is not None:
            rect = self._field_rect_to_pixels(self._fields[clicked_index])
            if self._resize_handle_rect(rect).contains(event.position()):
                self._interaction = "resize"
                self._resize_start = event.position()
                field = self._fields[clicked_index]
                self._resize_start_size = (field.width, field.height)
            else:
                self._interaction = "move"
                self._drag_offset_px = event.position() - rect.topLeft()

        self.update()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._selected_index is None or self._metrics is None:
            return

        field = self._fields[self._selected_index]
        sx, sy = self._scale_factors()

        if self._interaction == "move":
            offset = self._drag_offset_px or QPointF(0, 0)
            top_left_px = event.position() - offset

            x_px = max(0.0, min(top_left_px.x(), float(self.width())))
            y_px = max(0.0, min(top_left_px.y(), float(self.height())))

            field.x = x_px / sx
            field.y = self._metrics.height_pt - (y_px / sy) - field.height

            max_x = max(0.0, self._metrics.width_pt - field.width)
            max_y = max(0.0, self._metrics.height_pt - field.height)
            field.x = max(0.0, min(field.x, max_x))
            field.y = max(0.0, min(field.y, max_y))
            self.fields_changed.emit()
            self.update()
        elif self._interaction == "resize":
            if self._resize_start is None or self._resize_start_size is None:
                return
            dx_pt = (event.position().x() - self._resize_start.x()) / sx
            dy_pt = (event.position().y() - self._resize_start.y()) / sy
            start_w, start_h = self._resize_start_size

            min_w_pt = 7.0 / max(sx, 1e-9)
            min_h_pt = 7.0 / max(sy, 1e-9)
            if field.field_type is FieldType.CHECKBOX:
                min_side_pt = max(min_w_pt, min_h_pt)
                side = max(start_w + dx_pt, start_h + dy_pt, min_side_pt)
                max_side = min(self._metrics.width_pt - field.x, self._metrics.height_pt - field.y)
                side = max(min_side_pt, min(side, max_side))
                field.width = side
                field.height = side
            else:
                new_w = max(min_w_pt, start_w + dx_pt)
                new_h = max(min_h_pt, start_h + dy_pt)
                field.width = min(new_w, self._metrics.width_pt - field.x)
                field.height = min(new_h, self._metrics.height_pt - field.y)
            self.fields_changed.emit()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        del event
        self._interaction = None
        self._drag_offset_px = None
        self._resize_start = None
        self._resize_start_size = None

    def delete_selected_field(self) -> bool:
        if self._selected_index is None:
            return False
        self._fields.pop(self._selected_index)
        self._selected_index = None
        self._interaction = None
        self._drag_offset_px = None
        self._resize_start = None
        self._resize_start_size = None
        self.field_selection_changed.emit(None)
        self.fields_changed.emit()
        self.update()
        return True

    def duplicate_selected_field(self) -> bool:
        if self._selected_index is None or self._metrics is None:
            return False

        source = self._fields[self._selected_index]
        duplicate = deepcopy(source)
        duplicate.name = ""

        offset = 12.0
        max_x = max(0.0, self._metrics.width_pt - duplicate.width)
        max_y = max(0.0, self._metrics.height_pt - duplicate.height)
        duplicate.x = min(source.x + offset, max_x)
        duplicate.y = min(source.y + offset, max_y)

        self._fields.append(duplicate)
        self._selected_index = len(self._fields) - 1
        self.field_selection_changed.emit(duplicate)
        self.fields_changed.emit()
        self.update()
        return True

    def _create_field_at(self, pos: QPointF) -> None:
        if self._metrics is None or self._placement_type is None:
            return

        default_w = 140.0 if self._placement_type is FieldType.TEXT else 18.0
        default_h = 24.0 if self._placement_type is FieldType.TEXT else 18.0

        sx, sy = self._scale_factors()
        x_pt = pos.x() / sx
        y_top_pt = self._metrics.height_pt - (pos.y() / sy)
        y_pt = y_top_pt - default_h

        max_x = max(0.0, self._metrics.width_pt - default_w)
        max_y = max(0.0, self._metrics.height_pt - default_h)
        x_pt = max(0.0, min(x_pt, max_x))
        y_pt = max(0.0, min(y_pt, max_y))

        field = FormField(
            page_index=-1,
            name="",
            field_type=self._placement_type,
            x=x_pt,
            y=y_pt,
            width=default_w,
            height=default_h,
            checked=False,
        )
        self._fields.append(field)
        self._selected_index = len(self._fields) - 1
        self.field_selection_changed.emit(field)
        self.fields_changed.emit()
        self.field_created.emit()
        self.update()

    def _field_rect_to_pixels(self, field: FormField) -> QRectF:
        sx, sy = self._scale_factors()
        left = field.x * sx
        top = (self._metrics.height_pt - (field.y + field.height)) * sy
        width = field.width * sx
        height = field.height * sy
        return QRectF(left, top, width, height)

    def _resize_handle_rect(self, field_rect: QRectF) -> QRectF:
        handle_size = 10.0
        return QRectF(
            field_rect.right() - handle_size / 2.0,
            field_rect.bottom() - handle_size / 2.0,
            handle_size,
            handle_size,
        )

    def _field_index_at(self, pos: QPointF) -> int | None:
        for index in range(len(self._fields) - 1, -1, -1):
            if self._field_rect_to_pixels(self._fields[index]).contains(pos):
                return index
        return None

    def _scale_factors(self) -> tuple[float, float]:
        if self._pixmap is None or self._metrics is None:
            return 1.0, 1.0
        sx = self._pixmap.width() / self._metrics.width_pt
        sy = self._pixmap.height() / self._metrics.height_pt
        return sx, sy
