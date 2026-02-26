"""Main application window for PDF preview and page navigation."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QToolBar,
)

from app.model.document import PdfDocument
from app.pdf.loader import PdfLoadError, load_pdf
from app.pdf.renderer import PdfRenderError, render_page_image


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PDF Form Builder")
        self.resize(1200, 800)

        self._document: PdfDocument | None = None
        self._current_page_index = 0
        self._zoom = 1.25

        self.page_list = QListWidget()
        self.page_list.currentRowChanged.connect(self._on_page_selected)

        self.page_label = QLabel("Open a PDF to begin")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setMinimumSize(400, 400)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.page_label)

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

        prev_action = QAction("Previous", self)
        prev_action.triggered.connect(self.show_previous_page)
        toolbar.addAction(prev_action)

        next_action = QAction("Next", self)
        next_action.triggered.connect(self.show_next_page)
        toolbar.addAction(next_action)

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

        self._current_page_index = 0
        self._populate_page_list()
        self._render_current_page()
        self.statusBar().showMessage(f"Loaded: {file_path}")

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

    def _render_current_page(self) -> None:
        if self._document is None:
            self.page_label.setText("Open a PDF to begin")
            return

        try:
            image = render_page_image(
                self._document.handle,
                self._current_page_index,
                zoom=self._zoom,
            )
        except PdfRenderError as exc:
            QMessageBox.critical(self, "Render Failed", str(exc))
            return

        pixmap = QPixmap.fromImage(image)
        self.page_label.setPixmap(pixmap)
        self.page_label.adjustSize()
        self.statusBar().showMessage(
            f"Page {self._current_page_index + 1}/{self._document.page_count}"
        )

    def _close_document(self) -> None:
        if self._document is not None:
            self._document.close()
            self._document = None
            self.page_list.clear()
            self.page_label.clear()
            self.page_label.setText("Open a PDF to begin")
