"""LLM智能解析需求文档

接入大语言模型，理解复杂/模糊的格式需求描述，
输出结构化的格式规则JSON。

支持的LLM提供商：
- OpenAI (GPT-4/GPT-3.5)
- Anthropic (Claude)
- 本地模型 (Ollama/任意OpenAI兼容API)

工作流程：
1. 读取需求文档全文
2. 构造prompt让LLM提取格式规则
3. 解析LLM返回的JSON
4. 转换为标准config格式
5. 失败时fallback到正则解析
"""

import re
import json
import os
import ipaddress
from pathlib import Path
from urllib.parse import urlparse


# LLM 提取格式规则的 prompt
EXTRACT_PROMPT = """你是一个论文格式规则提取专家。请从以下文档中提取所有论文格式要求，输出为JSON格式。

要求：
1. 提取每个部分的字体、字号、对齐方式、是否加粗、行距、缩进等
2. 中文字号请转换为pt值（初号=42, 小初=36, 一号=26, 小一=24, 二号=22, 小二=18, 三号=16, 小三=15, 四号=14, 小四=12, 五号=10.5, 小五=9）
3. 行距用数字表示（如1.5倍行距=1.5, 固定值20磅={"type":"exact","value":20}）
4. 如果文档提到"页边距"，也提取出来

请严格按以下JSON格式输出，不要有多余文字：

```json
{
  "title_page": {
    "title_font_size": 22,
    "title_bold": true,
    "title_align": "center",
    "title_chinese_font": "黑体"
  },
  "headings": {
    "heading1": {"font_size": 22, "bold": true, "align": "center", "chinese_font": "黑体"},
    "heading2": {"font_size": 16, "bold": true, "align": "left", "chinese_font": "黑体"},
    "heading3": {"font_size": 14, "bold": true, "align": "left", "chinese_font": "黑体"}
  },
  "body_text": {
    "font_size": 12,
    "chinese_font": "宋体",
    "english_font": "Times New Roman",
    "line_spacing": 1.5,
    "first_line_indent": 2,
    "align": "justify"
  },
  "abstract": {
    "title_font_size": 16,
    "title_bold": true,
    "content_font_size": 12,
    "content_line_spacing": 1.5
  },
  "keywords": {
    "font_size": 12,
    "bold_label": true
  },
  "references": {
    "font_size": 10.5,
    "line_spacing": 1.25,
    "hanging_indent": true
  },
  "margins": {
    "top": 2.54,
    "bottom": 2.54,
    "left": 3.17,
    "right": 3.17
  },
  "header_footer": {
    "header": {"text": "", "font_size": 10.5},
    "footer": {"page_number": true}
  }
}
```

以下是需要提取格式规则的文档内容：

---
{document_text}
---

请输出JSON："""


class LLMParser:
    """LLM智能需求文档解析器"""

    # 允许的外部 API 域名白名单
    ALLOWED_DOMAINS = {
        "api.openai.com",
        "api.anthropic.com",
        "localhost",
        "127.0.0.1",
    }

    def __init__(self, provider="openai", api_key=None, base_url=None, model=None):
        self.provider = provider
        self.api_key = api_key or self._get_default_key()
        self.base_url = self._validate_url(base_url) if base_url else None
        self.model = model or self._get_default_model()

    def _validate_url(self, url):
        """校验 URL 安全性"""
        parsed = urlparse(url)
        host = parsed.hostname or ""

        if not host:
            raise ValueError(f"URL 缺少主机名: {url}")

        # 阻止内网/环回/链路本地 IP 地址
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                if self.provider != "ollama":
                    raise ValueError(f"不允许访问内网地址: {host}")
            if str(ip) == "169.254.169.254":
                raise ValueError("不允许访问云服务商元数据地址")
        except ValueError:
            raise  # 重新抛出我们自己抛出的 ValueError
        except ipaddress.AddressValueError:
            pass  # 不是 IP 地址，是域名，继续检查

        # Ollama 只允许 localhost
        if self.provider == "ollama":
            if host not in ("localhost", "127.0.0.1"):
                raise ValueError(f"Ollama 仅支持 localhost，不允许远程地址: {host}")
            return url

        # 外部 API 必须使用 HTTPS（localhost 除外）
        if parsed.scheme not in ("https",):
            if parsed.scheme == "http" and host in ("localhost", "127.0.0.1"):
                return url
            raise ValueError(f"不允许的 URL 协议: {parsed.scheme}")

        # 检查域名白名单（自定义 base_url 时）
        if host not in self.ALLOWED_DOMAINS:
            raise ValueError(f"不允许的 API 域名: {host}，允许: {self.ALLOWED_DOMAINS}")

        return url

    def _get_default_key(self):
        """从环境变量获取API Key"""
        if self.provider == "openai":
            return os.environ.get("OPENAI_API_KEY", "")
        elif self.provider == "anthropic":
            return os.environ.get("ANTHROPIC_API_KEY", "")
        elif self.provider == "ollama":
            return "ollama"
        return ""

    def _get_default_model(self):
        if self.provider == "openai":
            return "gpt-4o-mini"
        elif self.provider == "anthropic":
            return "claude-sonnet-4-20250514"
        elif self.provider == "ollama":
            return "qwen2.5:7b"
        return "gpt-4o-mini"

    def parse(self, document_text):
        """用LLM解析需求文档，返回config字典"""
        if not self.api_key:
            raise ValueError(
                f"未配置 {self.provider} 的API Key。"
                f"请设置环境变量或在初始化时传入api_key参数。\n"
                f"  OpenAI: export OPENAI_API_KEY=sk-xxx\n"
                f"  Anthropic: export ANTHROPIC_API_KEY=sk-ant-xxx\n"
                f"  Ollama: 无需Key，确保服务运行在 localhost:11434"
            )

        # 截断过长的文档
        if len(document_text) > 8000:
            document_text = document_text[:8000] + "\n...(文档已截断)"

        prompt = EXTRACT_PROMPT.format(document_text=document_text)

        try:
            response = self._call_llm(prompt)
            config = self._parse_json_response(response)
            return config
        except Exception as e:
            print(f"LLM解析失败: {e}")
            print("将回退到正则解析...")
            return None

    def _call_llm(self, prompt):
        """调用LLM API"""
        if self.provider == "openai":
            return self._call_openai(prompt)
        elif self.provider == "anthropic":
            return self._call_anthropic(prompt)
        elif self.provider == "ollama":
            return self._call_ollama(prompt)
        else:
            raise ValueError(f"不支持的LLM提供商: {self.provider}")

    def _call_openai(self, prompt):
        """调用OpenAI API"""
        import urllib.request

        base_url = self.base_url or "https://api.openai.com/v1"
        url = f"{base_url}/chat/completions"

        data = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是论文格式规则提取专家。只输出JSON，不要多余文字。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]

    def _call_anthropic(self, prompt):
        """调用Anthropic Claude API"""
        import urllib.request

        base_url = self.base_url or "https://api.anthropic.com"
        url = f"{base_url}/v1/messages"

        data = json.dumps({
            "model": self.model,
            "max_tokens": 2000,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("x-api-key", self.api_key)
        req.add_header("anthropic-version", "2023-06-01")

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["content"][0]["text"]

    def _call_ollama(self, prompt):
        """调用本地Ollama API"""
        import urllib.request

        base_url = self.base_url or "http://localhost:11434"
        url = f"{base_url}/api/generate"

        data = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["response"]

    def _parse_json_response(self, response):
        """从LLM响应中提取JSON"""
        # 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 尝试从markdown代码块中提取
        m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试找到第一个 { 到最后一个 }
        start = response.find("{")
        end = response.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(response[start:end + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError(f"无法从LLM响应中提取JSON:\n{response[:500]}")


def llm_parse_to_config(llm_config_dict):
    """将LLM输出的字典转换为标准config格式"""
    config = {"format_rules": {}}

    # 字体
    font = {}
    if "body_text" in llm_config_dict:
        bt = llm_config_dict["body_text"]
        if "chinese_font" in bt:
            font["chinese"] = bt["chinese_font"]
        if "english_font" in bt:
            font["english"] = bt["english_font"]

    # 从标题中提取 heading_chinese
    headings_data = llm_config_dict.get("headings", {})
    for h in headings_data.values():
        if isinstance(h, dict) and "chinese_font" in h:
            font["heading_chinese"] = h["chinese_font"]
            break

    if font:
        config["format_rules"]["font"] = font

    # 标题
    headings = {}
    for key in ("heading1", "heading2", "heading3"):
        if key in headings_data:
            h = headings_data[key]
            headings[key] = {
                k: v for k, v in h.items()
                if k in ("font_size", "bold", "align", "line_spacing")
            }
    if headings:
        config["format_rules"]["headings"] = headings

    # 正文
    if "body_text" in llm_config_dict:
        bt = llm_config_dict["body_text"]
        body = {}
        for k in ("font_size", "line_spacing", "first_line_indent", "align"):
            if k in bt:
                body[k] = bt[k]
        if body:
            config["format_rules"]["body_text"] = body

    # 摘要
    if "abstract" in llm_config_dict:
        config["format_rules"]["abstract"] = llm_config_dict["abstract"]

    # 关键词
    if "keywords" in llm_config_dict:
        config["format_rules"]["keywords"] = llm_config_dict["keywords"]

    # 参考文献
    if "references" in llm_config_dict:
        config["format_rules"]["references"] = llm_config_dict["references"]

    # 页边距
    if "margins" in llm_config_dict:
        config["format_rules"]["margins"] = llm_config_dict["margins"]

    # 页眉页脚
    if "header_footer" in llm_config_dict:
        config["format_rules"]["header_footer"] = llm_config_dict["header_footer"]

    # 题目页
    if "title_page" in llm_config_dict:
        tp = llm_config_dict["title_page"]
        config["format_rules"]["title_page"] = tp

    return config
