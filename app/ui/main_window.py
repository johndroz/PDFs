"""Main application window for PDF preview, placement, and export."""

from __future__ import annotations

from pathlib import Path
import shutil

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QToolBar,
)

from app.model.document import PdfDocument
from app.model.field import FieldType
from app.pdf.importer import PdfImportError, import_pdf_fields
from app.pdf.loader import PdfLoadError, load_pdf
from app.pdf.renderer import PdfRenderError, render_page_image
from app.pdf.writer import PdfWriteError, write_pdf_with_fields
from app.state.session import DocumentSession
from app.viewer.canvas import PageMetrics, PdfCanvas


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PDF Form Builder")
        self.resize(1300, 850)

        self._document: PdfDocument | None = None
        self._session = DocumentSession()
        self._current_page_index = 0
        self._zoom = 1.25
        self._field_counter = 1

        self.page_list = QListWidget()
        self.page_list.currentRowChanged.connect(self._on_page_selected)

        self.canvas = PdfCanvas()
        self.canvas.fields_changed.connect(self._on_canvas_fields_changed)
        self.canvas.field_created.connect(self._on_canvas_field_created)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.canvas)

        splitter = QSplitter()
        splitter.addWidget(self.page_list)
        splitter.addWidget(self.scroll_area)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        self.setCentralWidget(splitter)

        self._build_toolbar()
        self.statusBar().showMessage("Ready")

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        open_action = QAction("Open PDF", self)
        open_action.triggered.connect(self.open_pdf)
        toolbar.addAction(open_action)

        save_action = QAction("Save As", self)
        save_action.triggered.connect(self.save_pdf)
        toolbar.addAction(save_action)

        delete_action = QAction("Delete Field", self)
        delete_action.triggered.connect(self.delete_selected_field)
        toolbar.addAction(delete_action)

        copy_action = QAction("Copy Field", self)
        copy_action.setShortcut("Ctrl+D")
        copy_action.triggered.connect(self.copy_selected_field)
        toolbar.addAction(copy_action)

        toolbar.addSeparator()

        prev_action = QAction("Previous", self)
        prev_action.triggered.connect(self.show_previous_page)
        toolbar.addAction(prev_action)

        next_action = QAction("Next", self)
        next_action.triggered.connect(self.show_next_page)
        toolbar.addAction(next_action)

        toolbar.addSeparator()

        mode_group = QActionGroup(self)
        mode_group.setExclusive(True)

        self._pointer_action = QAction("Pointer", self)
        self._pointer_action.setCheckable(True)
        self._pointer_action.setChecked(True)
        self._pointer_action.triggered.connect(lambda: self._set_mode(None))
        mode_group.addAction(self._pointer_action)
        toolbar.addAction(self._pointer_action)

        text_action = QAction("Add Text", self)
        text_action.setCheckable(True)
        text_action.triggered.connect(lambda: self._set_mode(FieldType.TEXT))
        mode_group.addAction(text_action)
        toolbar.addAction(text_action)

        checkbox_action = QAction("Add Checkbox", self)
        checkbox_action.setCheckable(True)
        checkbox_action.triggered.connect(lambda: self._set_mode(FieldType.CHECKBOX))
        mode_group.addAction(checkbox_action)
        toolbar.addAction(checkbox_action)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._close_document()
        super().closeEvent(event)

    def open_pdf(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF",
            str(Path.home()),
            "PDF Files (*.pdf)",
        )
        if not file_path:
            return

        self._close_document()
        try:
            self._document = load_pdf(file_path)
        except PdfLoadError as exc:
            QMessageBox.critical(self, "Open Failed", str(exc))
            return

        self._session = DocumentSession()
        self._field_counter = 1
        try:
            for field in import_pdf_fields(self._document.working_path):
                self._session.fields_by_page.setdefault(field.page_index, []).append(field)
        except PdfImportError as exc:
            QMessageBox.warning(self, "Field Import Warning", str(exc))
        self._sync_field_counter()
        self._current_page_index = 0
        self._populate_page_list()
        self._render_current_page()
        self.statusBar().showMessage(f"Loaded: {file_path} (editing temp working copy)")

    def save_pdf(self) -> None:
        if self._document is None:
            QMessageBox.information(self, "No Document", "Open a PDF first.")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Output PDF",
            str(self._document.path.with_stem(f"{self._document.path.stem}_fillable")),
            "PDF Files (*.pdf)",
        )
        if not output_path:
            return

        self._document.close_handle()
        try:
            write_pdf_with_fields(
                source_path=self._document.working_path,
                output_path=self._document.working_path,
                fields=self._session.all_fields(),
            )
            shutil.copy2(self._document.working_path, output_path)
        except (PdfWriteError, OSError) as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            self._document.reopen_handle()
            return
        self._document.reopen_handle()
        self._render_current_page()

        self.statusBar().showMessage(f"Saved: {output_path}")

    def show_previous_page(self) -> None:
        if self._document is None or self._current_page_index <= 0:
            return
        self._current_page_index -= 1
        self.page_list.setCurrentRow(self._current_page_index)

    def show_next_page(self) -> None:
        if self._document is None:
            return
        if self._current_page_index >= self._document.page_count - 1:
            return
        self._current_page_index += 1
        self.page_list.setCurrentRow(self._current_page_index)

    def delete_selected_field(self) -> None:
        if self._document is None:
            return
        if self.canvas.delete_selected_field():
            count = len(self._session.get_page_fields(self._current_page_index))
            self.statusBar().showMessage(
                f"Deleted field. Page {self._current_page_index + 1}: {count} field(s)"
            )
        else:
            self.statusBar().showMessage("No selected field to delete.")

    def copy_selected_field(self) -> None:
        if self._document is None:
            return
        if self.canvas.duplicate_selected_field():
            count = len(self._session.get_page_fields(self._current_page_index))
            self.statusBar().showMessage(
                f"Copied field. Page {self._current_page_index + 1}: {count} field(s)"
            )
        else:
            self.statusBar().showMessage("No selected field to copy.")

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected_field()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_selected_field()
            event.accept()
            return
        super().keyPressEvent(event)

    def _set_mode(self, mode: FieldType | None) -> None:
        self.canvas.set_placement_type(mode)
        label = "Pointer mode" if mode is None else f"Placement mode: {mode.value}"
        self.statusBar().showMessage(label)

    def _populate_page_list(self) -> None:
        self.page_list.clear()
        if self._document is None:
            return

        for page_number in range(1, self._document.page_count + 1):
            item = QListWidgetItem(f"Page {page_number}")
            self.page_list.addItem(item)

        self.page_list.setCurrentRow(0)

    def _on_page_selected(self, row: int) -> None:
        if self._document is None or row < 0:
            return

        self._current_page_index = row
        self._render_current_page()

    def _on_canvas_fields_changed(self) -> None:
        current_fields = self._session.get_page_fields(self._current_page_index)
        for field in current_fields:
            if field.page_index < 0:
                field.page_index = self._current_page_index
            if not field.name:
                field.name = self._next_field_name(field.field_type)
        self.statusBar().showMessage(
            f"Page {self._current_page_index + 1}: {len(current_fields)} field(s)"
        )

    def _on_canvas_field_created(self) -> None:
        self._pointer_action.setChecked(True)
        self._set_mode(None)

    def _next_field_name(self, field_type: FieldType) -> str:
        prefix = "text" if field_type is FieldType.TEXT else "checkbox"
        name = f"{prefix}_{self._field_counter}"
        self._field_counter += 1
        return name

    def _sync_field_counter(self) -> None:
        highest = 0
        for field in self._session.all_fields():
            parts = field.name.rsplit("_", maxsplit=1)
            if len(parts) != 2:
                continue
            try:
                value = int(parts[1])
            except ValueError:
                continue
            highest = max(highest, value)
        self._field_counter = highest + 1

    def _render_current_page(self) -> None:
        if self._document is None:
            self.canvas.clear_page()
            return

        try:
            image = render_page_image(
                self._document.handle,
                self._current_page_index,
                zoom=self._zoom,
            )
            page = self._document.handle.load_page(self._current_page_index)
        except PdfRenderError as exc:
            QMessageBox.critical(self, "Render Failed", str(exc))
            return

        pixmap = QPixmap.fromImage(image)
        metrics = PageMetrics(width_pt=float(page.rect.width), height_pt=float(page.rect.height))

        page_fields = self._session.fields_by_page.setdefault(self._current_page_index, [])
        self.canvas.set_page(pixmap=pixmap, fields=page_fields, metrics=metrics)
        self.statusBar().showMessage(
            f"Page {self._current_page_index + 1}/{self._document.page_count}"
        )

    def _close_document(self) -> None:
        if self._document is not None:
            self._document.close()
            self._document = None
        self._session = DocumentSession()
        self.page_list.clear()
        self.canvas.clear_page()
