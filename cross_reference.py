"""交叉引用更新模块

自动更新正文中对图表公式的引用编号。

检测并更新：
- "如图X所示" / "见图X" / "图X"
- "如表X所示" / "见表X" / "表X"
- "式(X)" / "公式(X)"
- "[X]" 在参考文献上下文中的引用
"""

import re


class CrossReferenceUpdater:
    """交叉引用更新器"""

    def __init__(self):
        self.fig_map = {}  # old_num -> new_num
        self.tab_map = {}
        self.eq_map = {}
        self.ref_map = {}

    def update(self, doc, fig_map=None, tab_map=None, eq_map=None, ref_map=None):
        """更新文档中的交叉引用"""
        self.fig_map = fig_map or {}
        self.tab_map = tab_map or {}
        self.eq_map = eq_map or {}
        self.ref_map = ref_map or {}

        updated_count = 0

        for para in doc.paragraphs:
            text = para.text
            if not text:
                continue

            new_text = self._update_text(text)
            if new_text != text:
                self._replace_paragraph_text(para, new_text)
                updated_count += 1

        return updated_count

    def _update_text(self, text):
        """更新文本中的引用编号"""
        result = text

        # 图引用：如图X所示, 见图X, 图X中
        for old, new in self.fig_map.items():
            result = re.sub(
                rf"(图)\s*{re.escape(old)}(?=[\s所示中，。、])",
                rf"\g<1>{new}",
                result,
            )

        # 表引用
        for old, new in self.tab_map.items():
            result = re.sub(
                rf"(表)\s*{re.escape(old)}(?=[\s所示中，。、])",
                rf"\g<1>{new}",
                result,
            )

        # 公式引用
        for old, new in self.eq_map.items():
            result = re.sub(
                rf"(式|公式)\s*\(?{re.escape(old)}\)?",
                rf"\g<1>({new})",
                result,
            )

        return result

    def _replace_paragraph_text(self, paragraph, new_text):
        """替换段落文本（保留第一个run的格式）"""
        if not paragraph.runs:
            return

        # 保留第一个run的格式
        first_run = paragraph.runs[0]
        first_run.text = new_text

        # 清空其他run
        for run in paragraph.runs[1:]:
            run.text = ""

    def build_renumber_map(self, captions, numbering_style="chapter"):
        """根据图表标题列表构建重编号映射

        Args:
            captions: [(old_num, chapter, seq), ...]
            numbering_style: "chapter" -> "2-1", "sequential" -> "5"
        """
        result = {}
        for old_num, chapter, seq in captions:
            if numbering_style == "chapter":
                new_num = f"{chapter}-{seq}"
            else:
                new_num = str(seq)
            if old_num != new_num:
                result[old_num] = new_num
        return result
