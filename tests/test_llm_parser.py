"""LLM 解析器安全测试

测试 URL 验证和 JSON 解析的安全性。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest

# ── URL 验证测试 ────────────────────────────────────────────────────


class TestLLMParserURLValidation:
    """测试 LLM URL 安全验证"""

    def _validate_url(self, url, provider="openai"):
        """辅助方法：调用 URL 验证"""
        from paper_format_corrector.core.document.llm_parser import LLMParser
        parser = LLMParser(provider=provider, api_key="test")
        return parser._validate_url(url)

    def test_rejects_private_ip_192(self):
        """应拒绝 192.168.x.x"""
        with pytest.raises(ValueError, match="内网"):
            self._validate_url("https://192.168.1.1/v1/chat")

    def test_rejects_private_ip_10(self):
        """应拒绝 10.x.x.x"""
        with pytest.raises(ValueError, match="内网"):
            self._validate_url("https://10.0.0.1/v1/chat")

    def test_rejects_cloud_metadata(self):
        """应拒绝云元数据地址"""
        with pytest.raises(ValueError, match="内网"):
            self._validate_url("https://169.254.169.254/metadata")

    def test_rejects_non_https(self):
        """应拒绝非 HTTPS（localhost 除外）"""
        with pytest.raises(ValueError):
            self._validate_url("http://api.openai.com/v1/chat")

    def test_allows_localhost_http(self):
        """应允许 localhost HTTP（ollama）"""
        # 不应抛出异常
        result = self._validate_url("http://localhost:11434/api/chat", provider="ollama")
        assert result is not None

    def test_rejects_empty_host(self):
        """应拒绝空主机名"""
        with pytest.raises(ValueError):
            self._validate_url("https:///v1/chat")

    def test_allows_valid_https(self):
        """应允许有效的 HTTPS URL"""
        result = self._validate_url("https://api.openai.com/v1/chat")
        assert result is not None


# ── JSON 解析测试 ────────────────────────────────────────────────────


class TestLLMParserJSONParsing:
    """测试 LLM JSON 响应解析"""

    def _parse_json(self, response):
        """辅助方法：调用 JSON 解析"""
        from paper_format_corrector.core.document.llm_parser import LLMParser
        parser = LLMParser(provider="openai", api_key="test")
        return parser._parse_json_response(response)

    def test_parses_raw_json(self):
        """应解析纯 JSON"""
        result = self._parse_json('{"body_text": {"font_size": 12}}')
        assert result["body_text"]["font_size"] == 12

    def test_parses_fenced_json(self):
        """应解析 markdown 围栏 JSON"""
        response = '```json\n{"body_text": {"font_size": 12}}\n```'
        result = self._parse_json(response)
        assert result["body_text"]["font_size"] == 12

    def test_parses_embedded_json(self):
        """应从文本中提取 JSON"""
        response = 'Here is the config:\n{"body_text": {"font_size": 12}}\nDone.'
        result = self._parse_json(response)
        assert result["body_text"]["font_size"] == 12

    def test_raises_on_invalid_json(self):
        """无效 JSON 应抛出 ValueError"""
        with pytest.raises(ValueError):
            self._parse_json("this is not json at all")

    def test_raises_on_empty_response(self):
        """空响应应抛出 ValueError"""
        with pytest.raises(ValueError):
            self._parse_json("")
