"""Simple modal dialog for editing raw XML/text files inside an EPUB."""
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QLabel,
    QMessageBox,
)


class TextEditorDialog(QDialog):
    """A minimal text editor for modifying auxiliary EPUB files (TOC, page-map, etc.)."""

    def __init__(self, title: str = "Edit File", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.path_lbl = QLabel("File: —")
        self.path_lbl.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.path_lbl)

        self.editor = QPlainTextEdit()
        font = self.editor.font()
        font.setFamily("Consolas, Courier New, monospace")
        font.setPointSize(10)
        self.editor.setFont(font)
        layout.addWidget(self.editor)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()

        layout.addLayout(btn_row)

        self._original_text: str = ""

    def set_content(self, text: str, path: str = "") -> None:
        """Load text into the editor and remember it as the original."""
        self._original_text = text
        self.editor.setPlainText(text)
        self.path_lbl.setText(f"File: {path}")

    def get_content(self) -> str:
        """Return the current editor text."""
        return self.editor.toPlainText()

    def _on_save(self) -> None:
        current = self.editor.toPlainText()
        if current == self._original_text:
            # No changes — just close
            self.accept()
            return

        reply = QMessageBox.question(
            self,
            "Confirm Save",
            "Save changes to the EPUB?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.accept()
