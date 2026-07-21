"""BibTeX parser for reference management.

Parses BibTeX files into structured BibEntry objects with support for
common LaTeX cleanup and reference list generation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# LaTeX special character map
_LATEX_SPECIAL_CHARS = {
    r"\'a": "á", r"\'e": "é", r"\'i": "í", r"\'o": "ó", r"\'u": "ú",
    r"\'A": "Á", r"\'E": "É", r"\'I": "Í", r"\'O": "Ó", r"\'U": "Ú",
    r"\`a": "à", r"\`e": "è", r"\`i": "ì", r"\`o": "ò", r"\`u": "ù",
    r"\"a": "ä", r"\"o": "ö", r"\"u": "ü", r"\"A": "Ä", r"\"O": "Ö", r"\"U": "Ü",
    r"\^a": "â", r"\^e": "ê", r"\^i": "î", r"\^o": "ô", r"\^u": "û",
    r"\~n": "ñ", r"\~N": "Ñ",
    r"\c{c}": "ç", r"\c{C}": "Ç",
    r"\ss": "ß", r"\o": "ø", r"\O": "Ø",
    r"\aa": "å", r"\AA": "Å",
    r"\ae": "æ", r"\AE": "Æ", r"\oe": "œ", r"\OE": "Œ",
    r"\&": "&", r"\%": "%", r"\$": "$", r"\#": "#",
    r"\_": "_", r"\{": "{", r"\}": "}",
    r"\textbackslash": "\\",
    r"\textasciitilde": "~",
    r"\textendash": "–", r"\textemdash": "—",
    r"\textquoteleft": "\u2018", r"\textquoteright": "\u2019",
    r"\textquotedblleft": "\u201c", r"\textquotedblright": "\u201d",
    r"\LaTeX": "LaTeX", r"\TeX": "TeX",
}

# Entry type mapping to normalized types
_ENTRY_TYPE_MAP = {
    "article": "journal",
    "inproceedings": "conference",
    "conference": "conference",
    "book": "book",
    "inbook": "book_section",
    "incollection": "book_section",
    "phdthesis": "phd_thesis",
    "mastersthesis": "masters_thesis",
    "techreport": "technical_report",
    "misc": "other",
    "unpublished": "other",
    "manual": "manual",
    "proceedings": "proceedings",
    "online": "online",
    "electronic": "online",
    "www": "online",
}


@dataclass
class BibEntry:
    """A single BibTeX entry."""

    entry_type: str
    cite_key: str
    authors: list[str] = field(default_factory=list)
    title: str = ""
    year: str = ""
    journal: str = ""
    volume: str = ""
    number: str = ""
    pages: str = ""
    doi: str = ""
    booktitle: str = ""
    publisher: str = ""
    school: str = ""
    fields: dict[str, str] = field(default_factory=dict)

    def _map_entry_type(self) -> str:
        """Map BibTeX entry type to a normalized type string."""
        return _ENTRY_TYPE_MAP.get(self.entry_type.lower(), "other")

    def to_dict(self) -> dict[str, Any]:
        """Convert entry to a normalized dictionary."""
        result: dict[str, Any] = {
            "type": self._map_entry_type(),
            "cite_key": self.cite_key,
            "authors": list(self.authors),
            "title": _clean_latex_braces(self.title),
            "year": self.year,
        }
        if self.journal:
            result["journal"] = self.journal
        if self.volume:
            result["volume"] = self.volume
        if self.number:
            result["number"] = self.number
        if self.pages:
            result["pages"] = self.pages.replace("--", "-")
        if self.doi:
            result["doi"] = self.doi
        if self.booktitle:
            result["booktitle"] = self.booktitle
        if self.publisher:
            result["publisher"] = self.publisher
        if self.school:
            result["school"] = self.school
        return result


def _clean_latex_braces(text: str) -> str:
    """Remove LaTeX braces that are used for case protection."""
    return text.replace("{", "").replace("}", "")


class BibTeXParser:
    """Parse BibTeX content into structured entries."""

    def __init__(self) -> None:
        self._entries: list[BibEntry] = []

    def parse_string(self, content: str) -> list[BibEntry]:
        """Parse BibTeX string and return list of entries."""
        self._entries = []
        if not content or not content.strip():
            return self._entries

        # Remove comment lines (lines starting with %)
        lines = content.split("\n")
        cleaned_lines = []
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("%"):
                continue
            # Also remove inline comments (but be careful with %)
            cleaned_lines.append(line)
        content = "\n".join(cleaned_lines)

        pos = 0
        while pos < len(content):
            match = re.search(r"@(\w+)\s*\{", content[pos:])
            if not match:
                break
            entry_type = match.group(1).lower()
            brace_start = pos + match.end() - 1
            brace_end = self._find_matching_brace(content, brace_start)
            if brace_end == -1:
                # Malformed entry, skip to next @
                next_at = content.find("@", pos + 1)
                if next_at == -1:
                    break
                pos = next_at
                continue
            body = content[brace_start + 1:brace_end]
            entry = self._parse_entry(entry_type, body)
            if entry:
                self._entries.append(entry)
            pos = brace_end + 1
        return self._entries

    def parse_file(self, path: str) -> list[BibEntry]:
        """Parse a .bib file and return list of entries."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"BibTeX file not found: {path}")
        content = file_path.read_text(encoding="utf-8")
        return self.parse_string(content)

    def to_reference_list(self) -> list[dict[str, Any]]:
        """Convert all parsed entries to a list of reference dictionaries."""
        return [entry.to_dict() for entry in self._entries]

    @property
    def entries(self) -> list[BibEntry]:
        return self._entries

    def _find_matching_brace(self, content: str, start: int) -> int:
        """Find the matching closing brace."""
        depth = 0
        i = start
        while i < len(content):
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return -1

    def _parse_entry(self, entry_type: str, body: str) -> BibEntry | None:
        """Parse a single BibTeX entry body."""
        # Extract cite key (everything before first comma)
        comma_idx = body.find(",")
        if comma_idx == -1:
            return None
        cite_key = body[:comma_idx].strip()
        if not cite_key:
            return None
        rest = body[comma_idx + 1:]

        # Parse fields
        fields: dict[str, str] = {}
        field_pattern = re.compile(
            r"(\w+)\s*=\s*(?:\{((?:[^{}]|\{[^{}]*\})*)\}|\"([^\"]*)\"|(\d+))",
            re.DOTALL,
        )
        for m in field_pattern.finditer(rest):
            key = m.group(1).lower()
            value = m.group(2) or m.group(3) or m.group(4) or ""
            fields[key] = value.strip()

        # Parse authors
        author_str = fields.get("author", "")
        authors = self._parse_authors(author_str)

        return BibEntry(
            entry_type=entry_type,
            cite_key=cite_key,
            authors=authors,
            title=fields.get("title", ""),
            year=fields.get("year", ""),
            journal=fields.get("journal", ""),
            volume=fields.get("volume", ""),
            number=fields.get("number", ""),
            pages=fields.get("pages", ""),
            doi=fields.get("doi", ""),
            booktitle=fields.get("booktitle", ""),
            publisher=fields.get("publisher", ""),
            school=fields.get("school", ""),
            fields=fields,
        )

    @staticmethod
    def _parse_authors(author_str: str) -> list[str]:
        """Parse author string into list of author names.

        Handles formats:
        - "First Last" → ["First Last"]
        - "First Last and First2 Last2" → ["First Last", "First2 Last2"]
        - "Last, First and Last2, First2" → ["First Last", "First2 Last2"]
        """
        if not author_str or not author_str.strip():
            return []

        # Split by " and "
        parts = re.split(r"\s+and\s+", author_str.strip())
        authors = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Check if "Last, First" format
            if "," in part:
                segments = part.split(",", 1)
                last = segments[0].strip()
                first = segments[1].strip() if len(segments) > 1 else ""
                if first:
                    authors.append(f"{first} {last}")
                else:
                    authors.append(last)
            else:
                authors.append(part)
        return authors

    @staticmethod
    def _clean_latex(text: str) -> str:
        """Clean LaTeX commands and special characters from text."""
        if not text:
            return text

        result = text

        # Handle \textbf{...}, \textit{...}, \emph{...} etc - keep content
        result = re.sub(r"\\(?:textbf|textit|emph|textrm|textsc|textsl|texttt|underline)\{([^{}]*)\}", r"\1", result)

        # Handle LaTeX special characters
        for latex_cmd, replacement in _LATEX_SPECIAL_CHARS.items():
            result = result.replace(latex_cmd, replacement)

        # Remove remaining braces (case protection braces)
        result = result.replace("{", "").replace("}", "")

        # Remove remaining backslash commands that take no args
        result = re.sub(r"\\[a-zA-Z]+", "", result)

        # Clean up extra spaces
        result = re.sub(r"\s+", " ", result).strip()

        return result
