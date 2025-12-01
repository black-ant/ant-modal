import { useState, useEffect } from 'react';
import { X, Variable, Plus, Trash2, Save, AlertCircle, Search, CheckCircle, AlertTriangle, RefreshCw } from 'lucide-react';
import clsx from 'clsx';
import Button from './Button';
import Card from './Card';
import { GetProjectVariables, SetProjectVariables, GetScripts, ReadScriptContent } from '../../wailsjs/go/main/App';
import { parseTemplateVariables, scriptTemplates, TemplateVariable } from '../data/scriptTemplates';

interface ProjectVariablesDialogProps {
  projectId: string;
  projectName: string;
  projectPath: string;  // 项目路径，用于读取脚本
  onClose: () => void;
}

interface VariableItem {
  key: string;
  value: string;
  isNew?: boolean;
}

// 检测到的需要配置的项目变量
interface DetectedVariable {
  name: string;
  label: string;
  defaultValue: string;
  usedInScripts: string[];  // 使用此变量的脚本列表
  isConfigured: boolean;    // 是否已配置
}

export default function ProjectVariablesDialog({
  projectId,
  projectName,
  projectPath,
  onClose,
}: ProjectVariablesDialogProps) {
  const [variables, setVariables] = useState<VariableItem[]>([]);
  const [detectedVars, setDetectedVars] = useState<DetectedVariable[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [hasChanges, setHasChanges] = useState(false);

  // 加载项目变量和扫描脚本
  useEffect(() => {
    loadVariables();
    scanProjectScripts();
  }, [projectId]);

  const loadVariables = async () => {
    try {
      const vars = await GetProjectVariables(projectId);
      const items: VariableItem[] = Object.entries(vars || {}).map(([key, value]) => ({
        key,
        value: value as string,
      }));
      setVariables(items);
      setHasChanges(false);
    } catch (err) {
      console.error('加载变量失败:', err);
    }
  };

  // 扫描项目所有脚本，检测需要的项目变量
  const scanProjectScripts = async () => {
    setIsScanning(true);
    try {
      // 获取项目所有脚本
      const scripts = await GetScripts(projectId);
      if (!scripts || scripts.length === 0) {
        setDetectedVars([]);
        return;
      }

      // 收集所有项目级变量
      const projectVarsMap = new Map<string, DetectedVariable>();

      for (const script of scripts) {
        try {
          // 读取脚本内容
          const content = await ReadScriptContent(script.fullPath || `${projectPath}/${script.path}`);
          if (!content) continue;

          // 解析脚本中的变量
          const parsedVars = parseTemplateVariables(content);

          // 对每个变量，检查是否为项目级别
          for (const v of parsedVars) {
            // 在模板库中查找变量的 scope 定义
            let scope: string | undefined;
            let label = v.label;
            let defaultValue = v.defaultValue;

            for (const template of scriptTemplates) {
              const templateVar = template.variables.find(tv => tv.name === v.name);
              if (templateVar) {
                scope = templateVar.scope;
                label = templateVar.label || v.label;
                defaultValue = templateVar.defaultValue || v.defaultValue;
                break;
              }
            }

            // 只收集 scope 为 'project' 的变量
            if (scope === 'project') {
              if (projectVarsMap.has(v.name)) {
                // 已存在，添加脚本引用
                const existing = projectVarsMap.get(v.name)!;
                if (!existing.usedInScripts.includes(script.name)) {
                  existing.usedInScripts.push(script.name);
                }
              } else {
                projectVarsMap.set(v.name, {
                  name: v.name,
                  label,
                  defaultValue,
                  usedInScripts: [script.name],
                  isConfigured: false,
                });
              }
            }
          }
        } catch (err) {
          console.error(`读取脚本 ${script.name} 失败:`, err);
        }
      }

      // 检查哪些变量已配置
      const currentVars = await GetProjectVariables(projectId);
      const detectedList = Array.from(projectVarsMap.values()).map(dv => ({
        ...dv,
        isConfigured: !!(currentVars && currentVars[dv.name]),
      }));

      setDetectedVars(detectedList);
    } catch (err) {
      console.error('扫描脚本失败:', err);
    } finally {
      setIsScanning(false);
    }
  };

  // 添加新变量
  const handleAddVariable = () => {
    setVariables([...variables, { key: '', value: '', isNew: true }]);
    setHasChanges(true);
  };

  // 删除变量
  const handleDeleteVariable = (index: number) => {
    const newVars = [...variables];
    newVars.splice(index, 1);
    setVariables(newVars);
    setHasChanges(true);
  };

  // 更新变量
  const handleUpdateVariable = (index: number, field: 'key' | 'value', newValue: string) => {
    const newVars = [...variables];
    newVars[index] = { ...newVars[index], [field]: newValue };
    setVariables(newVars);
    setHasChanges(true);
    setError('');
  };

  // 保存变量
  const handleSave = async () => {
    // 验证
    const keys = new Set<string>();
    for (const v of variables) {
      if (!v.key.trim()) {
        setError('变量名不能为空');
        return;
      }
      if (keys.has(v.key)) {
        setError(`变量名重复: ${v.key}`);
        return;
      }
      keys.add(v.key);
    }

    setIsSaving(true);
    setError('');

    try {
      const varsMap: Record<string, string> = {};
      variables.forEach(v => {
        varsMap[v.key.trim()] = v.value;
      });

      await SetProjectVariables(projectId, varsMap);
      setHasChanges(false);
      onClose();
    } catch (err: any) {
      setError(err.message || '保存失败');
    } finally {
      setIsSaving(false);
    }
  };

  // 添加检测到的缺失变量
  const handleAddDetected = (dv: DetectedVariable) => {
    if (variables.some(v => v.key === dv.name)) {
      setError(`变量 ${dv.name} 已存在`);
      return;
    }
    setVariables([...variables, { key: dv.name, value: dv.defaultValue }]);
    setHasChanges(true);
    // 更新检测状态
    setDetectedVars(prev => prev.map(v => 
      v.name === dv.name ? { ...v, isConfigured: true } : v
    ));
  };

  // 一键添加所有缺失变量
  const handleAddAllMissing = () => {
    const missing = detectedVars.filter(dv => !dv.isConfigured && !variables.some(v => v.key === dv.name));
    if (missing.length === 0) return;

    const newVars = missing.map(dv => ({ key: dv.name, value: dv.defaultValue }));
    setVariables([...variables, ...newVars]);
    setHasChanges(true);
    // 更新检测状态
    setDetectedVars(prev => prev.map(v => ({ ...v, isConfigured: true })));
  };

  // 统计缺失变量数量
  const missingCount = detectedVars.filter(dv => !dv.isConfigured && !variables.some(v => v.key === dv.name)).length;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <Card
        className="w-full max-w-xl max-h-[85vh] overflow-hidden flex flex-col animate-slide-in"
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gradient-to-r from-violet-50 to-white">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-violet-100 rounded-lg">
              <Variable className="w-5 h-5 text-violet-600" />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-800">项目变量管理</h2>
              <p className="text-xs text-gray-500">{projectName}</p>
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
          {/* 说明 */}
          <div className="mb-4 p-3 bg-violet-50 border border-violet-200 rounded-lg">
            <p className="text-xs text-violet-700 leading-relaxed">
              <strong>项目变量</strong>：在此项目内所有脚本共享的变量。脚本执行时会自动使用这些值，无需每次手动填写。
            </p>
          </div>

          {/* 检测到的变量 */}
          {(isScanning || detectedVars.length > 0) && (
            <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium text-amber-700 flex items-center gap-1">
                  <Search className="w-3 h-3" />
                  扫描脚本检测到的项目变量
                </p>
                <button
                  onClick={scanProjectScripts}
                  disabled={isScanning}
                  className="text-xs text-amber-600 hover:text-amber-700 flex items-center gap-1"
                >
                  <RefreshCw className={clsx("w-3 h-3", isScanning && "animate-spin")} />
                  {isScanning ? '扫描中...' : '重新扫描'}
                </button>
              </div>

              {isScanning ? (
                <div className="text-center py-4 text-amber-600">
                  <RefreshCw className="w-5 h-5 mx-auto animate-spin mb-2" />
                  <p className="text-xs">正在扫描脚本...</p>
                </div>
              ) : detectedVars.length === 0 ? (
                <p className="text-xs text-amber-600">未检测到需要配置的项目变量</p>
              ) : (
                <>
                  <div className="space-y-2">
                    {detectedVars.map((dv) => {
                      const isConfiguredNow = dv.isConfigured || variables.some(v => v.key === dv.name);
                      return (
                        <div
                          key={dv.name}
                          className={clsx(
                            'flex items-center justify-between p-2 rounded-lg border',
                            isConfiguredNow
                              ? 'bg-green-50 border-green-200'
                              : 'bg-white border-amber-200'
                          )}
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              {isConfiguredNow ? (
                                <CheckCircle className="w-3.5 h-3.5 text-green-500 shrink-0" />
                              ) : (
                                <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                              )}
                              <span className="text-xs font-mono font-medium text-gray-700">{dv.name}</span>
                              <span className="text-xs text-gray-500">({dv.label})</span>
                            </div>
                            <p className="text-xs text-gray-400 mt-0.5 truncate pl-5">
                              使用于: {dv.usedInScripts.join(', ')}
                            </p>
                          </div>
                          {!isConfiguredNow && (
                            <button
                              onClick={() => handleAddDetected(dv)}
                              className="ml-2 px-2 py-1 text-xs bg-amber-100 text-amber-700 hover:bg-amber-200 rounded transition-colors shrink-0"
                            >
                              添加
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                  
                  {missingCount > 0 && (
                    <button
                      onClick={handleAddAllMissing}
                      className="mt-3 w-full py-1.5 text-xs bg-amber-100 text-amber-700 hover:bg-amber-200 rounded-lg transition-colors flex items-center justify-center gap-1"
                    >
                      <Plus className="w-3 h-3" />
                      一键添加 {missingCount} 个缺失变量
                    </button>
                  )}
                </>
              )}
            </div>
          )}

          {/* 已配置的变量列表 */}
          <div className="mb-3">
            <p className="text-xs font-medium text-gray-600 mb-2">已配置的变量 ({variables.length})</p>
          </div>
          <div className="space-y-3">
            {variables.length === 0 ? (
              <div className="text-center py-6 text-gray-400 border-2 border-dashed border-gray-200 rounded-lg">
                <Variable className="w-10 h-10 mx-auto mb-2 opacity-50" />
                <p className="text-sm">暂无项目变量</p>
                <p className="text-xs mt-1">点击上方"添加"或下方按钮添加变量</p>
              </div>
            ) : (
              variables.map((variable, index) => (
                <div
                  key={index}
                  className="flex items-start gap-2 p-3 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <div className="flex-1 space-y-2">
                    <input
                      type="text"
                      value={variable.key}
                      onChange={(e) => handleUpdateVariable(index, 'key', e.target.value)}
                      placeholder="变量名 (如 VOLUME_NAME)"
                      className="w-full px-3 py-1.5 text-sm font-mono border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                    />
                    <input
                      type="text"
                      value={variable.value}
                      onChange={(e) => handleUpdateVariable(index, 'value', e.target.value)}
                      placeholder="变量值"
                      className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                    />
                  </div>
                  <button
                    onClick={() => handleDeleteVariable(index)}
                    className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>

          {/* 添加按钮 */}
          <button
            onClick={handleAddVariable}
            className="mt-3 w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-violet-400 hover:text-violet-600 hover:bg-violet-50 transition-all flex items-center justify-center gap-2"
          >
            <Plus className="w-4 h-4" />
            <span className="text-sm">手动添加变量</span>
          </button>

          {/* 错误提示 */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-gray-200 bg-gray-50">
          <p className="text-xs text-gray-500">
            {hasChanges ? '有未保存的更改' : `${variables.length} 个变量`}
          </p>
          <div className="flex items-center gap-3">
            <Button variant="secondary" onClick={onClose} disabled={isSaving}>
              取消
            </Button>
            <Button
              onClick={handleSave}
              disabled={isSaving || !hasChanges}
              className="bg-violet-500 hover:bg-violet-600"
            >
              <Save className="w-4 h-4 mr-1" />
              {isSaving ? '保存中...' : '保存'}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}

