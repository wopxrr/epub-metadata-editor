"""Data models for EPUB metadata."""
from dataclasses import dataclass, field, replace
from typing import List, Optional


@dataclass
class EpubMetadata:
    """Holds extracted metadata from an EPUB's OPF file."""
    title: str = ""
    creators: List[str] = field(default_factory=list)
    language: str = ""
    identifiers: List[str] = field(default_factory=list)
    description: str = ""
    publisher: str = ""
    date: str = ""
    rights: str = ""
    subjects: List[str] = field(default_factory=list)
    series: str = ""
    series_index: str = ""
    title_sort: str = ""
    author_sort: str = ""
    cover_id: str = ""
    version: str = ""
    rating: str = ""
    modification_date: str = ""

    def copy(self):
        return replace(self)

    def __repr__(self) -> str:
        parts = [f"EpubMetadata(title={self.title!r})"]
        return " ".join(parts)
