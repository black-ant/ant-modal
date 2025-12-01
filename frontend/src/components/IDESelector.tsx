import { X, Code2, ExternalLink } from 'lucide-react';
import { IDEConfig } from '../types';
import Button from './Button';

interface IDESelectorProps {
  ides: IDEConfig[];
  filePath: string;
  onClose: () => void;
  onSelect: (ide: IDEConfig) => void;
}

export default function IDESelector({ ides, filePath, onClose, onSelect }: IDESelectorProps) {
  const getIDEIcon = (icon: string) => {
    // 这里可以根据icon名称返回不同的颜色和样式
    const iconColors: Record<string, string> = {
      vscode: 'bg-blue-100 text-blue-600',
      cursor: 'bg-purple-100 text-purple-600',
      windsurf: 'bg-cyan-100 text-cyan-600',
      pycharm: 'bg-green-100 text-green-600',
      sublime: 'bg-orange-100 text-orange-600',
    };
    
    return iconColors[icon] || 'bg-gray-100 text-gray-600';
  };

  return (
    <div
      className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl bg-white rounded-lg shadow-2xl animate-slide-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-100 rounded-lg">
              <ExternalLink className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-800">选择IDE打开脚本</h2>
              <p className="text-xs text-gray-500 truncate max-w-md">{filePath}</p>
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
        <div className="p-6">
          {ides.length === 0 ? (
            <div className="text-center py-12">
              <Code2 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 text-sm mb-2">未检测到已安装的IDE</p>
              <p className="text-gray-400 text-xs">
                请确保已安装 VSCode、Cursor、Windsurf 等IDE
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {ides.map((ide) => (
                <button
                  key={ide.name}
                  onClick={() => onSelect(ide)}
                  className="group relative p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-all text-left"
                >
                  <div className="flex items-start gap-3">
                    <div className={`p-3 rounded-lg ${getIDEIcon(ide.icon)} group-hover:scale-110 transition-transform`}>
                      <Code2 className="w-6 h-6" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-gray-800 mb-1">{ide.name}</h3>
                      <p className="text-xs text-gray-500 truncate font-mono">{ide.path}</p>
                      {ide.detected && (
                        <span className="inline-block mt-2 px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                          已安装
                        </span>
                      )}
                    </div>
                  </div>
                  <ExternalLink className="absolute top-3 right-3 w-4 h-4 text-gray-400 group-hover:text-primary-600 transition-colors" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 bg-gray-50">
          <Button variant="secondary" size="sm" onClick={onClose}>
            取消
          </Button>
        </div>
      </div>
    </div>
  );
}

