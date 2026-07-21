/* global Office */

/**
 * Office API interaction layer.
 * Wraps Word.js APIs for document access and manipulation.
 */
const OfficeHelper = (() => {
  let _doc = null;

  /**
   * Initialize Office.js and return a promise that resolves when ready.
   */
  function initialize() {
    return new Promise((resolve, reject) => {
      Office.onReady((info) => {
        if (info.host === Office.HostType.DOCUMENT) {
          _doc = Office.context.document;
          resolve(info);
        } else {
          reject(new Error('当前插件仅支持 Word 文档'));
        }
      });
    });
  }

  /**
   * Get the current document object.
   */
  function getDocument() {
    return _doc;
  }

  /**
   * Get document content as a File object via the Office API.
   * Returns a Blob that can be sent to the backend API.
   */
  function getDocumentFile() {
    return new Promise((resolve, reject) => {
      if (!_doc) {
        reject(new Error('文档未初始化'));
        return;
      }

      _doc.getFileAsync(Office.FileType.Compressed, { sliceSize: 4096 * 4096 }, (result) => {
        if (result.status === Office.AsyncResultStatus.Succeeded) {
          const file = result.value;
          const slices = [];
          let sliceIndex = 0;

          function getSlice() {
            file.getSliceAsync(sliceIndex, file.sliceCount, (sliceResult) => {
              if (sliceResult.status === Office.AsyncResultStatus.Succeeded) {
                slices.push(sliceResult.value);
                sliceIndex++;
                if (sliceIndex < file.sliceCount) {
                  getSlice();
                } else {
                  file.closeAsync();
                  const blob = new Blob(slices, { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
                  resolve(blob);
                }
              } else {
                file.closeAsync();
                reject(new Error('读取文档切片失败: ' + sliceResult.error.message));
              }
            });
          }

          getSlice();
        } else {
          reject(new Error('获取文档失败: ' + result.error.message));
        }
      });
    });
  }

  /**
   * Replace the entire document content with a new file blob.
   * Uses insertFileAsync or setFileAsync depending on availability.
   */
  function replaceDocument(blob) {
    return new Promise((resolve, reject) => {
      if (!_doc) {
        reject(new Error('文档未初始化'));
        return;
      }

      const reader = new FileReader();
      reader.onload = () => {
        const arrayBuffer = reader.result;

        _doc.setSelectedDataAsync(arrayBuffer, {
          coercionType: Office.CoercionType.File,
        }, (result) => {
          if (result.status === Office.AsyncResultStatus.Succeeded) {
            resolve();
          } else {
            reject(new Error('替换文档失败: ' + result.error.message));
          }
        });
      };
      reader.onerror = () => reject(new Error('读取文件失败'));
      reader.readAsArrayBuffer(blob);
    });
  }

  /**
   * Get basic document info (title, word count).
   */
  function getDocumentInfo() {
    return new Promise((resolve, reject) => {
      if (!_doc) {
        reject(new Error('文档未初始化'));
        return;
      }

      _doc.settings.getAsync('Office.Title', (result) => {
        const title = result.status === Office.AsyncResultStatus.Succeeded
          ? result.value
          : '未命名文档';

        _doc.body.getAsync((bodyResult) => {
          if (bodyResult.status === Office.AsyncResultStatus.Succeeded) {
            const text = bodyResult.value.text || '';
            resolve({
              title: title,
              wordCount: text.split(/\s+/).filter(Boolean).length,
              charCount: text.length,
            });
          } else {
            resolve({ title: title, wordCount: 0, charCount: 0 });
          }
        });
      });
    });
  }

  return {
    initialize,
    getDocument,
    getDocumentFile,
    replaceDocument,
    getDocumentInfo,
  };
})();
