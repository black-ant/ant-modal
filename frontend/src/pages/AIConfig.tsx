import { useState, useEffect } from 'react';
import { Plus, Settings, Trash2, Check, X, Eye, EyeOff } from 'lucide-react';
import { AIConfig } from '../types';
import { CreateAIConfig, GetAIConfigs, UpdateAIConfig, DeleteAIConfig, SetDefaultAIConfig, TestAIConnection } from '../../wailsjs/go/main/App';

export default function AIConfigPage() {
  const [configs, setConfigs] = useState<AIConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showApiKey, setShowApiKey] = useState<Record<string, boolean>>({});
  
  // 表单数据
  const [formData, setFormData] = useState({
    name: '',
    provider: 'OpenAI',
    baseUrl: '',
    apiKey: '',
    model: '',
    temperature: 0.7,
    maxTokens: 2000,
  });

  // 加载配置列表
  const loadConfigs = async () => {
    try {
      const data = await GetAIConfigs();
      setConfigs(data || []);
    } catch (error) {
      console.error('加载AI配置失败:', error);
    }
  };

  useEffect(() => {
    loadConfigs();
  }, []);

  // 重置表单
  const resetForm = () => {
    setFormData({
      name: '',
      provider: 'OpenAI',
      baseUrl: '',
      apiKey: '',
      model: '',
      temperature: 0.7,
      maxTokens: 2000,
    });
    setEditingId(null);
  };

  // 打开编辑对话框
  const handleEdit = (config: AIConfig) => {
    setFormData({
      name: config.name,
      provider: config.provider,
      baseUrl: config.baseUrl,
      apiKey: config.apiKey,
      model: config.model,
      temperature: config.temperature,
      maxTokens: config.maxTokens,
    });
    setEditingId(config.id);
    setShowCreateDialog(true);
  };

  // 保存配置
  const handleSave = async () => {
    if (!formData.name || !formData.baseUrl || !formData.apiKey || !formData.model) {
      alert('请填写所有必填字段');
      return;
    }

    setLoading(true);
    try {
      if (editingId) {
        await UpdateAIConfig(
          editingId,
          formData.name,
          formData.provider,
          formData.baseUrl,
          formData.apiKey,
          formData.model,
          formData.temperature,
          formData.maxTokens
        );
      } else {
        await CreateAIConfig(
          formData.name,
          formData.provider,
          formData.baseUrl,
          formData.apiKey,
          formData.model,
          formData.temperature,
          formData.maxTokens
        );
      }
      
      await loadConfigs();
      setShowCreateDialog(false);
      resetForm();
    } catch (error) {
      console.error('保存配置失败:', error);
      alert('保存失败: ' + error);
    } finally {
      setLoading(false);
    }
  };

  // 删除配置
  const handleDelete = async (id: string) => {
    if (!confirm('确定要删除这个配置吗？')) return;

    try {
      await DeleteAIConfig(id);
      await loadConfigs();
    } catch (error) {
      console.error('删除配置失败:', error);
      alert('删除失败: ' + error);
    }
  };

  // 设置默认配置
  const handleSetDefault = async (id: string) => {
    try {
      await SetDefaultAIConfig(id);
      await loadConfigs();
    } catch (error) {
      console.error('设置默认配置失败:', error);
      alert('设置失败: ' + error);
    }
  };

  // 测试连接
  const handleTestConnection = async (config: AIConfig) => {
    setLoading(true);
    try {
      const result = await TestAIConnection(config.baseUrl, config.apiKey, config.model);
      alert('测试成功: ' + result);
    } catch (error) {
      console.error('测试连接失败:', error);
      alert('测试失败: ' + error);
    } finally {
      setLoading(false);
    }
  };

  // 切换API Key显示
  const toggleShowApiKey = (id: string) => {
    setShowApiKey(prev => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* 页面头部 */}
      <div className="bg-white shadow-sm px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">AI 配置</h1>
            <p className="text-sm text-gray-500 mt-1">管理 AI 模型的连接配置</p>
          </div>
          <button
            onClick={() => {
              resetForm();
              setShowCreateDialog(true);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            <Plus className="w-4 h-4" />
            新建配置
          </button>
        </div>
      </div>

      {/* 配置列表 */}
      <div className="flex-1 overflow-y-auto p-6">
        {configs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <Settings className="w-16 h-16 mb-4" />
            <p className="text-lg">还没有配置 AI</p>
            <p className="text-sm mt-1">点击「新建配置」开始</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {configs.map((config) => (
              <div
                key={config.id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-semibold text-gray-900">{config.name}</h3>
                      {config.isDefault && (
                        <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full">
                          默认
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 mt-1">{config.provider}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    {!config.isDefault && (
                      <button
                        onClick={() => handleSetDefault(config.id)}
                        className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                        title="设为默认"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => handleEdit(config)}
                      className="p-1.5 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded transition-colors"
                      title="编辑"
                    >
                      <Settings className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(config.id)}
                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                      title="删除"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500">Base URL:</span>
                    <span className="text-gray-700 font-mono text-xs">{config.baseUrl}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500">模型:</span>
                    <span className="text-gray-700">{config.model}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500">API Key:</span>
                    <div className="flex items-center gap-2">
                      <span className="text-gray-700 font-mono text-xs">
                        {showApiKey[config.id] ? config.apiKey : '••••••••••••••••'}
                      </span>
                      <button
                        onClick={() => toggleShowApiKey(config.id)}
                        className="p-1 text-gray-400 hover:text-gray-600 rounded"
                      >
                        {showApiKey[config.id] ? (
                          <EyeOff className="w-3 h-3" />
                        ) : (
                          <Eye className="w-3 h-3" />
                        )}
                      </button>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500">Temperature:</span>
                    <span className="text-gray-700">{config.temperature}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-500">Max Tokens:</span>
                    <span className="text-gray-700">{config.maxTokens}</span>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-gray-200">
                  <button
                    onClick={() => handleTestConnection(config)}
                    disabled={loading}
                    className="w-full px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors disabled:opacity-50"
                  >
                    测试连接
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 创建/编辑对话框 */}
      {showCreateDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto m-4">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-900">
                  {editingId ? '编辑配置' : '新建配置'}
                </h2>
                <button
                  onClick={() => {
                    setShowCreateDialog(false);
                    resetForm();
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  配置名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="例如：主用 AI"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Provider
                </label>
                <input
                  type="text"
                  value={formData.provider}
                  onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="例如：OpenAI, Anthropic"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Base URL <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.baseUrl}
                  onChange={(e) => setFormData({ ...formData, baseUrl: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="例如：https://api.openai.com/v1"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  API Key <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  value={formData.apiKey}
                  onChange={(e) => setFormData({ ...formData, apiKey: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="sk-..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  模型名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.model}
                  onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="例如：gpt-4, claude-3"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Temperature
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={formData.temperature}
                    onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max Tokens
                  </label>
                  <input
                    type="number"
                    value={formData.maxTokens}
                    onChange={(e) => setFormData({ ...formData, maxTokens: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
            </div>

            <div className="sticky bottom-0 bg-gray-50 px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowCreateDialog(false);
                  resetForm();
                }}
                className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSave}
                disabled={loading}
                className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50"
              >
                {loading ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

