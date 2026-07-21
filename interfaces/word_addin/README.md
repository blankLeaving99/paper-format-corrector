# Word 插件 - 论文格式矫正

在 Word 中直接使用论文格式矫正功能，无需切换到外部工具。

## 系统要求

- Word 2016 或更高版本（Windows / macOS）
- Node.js 16+（开发模式）
- Python 后端服务运行中

## 开发模式安装

### 1. 启动 API 服务

```bash
cd /path/to/paper-format-corrector
python -m paper_format_corrector.api.app
# 或
uvicorn paper_format_corrector.api.app:app --host 0.0.0.0 --port 8000
```

### 2. 启动静态文件服务器

```bash
cd interfaces/word_addin
npx http-server . -p 3000 -S --ssl
```

> 如果没有 SSL 证书，可以用 Python 启动（需在 manifest.xml 中将 https 改为 http）：
> ```bash
> python -m http.server 3000
> ```

### 3. 在 Word 中侧加载插件

1. 打开 Word 文档
2. 进入 **插入** > **我的加载项** > **管理我的加载项**
3. 选择 **从文件加载** → 选择 `manifest.xml`
4. 任务窗格将出现在右侧

## 发布部署

### 打包为 Office 应用商店格式

1. 将 `interfaces/word_addin/` 目录内容打包为 `.zip`
2. 重命名为 `.ppam` 或保持 `.zip` 上传到 [Office 应用商店](https:// sellers.office.com/)
3. 或通过 Microsoft 365 管理中心的组策略部署

### 本地共享（团队内）

1. 将插件文件夹放在共享网络位置
2. 团队成员在 Word 中通过 URL 侧加载

## 文件结构

```
word_addin/
├── manifest.xml           # Office 插件清单
├── src/
│   ├── taskpane.html      # 任务窗格 UI
│   ├── taskpane.js        # 核心逻辑
│   ├── taskpane.css       # 样式
│   └── office.js          # Office API 交互层
├── assets/
│   └── logo.png           # 插件图标（需自行添加）
└── README.md
```

## API 端点

插件依赖以下后端 API：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/presets` | GET | 获取内置预设列表 |
| `/templates` | GET | 获取模板库列表 |
| `/scan` | POST | 扫描文档结构 |
| `/correct` | POST | 执行格式矫正 |

## 故障排除

- **API 未连接**: 确认后端服务已启动（`http://localhost:8000`）
- **SSL 证书错误**: 开发模式可用 `--ignore-certificate-errors` 启动 Chrome，或改用 HTTP
- **插件无法加载**: 检查 manifest.xml 中的 URL 是否正确，端口是否开放
- **文档读取失败**: 确认文档未被其他程序锁定

## 注意事项

- 插件通过 Office.js API 读取文档，以 `.docx` 格式发送到后端
- 矫正后的文件会直接替换当前文档内容
- 所有处理在本地进行，不会上传到外部服务器
