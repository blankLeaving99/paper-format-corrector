"""Tests for model discovery and probing."""

from unittest.mock import patch

import pytest

from paper_format_corrector.parsers.ai_doc_generator import AIDocGenerator
from paper_format_corrector.parsers.llm_parser import LLMParser
from paper_format_corrector.parsers.model_discovery import (
    _KNOWN_ANTHROPIC_MODELS,
    list_models,
    list_ollama_models,
    list_openai_models,
    probe_anthropic_models,
    probe_model,
)


class TestListOpenAIModels:
    """Tests for OpenAI model listing."""

    def test_returns_sorted_model_ids(self):
        mock_resp = {
            "data": [
                {"id": "gpt-4o"},
                {"id": "gpt-4o-mini"},
                {"id": "gpt-4o-2024-11-20"},
            ]
        }
        with patch("paper_format_corrector.parsers.model_discovery._make_request",
                    return_value=mock_resp):
            result = list_openai_models("sk-test")
        assert result == ["gpt-4o", "gpt-4o-2024-11-20", "gpt-4o-mini"]

    def test_deduplicates_models(self):
        mock_resp = {
            "data": [
                {"id": "gpt-4o"},
                {"id": "gpt-4o"},
            ]
        }
        with patch("paper_format_corrector.parsers.model_discovery._make_request",
                    return_value=mock_resp):
            result = list_openai_models("sk-test")
        assert result == ["gpt-4o"]

    def test_returns_empty_on_failure(self):
        with patch("paper_format_corrector.parsers.model_discovery._make_request",
                    return_value=None):
            result = list_openai_models("sk-test")
        assert result == []

    def test_filters_empty_ids(self):
        mock_resp = {"data": [{"id": "gpt-4o"}, {"id": ""}, {}]}
        with patch("paper_format_corrector.parsers.model_discovery._make_request",
                    return_value=mock_resp):
            result = list_openai_models("sk-test")
        assert result == ["gpt-4o"]

    def test_uses_custom_base_url(self):
        mock_resp = {"data": [{"id": "deepseek-chat"}]}
        with patch("paper_format_corrector.parsers.model_discovery._make_request",
                    return_value=mock_resp) as mock_req:
            list_openai_models("sk-test", base_url="https://api.deepseek.com/v1")
            call_url = mock_req.call_args[0][0]
            assert call_url == "https://api.deepseek.com/v1/models"


class TestListOllamaModels:
    """Tests for Ollama model listing."""

    def test_returns_sorted_names(self):
        mock_resp = {
            "models": [
                {"name": "qwen2.5:7b"},
                {"name": "llama3:8b"},
            ]
        }
        with patch("paper_format_corrector.parsers.model_discovery._make_request",
                    return_value=mock_resp):
            result = list_ollama_models()
        assert result == ["llama3:8b", "qwen2.5:7b"]

    def test_returns_empty_on_failure(self):
        with patch("paper_format_corrector.parsers.model_discovery._make_request",
                    return_value=None):
            result = list_ollama_models()
        assert result == []


class TestProbeModel:
    """Tests for model probing."""

    def test_openai_probe_success(self):
        mock_resp = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
        with patch("paper_format_corrector.parsers.model_discovery._post_request",
                    return_value=mock_resp):
            result = probe_model("openai", "gpt-4o", api_key="sk-test")
        assert result["available"] is True
        assert result["model"] == "gpt-4o"
        assert result["provider"] == "openai"
        assert result["latency_ms"] is not None
        assert result["error"] is None

    def test_openai_probe_failure(self):
        mock_resp = {
            "error": {"message": "model not found", "type": "invalid_request_error"},
        }
        with patch("paper_format_corrector.parsers.model_discovery._post_request",
                    return_value=mock_resp):
            result = probe_model("openai", "nonexistent", api_key="sk-test")
        assert result["available"] is False
        assert "model not found" in result["error"]

    def test_openai_probe_no_key(self):
        with patch.dict("os.environ", {}, clear=True):
            result = probe_model("openai", "gpt-4o", api_key=None)
        assert result["available"] is False
        assert "未配置API Key" in result["error"]

    def test_anthropic_probe_success(self):
        mock_resp = {"content": [{"text": "ok"}], "usage": {"input_tokens": 1}}
        with patch("paper_format_corrector.parsers.model_discovery._post_request",
                    return_value=mock_resp):
            result = probe_model("anthropic", "claude-sonnet-4-20250514",
                                 api_key="sk-ant-test")
        assert result["available"] is True
        assert result["model"] == "claude-sonnet-4-20250514"

    def test_anthropic_probe_failure(self):
        mock_resp = {"error": {"message": "unknown model"}}
        with patch("paper_format_corrector.parsers.model_discovery._post_request",
                    return_value=mock_resp):
            result = probe_model("anthropic", "fake-model", api_key="sk-ant-test")
        assert result["available"] is False

    def test_ollama_probe_success(self):
        mock_resp = {"message": {"content": "ok"}}
        with patch("paper_format_corrector.parsers.model_discovery._post_request",
                    return_value=mock_resp):
            result = probe_model("ollama", "qwen2.5:7b")
        assert result["available"] is True
        assert result["provider"] == "ollama"

    def test_ollama_probe_failure(self):
        mock_resp = {"error": "model not found"}
        with patch("paper_format_corrector.parsers.model_discovery._post_request",
                    return_value=mock_resp):
            result = probe_model("ollama", "nonexistent")
        assert result["available"] is False

    def test_unknown_provider(self):
        result = probe_model("unknown", "model")
        assert result["available"] is False
        assert "不支持的provider" in result["error"]

    def test_probe_returns_none_response(self):
        with patch("paper_format_corrector.parsers.model_discovery._post_request",
                    return_value=None):
            result = probe_model("openai", "gpt-4o", api_key="sk-test")
        assert result["available"] is False
        assert "无响应" in result["error"]

    def test_probe_latency_measured(self):
        mock_resp = {"choices": [{"message": {"content": "ok"}}]}
        with patch("paper_format_corrector.parsers.model_discovery._post_request",
                    return_value=mock_resp), \
             patch("time.time", side_effect=[0.0, 0.1]):
            result = probe_model("openai", "gpt-4o", api_key="sk-test")
        assert result["latency_ms"] == 100.0


class TestProbeAnthropicModels:
    """Tests for Anthropic model probing (batch)."""

    def test_probes_known_models(self):
        mock_resp = {"content": [{"text": "ok"}]}
        with patch("paper_format_corrector.parsers.model_discovery._post_request",
                    return_value=mock_resp) as mock_req:
            result = probe_anthropic_models("sk-ant-test")
        assert len(result) == len(_KNOWN_ANTHROPIC_MODELS)
        assert mock_req.call_count == len(_KNOWN_ANTHROPIC_MODELS)

    def test_returns_only_working_models(self):
        def side_effect(url, data=None, headers=None, timeout=15):
            model = data.get("model", "") if data else ""
            if "sonnet" in model:
                return {"content": [{"text": "ok"}]}
            return None

        with patch("paper_format_corrector.parsers.model_discovery._post_request",
                    side_effect=side_effect):
            result = probe_anthropic_models("sk-ant-test")
        assert all("sonnet" in m for m in result)


class TestLLMParserDiscovery:
    """Tests for LLMParser model discovery integration."""

    def test_class_method_discover_models(self):
        mock_resp = {"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]}
        with patch("paper_format_corrector.parsers.model_discovery._make_request",
                    return_value=mock_resp):
            result = LLMParser.discover_models("openai", api_key="sk-test")
        assert "gpt-4o" in result
        assert "gpt-4o-mini" in result

    def test_class_method_probe_model(self):
        mock_resp = {"choices": [{"message": {"content": "ok"}}]}
        with patch("paper_format_corrector.parsers.model_discovery._post_request",
                    return_value=mock_resp):
            result = LLMParser.probe_model("openai", "gpt-4o", api_key="sk-test")
        assert result["available"] is True

    def test_class_method_probe_custom_models(self):
        mock_resp = {"choices": [{"message": {"content": "ok"}}]}
        with patch("paper_format_corrector.parsers.model_discovery._post_request",
                    return_value=mock_resp):
            results = LLMParser.probe_custom_models(
                "openai", ["model-a", "model-b"], api_key="sk-test"
            )
        assert len(results) == 2
        assert all(r["available"] for r in results)

    def test_allow_custom_base_url_relaxes_validation(self):
        """Custom base_url should be accepted when allow_custom_base_url=True"""
        parser = LLMParser(
            provider="openai",
            base_url="https://api.deepseek.com/v1",
            allow_custom_base_url=True,
        )
        assert parser.base_url == "https://api.deepseek.com/v1"

    def test_strict_mode_rejects_unknown_domain(self):
        """Strict mode (default) should reject unknown domains"""
        with pytest.raises(ValueError, match="不允许的 API 域名"):
            LLMParser(
                provider="openai",
                base_url="https://api.deepseek.com/v1",
            )


class TestAIDocGeneratorDiscovery:
    """Tests for AIDocGenerator model discovery integration."""

    def test_class_method_discover_models(self):
        mock_resp = {"data": [{"id": "gpt-4o"}]}
        with patch("paper_format_corrector.parsers.model_discovery._make_request",
                    return_value=mock_resp):
            result = AIDocGenerator.discover_models("openai", api_key="sk-test")
        assert "gpt-4o" in result

    def test_class_method_probe_model(self):
        mock_resp = {"choices": [{"message": {"content": "ok"}}]}
        with patch("paper_format_corrector.parsers.model_discovery._post_request",
                    return_value=mock_resp):
            result = AIDocGenerator.probe_model("openai", "gpt-4o", api_key="sk-test")
        assert result["available"] is True

    def test_allow_custom_base_url(self):
        gen = AIDocGenerator(
            provider="openai",
            base_url="https://api.deepseek.com/v1",
            allow_custom_base_url=True,
        )
        assert gen.base_url == "https://api.deepseek.com/v1"


class TestListModelsUnified:
    """Tests for the unified list_models function."""

    def test_openai_requires_key(self):
        with patch.dict("os.environ", {}, clear=True):
            result = list_models("openai", api_key=None)
        assert result == []

    def test_ollama_does_not_require_key(self):
        mock_resp = {"models": [{"name": "qwen2.5:7b"}]}
        with patch("paper_format_corrector.parsers.model_discovery._make_request",
                    return_value=mock_resp):
            result = list_models("ollama")
        assert result == ["qwen2.5:7b"]

    def test_unknown_provider_returns_empty(self):
        result = list_models("unknown")
        assert result == []
