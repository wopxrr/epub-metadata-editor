"""Core EPUB handling: open ZIP, find OPF, parse metadata."""
import io
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

try:
    from .metadata import EpubMetadata
except ImportError:
    from metadata import EpubMetadata

# OPF namespace map
_OPF_NS = "http://www.idpf.org/2007/opf"
_DC_NS = "http://purl.org/dc/elements/1.1/"
_CALIBRE_NS = "http://calibre-ebook.com/namespaces/calibre"


def _ns(tag: str, ns: str = _OPF_NS) -> str:
    return f"{{{ns}}}{tag}"


class EpubHandler:
    """Handles reading (and eventually writing) EPUB files."""

    def __init__(self) -> None:
        self.zip_path: Optional[Path] = None
        self.zip_file: Optional[zipfile.ZipFile] = None
        self.opf_path_in_zip: Optional[str] = None
        self.opf_tree: Optional[ET.ElementTree] = None
        self.metadata: EpubMetadata = EpubMetadata()
        self.version: str = ""
        self.toc_path: Optional[str] = None
        self.toc_ncx_path: Optional[str] = None
        self.page_map_path: Optional[str] = None

    def open_epub(self, path: str) -> None:
        """Open an EPUB file and parse its metadata."""
        self.close()
        self.zip_path = Path(path)
        self.zip_file = zipfile.ZipFile(path, "r")
        self._locate_opf()
        self._parse_opf()
        self._locate_aux_files()

    def _locate_opf(self) -> None:
        """Find the OPF file via META-INF/container.xml or by scanning."""
        if self.zip_file is None:
            raise RuntimeError("No ZIP file is open.")

        # Standard way: read container.xml
        container_name = "META-INF/container.xml"
        if container_name in self.zip_file.namelist():
            data = self.zip_file.read(container_name)
            root = ET.fromstring(data)
            # container.xml uses urn:oasis:names:tc:opendocument:xmlns:container
            # but ElementTree parsing with default namespace handling
            rootfile = root.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")
            if rootfile is not None:
                full_path = rootfile.get("full-path")
                if full_path:
                    self.opf_path_in_zip = full_path
                    return

        # Fallback: scan for any .opf file
        for name in self.zip_file.namelist():
            if name.lower().endswith(".opf") and "_macosx" not in name.lower():
                self.opf_path_in_zip = name
                return

        raise FileNotFoundError("No OPF file found inside EPUB.")

    def _parse_opf(self) -> None:
        """Parse the OPF XML and populate self.metadata."""
        if self.zip_file is None or self.opf_path_in_zip is None:
            raise RuntimeError("OPF not located.")

        opf_bytes = self.zip_file.read(self.opf_path_in_zip)
        self.opf_tree = ET.fromstring(opf_bytes)

        root = self.opf_tree
        if root is None:
            raise RuntimeError("Failed to parse OPF XML.")

        # EPUB version from package element
        self.version = root.get("version", "")
        self.metadata.version = self.version

        # Metadata element
        meta_elem = root.find(_ns("metadata"))
        if meta_elem is None:
            raise RuntimeError("<metadata> element missing from OPF.")

        # --- dc:title ---
        title_el = meta_elem.find(_ns("title", _DC_NS))
        if title_el is not None:
            self.metadata.title = title_el.text.strip() if title_el.text else ""
            # EPUB2 style title-sort
            self.metadata.title_sort = title_el.get(f"{{{_OPF_NS}}}file-as", "")

        # --- dc:creator --- (can be multiple)
        creator_els = meta_elem.findall(_ns("creator", _DC_NS))
        self.metadata.creators = [
            el.text.strip()
            for el in creator_els
            if el.text
        ]
        # author sort from first creator
        if creator_els:
            self.metadata.author_sort = creator_els[0].get(f"{{{_OPF_NS}}}file-as", "")

        # --- dc:language ---
        lang_el = meta_elem.find(_ns("language", _DC_NS))
        self.metadata.language = lang_el.text.strip() if lang_el is not None and lang_el.text else ""

        # --- dc:identifier --- (can be multiple, deduplicate)
        seen = set()
        ids = []
        for el in meta_elem.findall(_ns("identifier", _DC_NS)):
            if el.text:
                val = el.text.strip()
                if val and val not in seen:
                    seen.add(val)
                    ids.append(val)
        self.metadata.identifiers = ids

        # --- dc:description ---
        desc_el = meta_elem.find(_ns("description", _DC_NS))
        self.metadata.description = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

        # --- dc:publisher ---
        pub_el = meta_elem.find(_ns("publisher", _DC_NS))
        self.metadata.publisher = pub_el.text.strip() if pub_el is not None and pub_el.text else ""

        # --- dc:date --- (publication date; skip event=modification)
        self.metadata.date = ""
        self.metadata.modification_date = ""
        for date_el in meta_elem.findall(_ns("date", _DC_NS)):
            if date_el.text:
                event = date_el.get("event", "")
                if event == "modification":
                    self.metadata.modification_date = date_el.text.strip()
                elif not self.metadata.date:
                    self.metadata.date = date_el.text.strip()

        # --- dc:rights ---
        rights_el = meta_elem.find(_ns("rights", _DC_NS))
        self.metadata.rights = rights_el.text.strip() if rights_el is not None and rights_el.text else ""

        # --- dc:subject --- (can be multiple)
        self.metadata.subjects = [
            el.text.strip()
            for el in meta_elem.findall(_ns("subject", _DC_NS))
            if el.text
        ]

        # --- calibre & other meta tags ---
        for meta in meta_elem.findall(_ns("meta")):
            name = meta.get("name")
            if name == "cover":
                self.metadata.cover_id = meta.get("content", "")
            elif name == "calibre:series":
                self.metadata.series = meta.get("content", "")
            elif name == "calibre:series_index":
                self.metadata.series_index = meta.get("content", "")
            elif name == "calibre:title_sort":
                self.metadata.title_sort = meta.get("content", "")
            elif name == "calibre:rating":
                self.metadata.rating = meta.get("content", "")
            elif name == "calibre:author_link_map":
                pass

            # EPUB3 meta property style
            prop = meta.get("property")
            if prop == "title-type" and meta.text == "main":
                pass
            elif prop == "belongs-to-collection":
                self.metadata.series = meta.text.strip() if meta.text else ""
            elif prop == "group-position":
                self.metadata.series_index = meta.text.strip() if meta.text else ""
            elif prop == "file-as":
                pass
            elif prop == "dcterms:modified":
                self.metadata.modification_date = meta.text.strip() if meta.text else ""

        # Fallback: EPUB3 often uses properties="cover-image" on manifest item
        if not self.metadata.cover_id:
            manifest = root.find(_ns("manifest"))
            if manifest is not None:
                for item in manifest.findall(_ns("item")):
                    props = item.get("properties", "")
                    if "cover-image" in props.split():
                        self.metadata.cover_id = item.get("id", "")
                        break

    def _locate_aux_files(self) -> None:
        """Find TOC/nav, toc.ncx, and page-map.xml inside the ZIP."""
        if self.zip_file is None or self.opf_tree is None:
            return

        self.toc_path = None
        self.toc_ncx_path = None
        self.page_map_path = None

        # --- EPUB 3: find nav document via manifest properties="nav" ---
        manifest = self.opf_tree.find(_ns("manifest"))
        if manifest is not None:
            for item in manifest.findall(_ns("item")):
                props = item.get("properties", "")
                if "nav" in props.split():
                    href = item.get("href", "")
                    if href:
                        self.toc_path = self._resolve_manifest_href(href)
                    break

        # --- Find toc.ncx (EPUB 2 or EPUB 3 backward-compat) ---
        for name in self.zip_file.namelist():
            if name.lower().endswith(".ncx") and "_macosx" not in name.lower():
                self.toc_ncx_path = name
                break

        # If we didn't find a nav file, fall back to toc.ncx as primary TOC
        if self.toc_path is None and self.toc_ncx_path is not None:
            self.toc_path = self.toc_ncx_path

        # --- Find page-map.xml ---
        for name in self.zip_file.namelist():
            if name.lower().endswith("page-map.xml") and "_macosx" not in name.lower():
                self.page_map_path = name
                break

    def get_aux_file_text(self, path_in_zip: str) -> str:
        """Return decoded text of an auxiliary file inside the ZIP."""
        if self.zip_file is None:
            raise RuntimeError("No EPUB is open.")
        raw = self.zip_file.read(path_in_zip)
        # Try UTF-8 first, then fall back to latin-1 (never fails)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1")

    def save_aux_file(self, path_in_zip: str, text: str) -> None:
        """Rewrite the EPUB ZIP in-place, replacing one auxiliary file."""
        if self.zip_file is None:
            raise RuntimeError("No EPUB is open.")

        original_path = self.zip_path
        temp_path = original_path.with_suffix(".epub.tmp")

        self.zip_file.close()
        self.zip_file = None

        try:
            with zipfile.ZipFile(original_path, "r") as zin, \
                 zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    if item.filename == path_in_zip:
                        zout.writestr(item, text.encode("utf-8"))
                    else:
                        zout.writestr(item, zin.read(item.filename))
            temp_path.replace(original_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise
        finally:
            self.zip_file = zipfile.ZipFile(original_path, "r")

    def get_metadata(self) -> EpubMetadata:
        """Return the parsed metadata object."""
        return self.metadata

    def set_metadata(self, meta: EpubMetadata) -> None:
        """Update the in-memory metadata object."""
        self.metadata = meta

    # ------------------------------------------------------------------
    # Cover image helpers
    # ------------------------------------------------------------------
    def get_cover_image_bytes(self) -> tuple[Optional[bytes], Optional[str]]:
        """Return (image_bytes, mimetype) for the current cover, or (None, None)."""
        if self.zip_file is None or self.opf_tree is None:
            raise RuntimeError("No EPUB is open.")

        cover_id = self.metadata.cover_id
        if not cover_id:
            return None, None

        manifest = self.opf_tree.find(_ns("manifest"))
        if manifest is None:
            return None, None

        item = self._find_manifest_item_by_id(manifest, cover_id)
        if item is None:
            return None, None

        href = item.get("href")
        if not href:
            return None, None

        image_path = self._resolve_manifest_href(href)
        if image_path not in self.zip_file.namelist():
            return None, None

        mimetype = item.get("media-type", "")
        return self.zip_file.read(image_path), mimetype

    def remove_cover_image(self) -> None:
        """Remove the cover image from the EPUB (manifest, meta, and ZIP file)."""
        if self.zip_file is None or self.opf_tree is None or self.opf_path_in_zip is None:
            raise RuntimeError("No EPUB is open.")

        cover_id = self.metadata.cover_id or "cover-image"
        manifest = self.opf_tree.find(_ns("manifest"))
        if manifest is None:
            raise RuntimeError("<manifest> missing from OPF.")

        # Find manifest item
        item = self._find_manifest_item_by_id(manifest, cover_id)
        image_path: Optional[str] = None
        if item is not None:
            href = item.get("href")
            if href:
                image_path = self._resolve_manifest_href(href)
            manifest.remove(item)

        # Remove meta name="cover"
        meta_elem = self.opf_tree.find(_ns("metadata"))
        if meta_elem is not None:
            for meta in meta_elem.findall(_ns("meta")):
                if meta.get("name") == "cover":
                    meta_elem.remove(meta)
                    break

        self.metadata.cover_id = ""

        # Rewrite ZIP without the image
        original_path = self.zip_path
        temp_path = original_path.with_suffix(".epub.tmp")

        self.zip_file.close()
        self.zip_file = None

        try:
            with zipfile.ZipFile(original_path, "r") as zin, \
                 zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zout:
                for zitem in zin.infolist():
                    if zitem.filename == self.opf_path_in_zip:
                        zout.writestr(zitem, self._serialize_opf())
                    elif image_path and zitem.filename == image_path:
                        continue  # skip old cover image
                    else:
                        zout.writestr(zitem, zin.read(zitem.filename))
            temp_path.replace(original_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise
        finally:
            self.zip_file = zipfile.ZipFile(original_path, "r")

    def _find_manifest_item_by_id(self, manifest: ET.Element, item_id: str) -> Optional[ET.Element]:
        for item in manifest.findall(_ns("item")):
            if item.get("id") == item_id:
                return item
        return None

    def _resolve_manifest_href(self, href: str) -> str:
        """Resolve a relative href against the OPF directory inside the ZIP."""
        opf_dir = Path(self.opf_path_in_zip).parent.as_posix()
        if opf_dir == ".":
            opf_dir = ""
        # normalise forward-slash separators
        combined = (opf_dir + "/" + href) if opf_dir else href
        # collapse ".." and "."
        parts = []
        for p in combined.split("/"):
            if p == "..":
                if parts:
                    parts.pop()
            elif p and p != ".":
                parts.append(p)
        return "/".join(parts)

    def set_cover_image(self, image_bytes: bytes, filename: str, mimetype: str = "image/jpeg") -> None:
        """Replace the cover image inside the ZIP and update the manifest.

        *image_bytes* — raw bytes of the new image.
        *filename*    — base name to store inside the EPUB (e.g. "cover.jpg").
        """
        if self.zip_file is None or self.opf_tree is None or self.opf_path_in_zip is None:
            raise RuntimeError("No EPUB is open.")

        cover_id = self.metadata.cover_id or "cover-image"
        self.metadata.cover_id = cover_id

        manifest = self.opf_tree.find(_ns("manifest"))
        if manifest is None:
            raise RuntimeError("<manifest> missing from OPF.")

        item = self._find_manifest_item_by_id(manifest, cover_id)
        if item is None:
            # Create new manifest item
            item = ET.SubElement(manifest, _ns("item"))
            item.set("id", cover_id)

        # Determine storage path (same dir as OPF)
        opf_dir = Path(self.opf_path_in_zip).parent.as_posix()
        if opf_dir == ".":
            opf_dir = ""
        image_path = (opf_dir + "/" + filename) if opf_dir else filename

        item.set("href", filename)
        item.set("media-type", mimetype)

        # Ensure meta name="cover" exists
        meta_elem = self.opf_tree.find(_ns("metadata"))
        if meta_elem is not None:
            cover_meta = None
            for meta in meta_elem.findall(_ns("meta")):
                if meta.get("name") == "cover":
                    cover_meta = meta
                    break
            if cover_meta is None:
                cover_meta = ET.SubElement(meta_elem, _ns("meta"))
                cover_meta.set("name", "cover")
            cover_meta.set("content", cover_id)

        # Now rewrite the ZIP, injecting the new image bytes
        self._rewrite_zip_with_new_image(image_path, image_bytes)

    def _serialize_opf(self) -> bytes:
        """Serialize the OPF tree to UTF-8 bytes with proper namespace prefixes."""
        ET.register_namespace("", _OPF_NS)
        ET.register_namespace("dc", _DC_NS)
        ET.register_namespace("opf", _OPF_NS)
        return ET.tostring(self.opf_tree, encoding="utf-8", xml_declaration=True)

    def _rewrite_zip_with_new_image(self, image_path: str, image_bytes: bytes) -> None:
        """Rewrite the EPUB ZIP in-place, replacing OPF and adding/replacing image."""
        # Serialize updated OPF first
        new_opf_bytes = self._serialize_opf()

        original_path = self.zip_path
        temp_path = original_path.with_suffix(".epub.tmp")

        self.zip_file.close()
        self.zip_file = None

        try:
            with zipfile.ZipFile(original_path, "r") as zin, \
                 zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    if item.filename == self.opf_path_in_zip:
                        zout.writestr(item, new_opf_bytes)
                    elif item.filename == image_path:
                        # Skip old image; we'll write the new one explicitly
                        continue
                    else:
                        zout.writestr(item, zin.read(item.filename))

                # Write new image
                zout.writestr(image_path, image_bytes)

            temp_path.replace(original_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise
        finally:
            self.zip_file = zipfile.ZipFile(original_path, "r")

    def save_metadata(self) -> None:
        """Write updated metadata back into the EPUB ZIP file."""
        if self.zip_file is None or self.opf_tree is None or self.opf_path_in_zip is None:
            raise RuntimeError("No EPUB is open.")

        # Update the OPF tree in memory
        self._update_opf_tree()

        # Serialize updated OPF
        new_opf_bytes = self._serialize_opf()

        # Rewrite ZIP in-place via a temp file
        original_path = self.zip_path
        temp_path = original_path.with_suffix(".epub.tmp")

        # Close original so we can overwrite it
        self.zip_file.close()
        self.zip_file = None

        try:
            with zipfile.ZipFile(original_path, "r") as zin, \
                 zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    if item.filename == self.opf_path_in_zip:
                        zout.writestr(item, new_opf_bytes)
                    else:
                        zout.writestr(item, zin.read(item.filename))

            # Replace original with temp
            temp_path.replace(original_path)
        except Exception:
            # Clean up temp file on failure
            if temp_path.exists():
                temp_path.unlink()
            raise
        finally:
            # Re-open the (now updated) original
            self.zip_file = zipfile.ZipFile(original_path, "r")

    def _update_opf_tree(self) -> None:
        """Mutate the stored OPF ElementTree with current self.metadata."""
        if self.opf_tree is None:
            raise RuntimeError("No OPF tree loaded.")

        meta_elem = self.opf_tree.find(_ns("metadata"))
        if meta_elem is None:
            raise RuntimeError("<metadata> element missing from OPF.")

        def _set_or_replace(tag: str, ns: str, values: list[str]) -> None:
            """Remove existing elements and recreate with new values."""
            # Remove all existing
            for el in meta_elem.findall(_ns(tag, ns)):
                meta_elem.remove(el)
            # Add new
            for val in values:
                if val:
                    el = ET.SubElement(meta_elem, _ns(tag, ns))
                    el.text = val

        def _set_single(tag: str, ns: str, value: str) -> None:
            """Set exactly one element, creating if absent."""
            existing = meta_elem.find(_ns(tag, ns))
            if existing is not None:
                existing.text = value
            else:
                el = ET.SubElement(meta_elem, _ns(tag, ns))
                el.text = value

        _set_single("title", _DC_NS, self.metadata.title)
        # EPUB2 style title-sort
        title_el = meta_elem.find(_ns("title", _DC_NS))
        if title_el is not None and self.metadata.title_sort:
            title_el.set(f"{{{_OPF_NS}}}file-as", self.metadata.title_sort)

        _set_or_replace("creator", _DC_NS, self.metadata.creators)
        # Author sort for first creator
        if self.metadata.author_sort:
            creator_els = meta_elem.findall(_ns("creator", _DC_NS))
            if creator_els:
                creator_els[0].set(f"{{{_OPF_NS}}}file-as", self.metadata.author_sort)

        _set_single("language", _DC_NS, self.metadata.language)
        # Deduplicate identifiers before saving
        seen_ids = set()
        unique_ids = []
        for val in self.metadata.identifiers:
            if val and val not in seen_ids:
                seen_ids.add(val)
                unique_ids.append(val)
        _set_or_replace("identifier", _DC_NS, unique_ids)
        _set_single("description", _DC_NS, self.metadata.description)
        _set_single("publisher", _DC_NS, self.metadata.publisher)
        _set_single("date", _DC_NS, self.metadata.date)
        _set_single("rights", _DC_NS, self.metadata.rights)
        _set_or_replace("subject", _DC_NS, self.metadata.subjects)

        # Remove old calibre meta to avoid duplicates
        to_remove = []
        for meta in meta_elem.findall(_ns("meta")):
            name = meta.get("name")
            prop = meta.get("property")
            if name in ("calibre:series", "calibre:series_index", "calibre:title_sort", "calibre:rating"):
                to_remove.append(meta)
            elif prop in ("belongs-to-collection", "group-position", "dcterms:modified"):
                to_remove.append(meta)
        for meta in to_remove:
            meta_elem.remove(meta)

        # Add calibre meta
        if self.metadata.series:
            el = ET.SubElement(meta_elem, _ns("meta"))
            el.set("name", "calibre:series")
            el.set("content", self.metadata.series)
            # EPUB3 style
            el3 = ET.SubElement(meta_elem, _ns("meta"))
            el3.set("property", "belongs-to-collection")
            el3.text = self.metadata.series
            
        if self.metadata.series_index:
            el = ET.SubElement(meta_elem, _ns("meta"))
            el.set("name", "calibre:series_index")
            el.set("content", self.metadata.series_index)
            # EPUB3 style
            el3 = ET.SubElement(meta_elem, _ns("meta"))
            el3.set("property", "group-position")
            el3.text = self.metadata.series_index

        if self.metadata.title_sort:
            el = ET.SubElement(meta_elem, _ns("meta"))
            el.set("name", "calibre:title_sort")
            el.set("content", self.metadata.title_sort)

        if self.metadata.rating:
            el = ET.SubElement(meta_elem, _ns("meta"))
            el.set("name", "calibre:rating")
            el.set("content", self.metadata.rating)

        if self.metadata.modification_date:
            # EPUB3 dcterms:modified
            el = ET.SubElement(meta_elem, _ns("meta"))
            el.set("property", "dcterms:modified")
            el.text = self.metadata.modification_date

        # Handle cover meta
        cover_meta = None
        for meta in meta_elem.findall(_ns("meta")):
            if meta.get("name") == "cover":
                cover_meta = meta
                break
        if self.metadata.cover_id:
            if cover_meta is not None:
                cover_meta.set("content", self.metadata.cover_id)
            else:
                el = ET.SubElement(meta_elem, _ns("meta"))
                el.set("name", "cover")
                el.set("content", self.metadata.cover_id)
        else:
            if cover_meta is not None:
                meta_elem.remove(cover_meta)

    def clean_metadata(self) -> None:
        """Strip all dc: metadata and meta tags from the OPF (keep only manifest/spine).
        Preserves the cover meta tag so the cover image reference isn't lost.
        """
        if self.zip_file is None or self.opf_tree is None or self.opf_path_in_zip is None:
            raise RuntimeError("No EPUB is open.")

        meta_elem = self.opf_tree.find(_ns("metadata"))
        if meta_elem is None:
            raise RuntimeError("<metadata> element missing from OPF.")

        # Remove all dc: elements
        dc_tags = ("title", "creator", "language", "identifier", "description",
                   "publisher", "date", "rights", "subject", "contributor",
                   "source", "relation", "coverage", "format", "type")
        for tag in dc_tags:
            for el in meta_elem.findall(_ns(tag, _DC_NS)):
                meta_elem.remove(el)

        # Remove all <meta> tags except cover
        cover_meta = None
        for meta in meta_elem.findall(_ns("meta")):
            if meta.get("name") == "cover":
                cover_meta = meta
            else:
                meta_elem.remove(meta)

        # Reset in-memory metadata
        self.metadata = EpubMetadata()
        self.metadata.cover_id = cover_meta.get("content", "") if cover_meta is not None else ""
        self.metadata.version = self.version

        # Serialize and rewrite ZIP
        new_opf_bytes = self._serialize_opf()
        original_path = self.zip_path
        temp_path = original_path.with_suffix(".epub.tmp")

        self.zip_file.close()
        self.zip_file = None

        try:
            with zipfile.ZipFile(original_path, "r") as zin, \
                 zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    if item.filename == self.opf_path_in_zip:
                        zout.writestr(item, new_opf_bytes)
                    else:
                        zout.writestr(item, zin.read(item.filename))
            temp_path.replace(original_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise
        finally:
            self.zip_file = zipfile.ZipFile(original_path, "r")

    def close(self) -> None:
        """Close the ZIP handle and reset state."""
        if self.zip_file:
            self.zip_file.close()
        self.zip_file = None
        self.zip_path = None
        self.opf_path_in_zip = None
        self.opf_tree = None
        self.metadata = EpubMetadata()
        self.version = ""
        self.toc_path = None
        self.toc_ncx_path = None
        self.page_map_path = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
