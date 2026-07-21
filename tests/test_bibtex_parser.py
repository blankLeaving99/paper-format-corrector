"""BibTeX 解析器测试"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest

from paper_format_corrector.domain.document.parser.bibtex_parser import BibEntry, BibTeXParser


SAMPLE_BIB = r"""
@article{smith2020deep,
  author = {Smith, John and Doe, Jane},
  title = {Deep Learning for {NLP}: A Survey},
  journal = {Journal of Artificial Intelligence},
  year = {2020},
  volume = {15},
  number = {3},
  pages = {100--125},
  doi = {10.1234/jai.2020.15.3.100},
}

@inproceedings{wang2021transformer,
  author = {Wang, Wei and Li, Na},
  title = {Transformer Architecture Improvements},
  booktitle = {Proceedings of ACL 2021},
  year = {2021},
  pages = {50--60},
  publisher = {ACL},
}

@book{goodfellow2016deep,
  author = {Goodfellow, Ian and Bengio, Yoshua and Courville, Aaron},
  title = {Deep Learning},
  year = {2016},
  publisher = {MIT Press},
}

@phdthesis{zhang2019neural,
  author = {Zhang, San},
  title = {Neural Machine Translation},
  year = {2019},
  school = {Peking University},
}
"""


class TestBibTeXParser:
    """BibTeX 解析器基本功能测试"""

    @pytest.fixture
    def parser(self):
        return BibTeXParser()

    def test_parse_string_basic(self, parser):
        entries = parser.parse_string(SAMPLE_BIB)
        assert len(entries) == 4

    def test_parse_article_entry(self, parser):
        entries = parser.parse_string(SAMPLE_BIB)
        article = entries[0]
        assert article.entry_type == "article"
        assert article.cite_key == "smith2020deep"
        assert len(article.authors) == 2
        assert article.authors[0] == "John Smith"
        assert article.authors[1] == "Jane Doe"
        assert "Deep Learning" in article.title
        assert article.journal == "Journal of Artificial Intelligence"
        assert article.year == "2020"
        assert article.volume == "15"
        assert article.number == "3"
        assert article.pages == "100--125"
        assert article.doi == "10.1234/jai.2020.15.3.100"

    def test_parse_inproceedings_entry(self, parser):
        entries = parser.parse_string(SAMPLE_BIB)
        conf = entries[1]
        assert conf.entry_type == "inproceedings"
        assert conf.cite_key == "wang2021transformer"
        assert conf.booktitle == "Proceedings of ACL 2021"
        assert conf.publisher == "ACL"

    def test_parse_book_entry(self, parser):
        entries = parser.parse_string(SAMPLE_BIB)
        book = entries[2]
        assert book.entry_type == "book"
        assert book.cite_key == "goodfellow2016deep"
        assert len(book.authors) == 3
        assert book.publisher == "MIT Press"

    def test_parse_phdthesis_entry(self, parser):
        entries = parser.parse_string(SAMPLE_BIB)
        thesis = entries[3]
        assert thesis.entry_type == "phdthesis"
        assert thesis.cite_key == "zhang2019neural"

    def test_parse_file_not_found(self, parser):
        with pytest.raises(FileNotFoundError):
            parser.parse_file("/nonexistent/path/references.bib")

    def test_parse_file(self, parser, tmp_path):
        bib_file = tmp_path / "test.bib"
        bib_file.write_text(SAMPLE_BIB, encoding="utf-8")
        entries = parser.parse_file(str(bib_file))
        assert len(entries) == 4

    def test_comments_are_ignored(self, parser):
        bib_with_comments = "% This is a comment\n" + SAMPLE_BIB
        entries = parser.parse_string(bib_with_comments)
        assert len(entries) == 4

    def test_empty_string_returns_empty(self, parser):
        entries = parser.parse_string("")
        assert entries == []

    def test_malformed_entry_skipped(self, parser):
        malformed = "@article{broken, title = {unclosed\n@article{good, title = {Good}, year = {2020}}\n"
        entries = parser.parse_string(malformed)
        # Should parse at least the good entry
        assert any(e.cite_key == "good" for e in entries)


class TestBibEntry:
    """BibEntry 数据模型测试"""

    def test_to_dict_article(self):
        entry = BibEntry(
            entry_type="article",
            cite_key="test2020",
            authors=["Author One", "Author Two"],
            title="Test Title",
            journal="Test Journal",
            year="2020",
            volume="10",
            pages="1--10",
            doi="10.1234/test",
        )
        d = entry.to_dict()
        assert d["type"] == "journal"
        assert d["cite_key"] == "test2020"
        assert len(d["authors"]) == 2
        assert d["journal"] == "Test Journal"
        assert d["pages"] == "1-10"  # -- converted to -
        assert d["doi"] == "10.1234/test"

    def test_to_dict_conference(self):
        entry = BibEntry(
            entry_type="inproceedings",
            cite_key="conf2021",
            authors=["Conf Author"],
            title="Conf Paper",
            year="2021",
            booktitle="Proc. of Conf",
        )
        d = entry.to_dict()
        assert d["type"] == "conference"
        assert d["booktitle"] == "Proc. of Conf"

    def test_to_dict_thesis(self):
        entry = BibEntry(
            entry_type="phdthesis",
            cite_key="thesis2019",
            authors=["Student"],
            title="Thesis Title",
            year="2019",
        )
        d = entry.to_dict()
        assert d["type"] == "phd_thesis"

    def test_map_entry_type_misc(self):
        entry = BibEntry(entry_type="misc", cite_key="misc1")
        assert entry._map_entry_type() == "other"

    def test_map_entry_type_unknown(self):
        entry = BibEntry(entry_type="unknowntype", cite_key="unk1")
        assert entry._map_entry_type() == "other"


class TestBibTeXParserHelpers:
    """解析器辅助方法测试"""

    def test_parse_authors_single(self):
        result = BibTeXParser._parse_authors("John Smith")
        assert result == ["John Smith"]

    def test_parse_authors_multiple(self):
        result = BibTeXParser._parse_authors("John Smith and Jane Doe")
        assert result == ["John Smith", "Jane Doe"]

    def test_parse_authors_last_first_format(self):
        result = BibTeXParser._parse_authors("Smith, John and Doe, Jane")
        assert result == ["John Smith", "Jane Doe"]

    def test_parse_authors_empty(self):
        result = BibTeXParser._parse_authors("")
        assert result == []

    def test_clean_latex_special_chars(self):
        result = BibTeXParser._clean_latex(r"caf\'e")
        assert "é" in result

    def test_clean_latex_removes_braces(self):
        result = BibTeXParser._clean_latex("{Deep} {Learning}")
        assert result == "Deep Learning"

    def test_clean_latex_commands(self):
        result = BibTeXParser._clean_latex(r"\textbf{Bold} text")
        assert "Bold" in result
        assert "\\textbf" not in result

    def test_to_reference_list(self):
        parser = BibTeXParser()
        parser.parse_string(SAMPLE_BIB)
        refs = parser.to_reference_list()
        assert len(refs) == 4
        assert all(isinstance(r, dict) for r in refs)
        assert all("type" in r for r in refs)
        assert all("cite_key" in r for r in refs)
