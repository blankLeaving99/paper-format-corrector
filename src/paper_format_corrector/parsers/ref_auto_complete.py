"""参考文献自动补全模块

通过 CrossRef API 根据论文标题/DOI 自动补全缺失的元数据：
- 卷号(volume)
- 期号(number)
- 页码(pages)
- DOI
- 完整作者名
"""

import re
import json
import urllib.request
import urllib.parse
import time


class RefAutoComplete:
    """参考文献自动补全器"""

    API_BASE = "https://api.crossref.org"

    def __init__(self, email=None):
        self.email = email
        self.cache = {}
        self.rate_limit_delay = 1.0  # 秒
        self._last_request = 0

    def complete_references(self, doc, ref_start_idx):
        """补全参考文献列表"""
        paragraphs = doc.paragraphs
        results = []

        ref_num = 0
        for i in range(ref_start_idx + 1, len(paragraphs)):
            text = paragraphs[i].text.strip()
            if not text:
                continue
            if re.match(r"^第[一二三四五六七八九十\d]+[章部分篇]", text):
                break

            ref_num += 1
            result = self._complete_single_ref(text, ref_num)
            if result:
                results.append(result)

        return results

    def _complete_single_ref(self, text, num):
        """补全单条参考文献"""
        # 提取标题
        title = self._extract_title(text)
        if not title:
            return None

        # 先查缓存
        if title.lower() in self.cache:
            return self._merge_ref(text, self.cache[title.lower()], num)

        # 调用 CrossRef API
        metadata = self._query_crossref(title)
        if metadata:
            self.cache[title.lower()] = metadata
            return self._merge_ref(text, metadata, num)

        return None

    def _extract_title(self, text):
        """从参考文献文本中提取标题"""
        # 去掉编号
        text = re.sub(r"^\[\d+\]\s*", "", text)
        text = re.sub(r"^\d+[\.\)]\s*", "", text)

        # 去掉文献类型标识
        text = re.sub(r"\[[A-Z/]+\]\s*", "", text)

        # 提取标题（在作者之后，期刊之前）
        # 尝试匹配 "作者. 标题[J]. 期刊" 模式
        m = re.search(r"[\.\。]\s*(.+?)[\[【]", text)
        if m:
            return m.group(1).strip()

        # 尝试匹配英文格式 "Author. Title[J]."
        m = re.search(r"\.\s*(.+?)\s*\[", text)
        if m:
            return m.group(1).strip()

        # 回退：取去掉作者后的部分
        parts = re.split(r"[\.\。]\s*", text, maxsplit=2)
        if len(parts) >= 2:
            return parts[1].strip()

        return text[:100]

    def _query_crossref(self, title):
        """查询 CrossRef API"""
        self._rate_limit()

        params = {
            "query.title": title,
            "rows": 1,
        }
        if self.email:
            params["mailto"] = self.email

        url = f"{self.API_BASE}/works?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "PaperFormatCorrector/1.0")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            items = data.get("message", {}).get("items", [])
            if not items:
                return None

            item = items[0]
            return {
                "title": self._get_field(item, "title"),
                "authors": self._get_authors(item),
                "journal": self._get_field(item, "container-title"),
                "year": self._get_year(item),
                "volume": self._get_field(item, "volume"),
                "number": self._get_field(item, "issue"),
                "pages": self._get_field(item, "page"),
                "doi": self._get_field(item, "DOI"),
            }
        except Exception as e:
            return None

    def _get_field(self, item, field):
        val = item.get(field)
        if isinstance(val, list):
            return val[0] if val else ""
        return str(val) if val else ""

    def _get_authors(self, item):
        authors = item.get("author", [])
        result = []
        for a in authors[:6]:
            family = a.get("family", "")
            given = a.get("given", "")
            if family:
                result.append(f"{family} {given}".strip())
        return ", ".join(result)

    def _get_year(self, item):
        dp = item.get("published-print") or item.get("published-online") or item.get("created")
        if dp:
            parts = dp.get("date-parts", [[]])[0]
            if parts:
                return str(parts[0])
        return ""

    def _merge_ref(self, original, metadata, num):
        """合并原始文本和API返回的元数据"""
        return {
            "num": num,
            "original": original,
            "metadata": metadata,
            "suggestions": [],
        }

    def _rate_limit(self):
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request = time.time()
