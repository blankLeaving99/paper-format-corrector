"""AI文档内容生成器 v2

通过LLM根据用户自然语言输入生成结构化的文档JSON，
支持流式输出、多轮对话、大纲生成、逐节内容填充。

工作流程：
1. 用户输入描述 → AI自动识别文档类型
2. AI生成大纲（标题+摘要） → 用户确认/修改
3. AI逐节流式生成内容 → 实时显示
4. 用户可编辑内容 → 最终导出docx

支持的LLM提供商：
- OpenAI (GPT-4/GPT-3.5)
- Anthropic (Claude)
- 本地模型 (Ollama)
- DeepSeek (深度求索)
- 通义千问 (阿里云)
- 智谱 AI (GLM)
- 月之暗面 (Kimi)
- 百川智能
- 阶跃星辰
- 零一万物 (Yi)
- MiniMax (海螺AI)
- 讯飞星火
- 硅基流动 (SiliconFlow)
- 任意 OpenAI 兼容 API
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Generator
from typing import Any

# ---------- Prompt 模板 ----------

SYSTEM_PROMPT = """你是一个专业的文档撰写助手。你的任务是帮助用户创建格式化的Word文档。

工作方式：
1. 首先理解用户需求，识别文档类型
2. 生成文档大纲（仅标题结构，不含正文）
3. 用户确认大纲后，逐节生成详细正文内容
4. 支持用户修改和调整

重要规则：
- 输出必须是合法JSON
- 正文内容每段200-500字
- 使用中文写作（除非用户要求英文）
- 标题层级清晰（heading1 > heading2 > heading3）
- 适当包含表格和列表"""

OUTLINE_PROMPT = """根据以下用户描述，生成文档大纲。

要求：
1. 仅生成标题结构，不含正文内容
2. 每个标题包含简短说明（1-2句话概述该节内容）
3. 标题层级合理（heading1 > heading2 > heading3）
4. 包含文档标题和摘要

用户描述：
{user_input}

文档类型：{doc_type}

请严格按以下JSON格式输出：

```json
{{
  "doc_type": "识别出的文档类型",
  "title": "文档标题",
  "abstract": "文档摘要（2-3句话概述全文）",
  "outline": [
    {{
      "type": "heading1",
      "title": "一、章节标题",
      "description": "本节概述..."
    }},
    {{
      "type": "heading2",
      "title": "1.1 子章节标题",
      "description": "本节概述..."
    }}
  ]
}}
```"""

SECTION_CONTENT_PROMPT = """为以下文档章节生成详细正文内容。

文档信息：
- 标题：{title}
- 类型：{doc_type}
- 摘要：{abstract}

当前章节：
- 标题：{section_title}
- 层级：{section_type}
- 概述：{section_description}

上下文（前后章节标题）：
{context}

要求：
1. 内容专业、充实、有深度
2. 每段200-500字
3. 逻辑连贯，与上下文衔接自然
4. 适当使用数据、案例、引用
5. 如需表格，使用JSON格式的table类型

请严格按以下JSON格式输出：

```json
{{
  "sections": [
    {{"type": "body", "content": "正文段落1..."}},
    {{"type": "body", "content": "正文段落2..."}},
    {{"type": "table", "header": ["列1", "列2"], "rows": [["值1", "值2"]]}},
    {{"type": "list", "ordered": false, "items": ["项目1", "项目2"]}}
  ]
}}
```"""

FULL_DOC_PROMPT = """根据以下用户描述，生成完整的文档内容JSON。

要求：
1. 文档结构清晰，逻辑连贯
2. 内容专业、完整、有深度
3. 标题层级合理（heading1 > heading2 > heading3）
4. 正文段落内容充实，每段200-500字
5. 适当包含表格（如数据对比、参数列表等）
6. 中文文档用中文写作，英文文档用英文写作

用户描述：{user_input}

文档类型：{doc_type}

请严格按以下JSON格式输出：

```json
{{
  "title": "文档标题",
  "sections": [
    {{"type": "heading1", "title": "一、章节标题"}},
    {{"type": "body", "content": "正文段落内容..."}},
    {{"type": "heading2", "title": "1.1 子章节标题"}},
    {{"type": "body", "content": "正文段落内容..."}},
    {{"type": "table", "header": ["列1", "列2", "列3"], "rows": [["值1", "值2", "值3"]]}},
    {{"type": "list", "ordered": false, "items": ["项目1", "项目2"]}},
    {{"type": "page_break"}},
    {{"type": "body", "content": "新一页的正文..."}}
  ]
}}
```"""


class ChatSession:
    """对话会话管理器"""

    def __init__(self):
        self.history: list[dict[str, str]] = []
        self.outline: dict[str, Any] | None = None
        self.title: str = ""
        self.doc_type: str = ""
        self.abstract: str = ""
        self.filled_sections: list[dict[str, Any]] = []
        self.pending_outline: dict[str, Any] | None = None

    def add_message(self, role: str, content: str) -> None:
        """添加一条消息到历史"""
        self.history.append({"role": role, "content": content})

    def get_context_messages(self, max_turns: int = 10) -> list[dict[str, str]]:
        """获取最近的对话历史（用于LLM上下文）"""
        return self.history[-max_turns * 2:]

    def reset(self) -> None:
        """重置会话"""
        self.history.clear()
        self.outline = None
        self.title = ""
        self.doc_type = ""
        self.abstract = ""
        self.filled_sections.clear()
        self.pending_outline = None

    def to_dict(self) -> dict[str, Any]:
        """导出会话状态"""
        return {
            "outline": self.outline,
            "title": self.title,
            "doc_type": self.doc_type,
            "abstract": self.abstract,
            "filled_sections": self.filled_sections,
        }


class AIDocGenerator:
    """AI文档内容生成器 v2 - 支持流式输出和多轮对话"""

    # 允许的域名白名单（仅用于严格模式）
    ALLOWED_DOMAINS = {
        "api.openai.com",
        "api.anthropic.com",
        "localhost",
        "127.0.0.1",
    }

    def __init__(
        self,
        provider: str = "openai",
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        allow_custom_base_url: bool = True,
    ):
        from paper_format_corrector.infrastructure.llm.provider_config import (
            get_provider_by_name, get_default_base_url, get_default_model,
        )
        self.provider_config = get_provider_by_name(provider)
        self.provider = provider
        self.api_key = api_key or self._get_default_key()

        # 确定 base_url: 用户传入 > provider 默认
        resolved_base = base_url or get_default_base_url(provider)
        # 对于非 ollama 提供商，放宽域名限制
        self.base_url = self._validate_url(resolved_base, strict=False) if resolved_base else None

        self.model = model or get_default_model(provider)
        self.session = ChatSession()

    # ---------- 模型发现 API ----------

    @classmethod
    def discover_models(cls, provider: str, api_key: str | None = None,
                        base_url: str | None = None) -> list[str]:
        """类方法：发现指定provider下所有可用模型

        Args:
            provider: "openai" | "anthropic" | "ollama"
            api_key: API密钥（ollama不需要）
            base_url: 自定义API端点（如 https://api.deepseek.com/v1）

        Returns:
            可用模型ID列表
        """
        from .model_discovery import list_models as _discover
        if api_key is None:
            if provider == "openai":
                api_key = os.environ.get("OPENAI_API_KEY", "")
            elif provider == "anthropic":
                api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        return _discover(provider, api_key, base_url)

    @classmethod
    def probe_model(cls, provider: str, model: str,
                    api_key: str | None = None,
                    base_url: str | None = None) -> dict:
        """类方法：探测指定模型是否可用（支持任意用户输入的模型名）

        Args:
            provider: "openai" | "anthropic" | "ollama"
            model: 模型ID，可以是官方名也可以是自定义名
            api_key: API密钥
            base_url: 自定义API端点

        Returns:
            {
                "available": bool,
                "model": str,
                "provider": str,
                "latency_ms": float | None,
                "error": str | None,
                "details": dict
            }
        """
        from .model_discovery import probe_model as _probe
        if api_key is None:
            if provider == "openai":
                api_key = os.environ.get("OPENAI_API_KEY", "")
            elif provider == "anthropic":
                api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        return _probe(provider, model, api_key, base_url)

    @classmethod
    def probe_custom_models(cls, provider: str, model_names: list[str],
                            api_key: str | None = None,
                            base_url: str | None = None) -> list[dict]:
        """类方法：批量探测多个模型（支持非官方名称）

        Args:
            provider: "openai" | "anthropic" | "ollama"
            model_names: 要探测的模型名列表（任意用户输入）
            api_key: API密钥
            base_url: 自定义API端点

        Returns:
            探测结果列表
        """
        from .model_discovery import probe_model as _probe
        if api_key is None:
            if provider == "openai":
                api_key = os.environ.get("OPENAI_API_KEY", "")
            elif provider == "anthropic":
                api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        results = []
        for name in model_names:
            name = name.strip()
            if not name:
                continue
            results.append(_probe(provider, name, api_key, base_url))
        return results

    def _validate_url(self, url, strict=True):  # noqa: C901
        """校验 URL 安全性

        Args:
            url: 要验证的URL
            strict: True=仅允许白名单域名，False=允许任何HTTPS URL
        """
        import ipaddress
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname or ""

        if not host:
            raise ValueError(f"URL 缺少主机名: {url}")

        # 阻止内网/环回/链路本地 IP 地址（ollama 除外）
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            ip = None

        if ip is not None:
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                if self._get_protocol() != "ollama":
                    if strict:
                        raise ValueError(f"不允许访问内网地址: {host}")
                    if host not in ("localhost", "127.0.0.1"):
                        raise ValueError(f"不允许访问内网地址: {host}")
            if str(ip) == "169.254.169.254":
                raise ValueError("不允许访问云服务商元数据地址")

        # Ollama 只允许 localhost
        if self._get_protocol() == "ollama":
            if host not in ("localhost", "127.0.0.1"):
                raise ValueError(f"Ollama 仅支持 localhost，不允许远程地址: {host}")
            return url

        # 非严格模式：允许 HTTPS 和 localhost HTTP
        if not strict:
            if parsed.scheme == "http" and host in ("localhost", "127.0.0.1"):
                return url
            if parsed.scheme != "https":
                raise ValueError(f"必须使用 HTTPS，不允许: {parsed.scheme}://")
            return url

        # 严格模式：只允许白名单域名
        if parsed.scheme not in ("https",):
            if parsed.scheme == "http" and host in ("localhost", "127.0.0.1"):
                return url
            raise ValueError(f"不允许的 URL 协议: {parsed.scheme}")

        if host not in self.ALLOWED_DOMAINS:
            raise ValueError(f"不允许的 API 域名: {host}，允许: {self.ALLOWED_DOMAINS}")

        return url

    def _get_default_key(self) -> str:
        """获取默认 API Key，优先从环境变量读取"""
        env_var = self.provider_config.api_key_env if hasattr(self, 'provider_config') else ""
        if env_var:
            key = os.environ.get(env_var, "")
            if key:
                return key
        # 兼容旧的环境变量名
        if self.provider == "openai":
            return os.environ.get("OPENAI_API_KEY", "")
        elif self.provider == "anthropic":
            return os.environ.get("ANTHROPIC_API_KEY", "")
        elif self.provider == "ollama":
            return "ollama"
        return ""

    def _get_protocol(self) -> str:
        """获取当前提供商的协议类型"""
        if hasattr(self, 'provider_config'):
            return self.provider_config.protocol
        if self.provider == "anthropic":
            return "anthropic"
        if self.provider == "ollama":
            return "ollama"
        return "openai_compatible"

    def reset_session(self) -> None:
        """重置对话会话"""
        self.session.reset()

    # ---------- 大纲生成 ----------

    def generate_outline(
        self,
        user_input: str,
        doc_type: str = "通用文档",
    ) -> dict[str, Any]:
        """生成文档大纲（非流式）

        Returns:
            {"doc_type": "...", "title": "...", "abstract": "...", "outline": [...]}
        """
        self._validate_api_key()
        self.session.add_message("user", user_input)

        prompt = OUTLINE_PROMPT.format(user_input=user_input, doc_type=doc_type)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = self._call_llm(messages)
        outline = self._parse_json_response(response)

        self.session.outline = outline
        self.session.title = outline.get("title", "")
        self.session.doc_type = outline.get("doc_type", doc_type)
        self.session.abstract = outline.get("abstract", "")
        self.session.pending_outline = outline

        self.session.add_message("assistant", json.dumps(outline, ensure_ascii=False))
        return outline

    def generate_outline_stream(
        self,
        user_input: str,
        doc_type: str = "通用文档",
    ) -> Generator[str, None, None]:
        """生成文档大纲（流式）

        Yields:
            文本片段
        """
        self._validate_api_key()
        self.session.add_message("user", user_input)

        prompt = OUTLINE_PROMPT.format(user_input=user_input, doc_type=doc_type)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        full_response = ""
        for chunk in self._call_llm_stream(messages):
            full_response += chunk
            yield chunk

        outline = self._parse_json_response(full_response)
        self.session.outline = outline
        self.session.title = outline.get("title", "")
        self.session.doc_type = outline.get("doc_type", doc_type)
        self.session.abstract = outline.get("abstract", "")
        self.session.pending_outline = outline
        self.session.add_message("assistant", json.dumps(outline, ensure_ascii=False))

    def confirm_outline(self, confirmed: bool = True) -> None:
        """确认或拒绝大纲"""
        if confirmed and self.session.pending_outline:
            self.session.outline = self.session.pending_outline
            self.session.pending_outline = None

    # ---------- 逐节内容生成 ----------

    def generate_section_content(
        self,
        section_index: int,
    ) -> dict[str, Any]:
        """生成指定章节的内容（非流式）

        Args:
            section_index: 大纲中章节的索引

        Returns:
            {"sections": [...]} 格式的章节内容
        """
        self._validate_api_key()
        if not self.session.outline:
            raise ValueError("请先生成并确认大纲")

        outline = self.session.outline
        sections = outline.get("outline", [])
        if section_index >= len(sections):
            raise ValueError(f"章节索引 {section_index} 超出范围（共 {len(sections)} 个章节）")

        section = sections[section_index]
        context = self._build_context(section_index, sections)

        prompt = SECTION_CONTENT_PROMPT.format(
            title=outline.get("title", ""),
            doc_type=outline.get("doc_type", ""),
            abstract=outline.get("abstract", ""),
            section_title=section.get("title", ""),
            section_type=section.get("type", "heading1"),
            section_description=section.get("description", ""),
            context=context,
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = self._call_llm(messages)
        result = self._parse_json_response(response)
        return result

    def generate_section_content_stream(
        self,
        section_index: int,
    ) -> Generator[str, None, None]:
        """生成指定章节的内容（流式）

        Yields:
            文本片段
        """
        self._validate_api_key()
        if not self.session.outline:
            raise ValueError("请先生成并确认大纲")

        outline = self.session.outline
        sections = outline.get("outline", [])
        if section_index >= len(sections):
            raise ValueError(f"章节索引 {section_index} 超出范围（共 {len(sections)} 个章节）")

        section = sections[section_index]
        context = self._build_context(section_index, sections)

        prompt = SECTION_CONTENT_PROMPT.format(
            title=outline.get("title", ""),
            doc_type=outline.get("doc_type", ""),
            abstract=outline.get("abstract", ""),
            section_title=section.get("title", ""),
            section_type=section.get("type", "heading1"),
            section_description=section.get("description", ""),
            context=context,
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        full_response = ""
        for chunk in self._call_llm_stream(messages):
            full_response += chunk
            yield chunk

        result = self._parse_json_response(full_response)
        self.session.filled_sections.append(result)

    def generate_all_sections_stream(self) -> Generator[dict[str, Any], None, None]:
        """逐节生成所有章节内容（流式）

        Yields:
            {"type": "start", "section_index": 0, "section_title": "..."} |
            {"type": "chunk", "content": "..."} |
            {"type": "section_done", "section_index": 0, "result": {...}} |
            {"type": "all_done", "structure": {...}}
        """
        if not self.session.outline:
            yield {"type": "error", "message": "请先生成并确认大纲"}
            return

        outline = self.session.outline
        sections = outline.get("outline", [])
        full_structure = self._build_base_structure(outline)

        for i, section in enumerate(sections):
            yield {"type": "start", "section_index": i, "section_title": section.get("title", "")}

            context = self._build_context(i, sections)
            prompt = SECTION_CONTENT_PROMPT.format(
                title=outline.get("title", ""),
                doc_type=outline.get("doc_type", ""),
                abstract=outline.get("abstract", ""),
                section_title=section.get("title", ""),
                section_type=section.get("type", "heading1"),
                section_description=section.get("description", ""),
                context=context,
            )

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]

            full_response = ""
            for chunk in self._call_llm_stream(messages):
                full_response += chunk
                yield {"type": "chunk", "content": chunk}

            result = self._parse_json_response(full_response)
            section_content = result.get("sections", [])

            # 将标题和内容合并到full_structure
            full_structure["sections"].append(section)
            full_structure["sections"].extend(section_content)

            self.session.filled_sections.append(result)
            yield {"type": "section_done", "section_index": i, "result": result}

        self.session.outline["structure"] = full_structure
        yield {"type": "all_done", "structure": full_structure}

    def _build_base_structure(self, outline: dict[str, Any]) -> dict[str, Any]:
        """构建基础文档结构（标题+摘要）"""
        structure: dict[str, Any] = {
            "title": outline.get("title", ""),
            "sections": [],
        }
        # 添加摘要
        abstract = outline.get("abstract", "")
        if abstract:
            structure["sections"].append({"type": "heading1", "title": "摘要"})
            structure["sections"].append({"type": "body", "content": abstract})
            structure["sections"].append({"type": "page_break"})
        return structure

    def _build_context(self, current_index: int, sections: list[dict]) -> str:
        """构建当前章节的上下文信息"""
        prev_sections = []
        next_sections = []

        for i, s in enumerate(sections):
            title = s.get("title", "")
            if i < current_index and s.get("type", "").startswith("heading"):
                prev_sections.append(title)
            elif i > current_index and s.get("type", "").startswith("heading"):
                next_sections.append(title)

        lines = []
        if prev_sections:
            lines.append("前序章节: " + " > ".join(prev_sections[-3:]))
        if next_sections:
            lines.append("后续章节: " + " > ".join(next_sections[:3]))
        if not lines:
            lines.append("（文档首章）")

        return "\n".join(lines)

    # ---------- 对话修改 ----------

    def chat_modify(
        self,
        user_message: str,
    ) -> Generator[str, None, None]:
        """对话式修改文档内容（流式）

        用户可以：
        - 修改某个章节的内容
        - 调整大纲结构
        - 添加新章节
        - 其他文档相关的修改请求

        Yields:
            文本片段
        """
        self._validate_api_key()
        self.session.add_message("user", user_message)

        context_parts = []
        if self.session.outline:
            context_parts.append(f"当前文档标题: {self.session.title}")
            context_parts.append(f"文档类型: {self.session.doc_type}")
            outline_titles = [
                s.get("title", "") for s in self.session.outline.get("outline", [])
                if s.get("type", "").startswith("heading")
            ]
            context_parts.append(f"当前大纲: {' > '.join(outline_titles)}")

        history_context = "\n".join(context_parts) if context_parts else "（新对话）"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"文档上下文:\n{history_context}\n\n用户请求:\n{user_message}"},
        ]

        full_response = ""
        for chunk in self._call_llm_stream(messages):
            full_response += chunk
            yield chunk

        self.session.add_message("assistant", full_response)

    # ---------- 一次性生成完整文档（向后兼容） ----------

    def generate_structure(
        self,
        user_input: str,
        doc_type: str = "通用文档",
    ) -> dict[str, Any]:
        """调用LLM生成完整文档结构JSON（非流式，向后兼容v1）

        Args:
            user_input: 用户的自然语言描述
            doc_type: 文档类型（报告/公文/论文/合同等）

        Returns:
            结构化文档JSON
        """
        self._validate_api_key()
        self.session.add_message("user", user_input)

        prompt = FULL_DOC_PROMPT.format(user_input=user_input, doc_type=doc_type)
        messages = [
            {"role": "system", "content": "你是专业的文档撰写助手。只输出JSON，不要多余文字。"},
            {"role": "user", "content": prompt},
        ]

        response = self._call_llm(messages)
        return self._parse_json_response(response)

    def generate_structure_stream(
        self,
        user_input: str,
        doc_type: str = "通用文档",
    ) -> Generator[str, None, None]:
        """调用LLM生成完整文档结构JSON（流式，向后兼容v1）

        Yields:
            文本片段
        """
        self._validate_api_key()
        self.session.add_message("user", user_input)

        prompt = FULL_DOC_PROMPT.format(user_input=user_input, doc_type=doc_type)
        messages = [
            {"role": "system", "content": "你是专业的文档撰写助手。只输出JSON，不要多余文字。"},
            {"role": "user", "content": prompt},
        ]

        full_response = ""
        for chunk in self._call_llm_stream(messages):
            full_response += chunk
            yield chunk

        return self._parse_json_response(full_response)

    # ---------- LLM 调用 ----------

    def _validate_api_key(self) -> None:
        """验证API Key"""
        if self._get_protocol() == "ollama":
            return  # Ollama 不需要 API Key
        if not self.api_key:
            provider_display = self.provider_config.display_name if hasattr(self, 'provider_config') else self.provider
            env_var = self.provider_config.api_key_env if hasattr(self, 'provider_config') else ""
            env_hint = f"\n  设置环境变量: export {env_var}=your-key" if env_var else ""
            raise ValueError(
                f"未配置 {provider_display} 的API Key。"
                f"请在右侧配置区填写 API Key。{env_hint}"
            )

    def _call_llm(self, messages: list[dict[str, str]]) -> str:
        """调用LLM API（非流式）"""
        protocol = self._get_protocol()
        if protocol == "anthropic":
            return self._call_anthropic(messages, stream=False)
        elif protocol == "ollama":
            return self._call_ollama(messages, stream=False)
        else:  # openai_compatible - covers all Chinese providers
            return self._call_openai(messages, stream=False)

    def _call_llm_stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        """调用LLM API（流式）"""
        protocol = self._get_protocol()
        if protocol == "anthropic":
            yield from self._call_anthropic(messages, stream=True)
        elif protocol == "ollama":
            yield from self._call_ollama(messages, stream=True)
        else:  # openai_compatible
            yield from self._call_openai(messages, stream=True)

    def _call_openai(
        self, messages: list[dict[str, str]], stream: bool = False
    ) -> str | Generator[str, None, None]:
        import urllib.request

        base_url = self.base_url or "https://api.openai.com/v1"
        url = f"{base_url}/chat/completions"

        data = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4000,
            "stream": stream,
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")

        if not stream:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        else:
            return self._openai_stream(req)

    def _openai_stream(self, req: Any) -> Generator[str, None, None]:
        """处理OpenAI SSE流式响应"""
        import urllib.request

        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                line = line.decode("utf-8").strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue

    def _call_anthropic(
        self, messages: list[dict[str, str]], stream: bool = False
    ) -> str | Generator[str, None, None]:
        import urllib.request

        base_url = self.base_url or "https://api.anthropic.com"
        url = f"{base_url}/v1/messages"

        # Anthropic需要分离system和user消息
        system_msg = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4000,
            "messages": user_messages,
            "temperature": 0.7,
            "stream": stream,
        }
        if system_msg:
            payload["system"] = system_msg

        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("x-api-key", self.api_key)
        req.add_header("anthropic-version", "2023-06-01")

        if not stream:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["content"][0]["text"]
        else:
            return self._anthropic_stream(req)

    def _anthropic_stream(self, req: Any) -> Generator[str, None, None]:
        """处理Anthropic SSE流式响应"""
        import urllib.request

        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                line = line.decode("utf-8").strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                try:
                    data = json.loads(data_str)
                    if data.get("type") == "content_block_delta":
                        text = data.get("delta", {}).get("text", "")
                        if text:
                            yield text
                except json.JSONDecodeError:
                    continue

    def _call_ollama(
        self, messages: list[dict[str, str]], stream: bool = False
    ) -> str | Generator[str, None, None]:
        import urllib.request

        base_url = self.base_url or "http://localhost:11434"
        url = f"{base_url}/api/chat"

        # 将OpenAI格式消息转为Ollama格式
        ollama_messages = []
        for msg in messages:
            ollama_messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        data = json.dumps({
            "model": self.model,
            "messages": ollama_messages,
            "stream": stream,
            "options": {"temperature": 0.7},
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        if not stream:
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["message"]["content"]
        else:
            return self._ollama_stream(req)

    def _ollama_stream(self, req: Any) -> Generator[str, None, None]:
        """处理Ollama流式响应"""
        import urllib.request

        with urllib.request.urlopen(req, timeout=180) as resp:
            for line in resp:
                line = line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue

    # ---------- JSON 解析 ----------

    def _parse_json_response(self, response: str) -> dict[str, Any]:
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

        raise ValueError("无法从LLM响应中提取JSON，请检查输入内容或重试")
