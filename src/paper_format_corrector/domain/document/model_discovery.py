"""模型发现与探测工具

通过API端点探测可用的LLM模型，支持：
- OpenAI兼容API (/v1/models)
- Ollama (/api/tags)
- Anthropic (探测已知模型列表)

工作流程：
1. 给定provider + api_key + base_url
2. 调用API的模型列表接口
3. 返回可用模型ID列表
4. 可选：探测单个模型是否可用
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

# OpenAI/兼容API 的基础端点
_OPENAI_DEFAULT_BASE = "https://api.openai.com/v1"
_ANTHROPIC_DEFAULT_BASE = "https://api.anthropic.com"
_OLLAMA_DEFAULT_BASE = "http://localhost:11434"

# Anthropic 没有 list models 接口，探测已知模型
_KNOWN_ANTHROPIC_MODELS = [
    "claude-opus-4-20250514",
    "claude-sonnet-4-20250514",
    "claude-3-5-haiku-20241022",
    "claude-3-5-sonnet-20241022",
    "claude-3-haiku-20240307",
    "claude-3-opus-20240229",
]


def _make_request(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 15,
) -> dict[str, Any] | None:
    """发送GET请求并返回JSON，失败返回None"""
    req = urllib.request.Request(url, method="GET")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None


def _post_request(
    url: str,
    data: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: int = 15,
) -> dict[str, Any] | None:
    """发送POST请求并返回JSON，失败返回None"""
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None


def list_openai_models(
    api_key: str,
    base_url: str | None = None,
) -> list[str]:
    """获取OpenAI/兼容API的模型列表

    Args:
        api_key: API密钥
        base_url: 自定义API端点（如 https://api.deepseek.com/v1）

    Returns:
        可用模型ID列表
    """
    url = (base_url or _OPENAI_DEFAULT_BASE).rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    result = _make_request(url, headers=headers, timeout=20)
    if not result or "data" not in result:
        return []
    return sorted({m.get("id", "") for m in result["data"] if m.get("id")})


def list_ollama_models(
    base_url: str | None = None,
) -> list[str]:
    """获取Ollama本地模型列表

    Args:
        base_url: Ollama服务地址

    Returns:
        可用模型名称列表
    """
    url = (base_url or _OLLAMA_DEFAULT_BASE).rstrip("/") + "/api/tags"
    result = _make_request(url, timeout=10)
    if not result or "models" not in result:
        return []
    return sorted({m.get("name", "") for m in result["models"] if m.get("name")})


def probe_anthropic_models(
    api_key: str,
    base_url: str | None = None,
) -> list[str]:
    """探测Anthropic可用模型（逐个尝试发送最小请求）

    Anthropic没有list models接口，只能逐个探测。

    Args:
        api_key: Anthropic API密钥
        base_url: 自定义API端点

    Returns:
        可用模型ID列表
    """
    available = []
    url = (base_url or _ANTHROPIC_DEFAULT_BASE).rstrip("/") + "/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    for model_id in _KNOWN_ANTHROPIC_MODELS:
        data = {
            "model": model_id,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "hi"}],
        }
        result = _post_request(url, data=data, headers=headers, timeout=15)
        if result is not None and "content" in result:
            available.append(model_id)

    return available


def list_models(
    provider: str,
    api_key: str | None = None,
    base_url: str | None = None,
) -> list[str]:
    """统一模型发现入口

    Args:
        provider: "openai" | "anthropic" | "ollama"
        api_key: API密钥（ollama不需要）
        base_url: 自定义端点

    Returns:
        可用模型ID列表，失败返回空列表
    """
    if provider == "openai":
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return []
        return list_openai_models(api_key, base_url)

    elif provider == "anthropic":
        if not api_key:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return []
        return probe_anthropic_models(api_key, base_url)

    elif provider == "ollama":
        return list_ollama_models(base_url)

    return []


def probe_model(
    provider: str,
    model: str,
    api_key: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """探测单个模型是否可用

    Args:
        provider: "openai" | "anthropic" | "ollama"
        model: 模型ID（支持任意用户输入的名称）
        api_key: API密钥
        base_url: 自定义端点

    Returns:
        {
            "available": bool,
            "model": str,
            "provider": str,
            "latency_ms": float | None,
            "error": str | None,
            "details": dict  # 原始响应中的额外信息
        }
    """
    import time

    if provider == "openai":
        return _probe_openai(model, api_key, base_url, time)
    elif provider == "anthropic":
        return _probe_anthropic(model, api_key, base_url, time)
    elif provider == "ollama":
        return _probe_ollama(model, base_url, time)

    return {
        "available": False,
        "model": model,
        "provider": provider,
        "latency_ms": None,
        "error": f"不支持的provider: {provider}",
        "details": {},
    }


def _probe_openai(
    model: str,
    api_key: str | None,
    base_url: str | None,
    time_mod: Any,
) -> dict[str, Any]:
    """探测OpenAI/兼容模型"""
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return {
            "available": False,
            "model": model,
            "provider": "openai",
            "latency_ms": None,
            "error": "未配置API Key",
            "details": {},
        }

    url = (base_url or _OPENAI_DEFAULT_BASE).rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
        "temperature": 0,
    }

    t0 = time_mod.time()
    result = _post_request(url, data=data, headers=headers, timeout=20)
    latency = round((time_mod.time() - t0) * 1000, 1)

    if result and "choices" in result:
        return {
            "available": True,
            "model": model,
            "provider": "openai",
            "latency_ms": latency,
            "error": None,
            "details": {"usage": result.get("usage", {})},
        }
    elif result and "error" in result:
        return {
            "available": False,
            "model": model,
            "provider": "openai",
            "latency_ms": latency,
            "error": result["error"].get("message", str(result["error"])),
            "details": result,
        }
    else:
        return {
            "available": False,
            "model": model,
            "provider": "openai",
            "latency_ms": latency,
            "error": "无响应或格式异常",
            "details": result or {},
        }


def _probe_anthropic(
    model: str,
    api_key: str | None,
    base_url: str | None,
    time_mod: Any,
) -> dict[str, Any]:
    """探测Anthropic模型"""
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {
            "available": False,
            "model": model,
            "provider": "anthropic",
            "latency_ms": None,
            "error": "未配置API Key",
            "details": {},
        }

    url = (base_url or _ANTHROPIC_DEFAULT_BASE).rstrip("/") + "/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    data = {
        "model": model,
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "hi"}],
    }

    t0 = time_mod.time()
    result = _post_request(url, data=data, headers=headers, timeout=20)
    latency = round((time_mod.time() - t0) * 1000, 1)

    if result and "content" in result:
        return {
            "available": True,
            "model": model,
            "provider": "anthropic",
            "latency_ms": latency,
            "error": None,
            "details": {"usage": result.get("usage", {})},
        }
    elif result and "error" in result:
        return {
            "available": False,
            "model": model,
            "provider": "anthropic",
            "latency_ms": latency,
            "error": result["error"].get("message", str(result["error"])),
            "details": result,
        }
    else:
        return {
            "available": False,
            "model": model,
            "provider": "anthropic",
            "latency_ms": latency,
            "error": "无响应或格式异常",
            "details": result or {},
        }


def _probe_ollama(
    model: str,
    base_url: str | None,
    time_mod: Any,
) -> dict[str, Any]:
    """探测Ollama模型"""
    url = (base_url or _OLLAMA_DEFAULT_BASE).rstrip("/") + "/api/chat"
    data = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "stream": False,
        "options": {"num_predict": 1},
    }

    t0 = time_mod.time()
    result = _post_request(url, data=data, timeout=30)
    latency = round((time_mod.time() - t0) * 1000, 1)

    if result and "message" in result:
        return {
            "available": True,
            "model": model,
            "provider": "ollama",
            "latency_ms": latency,
            "error": None,
            "details": {},
        }
    elif result and "error" in result:
        return {
            "available": False,
            "model": model,
            "provider": "ollama",
            "latency_ms": latency,
            "error": result["error"],
            "details": result,
        }
    else:
        return {
            "available": False,
            "model": model,
            "provider": "ollama",
            "latency_ms": latency,
            "error": "模型未下载或服务不可用",
            "details": result or {},
        }
