import { useState, useEffect } from 'react';
import { Globe, Plus, Trash2, Save, AlertCircle, Info, Key } from 'lucide-react';
import clsx from 'clsx';
import Card from '../components/Card';
import Button from '../components/Button';
import { GetGlobalVariables, SetGlobalVariables } from '../../wailsjs/go/main/App';

interface VariableItem {
  key: string;
  value: string;
  isSecret?: boolean;
}

export default function GlobalVariables() {
  const [variables, setVariables] = useState<VariableItem[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [hasChanges, setHasChanges] = useState(false);

  // 加载全局变量
  useEffect(() => {
    loadVariables();
  }, []);

  const loadVariables = async () => {
    try {
      const vars = await GetGlobalVariables();
      const items: VariableItem[] = Object.entries(vars || {}).map(([key, value]) => ({
        key,
        value: value as string,
        isSecret: key.toLowerCase().includes('token') || key.toLowerCase().includes('secret') || key.toLowerCase().includes('key'),
      }));
      setVariables(items);
      setHasChanges(false);
    } catch (err) {
      console.error('加载变量失败:', err);
    }
  };

  // 添加新变量
  const handleAddVariable = () => {
    setVariables([...variables, { key: '', value: '' }]);
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
    newVars[index] = {
      ...newVars[index],
      [field]: newValue,
      isSecret: field === 'key'
        ? newValue.toLowerCase().includes('token') || newValue.toLowerCase().includes('secret') || newValue.toLowerCase().includes('key')
        : newVars[index].isSecret,
    };
    setVariables(newVars);
    setHasChanges(true);
    setError('');
    setSuccess('');
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
    setSuccess('');

    try {
      const varsMap: Record<string, string> = {};
      variables.forEach(v => {
        varsMap[v.key.trim()] = v.value;
      });

      await SetGlobalVariables(varsMap);
      setHasChanges(false);
      setSuccess('全局变量已保存');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.message || '保存失败');
    } finally {
      setIsSaving(false);
    }
  };

  // 常用变量建议
  const suggestedVariables = [
    { key: 'HF_TOKEN', value: '', desc: 'HuggingFace API Token' },
    { key: 'CIVITAI_TOKEN', value: '', desc: 'CivitAI API Token' },
  ];

  const handleAddSuggested = (key: string, value: string) => {
    if (variables.some(v => v.key === key)) {
      setError(`变量 ${key} 已存在`);
      return;
    }
    setVariables([...variables, { key, value, isSecret: true }]);
    setHasChanges(true);
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl shadow-lg">
            <Globe className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">全局变量</h1>
            <p className="text-sm text-gray-500">跨项目共享的变量配置</p>
          </div>
        </div>
        <Button
          onClick={handleSave}
          disabled={isSaving || !hasChanges}
        >
          <Save className="w-4 h-4 mr-1" />
          {isSaving ? '保存中...' : '保存更改'}
        </Button>
      </div>

      {/* 说明卡片 */}
      <Card className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" />
          <div className="text-sm text-blue-700">
            <p className="font-medium mb-1">关于全局变量</p>
            <ul className="list-disc list-inside space-y-1 text-xs text-blue-600">
              <li>全局变量在所有项目中共享，适合存储 API Token 等通用配置</li>
              <li>脚本执行时，全局变量会自动注入（优先级低于项目变量和脚本变量）</li>
              <li>敏感信息（如 Token）请妥善保管，不要分享给他人</li>
            </ul>
          </div>
        </div>
      </Card>

      {/* 变量列表 */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">变量列表</h2>
          <span className="text-sm text-gray-500">{variables.length} 个变量</span>
        </div>

        <div className="space-y-3">
          {variables.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Globe className="w-16 h-16 mx-auto mb-4 opacity-30" />
              <p className="text-base">暂无全局变量</p>
              <p className="text-sm mt-1">点击下方按钮添加变量</p>
            </div>
          ) : (
            variables.map((variable, index) => (
              <div
                key={index}
                className="flex items-start gap-3 p-4 bg-gray-50 rounded-xl border border-gray-200 hover:border-blue-300 transition-colors"
              >
                <div className="flex-1 grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">变量名</label>
                    <input
                      type="text"
                      value={variable.key}
                      onChange={(e) => handleUpdateVariable(index, 'key', e.target.value)}
                      placeholder="如 HF_TOKEN"
                      className="w-full px-3 py-2 text-sm font-mono border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1 flex items-center gap-1">
                      变量值
                      {variable.isSecret && <Key className="w-3 h-3 text-amber-500" />}
                    </label>
                    <input
                      type={variable.isSecret ? 'password' : 'text'}
                      value={variable.value}
                      onChange={(e) => handleUpdateVariable(index, 'value', e.target.value)}
                      placeholder="输入变量值"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </div>
                <button
                  onClick={() => handleDeleteVariable(index)}
                  className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors mt-5"
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
          className="mt-4 w-full py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-500 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50 transition-all flex items-center justify-center gap-2"
        >
          <Plus className="w-5 h-5" />
          <span>添加变量</span>
        </button>

        {/* 快速添加建议 */}
        <div className="mt-6 pt-4 border-t border-gray-200">
          <p className="text-sm text-gray-500 mb-3">快速添加常用变量：</p>
          <div className="flex flex-wrap gap-2">
            {suggestedVariables.map((sv) => (
              <button
                key={sv.key}
                onClick={() => handleAddSuggested(sv.key, sv.value)}
                disabled={variables.some(v => v.key === sv.key)}
                className={clsx(
                  'px-3 py-1.5 text-sm rounded-lg border transition-colors flex items-center gap-1.5',
                  variables.some(v => v.key === sv.key)
                    ? 'border-gray-200 text-gray-400 cursor-not-allowed bg-gray-50'
                    : 'border-blue-200 text-blue-600 hover:bg-blue-50'
                )}
                title={sv.desc}
              >
                <Key className="w-3 h-3" />
                {sv.key}
              </button>
            ))}
          </div>
        </div>

        {/* 消息提示 */}
        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {success && (
          <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2">
            <Save className="w-4 h-4 text-green-500 shrink-0" />
            <p className="text-sm text-green-600">{success}</p>
          </div>
        )}

        {hasChanges && (
          <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm text-amber-700">有未保存的更改，请点击右上角保存按钮</p>
          </div>
        )}
      </Card>
    </div>
  );
}

