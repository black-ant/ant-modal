import { useState, useEffect } from 'react';
import { Plus, Cloud, Trash2, Edit2, X, Check, Wifi, WifiOff, Loader2, Server, Play, Square, FileText, HardDrive, Key, Box } from 'lucide-react';
import clsx from 'clsx';
import Card from '../components/Card';
import Button from '../components/Button';
import { main } from '../../wailsjs/go/models';
import {
  GetModalAppList, CreateModalApp, UpdateModalApp, DeleteModalApp, TestModalConnection,
  ModalAppListWithTokenPair, ModalAppStopWithTokenPair, ModalAppLogsWithTokenPair,
  ModalVolumeListWithTokenPair, ModalSecretListWithTokenPair, ModalContainerListWithTokenPair,
  ModalTokenNew
} from '../../wailsjs/go/main/App';

export default function ModalApps() {
  const [apps, setApps] = useState<main.ModalApp[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [showOpsPanel, setShowOpsPanel] = useState(false);
  const [selectedApp, setSelectedApp] = useState<main.ModalApp | null>(null);
  const [editingApp, setEditingApp] = useState<main.ModalApp | null>(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [opsLoading, setOpsLoading] = useState(false);
  const [opsOutput, setOpsOutput] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    appName: '',
    description: '',
    token: '',
    tokenId: '',
    tokenSecret: '',
    workspace: '',
    suffix: '',
  });

  useEffect(() => {
    loadApps();
  }, []);

  const loadApps = async () => {
    const data = await GetModalAppList();
    setApps(data || []);
  };

  const resetForm = () => {
    setFormData({ name: '', appName: '', description: '', token: '', tokenId: '', tokenSecret: '', workspace: '', suffix: '' });
    setEditingApp(null);
    setTestResult(null);
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await TestModalConnection(formData.token, formData.workspace);
      if (result.success) {
        setTestResult({ success: true, message: '连接成功！Modal CLI 正常工作' });
      } else {
        setTestResult({ success: false, message: result.error || '连接失败' });
      }
    } catch (e) {
      setTestResult({ success: false, message: '测试失败: ' + String(e) });
    }
    setTesting(false);
  };

  const openCreateModal = () => {
    resetForm();
    setShowModal(true);
  };

  const openEditModal = (app: main.ModalApp) => {
    setEditingApp(app);
    setFormData({
      name: app.name,
      appName: app.appName,
      description: app.description,
      token: app.token || '',
      tokenId: app.tokenId || '',
      tokenSecret: app.tokenSecret || '',
      workspace: app.workspace,
      suffix: app.suffix || '',
    });
    setShowModal(true);
  };

  const handleSubmit = async () => {
    if (!formData.name || !formData.appName) return;

    if (editingApp) {
      await UpdateModalApp(
        editingApp.id,
        formData.name,
        formData.appName,
        formData.description,
        formData.token,
        formData.tokenId,
        formData.tokenSecret,
        formData.workspace,
        formData.suffix
      );
    } else {
      await CreateModalApp(
        formData.name,
        formData.appName,
        formData.description,
        formData.token,
        formData.tokenId,
        formData.tokenSecret,
        formData.workspace,
        formData.suffix
      );
    }

    setShowModal(false);
    resetForm();
    loadApps();
  };

  const handleDelete = async (id: string) => {
    if (confirm('确定要删除这个应用配置吗？')) {
      await DeleteModalApp(id);
      loadApps();
    }
  };

  const openOpsPanel = (app: main.ModalApp) => {
    setSelectedApp(app);
    setOpsOutput('');
    setShowOpsPanel(true);
  };

  const runOpsCommand = async (commandFn: () => Promise<main.CommandResult>, label: string) => {
    setOpsLoading(true);
    setOpsOutput(`执行: ${label}...\n`);
    try {
      const result = await commandFn();
      setOpsOutput((prev) => prev + (result.output || '') + (result.error ? `\n错误: ${result.error}` : '') + '\n');
    } catch (e) {
      setOpsOutput((prev) => prev + `执行失败: ${e}\n`);
    }
    setOpsLoading(false);
  };


  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h1 className="text-lg font-bold text-gray-800">Modal Apps</h1>
          <p className="text-gray-500 text-xs">管理 Modal 平台应用配置</p>
        </div>
        <Button onClick={openCreateModal}>
          <Plus className="w-4 h-4 mr-1" />
          新建应用
        </Button>
      </div>

      {/* Apps Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {apps.length === 0 ? (
          <Card className="col-span-full text-center py-8">
            <Cloud className="w-12 h-12 mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500 text-sm">还没有应用配置，点击上方按钮创建</p>
          </Card>
        ) : (
          apps.map((app) => (
            <Card key={app.id} className="p-3">
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <Cloud className="w-4 h-4 text-primary-500" />
                  <h3 className="text-sm font-semibold text-gray-800">{app.name}</h3>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => openEditModal(app)}
                    className="p-1 text-gray-400 hover:text-primary-500 hover:bg-primary-50 rounded transition-colors"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleDelete(app.id)}
                    className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
              <p className="text-xs text-gray-500 mb-1">{app.description || '暂无描述'}</p>
              <div className="text-xs text-gray-400 space-y-0.5 mb-2">
                <p>应用名: <span className="text-gray-600">{app.appName}</span></p>
                {app.workspace && <p>Workspace: <span className="text-gray-600">{app.workspace}</span></p>}
                {app.suffix && <p>后缀: <span className="text-primary-600 font-medium">{app.suffix}</span></p>}
              </div>
              <div className="pt-2 border-t border-gray-100 flex justify-end">
                <button
                  onClick={() => openOpsPanel(app)}
                  className="flex items-center gap-1 text-xs text-primary-500 hover:text-primary-600"
                >
                  <Server className="w-3.5 h-3.5" />
                  服务器操作
                </button>
              </div>
            </Card>
          ))
        )}
      </div>


      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowModal(false)}>
          <Card className="w-full max-w-sm animate-slide-in" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-base font-bold text-gray-800">{editingApp ? '编辑应用' : '新建应用'}</h2>
              <button onClick={() => setShowModal(false)} className="p-0.5 hover:bg-gray-100 rounded">
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">显示名称 *</label>
                <input
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="如: ComfyUI 生产环境"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Modal App 名称 *</label>
                <input
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
                  value={formData.appName}
                  onChange={(e) => setFormData({ ...formData, appName: e.target.value })}
                  placeholder="如: comfyui-prod"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Workspace</label>
                <input
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
                  value={formData.workspace}
                  onChange={(e) => setFormData({ ...formData, workspace: e.target.value })}
                  placeholder="Modal Workspace 名称"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">环境后缀</label>
                <input
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
                  value={formData.suffix}
                  onChange={(e) => setFormData({ ...formData, suffix: e.target.value })}
                  placeholder="如: -test, -prod, -dev"
                />
                <p className="mt-1 text-xs text-gray-400">部署时会自动添加到应用名和 Volume 名称后面</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Token ID</label>
                <input
                  type="text"
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
                  value={formData.tokenId}
                  onChange={(e) => setFormData({ ...formData, tokenId: e.target.value })}
                  placeholder="ak-xxxxxxxx"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Token Secret</label>
                <input
                  type="password"
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
                  value={formData.tokenSecret}
                  onChange={(e) => setFormData({ ...formData, tokenSecret: e.target.value })}
                  placeholder="as-xxxxxxxx"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">描述</label>
                <input
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="应用描述"
                />
              </div>

              {/* 测试连接 */}
              <div className="pt-2 border-t border-gray-100">
                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={testing}
                  className="flex items-center gap-1.5 text-xs text-primary-500 hover:text-primary-600 disabled:opacity-50"
                >
                  {testing ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Wifi className="w-3.5 h-3.5" />
                  )}
                  {testing ? '测试中...' : '测试连接'}
                </button>
                {testResult && (
                  <div className={clsx(
                    'mt-2 p-2 rounded-md text-xs',
                    testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                  )}>
                    <div className="flex items-center gap-1">
                      {testResult.success ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
                      {testResult.message}
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-4">
              <Button variant="secondary" size="sm" onClick={() => setShowModal(false)}>
                取消
              </Button>
              <Button size="sm" onClick={handleSubmit}>
                <Check className="w-3.5 h-3.5 mr-1" />
                {editingApp ? '保存' : '创建'}
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* 服务器操作面板 */}
      {showOpsPanel && selectedApp && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowOpsPanel(false)}>
          <Card className="w-full max-w-2xl animate-slide-in max-h-[80vh] flex flex-col" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4 shrink-0">
              <div className="flex items-center gap-2">
                <Server className="w-5 h-5 text-primary-500" />
                <h2 className="text-base font-bold text-gray-800">服务器操作 - {selectedApp.name}</h2>
              </div>
              <button onClick={() => setShowOpsPanel(false)} className="p-0.5 hover:bg-gray-100 rounded">
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>

            {/* Token 提示 */}
            {!selectedApp.tokenId && !selectedApp.tokenSecret && (
              <div className="mb-3 p-2 bg-yellow-50 text-yellow-700 text-xs rounded-md">
                ⚠️ 未配置 Token ID 和 Token Secret，将使用系统默认认证。如需使用独立 Token，请编辑应用配置。
              </div>
            )}

            {/* 快捷操作按钮 */}
            <div className="grid grid-cols-3 gap-2 mb-4 shrink-0">
              <button
                onClick={() => runOpsCommand(() => ModalAppListWithTokenPair(selectedApp.tokenId || '', selectedApp.tokenSecret || ''), 'modal app list')}
                disabled={opsLoading}
                className="flex items-center gap-2 p-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
              >
                <Play className="w-4 h-4 text-green-500" />
                <span>应用列表</span>
              </button>
              <button
                onClick={() => runOpsCommand(() => ModalAppStopWithTokenPair(selectedApp.appName, selectedApp.tokenId || '', selectedApp.tokenSecret || ''), `modal app stop ${selectedApp.appName}`)}
                disabled={opsLoading}
                className="flex items-center gap-2 p-2 text-sm bg-gray-50 hover:bg-red-50 rounded-md transition-colors disabled:opacity-50"
              >
                <Square className="w-4 h-4 text-red-500" />
                <span>停止应用</span>
              </button>
              <button
                onClick={() => runOpsCommand(() => ModalAppLogsWithTokenPair(selectedApp.appName, selectedApp.tokenId || '', selectedApp.tokenSecret || ''), `modal app logs ${selectedApp.appName}`)}
                disabled={opsLoading}
                className="flex items-center gap-2 p-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
              >
                <FileText className="w-4 h-4 text-blue-500" />
                <span>查看日志</span>
              </button>
              <button
                onClick={() => runOpsCommand(() => ModalVolumeListWithTokenPair(selectedApp.tokenId || '', selectedApp.tokenSecret || ''), 'modal volume list')}
                disabled={opsLoading}
                className="flex items-center gap-2 p-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
              >
                <HardDrive className="w-4 h-4 text-purple-500" />
                <span>Volume 列表</span>
              </button>
              <button
                onClick={() => runOpsCommand(() => ModalSecretListWithTokenPair(selectedApp.tokenId || '', selectedApp.tokenSecret || ''), 'modal secret list')}
                disabled={opsLoading}
                className="flex items-center gap-2 p-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
              >
                <Key className="w-4 h-4 text-yellow-500" />
                <span>Secret 列表</span>
              </button>
              <button
                onClick={() => runOpsCommand(() => ModalContainerListWithTokenPair(selectedApp.tokenId || '', selectedApp.tokenSecret || ''), 'modal container list')}
                disabled={opsLoading}
                className="flex items-center gap-2 p-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
              >
                <Box className="w-4 h-4 text-cyan-500" />
                <span>容器列表</span>
              </button>
            </div>

            {/* 输出区域 */}
            <div className="flex-1 min-h-0">
              <div className="bg-gray-900 rounded-md p-3 h-64 overflow-y-auto font-mono text-xs">
                {opsOutput ? (
                  <pre className="text-green-400 whitespace-pre-wrap">{opsOutput}</pre>
                ) : (
                  <span className="text-gray-500">点击上方按钮执行命令...</span>
                )}
                {opsLoading && <span className="text-green-400 animate-pulse">▋</span>}
              </div>
            </div>

            <div className="flex justify-end mt-4 shrink-0">
              <Button variant="secondary" size="sm" onClick={() => setShowOpsPanel(false)}>
                关闭
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
