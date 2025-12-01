import { useState, useEffect } from 'react';
import { X, Play, Settings, AlertCircle, RefreshCw, Terminal, Copy, Check } from 'lucide-react';
import clsx from 'clsx';
import Button from './Button';
import Card from './Card';
import { 
  DeployArg, 
  parseModalArgs, 
  initArgValues, 
  validateArgValues, 
  generateModalRunCommand 
} from '../data/deployArgs';

interface DeployArgsDialogProps {
  scriptName: string;
  scriptPath: string;
  scriptContent: string;
  onClose: () => void;
  onExecute: (argsString: string) => void;
}

export default function DeployArgsDialog({
  scriptName,
  scriptPath,
  scriptContent,
  onClose,
  onExecute,
}: DeployArgsDialogProps) {
  // 解析参数定义
  const [args, setArgs] = useState<DeployArg[]>([]);
  
  // 参数值
  const [values, setValues] = useState<Record<string, string>>({});
  
  // 验证错误
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  // 执行状态
  const [isExecuting, setIsExecuting] = useState(false);
  
  // 命令复制状态
  const [copied, setCopied] = useState(false);

  // 解析参数
  useEffect(() => {
    const parsedArgs = parseModalArgs(scriptContent);
    setArgs(parsedArgs);
    setValues(initArgValues(parsedArgs));
  }, [scriptContent]);

  // 更新参数值
  const handleValueChange = (name: string, value: string) => {
    setValues(prev => ({ ...prev, [name]: value }));
    // 清除错误
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  // 重置为默认值
  const handleReset = () => {
    setValues(initArgValues(args));
    setErrors({});
  };

  // 验证并执行
  const handleExecute = () => {
    const validationErrors = validateArgValues(args, values);
    
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }
    
    setIsExecuting(true);
    
    // 生成参数字符串并执行
    const argsString = args.map(arg => {
      const value = values[arg.name];
      if (arg.type === 'bool') {
        return value === 'true' ? `--${arg.name}` : '';
      }
      if (!value || value.trim() === '') return '';
      return `--${arg.name}=${value}`;
    }).filter(Boolean).join(' ');
    
    onExecute(argsString);
  };

  // 复制命令
  const handleCopyCommand = () => {
    const command = generateModalRunCommand(scriptPath, args, values);
    navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // 生成预览命令
  const previewCommand = generateModalRunCommand(scriptPath, args, values);

  // 渲染输入控件
  const renderInput = (arg: DeployArg) => {
    const value = values[arg.name] || '';
    const hasError = !!errors[arg.name];
    
    switch (arg.type) {
      case 'select':
        return (
          <div className="space-y-2">
            <select
              value={value}
              onChange={(e) => handleValueChange(arg.name, e.target.value)}
              className={clsx(
                'w-full px-3 py-2 text-sm border rounded-lg transition-all',
                'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                hasError
                  ? 'border-red-300 bg-red-50'
                  : 'border-gray-300 hover:border-gray-400'
              )}
              disabled={isExecuting}
            >
              <option value="">请选择...</option>
              {arg.options.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
            {/* 快捷选择按钮 */}
            <div className="flex flex-wrap gap-1">
              {arg.options.map(opt => (
                <button
                  key={opt}
                  onClick={() => handleValueChange(arg.name, opt)}
                  className={clsx(
                    'px-2 py-0.5 text-xs rounded-md transition-colors',
                    value === opt
                      ? 'bg-primary-500 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  )}
                  disabled={isExecuting}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>
        );
      
      case 'bool':
        return (
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name={arg.name}
                checked={value !== 'true'}
                onChange={() => handleValueChange(arg.name, 'false')}
                className="w-4 h-4 text-primary-600"
                disabled={isExecuting}
              />
              <span className="text-sm text-gray-600">关闭</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name={arg.name}
                checked={value === 'true'}
                onChange={() => handleValueChange(arg.name, 'true')}
                className="w-4 h-4 text-primary-600"
                disabled={isExecuting}
              />
              <span className="text-sm text-gray-600">开启</span>
            </label>
          </div>
        );
      
      case 'number':
        return (
          <input
            type="number"
            value={value}
            onChange={(e) => handleValueChange(arg.name, e.target.value)}
            placeholder={arg.defaultValue || `请输入 ${arg.label}`}
            className={clsx(
              'w-full px-3 py-2 text-sm border rounded-lg transition-all',
              'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
              hasError
                ? 'border-red-300 bg-red-50'
                : 'border-gray-300 hover:border-gray-400'
            )}
            disabled={isExecuting}
          />
        );
      
      default: // text
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => handleValueChange(arg.name, e.target.value)}
            placeholder={arg.defaultValue || `请输入 ${arg.label}`}
            className={clsx(
              'w-full px-3 py-2 text-sm border rounded-lg transition-all',
              'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
              hasError
                ? 'border-red-300 bg-red-50'
                : 'border-gray-300 hover:border-gray-400'
            )}
            disabled={isExecuting}
          />
        );
    }
  };

  return (
    <div 
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <Card 
        className="w-full max-w-xl max-h-[90vh] overflow-hidden flex flex-col animate-slide-in"
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-white">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Settings className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-800">配置执行参数</h2>
              <p className="text-xs text-gray-500">{scriptName}</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {args.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Settings className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p>此脚本没有定义参数</p>
              <p className="text-xs mt-2">将使用默认参数执行</p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-gray-600">
                  请配置以下 {args.length} 个参数：
                </p>
                <button
                  onClick={handleReset}
                  className="text-xs text-gray-500 hover:text-primary-600 flex items-center gap-1"
                >
                  <RefreshCw className="w-3 h-3" />
                  重置默认值
                </button>
              </div>
              
              <div className="space-y-4">
                {args.map((arg) => (
                  <div key={arg.name}>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                      {arg.label}
                      {arg.required && <span className="text-red-500 ml-1">*</span>}
                      <span className="ml-2 text-xs text-gray-400 font-normal">
                        --{arg.name}
                      </span>
                    </label>
                    {renderInput(arg)}
                    {errors[arg.name] && (
                      <p className="mt-1 text-xs text-red-500 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" />
                        {errors[arg.name]}
                      </p>
                    )}
                    {arg.defaultValue && !errors[arg.name] && arg.type === 'text' && (
                      <p className="mt-1 text-xs text-gray-400">
                        默认值: {arg.defaultValue}
                      </p>
                    )}
                  </div>
                ))}
              </div>

              {/* 命令预览 */}
              <div className="mt-6 p-3 bg-gray-900 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 text-gray-400 text-xs">
                    <Terminal className="w-3 h-3" />
                    生成的命令
                  </div>
                  <button
                    onClick={handleCopyCommand}
                    className="text-xs text-gray-400 hover:text-white flex items-center gap-1 transition-colors"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3 h-3 text-green-400" />
                        <span className="text-green-400">已复制</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        复制
                      </>
                    )}
                  </button>
                </div>
                <code className="text-xs text-green-400 font-mono break-all">
                  {previewCommand}
                </code>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 bg-gray-50">
          <Button variant="secondary" onClick={onClose} disabled={isExecuting}>
            取消
          </Button>
          <Button 
            onClick={handleExecute} 
            disabled={isExecuting}
            className="bg-blue-500 hover:bg-blue-600"
          >
            <Play className="w-4 h-4 mr-1" />
            {isExecuting ? '执行中...' : '执行'}
          </Button>
        </div>
      </Card>
    </div>
  );
}

/**
 * 检测脚本是否包含 @modal-args 参数定义
 */
export { hasModalArgs } from '../data/deployArgs';

