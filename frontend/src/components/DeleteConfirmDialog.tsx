import { useState } from 'react';
import { X, Trash2, AlertTriangle } from 'lucide-react';
import Button from './Button';

interface DeleteConfirmDialogProps {
  scriptName: string;
  scriptPath: string;
  onClose: () => void;
  onConfirm: (deleteFile: boolean) => Promise<void>;
}

export default function DeleteConfirmDialog({
  scriptName,
  scriptPath,
  onClose,
  onConfirm,
}: DeleteConfirmDialogProps) {
  const [deleteFile, setDeleteFile] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState('');

  const handleConfirm = async () => {
    setError('');
    setIsDeleting(true);

    try {
      await onConfirm(deleteFile);
      onClose();
    } catch (err: any) {
      setError(err.message || '删除失败');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-white rounded-lg shadow-2xl animate-slide-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-800">删除脚本</h2>
              <p className="text-xs text-gray-500">此操作无法撤销</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800">
              确定要删除以下脚本吗？
            </p>
          </div>

          <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-start gap-3">
              <Trash2 className="w-5 h-5 text-gray-400 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800">{scriptName}</p>
                <p className="text-xs text-gray-500 mt-1 font-mono truncate">
                  {scriptPath}
                </p>
              </div>
            </div>
          </div>

          {/* 删除选项 */}
          <div className="space-y-3">
            <label className="flex items-start gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
              <input
                type="checkbox"
                checked={deleteFile}
                onChange={(e) => setDeleteFile(e.target.checked)}
                className="mt-0.5"
                disabled={isDeleting}
              />
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-800">
                  同时删除脚本文件
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  勾选后将从磁盘中永久删除 .py 文件
                </p>
              </div>
            </label>

            {deleteFile && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-xs text-red-700 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>
                    <strong>警告：</strong>文件删除后无法恢复，请确保您已经备份重要数据
                  </span>
                </p>
              </div>
            )}
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 bg-gray-50">
          <Button variant="secondary" onClick={onClose} disabled={isDeleting}>
            取消
          </Button>
          <Button
            variant="danger"
            onClick={handleConfirm}
            disabled={isDeleting}
          >
            <Trash2 className="w-4 h-4 mr-1.5" />
            {isDeleting ? '删除中...' : deleteFile ? '删除脚本和文件' : '删除脚本'}
          </Button>
        </div>
      </div>
    </div>
  );
}

