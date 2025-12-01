import { useState, useEffect } from 'react';
import { X, Play, Variable, AlertCircle, RefreshCw, Globe, Folder, FileCode, History, Clock, Trash2, Upload } from 'lucide-react';
import clsx from 'clsx';
import Button from './Button';
import Card from './Card';
import { parseTemplateVariables, TemplateVariable, replaceTemplateVariables, scriptTemplates } from '../data/scriptTemplates';
import { GetProjectVariables, GetGlobalVariables, SelectModelFile } from '../../wailsjs/go/main/App';

// 历史记录项
interface HistoryItem {
  values: Record<string, string>;
  timestamp: number;
  label?: string;  // 可选的标签，用于快速识别
}

// 历史记录存储 key 前缀
const HISTORY_KEY_PREFIX = 'scriptHistory:';
const MAX_HISTORY_ITEMS = 5;

interface ExecuteVariableDialogProps {
  scriptName: string;
  scriptContent: string;
  projectId?: string;  // 用于加载项目变量
  onClose: () => void;
  onExecute: (finalContent: string, filledVariables?: Record<string, string>) => void;
}

export default function ExecuteVariableDialog({
  scriptName,
  scriptContent,
  projectId,
  onClose,
  onExecute,
}: ExecuteVariableDialogProps) {
  // 解析脚本中的变量
  const [allVariables, setAllVariables] = useState<TemplateVariable[]>([]);
  const [scriptVariables, setScriptVariables] = useState<TemplateVariable[]>([]); // 只有 script scope 的变量
  
  // 初始化变量值（使用默认值）
  const [values, setValues] = useState<Record<string, string>>({});
  
  // 项目变量和全局变量
  const [projectVars, setProjectVars] = useState<Record<string, string>>({});
  const [globalVars, setGlobalVars] = useState<Record<string, string>>({});
  
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isExecuting, setIsExecuting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  
  // 历史记录
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  // 获取历史记录存储 key
  const getHistoryKey = () => `${HISTORY_KEY_PREFIX}${projectId || 'global'}:${scriptName}`;

  // 加载历史记录
  const loadHistory = () => {
    try {
      const key = getHistoryKey();
      const stored = localStorage.getItem(key);
      if (stored) {
        const items: HistoryItem[] = JSON.parse(stored);
        setHistory(items);
      }
    } catch (err) {
      console.error('加载历史记录失败:', err);
    }
  };

  // 保存历史记录
  const saveHistory = (newValues: Record<string, string>) => {
    try {
      const key = getHistoryKey();
      
      // 生成标签（使用第一个有值的变量）
      const firstValue = Object.entries(newValues).find(([_, v]) => v && v.trim())?.[1];
      const label = firstValue ? (firstValue.length > 30 ? firstValue.substring(0, 30) + '...' : firstValue) : undefined;
      
      const newItem: HistoryItem = {
        values: { ...newValues },
        timestamp: Date.now(),
        label
      };
      
      // 检查是否有重复（相同的值组合）
      const isDuplicate = history.some(item => 
        JSON.stringify(item.values) === JSON.stringify(newValues)
      );
      
      if (!isDuplicate) {
        // 添加到历史记录开头，保留最近的 MAX_HISTORY_ITEMS 条
        const newHistory = [newItem, ...history].slice(0, MAX_HISTORY_ITEMS);
        setHistory(newHistory);
        localStorage.setItem(key, JSON.stringify(newHistory));
      }
    } catch (err) {
      console.error('保存历史记录失败:', err);
    }
  };

  // 应用历史记录
  const applyHistory = (item: HistoryItem) => {
    setValues(item.values);
    setShowHistory(false);
  };

  // 删除单条历史记录
  const deleteHistoryItem = (index: number, e: React.MouseEvent) => {
    e.stopPropagation();
    const newHistory = history.filter((_, i) => i !== index);
    setHistory(newHistory);
    localStorage.setItem(getHistoryKey(), JSON.stringify(newHistory));
  };

  // 清空所有历史记录
  const clearHistory = () => {
    setHistory([]);
    localStorage.removeItem(getHistoryKey());
  };

  // 加载项目变量、全局变量和历史记录
  useEffect(() => {
    const loadExternalVariables = async () => {
      setIsLoading(true);
      try {
        // 加载全局变量
        const gVars = await GetGlobalVariables();
        setGlobalVars(gVars || {});

        // 加载项目变量
        if (projectId) {
          const pVars = await GetProjectVariables(projectId);
          setProjectVars(pVars || {});
        }
        
        // 加载历史记录
        loadHistory();
      } catch (err) {
        console.error('加载变量失败:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadExternalVariables();
  }, [projectId, scriptName]);

  // 解析变量并根据 scope 分类
  useEffect(() => {
    const vars = parseTemplateVariables(scriptContent);
    
    // 尝试从模板库匹配变量的 scope
    const enrichedVars = vars.map(v => {
      // 在模板库中查找匹配的变量定义
      for (const template of scriptTemplates) {
        const templateVar = template.variables.find(tv => tv.name === v.name);
        if (templateVar && templateVar.scope) {
          return { ...v, scope: templateVar.scope, options: templateVar.options };
        }
      }
      return v;
    });
    
    setAllVariables(enrichedVars);
    
    // 过滤出只需要用户填写的 script scope 变量
    const scriptOnlyVars = enrichedVars.filter(v => !v.scope || v.scope === 'script');
    setScriptVariables(scriptOnlyVars);
    
    // 初始化默认值
    const initial: Record<string, string> = {};
    scriptOnlyVars.forEach(v => {
      initial[v.name] = v.defaultValue;
    });
    setValues(initial);
  }, [scriptContent]);

  // 更新变量值
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
    const initial: Record<string, string> = {};
    scriptVariables.forEach(v => {
      initial[v.name] = v.defaultValue;
    });
    setValues(initial);
    setErrors({});
  };

  // 验证表单
  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    scriptVariables.forEach(v => {
      if (v.required && !values[v.name]?.trim()) {
        newErrors[v.name] = `${v.label} 为必填项`;
      }
    });
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // 合并所有变量：global < project < script
  const getMergedValues = (): Record<string, string> => {
    const merged: Record<string, string> = {};
    
    // 1. 全局变量（最低优先级）
    Object.assign(merged, globalVars);
    
    // 2. 项目变量
    Object.assign(merged, projectVars);
    
    // 3. 脚本变量（最高优先级）
    Object.assign(merged, values);
    
    // 4. 对于没有用户填写的变量，使用默认值
    allVariables.forEach(v => {
      if (!merged[v.name] && v.defaultValue) {
        merged[v.name] = v.defaultValue;
      }
    });
    
    return merged;
  };

  // 获取变量的来源显示
  const getVariableSource = (varName: string): { source: string; value: string } | null => {
    const variable = allVariables.find(v => v.name === varName);
    if (!variable) return null;
    
    const scope = variable.scope || 'script';
    
    if (scope === 'project' && projectVars[varName]) {
      return { source: '项目变量', value: projectVars[varName] };
    }
    if (scope === 'global' && globalVars[varName]) {
      return { source: '全局变量', value: globalVars[varName] };
    }
    return null;
  };

  // 执行脚本
  const handleExecute = () => {
    if (!validate()) return;
    
    // 保存当前输入到历史记录（只保存脚本变量）
    if (scriptVariables.length > 0) {
      saveHistory(values);
    }
    
    setIsExecuting(true);
    const mergedValues = getMergedValues();
    const finalContent = replaceTemplateVariables(scriptContent, mergedValues);
    onExecute(finalContent, mergedValues);
  };

  // 计算自动填充的变量数量
  const autoFilledCount = allVariables.filter(v => {
    const scope = v.scope || 'script';
    return (scope === 'project' && projectVars[v.name]) || (scope === 'global' && globalVars[v.name]);
  }).length;

  return (
    <div 
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <Card 
        className="w-full max-w-lg max-h-[85vh] overflow-hidden flex flex-col animate-slide-in"
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gradient-to-r from-amber-50 to-white">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-100 rounded-lg">
              <Variable className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-800">填写执行参数</h2>
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
          {isLoading ? (
            <div className="text-center py-8 text-gray-500">
              <RefreshCw className="w-8 h-8 mx-auto mb-3 text-gray-300 animate-spin" />
              <p>加载变量配置...</p>
            </div>
          ) : allVariables.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Variable className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p>此脚本没有需要填写的变量</p>
            </div>
          ) : (
            <>
              {/* 自动填充的变量提示 */}
              {autoFilledCount > 0 && (
                <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-xs text-green-700 flex items-center gap-1">
                    <Globe className="w-3 h-3" />
                    已从项目/全局变量自动填充 {autoFilledCount} 个参数
                  </p>
                  <div className="mt-2 space-y-1">
                    {allVariables.filter(v => {
                      const scope = v.scope || 'script';
                      return (scope === 'project' && projectVars[v.name]) || (scope === 'global' && globalVars[v.name]);
                    }).map(v => {
                      const source = getVariableSource(v.name);
                      return source ? (
                        <div key={v.name} className="flex items-center gap-2 text-xs text-green-600">
                          {v.scope === 'project' ? <Folder className="w-3 h-3" /> : <Globe className="w-3 h-3" />}
                          <span className="font-mono">{v.name}</span>
                          <span className="text-green-700">=</span>
                          <span className="font-mono text-green-700 truncate max-w-[150px]" title={source.value}>{source.value}</span>
                          <span className="text-green-500">← {source.source}</span>
                        </div>
                      ) : null;
                    })}
                  </div>
                </div>
              )}

              {scriptVariables.length > 0 ? (
                <>
                  <div className="flex items-center justify-between mb-4">
                    <p className="text-sm text-gray-600 flex items-center gap-1">
                      <FileCode className="w-4 h-4" />
                      请填写以下 {scriptVariables.length} 个参数：
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
                    {scriptVariables.map((variable) => (
                      <div key={variable.name}>
                        <label className="block text-sm font-medium text-gray-700 mb-1.5">
                          {variable.label}
                          {variable.required && <span className="text-red-500 ml-1">*</span>}
                        </label>
                        {/* 文件选择类型 */}
                        {variable.inputType === 'file' ? (
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={values[variable.name] || ''}
                              onChange={(e) => handleValueChange(variable.name, e.target.value)}
                              placeholder="点击右侧按钮选择文件"
                              className={clsx(
                                'flex-1 px-3 py-2 text-sm border rounded-lg transition-all',
                                'focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent',
                                errors[variable.name]
                                  ? 'border-red-300 bg-red-50'
                                  : 'border-gray-300 hover:border-gray-400'
                              )}
                              disabled={isExecuting}
                            />
                            <button
                              type="button"
                              onClick={async () => {
                                try {
                                  const filePath = await SelectModelFile();
                                  if (filePath) {
                                    // Windows 路径转换：反斜杠转正斜杠，避免 Python 转义问题
                                    const normalizedPath = filePath.replace(/\\/g, '/');
                                    handleValueChange(variable.name, normalizedPath);
                                  }
                                } catch (err) {
                                  console.error('选择文件失败:', err);
                                }
                              }}
                              disabled={isExecuting}
                              className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50"
                            >
                              <Upload className="w-4 h-4" />
                              选择文件
                            </button>
                          </div>
                        ) : variable.options ? (
                          /* 下拉选择类型 */
                          <select
                            value={values[variable.name] || variable.defaultValue}
                            onChange={(e) => handleValueChange(variable.name, e.target.value)}
                            className={clsx(
                              'w-full px-3 py-2 text-sm border rounded-lg transition-all',
                              'focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent',
                              errors[variable.name]
                                ? 'border-red-300 bg-red-50'
                                : 'border-gray-300 hover:border-gray-400'
                            )}
                            disabled={isExecuting}
                          >
                            {variable.options.map((option) => (
                              <option key={option} value={option}>{option}</option>
                            ))}
                          </select>
                        ) : (
                          /* 文本输入类型 */
                          <input
                            type="text"
                            value={values[variable.name] || ''}
                            onChange={(e) => handleValueChange(variable.name, e.target.value)}
                            placeholder={variable.defaultValue || `请输入 ${variable.label}`}
                            className={clsx(
                              'w-full px-3 py-2 text-sm border rounded-lg transition-all',
                              'focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent',
                              errors[variable.name]
                                ? 'border-red-300 bg-red-50'
                                : 'border-gray-300 hover:border-gray-400'
                            )}
                            disabled={isExecuting}
                          />
                        )}
                        {errors[variable.name] && (
                          <p className="mt-1 text-xs text-red-500 flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" />
                            {errors[variable.name]}
                          </p>
                        )}
                        {variable.defaultValue && !errors[variable.name] && !variable.options && variable.inputType !== 'file' && (
                          <p className="mt-1 text-xs text-gray-400">
                            默认值: {variable.defaultValue}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                  
                  {/* 历史记录区域 */}
                  {history.length > 0 && (
                    <div className="mt-4">
                      <div 
                        className="flex items-center justify-between cursor-pointer p-2 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                        onClick={() => setShowHistory(!showHistory)}
                      >
                        <div className="flex items-center gap-2 text-sm text-gray-600">
                          <History className="w-4 h-4" />
                          <span>历史记录 ({history.length})</span>
                        </div>
                        <span className="text-xs text-gray-400">
                          {showHistory ? '收起' : '展开'}
                        </span>
                      </div>
                      
                      {showHistory && (
                        <div className="mt-2 space-y-2">
                          {history.map((item, index) => (
                            <div
                              key={item.timestamp}
                              className="flex items-center justify-between p-2 bg-white border border-gray-200 rounded-lg hover:border-amber-300 hover:bg-amber-50 cursor-pointer transition-all group"
                              onClick={() => applyHistory(item)}
                            >
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <Clock className="w-3 h-3 text-gray-400 shrink-0" />
                                  <span className="text-xs text-gray-500">
                                    {new Date(item.timestamp).toLocaleString('zh-CN', {
                                      month: 'numeric',
                                      day: 'numeric',
                                      hour: '2-digit',
                                      minute: '2-digit'
                                    })}
                                  </span>
                                </div>
                                <p className="text-sm text-gray-700 truncate mt-0.5 pl-5" title={item.label}>
                                  {item.label || Object.values(item.values).filter(v => v).join(', ') || '(空)'}
                                </p>
                              </div>
                              <button
                                onClick={(e) => deleteHistoryItem(index, e)}
                                className="p-1 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                                title="删除"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          ))}
                          
                          <button
                            onClick={clearHistory}
                            className="w-full py-1.5 text-xs text-gray-500 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                          >
                            清空所有历史
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-4 text-gray-500">
                  <p className="text-sm">所有变量已自动填充，可直接执行</p>
                </div>
              )}

              {/* 提示信息 */}
              <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-xs text-amber-700">
                  <strong>变量优先级：</strong>脚本变量 &gt; 项目变量 &gt; 全局变量
                </p>
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
            disabled={isExecuting || isLoading}
            className="bg-amber-500 hover:bg-amber-600"
          >
            <Play className="w-4 h-4 mr-1" />
            {isExecuting ? '执行中...' : '执行脚本'}
          </Button>
        </div>
      </Card>
    </div>
  );
}

// 检测脚本内容是否包含模板变量
export function hasTemplateVariables(content: string): boolean {
  const regex = /\{\{([^}]+)\}\}/;
  return regex.test(content);
}


