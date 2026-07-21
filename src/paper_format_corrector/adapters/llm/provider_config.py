"""LLM 提供商配置注册表

集中管理所有支持的 LLM 提供商配置，包括：
- 默认 API 端点 (base_url)
- API Key 环境变量名
- 默认模型
- 协议类型 (openai_compatible / anthropic / ollama)

中国 AI 提供商大多使用 OpenAI 兼容协议，只需改 base_url 即可。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProviderConfig:
    """LLM 提供商配置"""
    name: str
    display_name: str
    protocol: str = "openai_compatible"  # openai_compatible | anthropic | ollama
    default_base_url: str = ""
    api_key_env: str = ""  # 环境变量名
    api_key_prefix: str = ""  # API Key 前缀提示（如 sk-）
    default_model: str = ""
    popular_models: list[str] = field(default_factory=list)
    description: str = ""
    requires_api_key: bool = True


# ── 提供商注册表 ────────────────────────────────────────────

PROVIDERS: dict[str, ProviderConfig] = {

    # ━━━━━━ 国际提供商 ━━━━━━

    "openai": ProviderConfig(
        name="openai",
        display_name="OpenAI",
        protocol="openai_compatible",
        default_base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        api_key_prefix="sk-",
        default_model="gpt-4o-mini",
        popular_models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "o1-mini"],
        description="GPT-4o / GPT-3.5 系列",
    ),

    "anthropic": ProviderConfig(
        name="anthropic",
        display_name="Anthropic (Claude)",
        protocol="anthropic",
        default_base_url="https://api.anthropic.com",
        api_key_env="ANTHROPIC_API_KEY",
        api_key_prefix="sk-ant-",
        default_model="claude-sonnet-4-20250514",
        popular_models=[
            "claude-opus-4-20250514", "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
        ],
        description="Claude 系列模型",
    ),

    # ━━━━━━ 中国提供商 ━━━━━━

    "deepseek": ProviderConfig(
        name="deepseek",
        display_name="DeepSeek (深度求索)",
        protocol="openai_compatible",
        default_base_url="https://api.deepseek.com/v1",
        api_key_env="DEEPSEEK_API_KEY",
        api_key_prefix="sk-",
        default_model="deepseek-chat",
        popular_models=["deepseek-chat", "deepseek-reasoner"],
        description="DeepSeek-V3 / DeepSeek-R1，性价比极高",
    ),

    "qwen": ProviderConfig(
        name="qwen",
        display_name="通义千问 (阿里云)",
        protocol="openai_compatible",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_env="DASHSCOPE_API_KEY",
        api_key_prefix="sk-",
        default_model="qwen-plus",
        popular_models=[
            "qwen-max", "qwen-plus", "qwen-turbo",
            "qwen-long", "qwen2.5-72b-instruct",
        ],
        description="阿里通义千问系列，支持长文本",
    ),

    "zhipu": ProviderConfig(
        name="zhipu",
        display_name="智谱 AI (GLM)",
        protocol="openai_compatible",
        default_base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key_env="ZHIPU_API_KEY",
        api_key_prefix="",
        default_model="glm-4-flash",
        popular_models=[
            "glm-4-plus", "glm-4-flash", "glm-4-air",
            "glm-4-long", "glm-4v-plus",
        ],
        description="智谱 GLM-4 系列，免费额度多",
    ),

    "moonshot": ProviderConfig(
        name="moonshot",
        display_name="月之暗面 (Kimi)",
        protocol="openai_compatible",
        default_base_url="https://api.moonshot.cn/v1",
        api_key_env="MOONSHOT_API_KEY",
        api_key_prefix="sk-",
        default_model="moonshot-v1-8k",
        popular_models=["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        description="Kimi 大模型，超长上下文",
    ),

    "baichuan": ProviderConfig(
        name="baichuan",
        display_name="百川智能",
        protocol="openai_compatible",
        default_base_url="https://api.baichuan-ai.com/v1",
        api_key_env="BAICHUAN_API_KEY",
        api_key_prefix="sk-",
        default_model="Baichuan4",
        popular_models=["Baichuan4", "Baichuan3-Turbo", "Baichuan3-Turbo-128k"],
        description="百川大模型",
    ),

    "stepfun": ProviderConfig(
        name="stepfun",
        display_name="阶跃星辰 (Step)",
        protocol="openai_compatible",
        default_base_url="https://api.stepfun.com/v1",
        api_key_env="STEPFUN_API_KEY",
        api_key_prefix="",
        default_model="step-1-8k",
        popular_models=["step-1-8k", "step-1-32k", "step-1-128k", "step-2-16k"],
        description="阶跃星辰大模型",
    ),

    "lingyiwanwu": ProviderConfig(
        name="lingyiwanwu",
        display_name="零一万物 (Yi)",
        protocol="openai_compatible",
        default_base_url="https://api.lingyiwanwu.com/v1",
        api_key_env="LINGYI_API_KEY",
        api_key_prefix="",
        default_model="yi-lightning",
        popular_models=["yi-lightning", "yi-large", "yi-medium"],
        description="Yi 系列模型",
    ),

    "minimax": ProviderConfig(
        name="minimax",
        display_name="MiniMax (海螺AI)",
        protocol="openai_compatible",
        default_base_url="https://api.minimax.chat/v1",
        api_key_env="MINIMAX_API_KEY",
        api_key_prefix="",
        default_model="abab6.5s-chat",
        popular_models=["abab6.5s-chat", "abab6.5-chat", "abab5.5-chat"],
        description="海螺AI大模型",
    ),

    "xunfei": ProviderConfig(
        name="xunfei",
        display_name="讯飞星火",
        protocol="openai_compatible",
        default_base_url="https://spark-api-open.xf-yun.com/v1",
        api_key_env="XUNFEI_API_KEY",
        api_key_prefix="",
        default_model="generalv3.5",
        popular_models=["generalv3.5", "generalv3", "4.0Ultra"],
        description="科大讯飞星火大模型",
    ),

    "siliconflow": ProviderConfig(
        name="siliconflow",
        display_name="硅基流动 (SiliconFlow)",
        protocol="openai_compatible",
        default_base_url="https://api.siliconflow.cn/v1",
        api_key_env="SILICONFLOW_API_KEY",
        api_key_prefix="sk-",
        default_model="deepseek-ai/DeepSeek-V3",
        popular_models=[
            "deepseek-ai/DeepSeek-V3", "deepseek-ai/DeepSeek-R1",
            "Qwen/Qwen2.5-72B-Instruct", "Pro/Qwen/Qwen2.5-7B-Instruct",
        ],
        description="硅基流动聚合平台，免费额度多",
    ),

    # ━━━━━━ 本地 / 自部署 ━━━━━━

    "ollama": ProviderConfig(
        name="ollama",
        display_name="Ollama (本地模型)",
        protocol="ollama",
        default_base_url="http://localhost:11434",
        api_key_env="",
        api_key_prefix="",
        default_model="qwen2.5:7b",
        popular_models=["qwen2.5:7b", "llama3.1:8b", "deepseek-r1:7b", "gemma2:9b"],
        description="本地运行开源模型，无需 API Key",
        requires_api_key=False,
    ),

    "custom": ProviderConfig(
        name="custom",
        display_name="自定义 (OpenAI兼容)",
        protocol="openai_compatible",
        default_base_url="",
        api_key_env="",
        api_key_prefix="",
        default_model="",
        popular_models=[],
        description="任意 OpenAI 兼容 API，请手动填写 Base URL",
    ),
}


def get_provider_names() -> list[str]:
    """获取所有提供商名称列表"""
    return list(PROVIDERS.keys())


def get_provider_display_names() -> list[str]:
    """获取所有提供商显示名称列表"""
    return [p.display_name for p in PROVIDERS.values()]


def get_provider_by_name(name: str) -> ProviderConfig:
    """根据名称获取提供商配置，不存在返回 custom"""
    return PROVIDERS.get(name, PROVIDERS["custom"])


def get_provider_by_display(display_name: str) -> ProviderConfig:
    """根据显示名称获取提供商配置"""
    for p in PROVIDERS.values():
        if p.display_name == display_name:
            return p
    return PROVIDERS["custom"]


def get_default_base_url(provider: str) -> str:
    """获取提供商的默认 base_url"""
    config = get_provider_by_name(provider)
    return config.default_base_url


def get_api_key_env(provider: str) -> str:
    """获取提供商的 API Key 环境变量名"""
    config = get_provider_by_name(provider)
    return config.api_key_env


def get_default_model(provider: str) -> str:
    """获取提供商的默认模型"""
    config = get_provider_by_name(provider)
    return config.default_model
