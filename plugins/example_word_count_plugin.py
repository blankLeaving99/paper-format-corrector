"""Example plugin: Word count and statistics.

Demonstrates how to write a plugin for the paper-format-corrector system.

Usage:
    1. Place this file in the plugins/ directory (or anywhere on your Python path)
    2. Register it in your code:

        from paper_format_corrector.infra.plugin_manager import PluginManager
        from plugins.example_word_count_plugin import WordCountPlugin

        manager = PluginManager(config)
        manager.register(WordCountPlugin)
        manager.run_all(doc, context)

    3. After running, access the report via plugin.get_report()
"""

import re
from paper_format_corrector.infra.plugin_manager import Plugin


class WordCountPlugin(Plugin):
    """Count words, characters, and paragraphs in the document."""

    name = "word_count"
    description = "统计文档字数、字符数、段落数"
    priority = 200  # Low priority: runs after formatting plugins

    def __init__(self, config):
        super().__init__(config)
        self._stats = {}

    def process(self, doc, context):
        """Count words and characters in the document."""
        total_chars = 0
        total_words = 0
        cn_chars = 0
        en_words = 0
        para_count = 0

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            para_count += 1
            total_chars += len(text)
            # Count Chinese characters
            cn = len(re.findall(r"[一-鿿]", text))
            cn_chars += cn
            # Count English words
            en = len(re.findall(r"[a-zA-Z]+", text))
            en_words += en
            total_words += cn + en

        self._stats = {
            "total_characters": total_chars,
            "total_words": total_words,
            "chinese_characters": cn_chars,
            "english_words": en_words,
            "paragraph_count": para_count,
        }

        context["word_count"] = self._stats
        return context

    def get_report(self):
        return self._stats
