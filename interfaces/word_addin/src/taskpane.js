/* global Office, Word */

/**
 * 论文格式矫正 - 任务窗格核心逻辑
 */

// ── API 配置 ────────────────────────────────────────────────
const API_BASE = 'http://localhost:8000';

// ── DOM 元素引用 ────────────────────────────────────────────
const els = {};

function cacheElements() {
  els.templateSelect = document.getElementById('templateSelect');
  els.scanBtn = document.getElementById('scanBtn');
  els.scanResult = document.getElementById('scanResult');
  els.headingCount = document.getElementById('headingCount');
  els.bodyCount = document.getElementById('bodyCount');
  els.imageCount = document.getElementById('imageCount');
  els.tableCount = document.getElementById('tableCount');
  els.correctBtn = document.getElementById('correctBtn');
  els.progress = document.getElementById('progress');
  els.progressBar = document.getElementById('progressBar');
  els.progressText = document.getElementById('progressText');
  els.status = document.getElementById('status');
  els.presetHint = document.getElementById('presetHint');
  els.apiStatus = document.getElementById('apiStatus');
}

// ── Office 辅助对象 ──────────────────────────────────────────
const OfficeHelper = {
  _ready: false,

  async initialize() {
    return new Promise((resolve, reject) => {
      if (typeof Office === 'undefined') {
        // 非 Office 环境（测试模式）
        console.warn('Office.js 未加载，运行在测试模式');
        this._ready = true;
        resolve();
        return;
      }
      Office.onReady((info) => {
        if (info.host === Office.HostType.Word) {
          this._ready = true;
          resolve();
        } else {
          reject(new Error('此插件仅支持 Word'));
        }
      });
      // 超时保护：5秒后如果 Office.onReady 未回调则降级
      setTimeout(() => {
        if (!this._ready) {
          console.warn('Office.onReady 超时，降级为测试模式');
          this._ready = true;
          resolve();
        }
      }, 5000);
    });
  },

  /**
   * 获取当前文档的 .docx 文件 Blob
   */
  async getDocumentFile() {
    if (typeof Word === 'undefined' || typeof Office === 'undefined') {
      // 测试模式：返回空 Blob
      return new Blob(['test-mode'], { type: 'application/octet-stream' });
    }
    return new Promise((resolve, reject) => {
      Word.run(async (context) => {
        // 获取文档的 base64 内容
        const doc = context.document;
        doc.load('body');
        await context.sync();

        // 使用 getFileAsync 获取完整 .docx
        Office.context.document.getFileAsync(
          Office.FileType.Compressed,
          { sliceSize: 65536 },
          (result) => {
            if (result.status === Office.AsyncResultStatus.Failed) {
              reject(new Error('获取文档失败: ' + result.error.message));
              return;
            }
            const fileHandle = result.value;
            const slices = [];
            const readSlice = (index) => {
              fileHandle.getSliceAsync(index, (sliceResult) => {
                if (sliceResult.status === Office.AsyncResultStatus.Failed) {
                  fileHandle.closeAsync();
                  reject(new Error('读取文档分片失败'));
                  return;
                }
                if (sliceResult.value.index === index) {
                  slices.push(sliceResult.value.data);
                  if (sliceResult.value.index < fileHandle.sliceCount - 1) {
                    readSlice(index + 1);
                  } else {
                    fileHandle.closeAsync();
                    const blob = new Blob(slices, { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
                    resolve(blob);
                  }
                }
              });
            };
            readSlice(0);
          }
        );
      }).catch(reject);
    });
  },

  /**
   * 用矫正后的 Blob 替换当前文档内容
   */
  async replaceDocument(blob) {
    if (typeof Office === 'undefined') {
      console.log('测试模式：跳过文档替换');
      return;
    }
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result.split(',')[1];
        // 通过 base64 插入新文档内容
        Word.run(async (context) => {
          context.document.body.insertFileFromBase64(base64, 'replace');
          await context.sync();
          resolve();
        }).catch(reject);
      };
      reader.onerror = () => reject(new Error('文件读取失败'));
      reader.readAsDataURL(blob);
    });
  }
};

// ── 工具函数 ────────────────────────────────────────────────
function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function showStatus(msg, type) {
  els.status.textContent = msg;
  els.status.className = 'status ' + type;
}

function hideStatus() {
  els.status.className = 'status';
  els.status.textContent = '';
}

function setLoading(btn, loading) {
  if (loading) {
    btn.disabled = true;
    btn.dataset.originalText = btn.innerHTML;
  } else {
    btn.disabled = false;
    if (btn.dataset.originalText) {
      btn.innerHTML = btn.dataset.originalText;
    }
  }
}

// ── API 连接检测 ────────────────────────────────────────────
async function checkApiConnection() {
  try {
    const resp = await fetch(`${API_BASE}/health`, { method: 'GET' });
    if (resp.ok) {
      els.apiStatus.textContent = '● API 已连接';
      els.apiStatus.className = 'api-status connected';
      return true;
    }
  } catch (e) {
    // ignore
  }
  els.apiStatus.textContent = '● API 未连接，请先启动后端服务';
  els.apiStatus.className = 'api-status disconnected';
  return false;
}

// ── 加载预设/模板列表 ───────────────────────────────────────
async function loadTemplates() {
  try {
    // 加载内置预设
    const presetResp = await fetch(`${API_BASE}/presets`);
    const presets = await presetResp.json();

    // 加载模板库
    let templates = [];
    try {
      const tmplResp = await fetch(`${API_BASE}/templates`);
      templates = await tmplResp.json();
    } catch (e) {
      // 模板库可能为空
    }

    const options = [];

    // 预设分组
    if (Array.isArray(presets) && presets.length > 0) {
      const presetGroup = presets.map(p => {
        const name = typeof p === 'string' ? p : (p.name || p.id || JSON.stringify(p));
        const slug = typeof p === 'string' ? p : (p.slug || p.id || name);
        return `<option value="preset:${slug}">${name}</option>`;
      }).join('');
      options.push(`<optgroup label="内置预设">${presetGroup}</optgroup>`);
    }

    // 模板分组
    if (Array.isArray(templates) && templates.length > 0) {
      const tmplGroup = templates.map(t =>
        `<option value="template:${t.slug}">${t.name}${t.organization ? ' (' + t.organization + ')' : ''}</option>`
      ).join('');
      options.push(`<optgroup label="模板库">${tmplGroup}</optgroup>`);
    }

    if (options.length > 0) {
      els.templateSelect.innerHTML = `<option value="">-- 请选择 --</option>` + options.join('');
    } else {
      els.templateSelect.innerHTML = `<option value="">-- 暂无可用模板 --</option>`;
    }
  } catch (err) {
    els.templateSelect.innerHTML = `<option value="">-- 加载失败 --</option>`;
    showStatus('加载模板列表失败: ' + err.message, 'error');
  }
}

// ── 扫描文档 ────────────────────────────────────────────────
async function scanDocument() {
  const connected = await checkApiConnection();
  if (!connected) {
    showStatus('无法连接到 API 服务，请先启动后端', 'error');
    return;
  }

  setLoading(els.scanBtn, true);
  els.scanBtn.innerHTML = '<span class="btn-icon">&#128269;</span> 扫描中...';
  hideStatus();

  try {
    const blob = await OfficeHelper.getDocumentFile();
    const formData = new FormData();
    formData.append('file', blob, 'document.docx');

    const resp = await fetch(`${API_BASE}/scan`, {
      method: 'POST',
      body: formData,
    });

    if (!resp.ok) {
      const err = await resp.text();
      throw new Error(err || `HTTP ${resp.status}`);
    }

    const result = await resp.json();

    // 解析返回的 elements 统计
    const elements = result.elements || {};
    els.headingCount.textContent =
      (elements.heading1 || 0) + (elements.heading2 || 0) + (elements.heading3 || 0) + (elements.heading4 || 0);
    els.bodyCount.textContent = elements.body || 0;
    els.imageCount.textContent = elements.image || 0;
    els.tableCount.textContent = elements.table || 0;

    els.scanResult.style.display = 'block';
    els.correctBtn.disabled = false;
    showStatus('扫描完成，共 ' + (elements.total_paragraphs || 0) + ' 个段落', 'success');
  } catch (err) {
    showStatus('扫描失败: ' + err.message, 'error');
  } finally {
    setLoading(els.scanBtn, false);
  }
}

// ── 执行矫正（带真实进度轮询） ────────────────────────────────
async function correctDocument() {
  const templateValue = els.templateSelect.value;
  if (!templateValue) {
    showStatus('请先选择模板', 'error');
    return;
  }

  const connected = await checkApiConnection();
  if (!connected) {
    showStatus('无法连接到 API 服务，请先启动后端', 'error');
    return;
  }

  setLoading(els.correctBtn, true);
  els.correctBtn.innerHTML = '<span class="btn-icon">&#9989;</span> 矫正中...';
  els.progress.style.display = 'flex';
  els.progressBar.value = 0;
  els.progressText.textContent = '0%';
  hideStatus();

  try {
    const blob = await OfficeHelper.getDocumentFile();
    const formData = new FormData();
    formData.append('file', blob, 'document.docx');

    // 解析模板类型和名称
    const [type, slug] = templateValue.split(':');
    if (type === 'preset') {
      formData.append('preset', slug);
    }

    // 提交任务并获取 task_id（如果支持异步）
    let taskId = null;
    let usePolling = false;

    // 尝试异步提交
    try {
      const asyncResp = await fetch(`${API_BASE}/tasks/submit`, {
        method: 'POST',
        body: formData,
      });
      if (asyncResp.ok) {
        const asyncResult = await asyncResp.json();
        taskId = asyncResult.task_id;
        usePolling = true;
      }
    } catch (e) {
      // 异步接口不可用，回退到同步模式
    }

    if (usePolling && taskId) {
      // 真实进度轮询模式
      const pollProgress = async () => {
        try {
          const statusResp = await fetch(`${API_BASE}/tasks/${taskId}`);
          if (statusResp.ok) {
            const status = await statusResp.json();
            const progress = status.progress || 0;
            els.progressBar.value = progress;
            els.progressText.textContent = progress + '%';

            if (status.status === 'completed') {
              // 任务完成，下载结果
              if (status.result_path) {
                const resultResp = await fetch(`${API_BASE}/tasks/${taskId}/download`);
                if (resultResp.ok) {
                  const resultBlob = await resultResp.blob();
                  await OfficeHelper.replaceDocument(resultBlob);
                }
              }
              els.progressBar.value = 100;
              els.progressText.textContent = '100%';
              showStatus('矫正完成！文档已更新。', 'success');
              return;
            } else if (status.status === 'failed') {
              throw new Error(status.error || '矫正任务失败');
            }

            // 继续轮询
            setTimeout(pollProgress, 1000);
          }
        } catch (pollErr) {
          // 轮询失败，回退到同步
          throw pollErr;
        }
      };
      await pollProgress();
    } else {
      // 同步模式：直接等待结果，显示不确定进度
      let syncProgress = 0;
      const progressTimer = setInterval(() => {
        if (syncProgress < 85) {
          syncProgress += Math.random() * 5;
          els.progressBar.value = Math.min(syncProgress, 85);
          els.progressText.textContent = Math.round(Math.min(syncProgress, 85)) + '%';
        }
      }, 800);

      const resp = await fetch(`${API_BASE}/correct`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressTimer);

      if (!resp.ok) {
        const err = await resp.text();
        throw new Error(err || `HTTP ${resp.status}`);
      }

      // API 直接返回矫正后的文件
      const resultBlob = await resp.blob();

      els.progressBar.value = 95;
      els.progressText.textContent = '95%';

      // 将矫正后的文件写回 Word 文档
      await OfficeHelper.replaceDocument(resultBlob);

      els.progressBar.value = 100;
      els.progressText.textContent = '100%';
      showStatus('矫正完成！文档已更新。', 'success');
    }
  } catch (err) {
    showStatus('矫正失败: ' + err.message, 'error');
  } finally {
    setLoading(els.correctBtn, false);
    setTimeout(() => {
      els.progress.style.display = 'none';
    }, 2000);
  }
}

// ── 事件绑定 ────────────────────────────────────────────────
function bindEvents() {
  els.scanBtn.addEventListener('click', scanDocument);
  els.correctBtn.addEventListener('click', correctDocument);
  els.templateSelect.addEventListener('change', () => {
    const val = els.templateSelect.value;
    if (val) {
      const [type, slug] = val.split(':');
      els.presetHint.textContent = type === 'preset'
        ? '使用内置预设: ' + slug
        : '使用模板库模板: ' + slug;
    } else {
      els.presetHint.textContent = '';
    }
  });
}

// ── 初始化 ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  cacheElements();
  bindEvents();

  try {
    await OfficeHelper.initialize();
    await checkApiConnection();
    await loadTemplates();
  } catch (err) {
    showStatus('插件初始化失败: ' + err.message, 'error');
  }
});
