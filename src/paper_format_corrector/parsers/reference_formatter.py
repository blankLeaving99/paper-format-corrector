import re
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


class ReferenceFormatter:
    """参考文献格式矫正器 (GB/T 7714)"""

    # 常见文献类型标识
    TYPE_MAP = {
        "J": "journal",       # 期刊
        "M": "book",          # 专著
        "C": "conference",    # 会议
        "D": "thesis",        # 学位论文
        "R": "report",        # 报告
        "N": "newspaper",     # 报纸
        "S": "standard",      # 标准
        "P": "patent",        # 专利
        "EB/OL": "online",    # 网络文献
        "DB/OL": "online",
    }

    def __init__(self, config):
        ref_config = config.get("format_rules", {}).get("references", {})
        self.font_size = ref_config.get("font_size", 10.5)
        self.line_spacing = ref_config.get("line_spacing", 1.25)
        self.hanging_indent = ref_config.get("hanging_indent", True)
        self.numbering = ref_config.get("numbering", "sequential")
        self.font_rules = config.get("format_rules", {}).get("font", {})

    def format_references(self, doc, ref_start_idx, ref_end_idx=None):
        """格式化参考文献区域"""
        paragraphs = doc.paragraphs
        if ref_start_idx >= len(paragraphs):
            return

        # 格式化参考文献标题
        title_para = paragraphs[ref_start_idx]
        self._format_ref_title(title_para)

        # 格式化每条参考文献
        ref_num = 1
        for i in range(ref_start_idx + 1, len(paragraphs)):
            para = paragraphs[i]
            text = para.text.strip()
            if not text:
                continue

            # 如果遇到新的顶级标题，停止
            if self._is_new_section(text) and i > ref_start_idx + 1:
                break

            self._format_ref_item(para, ref_num)
            ref_num += 1

    def _format_ref_title(self, paragraph):
        """格式化参考文献标题"""
        rules = self.font_rules
        for run in paragraph.runs:
            run.font.name = rules.get("english", "Times New Roman")
            self._set_east_asian_font(run, rules.get("chinese", "宋体"))
            run.font.size = Pt(self.font_size)
            run.font.bold = True

        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(12)
        paragraph.paragraph_format.space_after = Pt(6)

    def _format_ref_item(self, paragraph, num):
        """格式化单条参考文献"""
        rules = self.font_rules
        for run in paragraph.runs:
            run.font.name = rules.get("english", "Times New Roman")
            self._set_east_asian_font(run, rules.get("chinese", "宋体"))
            run.font.size = Pt(self.font_size)
            run.font.bold = False

        paragraph.paragraph_format.line_spacing = self.line_spacing
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)

        if self.hanging_indent:
            paragraph.paragraph_format.first_line_indent = Pt(-24)  # 悬挂缩进
            paragraph.paragraph_format.left_indent = Pt(24)

    def validate_references(self, doc, ref_start_idx):
        """验证参考文献格式，返回问题列表"""
        issues = []
        paragraphs = doc.paragraphs

        ref_num = 0
        for i in range(ref_start_idx + 1, len(paragraphs)):
            text = paragraphs[i].text.strip()
            if not text:
                continue
            if self._is_new_section(text):
                break

            ref_num += 1
            problems = self._check_single_ref(text, ref_num)
            issues.extend(problems)

        return issues

    def _check_single_ref(self, text, expected_num):
        """检查单条参考文献格式"""
        issues = []

        # 检查编号格式 [1]
        m = re.match(r"^\[(\d+)\]", text)
        if m:
            num = int(m.group(1))
            if num != expected_num:
                issues.append(
                    f"参考文献 [{num}] 编号不连续，应为 [{expected_num}]"
                )
        else:
            # 没有 [N] 格式的编号
            m2 = re.match(r"^(\d+)[\.\)]", text)
            if m2:
                issues.append(
                    f"参考文献 {m2.group(1)} 建议使用 [N] 格式编号"
                )
            else:
                issues.append(f"参考文献 {expected_num} 缺少编号")

        # 检查是否包含文献类型标识
        if not re.search(r"\[[A-Z]", text):
            issues.append(f"参考文献 [{expected_num}] 缺少文献类型标识 (如 [J], [M])")

        # 检查作者格式 (中文文献作者间应用逗号)
        if re.search(r"[一-鿿]{2,4}\s+[一-鿿]{2,4}", text):
            if "，" not in text and "," not in text[:text.find(".")]:
                issues.append(f"参考文献 [{expected_num}] 多位作者间建议用逗号分隔")

        return issues

    def _is_new_section(self, text):
        """判断是否进入新的章节"""
        if re.match(r"^第[一二三四五六七八九十\d]+[章部分篇]", text):
            return True
        if re.match(r"^\d+\.\d+", text):
            return True
        return False

    def check_citation_consistency(self, doc, ref_start_idx):
        """检查正文引用与参考文献列表的一致性

        Returns:
            list of dict: [{"type": "orphan"|"missing"|"duplicate", "message": str}]
        """
        issues = []
        paragraphs = doc.paragraphs

        # 1. 收集正文中所有引用编号
        cited_nums = set()
        for i in range(ref_start_idx):
            text = paragraphs[i].text.strip()
            if not text:
                continue
            # 匹配 [1], [2], [1-3], [1,2,3], [1, 2, 3] 等
            for m in re.finditer(r"\[(\d+)(?:[,\s\-–—]*(\d+))*\]", text):
                for num_str in re.findall(r"\d+", m.group(0)):
                    cited_nums.add(int(num_str))

        # 2. 收集参考文献列表中的编号
        ref_nums = {}
        for i in range(ref_start_idx + 1, len(paragraphs)):
            text = paragraphs[i].text.strip()
            if not text:
                continue
            if self._is_new_section(text):
                break
            m = re.match(r"^\[(\d+)\]", text)
            if m:
                num = int(m.group(1))
                if num in ref_nums:
                    issues.append({"type": "duplicate", "message": f"参考文献 [{num}] 重复出现"})
                ref_nums[num] = text[:50]

        # 3. 检查孤立引用（正文引用了但参考文献列表中没有）
        for num in sorted(cited_nums):
            if num not in ref_nums:
                issues.append({"type": "orphan", "message": f"正文引用 [{num}] 在参考文献列表中不存在"})

        # 4. 检查未引用文献（参考文献列表中有但正文未引用）
        for num in sorted(ref_nums.keys()):
            if num not in cited_nums:
                issues.append({"type": "missing", "message": f"参考文献 [{num}] 未在正文中被引用"})

        return issues

    def _set_east_asian_font(self, run, font_name):
        rpr = run._element.get_or_add_rPr()
        rFonts = rpr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = run._element.makeelement(qn("w:rFonts"), {})
            rpr.insert(0, rFonts)
        rFonts.set(qn("w:eastAsia"), font_name)
