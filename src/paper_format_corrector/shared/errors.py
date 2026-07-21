"""集中化错误消息模块

提供错误代码到中文化消息的映射，统一项目中的用户可见错误提示。
"""

from __future__ import annotations

# 错误代码 → 中文化消息模板
_ERROR_MESSAGES: dict[str, str] = {
    # 文件相关
    "FILE_NOT_FOUND": "文件不存在: {path}",
    "FILE_NOT_READABLE": "文件无法读取: {path}",
    "FILE_NOT_WRITABLE": "文件无法写入: {path}",
    "FILE_EMPTY": "文件为空: {path}",
    "FILE_TOO_LARGE": "文件过大（最大 {max_size}MB）: {path}",

    # 格式相关
    "FORMAT_UNSUPPORTED": "不支持的文件格式: {fmt}，支持: {supported}",
    "FORMAT_CONVERSION_FAILED": "格式转换失败: {fmt} → {target}",
    "FORMAT_CONVERSION_TIMEOUT": "格式转换超时（{timeout}秒）",

    # 模板相关
    "TEMPLATE_NOT_FOUND": "模板不存在: {name}",
    "TEMPLATE_INVALID": "模板配置无效: {reason}",
    "TEMPLATE_LOAD_FAILED": "模板加载失败: {name}",
    "TEMPLATE_IMPORT_FAILED": "模板导入失败: {reason}",
    "TEMPLATE_DELETE_BUILTIN": "内置模板不允许删除，只能停用",

    # 路径安全
    "PATH_TRAVERSAL": "路径不安全: 包含非法字符或目录遍历",
    "PATH_OUTSIDE_ALLOWED": "路径超出允许范围: {path}",

    # 处理相关
    "PROCESS_FAILED": "文档处理失败: {reason}",
    "PROCESS_TIMEOUT": "文档处理超时",
    "PROCESS_NO_OUTPUT": "处理完成但未生成输出文件",

    # 权限相关
    "PERMISSION_DENIED": "权限不足: {path}",
    "DIRECTORY_CREATE_FAILED": "无法创建目录: {path}",

    # 依赖相关
    "DEPENDENCY_MISSING": "缺少必要依赖: {package}，请运行: pip install {install_hint}",
    "DEPENDENCY_OPTIONAL": "可选功能需要安装: {package}（pip install {install_hint}）",

    # LLM 相关
    "LLM_UNAVAILABLE": "AI 服务不可用，请检查配置",
    "LLM_TIMEOUT": "AI 请求超时",
    "LLM_RATE_LIMIT": "AI 请求频率超限，请稍后重试",

    # 批量处理
    "BATCH_NO_FILES": "未找到可处理的文件",
    "BATCH_ALL_FAILED": "所有文件处理失败",

    # 通用
    "UNKNOWN_ERROR": "发生未知错误，请查看日志获取详细信息",
    "CONFIG_INVALID": "配置无效: {reason}",
}


def get_error(code: str, **kwargs) -> str:
    """获取格式化的中文错误消息

    Args:
        code: 错误代码（如 'FILE_NOT_FOUND'）
        **kwargs: 消息模板中的变量

    Returns:
        格式化后的中文错误消息

    Example:
        >>> get_error('FILE_NOT_FOUND', path='/tmp/test.docx')
        '文件不存在: /tmp/test.docx'
    """
    template = _ERROR_MESSAGES.get(code)
    if template is None:
        return f"未知错误({code})"
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
