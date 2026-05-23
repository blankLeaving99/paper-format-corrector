"""自定义规则引擎

支持用户用YAML编写自定义校验规则，检查文档是否符合要求。

规则格式 (rules.yaml):
```yaml
rules:
  - name: "图标题必须在图下方"
    check: figure_caption_position
    severity: error

  - name: "参考文献不超过50篇"
    check: reference_count
    params:
      max: 50
    severity: warning

  - name: "正文字号为小四"
    check: body_font_size
    params:
      expected: 12
    severity: error
```
"""

import re
import yaml
from pathlib import Path


class RuleEngine:
    """自定义规则引擎"""

    SEVERITY_WEIGHT = {"error": 10, "warning": 5, "info": 1}

    def __init__(self):
        self.rules = []
        self.checkers = {
            "reference_count": self._check_reference_count,
            "body_font_size": self._check_body_font_size,
            "heading_exists": self._check_heading_exists,
            "abstract_exists": self._check_abstract_exists,
            "keywords_exists": self._check_keywords_exists,
            "figure_caption_format": self._check_figure_caption_format,
            "table_caption_format": self._check_table_caption_format,
            "page_margins": self._check_page_margins,
            "line_spacing": self._check_line_spacing,
            "first_line_indent": self._check_first_line_indent,
            "no_empty_paragraphs": self._check_no_empty_paragraphs,
            "font_consistency": self._check_font_consistency,
        }

    def load_rules(self, rules_path):
        """加载规则文件"""
        with open(rules_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.rules = data.get("rules", [])

    def load_rules_dict(self, rules_list):
        """直接加载规则列表"""
        self.rules = rules_list

    def check(self, doc, config):
        """执行所有规则检查"""
        results = []
        for rule in self.rules:
            checker = self.checkers.get(rule.get("check"))
            if not checker:
                results.append({
                    "rule": rule.get("name", "unknown"),
                    "status": "skip",
                    "message": f"未知检查类型: {rule.get('check')}",
                })
                continue

            params = rule.get("params", {})
            passed, message = checker(doc, config, params)
            results.append({
                "rule": rule.get("name", "unknown"),
                "check": rule.get("check"),
                "severity": rule.get("severity", "info"),
                "status": "pass" if passed else "fail",
                "message": message,
            })

        return results

    def format_report(self, results):
        """格式化检查报告"""
        lines = []
        lines.append("=" * 50)
        lines.append("  自定义规则检查报告")
        lines.append("=" * 50)

        passed = sum(1 for r in results if r["status"] == "pass")
        failed = sum(1 for r in results if r["status"] == "fail")
        skipped = sum(1 for r in results if r["status"] == "skip")

        lines.append(f"\n  通过: {passed}  失败: {failed}  跳过: {skipped}")

        # 扣分
        total_deduct = 0
        for r in results:
            if r["status"] == "fail":
                deduct = self.SEVERITY_WEIGHT.get(r.get("severity", "info"), 1)
                total_deduct += deduct

        score = max(0, 100 - total_deduct)
        lines.append(f"  规则得分: {score}/100")

        lines.append("\n  详细结果:")
        for r in results:
            icon = {"pass": "+", "fail": "x", "skip": "-"}.get(r["status"], "?")
            sev = r.get("severity", "info").upper()
            lines.append(f"    [{icon}] [{sev}] {r['rule']}")
            if r["message"]:
                lines.append(f"        {r['message']}")

        lines.append("=" * 50)
        return "\n".join(lines)

    # ========== 检查器 ==========

    def _check_reference_count(self, doc, config, params):
        max_count = params.get("max", 100)
        ref_start = None
        ref_keywords = config.get("auto_detect", {}).get("reference_keywords", ["参考文献"])

        for i, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if text in ref_keywords or any(text.startswith(kw) for kw in ref_keywords):
                ref_start = i
                break

        if ref_start is None:
            return True, "未找到参考文献"

        count = 0
        for i in range(ref_start + 1, len(doc.paragraphs)):
            text = doc.paragraphs[i].text.strip()
            if not text:
                continue
            if re.match(r"^第[一二三四五六七八九十\d]+[章部分篇]", text):
                break
            if re.match(r"^\[\d+\]", text) or re.match(r"^\d+[\.\)]", text):
                count += 1

        if count > max_count:
            return False, f"参考文献{count}篇，超过上限{max_count}篇"
        return True, f"参考文献{count}篇，符合要求"

    def _check_body_font_size(self, doc, config, params):
        expected = params.get("expected", 12)
        body_config = config.get("format_rules", {}).get("body_text", {})
        actual = body_config.get("font_size", 12)
        if abs(actual - expected) > 0.5:
            return False, f"正文字号{actual}pt，应为{expected}pt"
        return True, f"正文字号{actual}pt，符合要求"

    def _check_heading_exists(self, doc, config, params):
        pattern = params.get("pattern", r"^第[一二三四五六七八九十\d]+[章部分篇]")
        for para in doc.paragraphs:
            if re.match(pattern, para.text.strip()):
                return True, "检测到标题"
        return False, "未检测到标题"

    def _check_abstract_exists(self, doc, config, params):
        for para in doc.paragraphs:
            text = para.text.strip()
            if re.match(r"^摘\s*要$|^Abstract$|^ABSTRACT$", text):
                return True, "检测到摘要"
        return False, "未检测到摘要"

    def _check_keywords_exists(self, doc, config, params):
        for para in doc.paragraphs:
            if re.match(r"^关键词[:：]|^Key\s*[Ww]ords", para.text.strip()):
                return True, "检测到关键词"
        return False, "未检测到关键词"

    def _check_figure_caption_format(self, doc, config, params):
        pattern = params.get("pattern", r"^图\s*\d+")
        for para in doc.paragraphs:
            text = para.text.strip()
            if re.match(pattern, text):
                if not re.match(r"^图\s*\d+[\-\.]\d+\s+\S", text):
                    return False, f"图标题格式不规范: {text[:30]}"
                return True, "图标题格式正确"
        return True, "未检测到图标题"

    def _check_table_caption_format(self, doc, config, params):
        pattern = params.get("pattern", r"^表\s*\d+")
        for para in doc.paragraphs:
            text = para.text.strip()
            if re.match(pattern, text):
                if not re.match(r"^表\s*\d+[\-\.]\d+\s+\S", text):
                    return False, f"表标题格式不规范: {text[:30]}"
                return True, "表标题格式正确"
        return True, "未检测到表标题"

    def _check_page_margins(self, doc, config, params):
        expected = config.get("format_rules", {}).get("margins", {})
        if not expected:
            return True, "未设置边距要求"
        for section in doc.sections:
            top_cm = section.top_margin / 360000 if section.top_margin else 0
            expected_top = expected.get("top", 2.54)
            if abs(top_cm - expected_top) > 0.3:
                return False, f"上边距{top_cm:.1f}cm，应为{expected_top}cm"
        return True, "页面边距正确"

    def _check_line_spacing(self, doc, config, params):
        expected = params.get("expected", 1.5)
        body_config = config.get("format_rules", {}).get("body_text", {})
        actual = body_config.get("line_spacing", 1.5)
        if isinstance(actual, dict):
            actual = actual.get("value", 1.5)
        if abs(actual - expected) > 0.1:
            return False, f"行距{actual}，应为{expected}"
        return True, f"行距{actual}，符合要求"

    def _check_first_line_indent(self, doc, config, params):
        expected = params.get("expected", 2)
        body_config = config.get("format_rules", {}).get("body_text", {})
        actual = body_config.get("first_line_indent", 0)
        if actual != expected:
            return False, f"首行缩进{actual}字符，应为{expected}字符"
        return True, f"首行缩进{actual}字符，符合要求"

    def _check_no_empty_paragraphs(self, doc, config, params):
        max_empty = params.get("max", 5)
        count = 0
        for para in doc.paragraphs:
            if not para.text.strip():
                count += 1
        if count > max_empty:
            return False, f"空段落{count}个，超过上限{max_empty}个"
        return True, f"空段落{count}个，符合要求"

    def _check_font_consistency(self, doc, config, params):
        font_rules = config.get("format_rules", {}).get("font", {})
        cn_font = font_rules.get("chinese", "宋体")
        en_font = font_rules.get("english", "Times New Roman")

        mismatch = 0
        checked = 0
        for para in doc.paragraphs:
            if len(para.text.strip()) < 20:
                continue
            for run in para.runs:
                if run.font.name and run.font.name not in (cn_font, en_font):
                    mismatch += 1
                checked += 1
                if checked >= 100:
                    break
            if checked >= 100:
                break

        if mismatch > checked * 0.3:
            return False, f"字体不一致，{mismatch}/{checked}个run字体不符合要求"
        return True, "字体一致性检查通过"
