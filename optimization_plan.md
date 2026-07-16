# paper-format-corrector 项目优化计划

## 优化目标
基于用户需求，对项目进行全面优化，优先级：**功能增强 > 代码质量 > 性能 > 测试 > 文档 > 安全**

---

## 一、功能增强（优先级：高）

### 1.1 新增格式预设
当前已有 8 个预设，计划新增常用学术格式：

| 预设 | 说明 | 状态 |
|------|------|------|
| `springer.yaml` | Springer 期刊论文格式 | 待新增 |
| `elsevier.yaml` | Elsevier 期刊论文格式 | 待新增 |
| `acm.yaml` | ACM 会议论文格式 | 待新增 |
| `acs.yaml` | ACS 化学期刊格式 | 待新增 |
| `tuniversity.yaml` | 通用大学论文模板（可配置） | 待新增 |

**实现位置**: `presets/` 目录

### 1.2 增强离线能力（无 LLM 依赖）
当前 AI 功能完全依赖外部 API，计划增加离线处理能力：

#### 1.2.1 规则化需求解析（离线版）
- **文件**: `src/paper_format_corrector/parsers/rule_parser.py`（新建）
- **功能**: 基于正则表达式和规则匹配，从需求文档中提取格式规则
- **支持格式**:
  - 中文自然语言描述（如"正文用宋体小四"）
  - 表格格式的需求文档
  - Markdown 格式的需求文档
- **核心逻辑**:
  ```python
  class RuleParser:
      """规则化需求解析器（离线版）"""
      
      # 中文字号到 pt 的映射
      CHINESE_SIZE_MAP = {
          "初号": 42, "小初": 36, "一号": 26, "小一": 24,
          "二号": 22, "小二": 18, "三号": 16, "小三": 15,
          "四号": 14, "小四": 12, "五号": 10.5, "小五": 9,
      }
      
      # 字体名称模式
      FONT_PATTERNS = {
          "宋体": r"宋体|SimSun|songti",
          "黑体": r"黑体|SimHei|heiti",
          "楷体": r"楷体|KaiTi|kaiti",
          "Times New Roman": r"Times\s*New\s*Roman|TNR",
      }
      
      def parse(self, text: str) -> dict:
          """解析需求文本，返回配置字典"""
          config = {"format_rules": {}}
          
          # 提取字体规则
          self._extract_font_rules(text, config)
          # 提取字号规则
          self._extract_size_rules(text, config)
          # 提取对齐规则
          self._extract_alignment_rules(text, config)
          # 提取行距规则
          self._extract_spacing_rules(text, config)
          # 提取页边距
          self._extract_margin_rules(text, config)
          
          return config
  ```

#### 1.2.2 增强的文档检测（离线版）
- **文件**: `src/paper_format_corrector/parsers/document_analyzer.py`（新建）
- **功能**: 无需 LLM 即可分析文档结构和格式问题
- **核心能力**:
  - 段落类型检测（标题、正文、摘要、参考文献等）
  - 字体/字号/对齐方式提取
  - 格式一致性检查
  - 与标准规范的差异分析

### 1.3 增强参考文献处理
- **文件**: `src/paper_format_corrector/parsers/reference_formatter.py`（修改）
- **改进**:
  - 支持更多引用风格（Vancouver, Turabian, AMA 等）
  - 参考文献去重功能
  - 引用链接验证（检查正文引用与参考文献列表的一致性）
  - 支持 DOI 自动补全

### 1.4 增强图表处理
- **文件**: `src/paper_format_corrector/handlers/figure_table_handler.py`（修改）
- **改进**:
  - 支持自定义编号格式（如 "图 1-1", "Fig. 1", "Figure 1"）
  - 图表标题位置可配置（上方/下方）
  - 表格跨页续表处理
  - 图片自动调整大小以适应页面

### 1.5 增强目录生成
- **文件**: `src/paper_format_corrector/handlers/toc_handler.py`（修改）
- **改进**:
  - 支持自定义目录样式
  - 支持多级目录
  - 目录页码格式可配置

---

## 二、代码质量优化（优先级：中）

### 2.1 移除废弃代码引用
- **文件**: `src/paper_format_corrector/infra/plugin_manager.py`
- **操作**: 保留文件，更新文档注释为 `.. deprecated:: 1.0`
- **清理**: 检查其他文件中是否有引用 plugin_manager 的代码，如有则移除

### 2.2 改进类型注解
- **目标**: 为所有公共 API 添加完整的类型注解
- **涉及文件**: 所有 `src/paper_format_corrector/` 下的模块
- **示例**:
  ```python
  # 当前
  def correct_document(self, input_path, output_path, backup=True):
  
  # 优化后
  def correct_document(
      self, 
      input_path: str | Path, 
      output_path: str | Path, 
      backup: bool = True
  ) -> dict[str, Any]:
  ```

### 2.3 代码重复消除
- **检查**: `docx_utils.py` 中的辅助函数是否在多处重复定义
- **合并**: 将重复的字体设置逻辑统一到 `docx_utils.py`

### 2.4 错误处理改进
- **统一错误类型**: 定义项目专用的异常类层次
- **改进错误消息**: 提供更友好的中文错误提示

---

## 三、性能优化（优先级：中）

### 3.1 段落处理优化
- **文件**: `src/paper_format_corrector/core/format_corrector.py`
- **改进**:
  - 缓存配置查找结果
  - 减少重复的正则编译
  - 批量处理相似段落

### 3.2 批量处理优化
- **文件**: `src/paper_format_corrector/cli.py`
- **改进**:
  - 优化多进程通信
  - 添加进度回调
  - 内存使用优化

---

## 四、安全优化（优先级：中）

### 4.1 路径安全放宽
- **文件**: `src/paper_format_corrector/infra/path_security.py`
- **修改**:
  - 移除 ASCII-only 限制
  - 保留路径遍历防护
  - 添加路径长度限制（Windows MAX_PATH）
  - 添加特殊字符过滤（仅过滤危险字符，不限制中文）

**具体修改**:
```python
# 当前实现
_NON_ASCII_RE = re.compile(r'[^\x00-\x7f]')

def _is_ascii_path(path_str: str) -> bool:
    return not _NON_ASCII_RE.search(path_str)

# 优化后实现
# 移除 ASCII 限制，仅保留危险字符过滤
_DANGEROUS_CHARS_RE = re.compile(r'[\x00-\x1f\x7f<>:"|?*]')

def _is_safe_path(path_str: str) -> bool:
    """检查路径是否安全（不含危险字符）"""
    return not _DANGEROUS_CHARS_RE.search(path_str)
```

### 4.2 输入验证增强
- **文件**: `src/paper_format_corrector/infra/path_security.py`
- **新增**:
  - 路径长度限制（Windows 260 字符）
  - 文件大小检查（防止 DoS）
  - 临时文件安全清理

---

## 五、测试优化（优先级：中）

### 5.1 补充单元测试
- **新增测试文件**:
  - `tests/test_rule_parser.py` - 规则解析器测试
  - `tests/test_document_analyzer.py` - 文档分析器测试
  - `tests/test_reference_formatter.py` - 参考文献格式化测试
- **目标覆盖率**: 从当前约 60% 提升到 80%

### 5.2 补充集成测试
- **新增**: 端到端测试用例，覆盖常见使用场景
- **测试数据**: 添加更多样化的测试文档

### 5.3 边界测试
- **新增**: 空文档、损坏文档、超大文档的处理测试
- **新增**: 并发处理测试

---

## 六、文档优化（优先级：低）

### 6.1 更新 README
- **补充**: 新增预设的使用说明
- **补充**: 离线模式的使用说明
- **更新**: 项目结构图

### 6.2 API 文档
- **新增**: 为公共 API 添加 docstring 示例
- **工具**: 考虑使用 Sphinx 生成 API 文档

---

## 七、实施计划

### 阶段 1: 基础优化（1-2 天）
1. ✅ 放宽路径安全限制
2. ✅ 清理废弃代码引用
3. ✅ 添加缺失的类型注解

### 阶段 2: 功能增强（3-5 天）
1. ✅ 实现规则化需求解析器
2. ✅ 实现离线文档分析器
3. ✅ 新增 2-3 个格式预设

### 阶段 3: 质量提升（2-3 天）
1. ✅ 补充单元测试
2. ✅ 性能优化
3. ✅ 文档更新

### 阶段 4: 验证（1 天）
1. ✅ 运行完整测试套件
2. ✅ 代码审查
3. ✅ 性能基准测试

---

## 八、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 路径安全放宽可能导致安全问题 | 中 | 保留路径遍历防护，仅移除 ASCII 限制 |
| 新增功能可能引入回归 | 中 | 充分测试，灰度发布 |
| 性能优化可能影响可读性 | 低 | 保持代码清晰，添加注释 |

---

## 九、成功标准

1. ✅ 所有现有测试通过
2. ✅ 新增测试覆盖率达到 80%
3. ✅ 至少新增 3 个格式预设
4. ✅ 离线需求解析器可正常工作
5. ✅ 路径支持中文字符
6. ✅ 代码类型注解完整
7. ✅ 无明显性能退化
