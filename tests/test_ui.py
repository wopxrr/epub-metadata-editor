"""UI tests for Fitur 2 — PyQt6 MainWindow."""
import io
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow


# Ensure QApplication singleton exists
_app = QApplication.instance() or QApplication(sys.argv)


def _build_test_epub(**kwargs) -> bytes:
    """Return raw EPUB bytes."""
    buf = io.BytesIO()
    z = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)
    z.writestr("mimetype", "application/epub+zip")
    container = (
        '<?xml version="1.0"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        '  <rootfiles>\n'
        '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
        '  </rootfiles>\n'
        '</container>\n'
    )
    z.writestr("META-INF/container.xml", container)

    # Allow kwargs to override specific fields; default values below
    title = kwargs.get("title", "Python EPUB")
    creator = kwargs.get("creator", "Test Author")
    language = kwargs.get("language", "en")
    identifier = kwargs.get("identifier", "urn:test:002")
    description = kwargs.get("description", "Testing UI.")
    publisher = kwargs.get("publisher", "PyTest Press")
    date = kwargs.get("date", "2025-06-01")
    rights = kwargs.get("rights", "CC0")
    subject = kwargs.get("subject", "Testing")
    cover_id = kwargs.get("cover_id", "cover-id")
    version = kwargs.get("version", "2.0")

    opf = (
        f'<?xml version="1.0"?>\n'
        f'<package xmlns="http://www.idpf.org/2007/opf" '
        f'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        f'version="{version}" unique-identifier="bookid">\n'
        f'  <metadata>\n'
        f'    <dc:title>{title}</dc:title>\n'
        f'    <dc:creator>{creator}</dc:creator>\n'
        f'    <dc:language>{language}</dc:language>\n'
        f'    <dc:identifier>{identifier}</dc:identifier>\n'
        f'    <dc:description>{description}</dc:description>\n'
        f'    <dc:publisher>{publisher}</dc:publisher>\n'
        f'    <dc:date>{date}</dc:date>\n'
        f'    <dc:rights>{rights}</dc:rights>\n'
        f'    <dc:subject>{subject}</dc:subject>\n'
        f'    <meta name="cover" content="{cover_id}"/>\n'
        f'  </metadata>\n'
        f'  <manifest/>\n'
        f'  <spine/>\n'
        f'</package>\n'
    )
    z.writestr("OEBPS/content.opf", opf)
    z.close()
    return buf.getvalue()


class TestMainWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _app

    def setUp(self):
        self.win = MainWindow()

    def tearDown(self):
        self.win.close()

    def test_window_title(self):
        self.assertEqual(self.win.windowTitle(), "EPUB Metadata Editor")

    def test_fields_disabled_initially(self):
        self.assertFalse(self.win.ed_title.isEnabled())
        self.assertFalse(self.win.ed_version.isEnabled())

    def test_load_epub_populates_fields(self):
        data = _build_test_epub()
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            self.win._load_epub(tmp_path)

            self.assertTrue(self.win.ed_title.isEnabled())
            self.assertEqual(self.win.ed_title.text(), "Python EPUB")
            self.assertEqual(self.win.ed_creators.text(), "Test Author")
            self.assertEqual(self.win.ed_language.currentText(), "en — English")
            self.assertEqual(self.win._collect_identifiers(), ["urn:test:002"])
            self.assertEqual(self.win.ed_publisher.text(), "PyTest Press")
            self.assertEqual(self.win.ed_date.text(), "2025-06-01")
            self.assertEqual(self.win.ed_subjects.text(), "Testing")
            self.assertEqual(self.win.ed_version.text(), "2.0")
            self.assertEqual(
                self.win.ed_description.toPlainText(), "Testing UI."
            )
            self.assertTrue(self.win.file_bar.text().endswith(".epub"))
        finally:
            self.win.handler.close()
            os.remove(tmp_path)

    def test_drag_drop_accept_epub(self):
        # Verify dragEnter accepts EPUB mime data
        from PyQt6.QtCore import QMimeData, QUrl
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile("/fake/test.epub")])
        # QTest.dragEnter does not exist; call event manually via dragEnterEvent
        # We can construct the event and call the handler directly
        from PyQt6.QtGui import QDragEnterEvent
        from PyQt6.QtCore import QPoint
        event = QDragEnterEvent(QPoint(0, 0), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.win.dragEnterEvent(event)
        self.assertTrue(event.isAccepted())

    def test_drag_drop_reject_non_epub(self):
        from PyQt6.QtCore import QMimeData, QUrl
        from PyQt6.QtGui import QDragEnterEvent
        from PyQt6.QtCore import QPoint
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile("/fake/test.pdf")])
        event = QDragEnterEvent(QPoint(0, 0), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.win.dragEnterEvent(event)
        self.assertFalse(event.isAccepted())

    def test_fields_editable_after_load(self):
        data = _build_test_epub()
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            self.win._load_epub(tmp_path)
            self.assertFalse(self.win.ed_title.isReadOnly())
            self.assertFalse(self.win.ed_description.isReadOnly())
            self.win.handler.close()
        finally:
            os.remove(tmp_path)

    def test_typing_triggers_changed_flag(self):
        data = _build_test_epub()
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            self.win._load_epub(tmp_path)
            self.assertFalse(self.win.changed)
            self.win.ed_title.setText("New Title")
            self.assertTrue(self.win.changed)
            self.win.handler.close()
        finally:
            os.remove(tmp_path)

    def test_save_button_enabled_on_change(self):
        data = _build_test_epub()
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            self.win._load_epub(tmp_path)
            self.assertFalse(self.win.save_btn.isEnabled())
            self.win.ed_title.setText("X")
            self.assertTrue(self.win.save_btn.isEnabled())
            self.win.handler.close()
        finally:
            os.remove(tmp_path)

    def test_save_round_trip(self):
        data = _build_test_epub(title="Original")
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            self.win._load_epub(tmp_path)
            self.win.ed_title.setText("Modified")
            self.win._on_save()
            self.assertFalse(self.win.changed)

            # Re-open same file in fresh window
            win2 = MainWindow()
            win2._load_epub(tmp_path)
            self.assertEqual(win2.ed_title.text(), "Modified")
            win2.handler.close()
            win2.close()
            self.win.handler.close()
        finally:
            os.remove(tmp_path)


    def test_language_code_extraction(self):
        self.win.ed_language.setCurrentText("id — Indonesia (Bahasa Indonesia)")
        self.assertEqual(self.win._language_code_from_ui(), "id")
        self.win.ed_language.setCurrentText("fr")
        self.assertEqual(self.win._language_code_from_ui(), "fr")

    def test_opf_button_enabled_after_load(self):
        data = _build_test_epub()
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            self.win._load_epub(tmp_path)
            self.assertTrue(self.win.edit_opf_btn.isEnabled())
            self.win.handler.close()
        finally:
            os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
