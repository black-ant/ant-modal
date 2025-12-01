import { useState, useEffect } from 'react';
import { 
  X, Play, ChevronDown, ChevronRight, Terminal, Table2, 
  FileText, Copy, CheckCircle, XCircle, Loader2
} from 'lucide-react';
import clsx from 'clsx';
import Button from './Button';

interface QuickAction {
  id: string;
  name: string;
  description: string;
  command: string;
  icon: any;
  color: string;
  needsInput?: boolean;
  inputLabel?: string;
  inputPlaceholder?: string;
}

interface TableData {
  headers: string[];
  rows: string[][];
}

interface CommandExecuteDialogProps {
  action: QuickAction;
  onClose: () => void;
  onExecute: (command: string) => Promise<string>;
  selectedAppName?: string;
}

// 解析表格输出
function parseTableOutput(output: string): TableData | null {
  const lines = output.trim().split('\n').filter(line => line.trim());
  
  if (lines.length < 2) return null;
  
  // 尝试检测表格格式
  // 方式1: 检测分隔线 (如 +----+----+ 或 ├────┼────┤)
  const separatorPattern = /^[\+\-\|├┼┤─]+$/;
  const hasSeparator = lines.some(line => separatorPattern.test(line.trim()));
  
  // 方式2: 检测列对齐（多个空格分隔）
  const multiSpacePattern = /\s{2,}/;
  
  let headers: string[] = [];
  let rows: string[][] = [];
  
  if (hasSeparator) {
    // 带分隔线的表格
    const dataLines = lines.filter(line => !separatorPattern.test(line.trim()));
    if (dataLines.length >= 1) {
      // 第一行是表头
      headers = dataLines[0].split(/\s*\|\s*/).filter(cell => cell.trim()).map(cell => cell.trim());
      // 剩余行是数据
      for (let i = 1; i < dataLines.length; i++) {
        const cells = dataLines[i].split(/\s*\|\s*/).filter(cell => cell.trim()).map(cell => cell.trim());
        if (cells.length > 0) {
          rows.push(cells);
        }
      }
    }
  } else if (multiSpacePattern.test(lines[0])) {
    // 空格分隔的表格（如 Modal CLI 输出）
    // 尝试检测列位置
    const headerLine = lines[0];
    
    // 通过多个空格分割
    headers = headerLine.split(/\s{2,}/).map(h => h.trim()).filter(h => h);
    
    if (headers.length >= 2) {
      for (let i = 1; i < lines.length; i++) {
        const cells = lines[i].split(/\s{2,}/).map(c => c.trim()).filter(c => c);
        if (cells.length > 0) {
          rows.push(cells);
        }
      }
    }
  }
  
  // 验证解析结果
  if (headers.length >= 2 && rows.length >= 1) {
    return { headers, rows };
  }
  
  return null;
}

const colorClasses: Record<string, { bg: string; text: string; border: string }> = {
  blue: { bg: 'bg-blue-500', text: 'text-blue-600', border: 'border-blue-500' },
  green: { bg: 'bg-green-500', text: 'text-green-600', border: 'border-green-500' },
  yellow: { bg: 'bg-yellow-500', text: 'text-yellow-600', border: 'border-yellow-500' },
  purple: { bg: 'bg-purple-500', text: 'text-purple-600', border: 'border-purple-500' },
  indigo: { bg: 'bg-indigo-500', text: 'text-indigo-600', border: 'border-indigo-500' },
  red: { bg: 'bg-red-500', text: 'text-red-600', border: 'border-red-500' },
  gray: { bg: 'bg-gray-500', text: 'text-gray-600', border: 'border-gray-500' },
  cyan: { bg: 'bg-cyan-500', text: 'text-cyan-600', border: 'border-cyan-500' },
  teal: { bg: 'bg-teal-500', text: 'text-teal-600', border: 'border-teal-500' },
  slate: { bg: 'bg-slate-500', text: 'text-slate-600', border: 'border-slate-500' },
  orange: { bg: 'bg-orange-500', text: 'text-orange-600', border: 'border-orange-500' },
  pink: { bg: 'bg-pink-500', text: 'text-pink-600', border: 'border-pink-500' },
  amber: { bg: 'bg-amber-500', text: 'text-amber-600', border: 'border-amber-500' },
};

export default function CommandExecuteDialog({ 
  action, 
  onClose, 
  onExecute,
  selectedAppName 
}: CommandExecuteDialogProps) {
  const [inputValue, setInputValue] = useState('');
  const [isExecuting, setIsExecuting] = useState(false);
  const [output, setOutput] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(true);
  const [viewMode, setViewMode] = useState<'table' | 'raw'>('table');
  const [copied, setCopied] = useState(false);
  
  const colors = colorClasses[action.color] || colorClasses.gray;
  
  // 自动执行（如果不需要输入）
  useEffect(() => {
    if (!action.needsInput) {
      handleExecute();
    }
  }, []);
  
  const handleExecute = async () => {
    if (action.needsInput && !inputValue.trim()) {
      setError('请输入必要的参数');
      return;
    }
    
    setIsExecuting(true);
    setOutput(null);
    setError(null);
    
    try {
      const fullCommand = action.needsInput 
        ? `${action.command} ${inputValue.trim()}`
        : action.command;
      
      const result = await onExecute(fullCommand);
      setOutput(result);
    } catch (err: any) {
      setError(err.message || String(err));
    } finally {
      setIsExecuting(false);
    }
  };
  
  const copyToClipboard = () => {
    if (output) {
      navigator.clipboard.writeText(output);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };
  
  const tableData = output ? parseTableOutput(output) : null;
  const fullCommand = action.needsInput 
    ? `${action.command} ${inputValue || '<参数>'}`
    : action.command;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden animate-scale-in">
        {/* Header */}
        <div className={clsx('px-5 py-4 flex items-center justify-between border-b', colors.bg)}>
          <div className="flex items-center gap-3">
            <action.icon className="w-5 h-5 text-white" />
            <div>
              <h2 className="text-lg font-semibold text-white">{action.name}</h2>
              <p className="text-sm text-white/80">{action.description}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-white/20 transition-colors"
          >
            <X className="w-5 h-5 text-white" />
          </button>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-auto p-5 space-y-4">
          {/* 命令详情 (可收起) */}
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="w-full px-4 py-2.5 flex items-center gap-2 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
            >
              {showDetails ? (
                <ChevronDown className="w-4 h-4 text-gray-500" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-500" />
              )}
              <Terminal className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">命令详情</span>
              {selectedAppName && (
                <span className="ml-auto text-xs text-gray-500">
                  账号: {selectedAppName}
                </span>
              )}
            </button>
            
            {showDetails && (
              <div className="p-4 bg-gray-900">
                <code className="text-sm text-green-400 font-mono">
                  $ {fullCommand}
                </code>
              </div>
            )}
          </div>
          
          {/* 参数输入 */}
          {action.needsInput && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                {action.inputLabel || '参数'}
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder={action.inputPlaceholder}
                  className="flex-1 px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  onKeyDown={(e) => e.key === 'Enter' && handleExecute()}
                  disabled={isExecuting}
                />
                <Button
                  onClick={handleExecute}
                  disabled={isExecuting}
                  className="px-6"
                >
                  {isExecuting ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-1" />
                      执行
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
          
          {/* 执行状态 */}
          {isExecuting && (
            <div className="flex items-center justify-center gap-3 py-8">
              <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
              <span className="text-gray-600">正在执行命令...</span>
            </div>
          )}
          
          {/* 错误信息 */}
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <XCircle className="w-5 h-5 text-red-500" />
                <span className="font-medium text-red-700">执行失败</span>
              </div>
              <pre className="text-sm text-red-600 whitespace-pre-wrap font-mono">
                {error}
              </pre>
            </div>
          )}
          
          {/* 执行结果 */}
          {output && !error && (
            <div className="space-y-3">
              {/* 结果头部 */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-green-500" />
                  <span className="font-medium text-green-700">执行成功</span>
                </div>
                
                <div className="flex items-center gap-2">
                  {/* 视图切换 */}
                  {tableData && (
                    <div className="flex bg-gray-100 rounded-lg p-0.5">
                      <button
                        onClick={() => setViewMode('table')}
                        className={clsx(
                          'px-3 py-1 text-xs rounded-md transition-colors flex items-center gap-1',
                          viewMode === 'table' 
                            ? 'bg-white text-gray-800 shadow-sm' 
                            : 'text-gray-600 hover:text-gray-800'
                        )}
                      >
                        <Table2 className="w-3 h-3" />
                        表格
                      </button>
                      <button
                        onClick={() => setViewMode('raw')}
                        className={clsx(
                          'px-3 py-1 text-xs rounded-md transition-colors flex items-center gap-1',
                          viewMode === 'raw' 
                            ? 'bg-white text-gray-800 shadow-sm' 
                            : 'text-gray-600 hover:text-gray-800'
                        )}
                      >
                        <FileText className="w-3 h-3" />
                        原始
                      </button>
                    </div>
                  )}
                  
                  {/* 复制按钮 */}
                  <button
                    onClick={copyToClipboard}
                    className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
                    title="复制结果"
                  >
                    {copied ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : (
                      <Copy className="w-4 h-4 text-gray-500" />
                    )}
                  </button>
                </div>
              </div>
              
              {/* 表格视图 */}
              {tableData && viewMode === 'table' ? (
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 border-b border-gray-200">
                          {tableData.headers.map((header, i) => (
                            <th 
                              key={i} 
                              className="px-4 py-3 text-left font-semibold text-gray-700"
                            >
                              {header}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {tableData.rows.map((row, i) => (
                          <tr 
                            key={i} 
                            className={clsx(
                              'border-b border-gray-100 last:border-0',
                              i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'
                            )}
                          >
                            {row.map((cell, j) => (
                              <td key={j} className="px-4 py-2.5 text-gray-600">
                                {cell}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
                    共 {tableData.rows.length} 条记录
                  </div>
                </div>
              ) : (
                /* 原始输出 */
                <div className="bg-gray-900 rounded-lg p-4 overflow-auto max-h-80">
                  <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">
                    {output}
                  </pre>
                </div>
              )}
            </div>
          )}
          
          {/* 空状态（需要输入但未执行） */}
          {!isExecuting && !output && !error && action.needsInput && (
            <div className="text-center py-8 text-gray-400">
              <Terminal className="w-10 h-10 mx-auto mb-3 opacity-50" />
              <p className="text-sm">输入参数后点击执行</p>
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="px-5 py-3 bg-gray-50 border-t flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            关闭
          </Button>
          {!action.needsInput && !isExecuting && (
            <Button onClick={handleExecute}>
              <Play className="w-4 h-4 mr-1" />
              重新执行
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

