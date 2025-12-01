import { useState, useEffect, useRef } from 'react';
import { 
  Palette, 
  ExternalLink, 
  RefreshCw, 
  Package, 
  Download, 
  Trash2, 
  Play, 
  Square, 
  FileText,
  GitBranch,
  Link as LinkIcon,
  CheckCircle,
  XCircle,
  Loader2,
  ChevronDown,
  HardDrive,
  StopCircle,
  RotateCcw,
  AlertCircle
} from 'lucide-react';
import Card from '../components/Card';
import Button from '../components/Button';
import clsx from 'clsx';
import { 
  GetModalAppList,
  ExecuteModalCommandWithToken,
  ModalAppListWithTokenPair,
  ModalAppStopWithTokenPair,
  ModalAppLogsWithTokenPair,
  ModalVolumeListWithTokenPair,
  CancelRunningCommand
} from '../../wailsjs/go/main/App';
import { EventsOn, EventsOff } from '../../wailsjs/runtime/runtime';
import { BrowserOpenURL } from '../../wailsjs/runtime/runtime';
import { main } from '../../wailsjs/go/models';

// 模型类型选项
const MODEL_TYPES = [
  { value: 'checkpoints', label: 'Checkpoints (主模型)' },
  { value: 'loras', label: 'LoRA' },
  { value: 'vae', label: 'VAE' },
  { value: 'clip', label: 'CLIP' },
  { value: 'controlnet', label: 'ControlNet' },
  { value: 'upscale_models', label: 'Upscale Models' },
  { value: 'embeddings', label: 'Embeddings' },
];

// ComfyUI 应用状态
interface ComfyUIStatus {
  isOnline: boolean;
  appName: string;
  webUrl: string;
  lastChecked: Date | null;
}

export default function ComfyUIToolbox() {
  // Modal App 配置
  const [modalApps, setModalApps] = useState<main.ModalApp[]>([]);
  const [selectedApp, setSelectedApp] = useState<main.ModalApp | null>(null);
  
  // 状态
  const [status, setStatus] = useState<ComfyUIStatus>({
    isOnline: false,
    appName: 'comfyui-app',
    webUrl: '',
    lastChecked: null,
  });
  const [isCheckingStatus, setIsCheckingStatus] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  
  // 节点管理
  const [nodeGitUrl, setNodeGitUrl] = useState('');
  const [nodeBranch, setNodeBranch] = useState('main');
  
  // 模型管理
  const [modelSource, setModelSource] = useState<'huggingface' | 'url'>('huggingface');
  const [hfRepoId, setHfRepoId] = useState('');
  const [hfFilename, setHfFilename] = useState('');
  const [modelUrl, setModelUrl] = useState('');
  const [modelFilename, setModelFilename] = useState('');
  const [modelType, setModelType] = useState('checkpoints');
  
  // 控制台输出
  const [output, setOutput] = useState<string[]>([]);
  const outputRef = useRef<HTMLDivElement>(null);
  
  // 重启提示
  const [showRestartPrompt, setShowRestartPrompt] = useState(false);
  const [pendingChanges, setPendingChanges] = useState<string[]>([]);

  // 加载 Modal Apps
  useEffect(() => {
    loadModalApps();
    
    // 监听命令输出事件
    EventsOn('command:start', (cmd: string) => {
      setIsRunning(true);
      setOutput((prev) => [...prev, `> ${cmd}`]);
    });

    EventsOn('command:output', (line: string) => {
      setOutput((prev) => [...prev, line]);
    });

    EventsOn('command:complete', (result: main.CommandResult) => {
      setIsRunning(false);
      if (result.output) {
        setOutput((prev) => [...prev, result.output]);
      }
      setOutput((prev) => [...prev, result.success ? '✓ 完成' : `✗ 错误: ${result.error}`, '']);
    });

    return () => {
      EventsOff('command:start');
      EventsOff('command:output');
      EventsOff('command:complete');
    };
  }, []);

  // 自动滚动到底部
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output]);

  const loadModalApps = async () => {
    try {
      const apps = await GetModalAppList();
      setModalApps(apps || []);
      if (apps && apps.length > 0) {
        setSelectedApp(apps[0]);
      }
    } catch (err) {
      console.error('加载 Modal Apps 失败:', err);
    }
  };

  // 检查 ComfyUI 状态
  const checkStatus = async () => {
    if (!selectedApp) return;
    
    setIsCheckingStatus(true);
    try {
      const result = await ModalAppListWithTokenPair(selectedApp.tokenId, selectedApp.tokenSecret);
      
      if (result.success && result.output) {
        // 解析应用列表，查找 comfyui 相关应用
        const lines = result.output.split('\n');
        const comfyApp = lines.find(line => 
          line.toLowerCase().includes('comfyui') || 
          line.toLowerCase().includes('comfy-')
        );
        
        if (comfyApp) {
          // 尝试从输出中提取 URL
          const urlMatch = comfyApp.match(/https?:\/\/[^\s]+/);
          setStatus({
            isOnline: true,
            appName: comfyApp.split(/\s+/)[0] || 'comfyui-app',
            webUrl: urlMatch ? urlMatch[0] : '',
            lastChecked: new Date(),
          });
        } else {
          setStatus(prev => ({
            ...prev,
            isOnline: false,
            lastChecked: new Date(),
          }));
        }
      }
    } catch (err) {
      console.error('检查状态失败:', err);
    } finally {
      setIsCheckingStatus(false);
    }
  };

  // 打开 ComfyUI UI
  const openUI = () => {
    if (status.webUrl) {
      BrowserOpenURL(status.webUrl);
    } else {
      setOutput(prev => [...prev, '⚠️ 未找到 ComfyUI Web URL，请先检查服务状态']);
    }
  };

  // 查看日志
  const viewLogs = async () => {
    if (!selectedApp || !status.appName) return;
    
    setOutput(prev => [...prev, `📋 获取日志: ${status.appName}`]);
    try {
      const result = await ModalAppLogsWithTokenPair(status.appName, selectedApp.tokenId, selectedApp.tokenSecret);
      if (result.output) {
        setOutput(prev => [...prev, result.output]);
      }
    } catch (err: any) {
      setOutput(prev => [...prev, `✗ 获取日志失败: ${err.message || err}`]);
    }
  };

  // 停止服务
  const stopService = async () => {
    if (!selectedApp || !status.appName) return;
    
    setOutput(prev => [...prev, `⏹️ 停止服务: ${status.appName}`]);
    try {
      const result = await ModalAppStopWithTokenPair(status.appName, selectedApp.tokenId, selectedApp.tokenSecret);
      if (result.success) {
        setOutput(prev => [...prev, '✓ 服务已停止']);
        setStatus(prev => ({ ...prev, isOnline: false }));
      } else {
        setOutput(prev => [...prev, `✗ 停止失败: ${result.error}`]);
      }
    } catch (err: any) {
      setOutput(prev => [...prev, `✗ 停止失败: ${err.message || err}`]);
    }
  };

  // 添加节点
  const addNode = async () => {
    if (!nodeGitUrl.trim()) {
      setOutput(prev => [...prev, '⚠️ 请输入 Git 仓库 URL']);
      return;
    }
    
    if (!selectedApp) {
      setOutput(prev => [...prev, '⚠️ 请先选择 Modal App']);
      return;
    }

    const nodeName = nodeGitUrl.split('/').pop()?.replace('.git', '') || 'node';
    setOutput(prev => [...prev, `📦 添加节点: ${nodeName}`]);
    
    try {
      // 执行添加节点命令
      const cmd = `run add_custom_nodes.py --action=install --repo-url=${nodeGitUrl} --branch=${nodeBranch}`;
      const result = await ExecuteModalCommandWithToken(cmd, selectedApp.tokenId, selectedApp.tokenSecret);
      setOutput(prev => [...prev, result || '命令已发送']);
      
      // 显示重启提示
      setPendingChanges(prev => [...prev, `节点: ${nodeName}`]);
      setShowRestartPrompt(true);
    } catch (err: any) {
      setOutput(prev => [...prev, `✗ 添加失败: ${err.message || err}`]);
    }
    
    // 清空输入
    setNodeGitUrl('');
  };

  // 添加模型
  const addModel = async () => {
    if (!selectedApp) {
      setOutput(prev => [...prev, '⚠️ 请先选择 Modal App']);
      return;
    }

    let modelName = '';
    
    if (modelSource === 'huggingface') {
      if (!hfRepoId.trim() || !hfFilename.trim()) {
        setOutput(prev => [...prev, '⚠️ 请输入 HuggingFace 仓库 ID 和文件名']);
        return;
      }
      
      modelName = hfFilename;
      setOutput(prev => [...prev, `📥 从 HuggingFace 下载: ${hfRepoId}/${hfFilename}`]);
      
      try {
        const cmd = `run add_models.py --action=add-hf --repo-id=${hfRepoId} --filename=${hfFilename} --type=${modelType}`;
        const result = await ExecuteModalCommandWithToken(cmd, selectedApp.tokenId, selectedApp.tokenSecret);
        setOutput(prev => [...prev, result || '命令已发送']);
        
        // 显示重启提示
        setPendingChanges(prev => [...prev, `模型: ${modelName}`]);
        setShowRestartPrompt(true);
      } catch (err: any) {
        setOutput(prev => [...prev, `✗ 下载失败: ${err.message || err}`]);
      }
      
      setHfRepoId('');
      setHfFilename('');
    } else {
      if (!modelUrl.trim() || !modelFilename.trim()) {
        setOutput(prev => [...prev, '⚠️ 请输入模型 URL 和文件名']);
        return;
      }
      
      modelName = modelFilename;
      setOutput(prev => [...prev, `📥 从 URL 下载: ${modelFilename}`]);
      
      try {
        const cmd = `run add_models.py --action=add-url --url=${modelUrl} --filename=${modelFilename} --type=${modelType}`;
        const result = await ExecuteModalCommandWithToken(cmd, selectedApp.tokenId, selectedApp.tokenSecret);
        setOutput(prev => [...prev, result || '命令已发送']);
        
        // 显示重启提示
        setPendingChanges(prev => [...prev, `模型: ${modelName}`]);
        setShowRestartPrompt(true);
      } catch (err: any) {
        setOutput(prev => [...prev, `✗ 下载失败: ${err.message || err}`]);
      }
      
      setModelUrl('');
      setModelFilename('');
    }
  };

  // 查看 Volume
  const viewVolume = async () => {
    if (!selectedApp) return;
    
    setOutput(prev => [...prev, '💾 查看 Volume 列表...']);
    try {
      const result = await ModalVolumeListWithTokenPair(selectedApp.tokenId, selectedApp.tokenSecret);
      if (result.output) {
        setOutput(prev => [...prev, result.output]);
      }
    } catch (err: any) {
      setOutput(prev => [...prev, `✗ 获取 Volume 失败: ${err.message || err}`]);
    }
  };

  // 清空控制台
  const clearOutput = () => setOutput([]);

  return (
    <div className="space-y-4">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl shadow-lg">
            <Palette className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-800">ComfyUI 工具箱</h1>
            <p className="text-sm text-gray-500">快速管理已部署的 ComfyUI 应用</p>
          </div>
        </div>
        
        {/* Modal App 选择器 */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">使用:</span>
          <select
            value={selectedApp?.id || ''}
            onChange={(e) => {
              const app = modalApps.find(a => a.id === e.target.value);
              setSelectedApp(app || null);
            }}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            {modalApps.map(app => (
              <option key={app.id} value={app.id}>{app.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* 快捷操作卡片 */}
      <div className="grid grid-cols-4 gap-3">
        {/* 服务状态 */}
        <Card className="p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-600">服务状态</span>
            <button
              onClick={checkStatus}
              disabled={isCheckingStatus}
              className="p-1 hover:bg-gray-100 rounded transition-colors"
            >
              <RefreshCw className={clsx("w-4 h-4 text-gray-400", isCheckingStatus && "animate-spin")} />
            </button>
          </div>
          <div className="flex items-center gap-2">
            {status.isOnline ? (
              <CheckCircle className="w-5 h-5 text-green-500" />
            ) : (
              <XCircle className="w-5 h-5 text-gray-300" />
            )}
            <span className={clsx("text-sm font-semibold", status.isOnline ? "text-green-600" : "text-gray-400")}>
              {status.isOnline ? '在线' : '离线'}
            </span>
          </div>
          {status.appName && status.isOnline && (
            <p className="text-xs text-gray-500 mt-1 truncate">{status.appName}</p>
          )}
        </Card>

        {/* 打开 UI */}
        <Card 
          className="p-4 cursor-pointer hover:shadow-md transition-shadow"
          onClick={openUI}
        >
          <div className="flex items-center gap-2 mb-2">
            <ExternalLink className="w-5 h-5 text-blue-500" />
            <span className="text-sm font-medium text-gray-600">打开 UI</span>
          </div>
          <p className="text-xs text-gray-400">访问 ComfyUI Web 界面</p>
        </Card>

        {/* 查看日志 */}
        <Card 
          className="p-4 cursor-pointer hover:shadow-md transition-shadow"
          onClick={viewLogs}
        >
          <div className="flex items-center gap-2 mb-2">
            <FileText className="w-5 h-5 text-amber-500" />
            <span className="text-sm font-medium text-gray-600">查看日志</span>
          </div>
          <p className="text-xs text-gray-400">获取应用运行日志</p>
        </Card>

        {/* 停止服务 */}
        <Card 
          className="p-4 cursor-pointer hover:shadow-md transition-shadow"
          onClick={stopService}
        >
          <div className="flex items-center gap-2 mb-2">
            <Square className="w-5 h-5 text-red-500" />
            <span className="text-sm font-medium text-gray-600">停止服务</span>
          </div>
          <p className="text-xs text-gray-400">停止 ComfyUI 应用</p>
        </Card>
      </div>

      {/* 节点和模型管理 */}
      <div className="grid grid-cols-2 gap-4">
        {/* 节点管理 */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-4">
            <Package className="w-5 h-5 text-purple-500" />
            <h3 className="text-sm font-semibold text-gray-700">快速添加节点</h3>
          </div>
          
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Git 仓库 URL</label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <GitBranch className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    value={nodeGitUrl}
                    onChange={(e) => setNodeGitUrl(e.target.value)}
                    placeholder="https://github.com/xxx/xxx.git"
                    className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>
              </div>
            </div>
            
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="block text-xs text-gray-500 mb-1">分支</label>
                <input
                  type="text"
                  value={nodeBranch}
                  onChange={(e) => setNodeBranch(e.target.value)}
                  placeholder="main"
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
              <div className="flex items-end">
                <Button 
                  onClick={addNode}
                  disabled={isRunning || !nodeGitUrl.trim()}
                  className="bg-purple-500 hover:bg-purple-600"
                >
                  <Download className="w-4 h-4 mr-1" />
                  安装
                </Button>
              </div>
            </div>
          </div>
        </Card>

        {/* 模型管理 */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-4">
            <HardDrive className="w-5 h-5 text-pink-500" />
            <h3 className="text-sm font-semibold text-gray-700">快速添加模型</h3>
          </div>
          
          <div className="space-y-3">
            {/* 来源选择 */}
            <div className="flex gap-4">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  checked={modelSource === 'huggingface'}
                  onChange={() => setModelSource('huggingface')}
                  className="text-pink-500 focus:ring-pink-500"
                />
                <span className="text-sm text-gray-600">HuggingFace</span>
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  checked={modelSource === 'url'}
                  onChange={() => setModelSource('url')}
                  className="text-pink-500 focus:ring-pink-500"
                />
                <span className="text-sm text-gray-600">URL 直链</span>
              </label>
            </div>

            {modelSource === 'huggingface' ? (
              <>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">仓库 ID</label>
                  <input
                    type="text"
                    value={hfRepoId}
                    onChange={(e) => setHfRepoId(e.target.value)}
                    placeholder="Comfy-Org/flux1-dev"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-pink-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">文件名</label>
                  <input
                    type="text"
                    value={hfFilename}
                    onChange={(e) => setHfFilename(e.target.value)}
                    placeholder="flux1-dev-fp8.safetensors"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-pink-500"
                  />
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">下载 URL</label>
                  <input
                    type="text"
                    value={modelUrl}
                    onChange={(e) => setModelUrl(e.target.value)}
                    placeholder="https://civitai.com/api/download/..."
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-pink-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">保存文件名</label>
                  <input
                    type="text"
                    value={modelFilename}
                    onChange={(e) => setModelFilename(e.target.value)}
                    placeholder="model.safetensors"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-pink-500"
                  />
                </div>
              </>
            )}

            <div className="flex gap-2">
              <div className="flex-1">
                <label className="block text-xs text-gray-500 mb-1">模型类型</label>
                <select
                  value={modelType}
                  onChange={(e) => setModelType(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-pink-500"
                >
                  {MODEL_TYPES.map(type => (
                    <option key={type.value} value={type.value}>{type.label}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <Button 
                  onClick={addModel}
                  disabled={isRunning}
                  className="bg-pink-500 hover:bg-pink-600"
                >
                  <Download className="w-4 h-4 mr-1" />
                  下载
                </Button>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* 重启提示横幅 */}
      {showRestartPrompt && pendingChanges.length > 0 && (
        <Card className="p-4 bg-gradient-to-r from-amber-50 to-orange-50 border-amber-200">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-amber-800">需要重启服务</h4>
              <p className="text-xs text-amber-700 mt-1">
                以下更改需要重启 ComfyUI 服务后才能生效：
              </p>
              <ul className="text-xs text-amber-600 mt-2 space-y-1">
                {pendingChanges.map((change, i) => (
                  <li key={i}>• {change}</li>
                ))}
              </ul>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setShowRestartPrompt(false);
                  setPendingChanges([]);
                }}
                className="px-3 py-1.5 text-xs text-amber-600 hover:bg-amber-100 rounded transition-colors"
              >
                稍后
              </button>
              <button
                onClick={async () => {
                  // 停止服务
                  setOutput(prev => [...prev, '🔄 正在重启服务以加载更改...']);
                  await stopService();
                  setOutput(prev => [...prev, '✓ 服务已停止，请访问 ComfyUI URL 以重新启动服务']);
                  setShowRestartPrompt(false);
                  setPendingChanges([]);
                }}
                className="px-3 py-1.5 text-xs bg-amber-500 text-white hover:bg-amber-600 rounded transition-colors flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3" />
                重启服务
              </button>
            </div>
          </div>
        </Card>
      )}

      {/* 控制台输出 */}
      <Card className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-gray-500" />
            <h3 className="text-sm font-semibold text-gray-700">控制台输出</h3>
            {isRunning && (
              <Loader2 className="w-4 h-4 text-purple-500 animate-spin" />
            )}
          </div>
          <div className="flex gap-2">
            {isRunning && (
              <button
                onClick={async () => {
                  const cancelled = await CancelRunningCommand();
                  if (cancelled) {
                    setOutput((prev) => [...prev, '⚠️ 命令已中止']);
                  }
                }}
                className="px-2 py-1 text-xs text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors flex items-center gap-1"
                title="中止命令"
              >
                <StopCircle className="w-3 h-3" />
                中止
              </button>
            )}
            <button
              onClick={viewVolume}
              className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
            >
              <HardDrive className="w-3 h-3 inline mr-1" />
              Volume
            </button>
            <button
              onClick={clearOutput}
              className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
            >
              清空
            </button>
          </div>
        </div>
        
        <div 
          ref={outputRef}
          className="h-48 bg-gray-900 rounded-lg p-3 overflow-y-auto font-mono text-xs"
        >
          {output.length === 0 ? (
            <p className="text-gray-500">等待执行命令...</p>
          ) : (
            output.map((line, i) => (
              <div 
                key={i} 
                className={clsx(
                  "whitespace-pre-wrap",
                  line.startsWith('✓') ? 'text-green-400' :
                  line.startsWith('✗') ? 'text-red-400' :
                  line.startsWith('⚠️') ? 'text-yellow-400' :
                  line.startsWith('>') ? 'text-blue-400' :
                  'text-gray-300'
                )}
              >
                {line}
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}

