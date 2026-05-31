"""Unit tests for EpubHandler — Fitur 1: Baca EPUB."""
import io
import os
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from epub_handler import EpubHandler
from metadata import EpubMetadata


def _build_minimal_epub(
    title: str = "Test Title",
    creator: str = "Test Author",
    language: str = "en",
    identifier: str = "urn:test:001",
    description: str = "A test book.",
    publisher: str = "Test Publisher",
    date: str = "2024-01-01",
    rights: str = "Public Domain",
    subject: str = "Fiction",
    cover_id: str = "cover-img",
    version: str = "2.0",
) -> io.BytesIO:
    """Construct an in-memory EPUB with basic metadata."""
    buf = io.BytesIO()
    z = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)

    # mimetype (must be first, uncompressed)
    z.writestr("mimetype", "application/epub+zip")

    # container.xml
    container = (
        '<?xml version="1.0"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        '  <rootfiles>\n'
        '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
        '  </rootfiles>\n'
        '</container>\n'
    )
    z.writestr("META-INF/container.xml", container)

    # content.opf
    opf = (
        f'<?xml version="1.0"?>\n'
        f'<package xmlns="http://www.idpf.org/2007/opf" '
        f'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        f'version="{version}" unique-identifier="bookid">\n'
        f'  <metadata>\n'
        f'    <dc:title>{title}</dc:title>\n'
        f'    <dc:creator>{creator}</dc:creator>\n'
        f'    <dc:language>{language}</dc:language>\n'
        f'    <dc:identifier id="bookid">{identifier}</dc:identifier>\n'
        f'    <dc:description>{description}</dc:description>\n'
        f'    <dc:publisher>{publisher}</dc:publisher>\n'
        f'    <dc:date>{date}</dc:date>\n'
        f'    <dc:rights>{rights}</dc:rights>\n'
        f'    <dc:subject>{subject}</dc:subject>\n'
        f'    <meta name="cover" content="{cover_id}"/>\n'
        f'  </metadata>\n'
        f'  <manifest>\n'
        f'    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n'
        f'  </manifest>\n'
        f'  <spine toc="ncx">\n'
        f'    <itemref idref="ncx"/>\n'
        f'  </spine>\n'
        f'</package>\n'
    )
    z.writestr("OEBPS/content.opf", opf)

    # Dummy toc.ncx
    toc = (
        '<?xml version="1.0"?>\n'
        '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/">\n'
        '  <head>\n'
        '    <meta name="dtb:uid" content="test"/>\n'
        '  </head>\n'
        '</ncx>\n'
    )
    z.writestr("OEBPS/toc.ncx", toc)

    z.close()
    buf.seek(0)
    return buf


class TestEpubHandler(unittest.TestCase):
    def test_open_and_read_metadata(self):
        epub_buf = _build_minimal_epub()
        # Write to temp file so ZipFile can open it
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            tmp.write(epub_buf.read())
            tmp_path = tmp.name

        try:
            handler = EpubHandler()
            handler.open_epub(tmp_path)
            meta = handler.get_metadata()

            self.assertEqual(meta.title, "Test Title")
            self.assertEqual(meta.creators, ["Test Author"])
            self.assertEqual(meta.language, "en")
            self.assertEqual(meta.identifiers, ["urn:test:001"])
            self.assertEqual(meta.description, "A test book.")
            self.assertEqual(meta.publisher, "Test Publisher")
            self.assertEqual(meta.date, "2024-01-01")
            self.assertEqual(meta.rights, "Public Domain")
            self.assertEqual(meta.subjects, ["Fiction"])
            self.assertEqual(meta.cover_id, "cover-img")
            self.assertEqual(meta.version, "2.0")
        finally:
            handler.close()
            os.remove(tmp_path)

    def test_missing_opf_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            z = zipfile.ZipFile(tmp, "w")
            z.writestr("random.txt", "hello")
            z.close()
            tmp_path = tmp.name

        handler = EpubHandler()
        with self.assertRaises(FileNotFoundError):
            handler.open_epub(tmp_path)
        handler.close()
        os.remove(tmp_path)

    def test_multiple_creators_and_subjects(self):
        epub_buf = _build_minimal_epub()
        # We need to build a custom OPF with multiple creators
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
        opf = (
            '<?xml version="1.0"?>\n'
            '<package xmlns="http://www.idpf.org/2007/opf" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'version="3.0" unique-identifier="bookid">\n'
            '  <metadata>\n'
            '    <dc:title>Multi</dc:title>\n'
            '    <dc:creator>Alice</dc:creator>\n'
            '    <dc:creator>Bob</dc:creator>\n'
            '    <dc:language>id</dc:language>\n'
            '    <dc:identifier>id1</dc:identifier>\n'
            '    <dc:identifier>id2</dc:identifier>\n'
            '    <dc:subject>Sci-Fi</dc:subject>\n'
            '    <dc:subject>Adventure</dc:subject>\n'
            '  </metadata>\n'
            '  <manifest/>\n'
            '  <spine/>\n'
            '</package>\n'
        )
        z.writestr("OEBPS/content.opf", opf)
        z.close()
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            tmp.write(buf.read())
            tmp_path = tmp.name

        handler = EpubHandler()
        handler.open_epub(tmp_path)
        meta = handler.get_metadata()
        self.assertEqual(meta.creators, ["Alice", "Bob"])
        self.assertEqual(meta.subjects, ["Sci-Fi", "Adventure"])
        self.assertEqual(meta.version, "3.0")
        handler.close()
        os.remove(tmp_path)

    def test_save_metadata_round_trip(self):
        data = _build_minimal_epub(title="Old Title", creator="Old Author")
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            tmp.write(data.read())
            tmp_path = tmp.name

        try:
            handler = EpubHandler()
            handler.open_epub(tmp_path)

            # Modify metadata
            handler.metadata.title = "New Title"
            handler.metadata.creators = ["New Author", "Co Author"]
            handler.metadata.language = "id"
            handler.metadata.description = "New desc"
            handler.metadata.publisher = "New Pub"
            handler.metadata.date = "2026-05-29"
            handler.metadata.rights = "GPL"
            handler.metadata.subjects = ["A", "B"]
            handler.metadata.cover_id = "new-cover"

            handler.save_metadata()
            handler.close()

            # Re-open and verify
            handler2 = EpubHandler()
            handler2.open_epub(tmp_path)
            meta = handler2.get_metadata()

            self.assertEqual(meta.title, "New Title")
            self.assertEqual(meta.creators, ["New Author", "Co Author"])
            self.assertEqual(meta.language, "id")
            self.assertEqual(meta.description, "New desc")
            self.assertEqual(meta.publisher, "New Pub")
            self.assertEqual(meta.date, "2026-05-29")
            self.assertEqual(meta.rights, "GPL")
            self.assertEqual(meta.subjects, ["A", "B"])
            self.assertEqual(meta.cover_id, "new-cover")
            handler2.close()
        finally:
            os.remove(tmp_path)


    def test_get_cover_image_bytes(self):
        """Build an EPUB with a dummy cover image and retrieve it."""
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

        fake_image = b"FAKE_IMAGE_BYTES"
        opf = (
            '<?xml version="1.0"?>\n'
            '<package xmlns="http://www.idpf.org/2007/opf" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">\n'
            '  <metadata>\n'
            '    <dc:title>T</dc:title>\n'
            '    <meta name="cover" content="cover-id"/>\n'
            '  </metadata>\n'
            '  <manifest>\n'
            '    <item id="cover-id" href="cover.jpg" media-type="image/jpeg"/>\n'
            '  </manifest>\n'
            '  <spine/>\n'
            '</package>\n'
        )
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/cover.jpg", fake_image)
        z.close()
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            tmp.write(buf.read())
            tmp_path = tmp.name

        handler = EpubHandler()
        try:
            handler.open_epub(tmp_path)
            img_bytes, mimetype = handler.get_cover_image_bytes()
            self.assertEqual(img_bytes, fake_image)
            self.assertEqual(mimetype, "image/jpeg")
        finally:
            handler.close()
            os.remove(tmp_path)

    def test_set_cover_image(self):
        """Replace cover image inside an EPUB."""
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
        opf = (
            '<?xml version="1.0"?>\n'
            '<package xmlns="http://www.idpf.org/2007/opf" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">\n'
            '  <metadata>\n'
            '    <dc:title>T</dc:title>\n'
            '    <meta name="cover" content="old-cover"/>\n'
            '  </metadata>\n'
            '  <manifest>\n'
            '    <item id="old-cover" href="old.png" media-type="image/png"/>\n'
            '  </manifest>\n'
            '  <spine/>\n'
            '</package>\n'
        )
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/old.png", b"OLD")
        z.close()
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            tmp.write(buf.read())
            tmp_path = tmp.name

        handler = EpubHandler()
        try:
            handler.open_epub(tmp_path)
            new_bytes = b"NEW_IMAGE_DATA"
            handler.set_cover_image(new_bytes, "new.jpg", "image/jpeg")

            # Re-open to verify
            handler2 = EpubHandler()
            handler2.open_epub(tmp_path)
            img_bytes, mimetype = handler2.get_cover_image_bytes()
            self.assertEqual(img_bytes, new_bytes)
            self.assertEqual(mimetype, "image/jpeg")
            self.assertEqual(handler2.metadata.cover_id, "old-cover")
            handler2.close()
        finally:
            handler.close()
            os.remove(tmp_path)


    def test_locate_aux_files_epub2(self):
        """EPUB 2 should detect toc.ncx and page-map.xml."""
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
        opf = (
            '<?xml version="1.0"?>\n'
            '<package xmlns="http://www.idpf.org/2007/opf" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">\n'
            '  <metadata>\n'
            '    <dc:title>T</dc:title>\n'
            '    <dc:language>en</dc:language>\n'
            '  </metadata>\n'
            '  <manifest>\n'
            '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n'
            '  </manifest>\n'
            '  <spine toc="ncx"/>\n'
            '</package>\n'
        )
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/toc.ncx", "<ncx/>")
        z.writestr("OEBPS/page-map.xml", "<page-map/>")
        z.close()
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            tmp.write(buf.read())
            tmp_path = tmp.name

        handler = EpubHandler()
        try:
            handler.open_epub(tmp_path)
            self.assertEqual(handler.toc_path, "OEBPS/toc.ncx")
            self.assertEqual(handler.toc_ncx_path, "OEBPS/toc.ncx")
            self.assertEqual(handler.page_map_path, "OEBPS/page-map.xml")
        finally:
            handler.close()
            os.remove(tmp_path)

    def test_save_aux_file(self):
        """Modify an auxiliary file inside the EPUB."""
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
        opf = (
            '<?xml version="1.0"?>\n'
            '<package xmlns="http://www.idpf.org/2007/opf" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">\n'
            '  <metadata>\n'
            '    <dc:title>T</dc:title>\n'
            '    <dc:language>en</dc:language>\n'
            '  </metadata>\n'
            '  <manifest/>\n'
            '  <spine/>\n'
            '</package>\n'
        )
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/toc.ncx", "<ncx>old</ncx>")
        z.close()
        buf.seek(0)

        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            tmp.write(buf.read())
            tmp_path = tmp.name

        handler = EpubHandler()
        try:
            handler.open_epub(tmp_path)
            handler.save_aux_file("OEBPS/toc.ncx", "<ncx>new</ncx>")

            # Verify via fresh open
            handler2 = EpubHandler()
            handler2.open_epub(tmp_path)
            text = handler2.get_aux_file_text("OEBPS/toc.ncx")
            self.assertEqual(text, "<ncx>new</ncx>")
            handler2.close()
        finally:
            handler.close()
            os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
