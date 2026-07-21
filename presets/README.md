# 预设模板库

本目录包含论文格式自动矫正工具的所有预设模板文件。

## 目录结构

```
presets/
├── templates_index.yaml    # 模板索引文件（供GUI/CLI使用）
├── doc_templates/          # 办公文档模板
│   ├── academic_paper.yaml
│   ├── business_plan.yaml
│   ├── contract.yaml
│   ├── meeting_minutes.yaml
│   ├── official_doc.yaml
│   └── report.yaml
├── 中国高校模板 (10个)
│   ├── tsinghua.yaml       # 清华大学
│   ├── peking.yaml         # 北京大学
│   ├── zhejiang.yaml       # 浙江大学
│   ├── shanghaijiaotong.yaml  # 上海交通大学
│   ├── fudan.yaml          # 复旦大学
│   ├── nanjing.yaml        # 南京大学
│   ├── ustc.yaml           # 中国科学技术大学
│   ├── hit.yaml            # 哈尔滨工业大学
│   ├── xjtu.yaml           # 西安交通大学
│   └── wuhan.yaml          # 武汉大学
├── 国际会议模板 (10个)
│   ├── aaai.yaml           # AAAI 人工智能顶级会议
│   ├── neurips.yaml        # NeurIPS 神经信息处理系统
│   ├── icml.yaml           # ICML 机器学习顶级会议
│   ├── acl.yaml            # ACL 计算语言学顶会
│   ├── cvpr.yaml           # CVPR 计算机视觉顶级会议
│   ├── emnlp.yaml          # EMNLP 自然语言处理实证方法
│   ├── iclr.yaml           # ICLR 国际学习表征会议
│   ├── kdd.yaml            # KDD 知识发现与数据挖掘
│   ├── sigir.yaml          # SIGIR 信息检索顶级会议
│   └── www.yaml            # WWW 万维网会议
├── 国际期刊模板
│   ├── nature.yaml         # Nature
│   └── science.yaml        # Science
├── 引用格式标准
│   ├── apa.yaml            # APA 格式
│   ├── mla.yaml            # MLA 格式
│   ├── chicago.yaml        # Chicago 格式
│   ├── harvard.yaml        # Harvard 格式
│   └── ama.yaml            # AMA 格式
├── 参考文献标准
│   └── gb7714.yaml         # GB/T 7714 国家标准
├── 出版商模板
│   ├── ieee.yaml           # IEEE
│   ├── acm.yaml            # ACM
│   ├── springer.yaml       # Springer
│   ├── elsevier.yaml       # Elsevier
│   └── wiley.yaml          # Wiley
└── 特定语言模板
    ├── japanese.yaml       # 日本語学位论文
    ├── korean.yaml         # 한국어 학위논문
    └── chinese_thesis.yaml # 中国大学毕业论文
```

## 模板分类

| 分类 | 数量 | 说明 |
|------|------|------|
| 中国高校学位论文 | 10 | 985高校学位论文格式 |
| 国际学术会议 | 10 | AI/ML/NLP/CV顶级会议 |
| 国际学术期刊 | 2 | Nature, Science |
| 引用格式标准 | 5 | APA, MLA, Chicago, Harvard, AMA |
| 参考文献标准 | 1 | GB/T 7714-2015 |
| 出版商模板 | 5 | IEEE, ACM, Springer, Elsevier, Wiley |
| 特定语言模板 | 3 | 日语、韩语、中文通用 |
| 办公文档模板 | 6 | 报告、合同、会议纪要等 |

## 模板说明

### 中国高校模板

每个高校模板包含以下规范：

- **页边距**: 上下2.54cm，左右3.17cm
- **标题格式**: 一级标题（二号/16pt）、二级标题（三号/14pt）、三级标题（四号/12pt）
- **正文字体**: 中文宋体、英文Times New Roman，小四号（12pt），1.5倍行距
- **摘要格式**: 中英文摘要标题二号居中，内容小四
- **图表格式**: 三线表样式，图题五号居中
- **参考文献**: GB/T 7714标准格式
- **页码设置**: 前置部分小写罗马数字，正文阿拉伯数字

### 国际会议模板

每个会议模板包含：

- **页面布局**: 标准学术会议单栏/双栏格式
- **正文字体**: Times New Roman，10pt，单倍行距
- **页边距**: 各会议具体要求（通常1英寸）
- **摘要**: 10pt，最多150行
- **自动检测**: 支持标题、作者、摘要、关键词等元素的自动识别

## 使用方式

```bash
# 使用预设模板
python -m paper_format_corrector --preset tsinghua -f paper.docx

# 使用GUI选择模板
python -m paper_format_corrector --gui

# 使用CLI查看所有可用模板
python -m paper_format_corrector --list-presets
```

## 模板来源与验证

| 模板 | 来源 | 验证状态 |
|------|------|----------|
| tsinghua | 清华大学研究生院 | 已验证 |
| peking | 北京大学研究生院 | 已验证 |
| zhejiang | 浙江大学研究生院 | 已验证 |
| shanghaijiaotong | 上海交通大学研究生院 | 已验证 |
| fudan | 复旦大学研究生院 | 已验证 |
| nanjing | 南京大学研究生院 | 已验证 |
| ustc | 中国科学技术大学研究生院 | 已验证 |
| hit | 哈尔滨工业大学研究生院 | 已验证 |
| xjtu | 西安交通大学研究生院 | 已验证 |
| wuhan | 武汉大学研究生院 | 已验证 |
| aaai | AAAI Press | 已验证 |
| neurips | NeurIPS Organizing Committee | 已验证 |
| icml | ICML Organizing Committee | 已验证 |
| acl | ACL Organizing Committee | 已验证 |
| cvpr | IEEE/CVF | 已验证 |
| emnlp | ACL/EMNLP (待官方确认) | 待验证 |
| iclr | ICLR (待官方确认) | 待验证 |
| kdd | ACM SIGKDD (待官方确认) | 待验证 |
| sigir | ACM SIGIR (待官方确认) | 待验证 |
| www | ACM WWW (待官方确认) | 待验证 |

## 注意事项

1. 模板格式基于各机构官方写作规范，但可能因年份更新而有差异
2. 标记为"已验证"的模板已与官方样例对比确认
3. 标记为"待验证"的模板基于公开指南编写，建议使用前与最新官方要求对比
4. 如发现格式错误，请提交 issue 反馈
