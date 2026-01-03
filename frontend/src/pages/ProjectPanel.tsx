import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Upload, RefreshCw, Trash2, FileCode, File, Info, Settings, Server, HardDrive, Key, Box, BarChart3, Plus, ChevronUp, ChevronDown, Code, X, List, Variable, Copy, Check, StopCircle, Search, Cog, Play, History, FolderOpen, Database, User, Layers, AlertTriangle, Clock, Terminal, UploadCloud, ScrollText } from 'lucide-react';
import ExecutionLogs from './ExecutionLogs';
import clsx from 'clsx';
import Card from '../components/Card';
import Button from '../components/Button';
import ScriptEditor from '../components/ScriptEditor';
import CreateScriptDialog from '../components/CreateScriptDialog';
import DeleteConfirmDialog from '../components/DeleteConfirmDialog';
import ExecuteConfirmDialog from '../components/ExecuteConfirmDialog';
import ExecuteVariableDialog, { hasTemplateVariables } from '../components/ExecuteVariableDialog';
import DeployArgsDialog, { hasModalArgs } from '../components/DeployArgsDialog';
import ProjectVariablesDialog from '../components/ProjectVariablesDialog';
import CodeMirror, { ReactCodeMirrorRef } from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { vscodeDark } from '@uiw/codemirror-theme-vscode';
import { search, highlightSelectionMatches, searchKeymap, SearchQuery, setSearchQuery, findNext, findPrevious } from '@codemirror/search';
import { EditorView, Decoration, DecorationSet } from '@codemirror/view';
import { StateField, StateEffect, RangeSetBuilder } from '@codemirror/state';

// 创建高亮当前匹配行的效果
const highlightLineEffect = StateEffect.define<number>();
const clearHighlightEffect = StateEffect.define();

// 高亮装饰样式
const highlightLineMark = Decoration.line({
  class: 'cm-search-highlight-line'
});

// 高亮状态字段
const searchHighlightField = StateField.define<DecorationSet>({
  create() {
    return Decoration.none;
  },
  update(decorations, tr) {
    for (const effect of tr.effects) {
      if (effect.is(highlightLineEffect)) {
        const line = tr.state.doc.lineAt(effect.value);
        const builder = new RangeSetBuilder<Decoration>();
        builder.add(line.from, line.from, highlightLineMark);
        return builder.finish();
      }
      if (effect.is(clearHighlightEffect)) {
        return Decoration.none;
      }
    }
    return decorations;
  },
  provide: f => EditorView.decorations.from(f)
});

// 搜索高亮主题
const searchHighlightTheme = EditorView.baseTheme({
  // 当前匹配项的高亮（更明显的背景色）
  '.cm-searchMatch': {
    backgroundColor: '#ffeb3b !important',
    color: '#000 !important',
    borderRadius: '2px',
    padding: '0 2px',
  },
  // 当前选中的匹配项
  '.cm-searchMatch.cm-searchMatch-selected': {
    backgroundColor: '#ff9800 !important',
    color: '#000 !important',
    boxShadow: '0 0 0 2px #ff5722',
  },
  // 高亮的行背景
  '.cm-search-highlight-line': {
    backgroundColor: 'rgba(255, 152, 0, 0.15) !important',
    borderLeft: '3px solid #ff9800 !important',
  },
});
import { main } from '../../wailsjs/go/models';
import {
  GetProjects,
  GetScripts,
  DeployScriptAsync,
  DeployScriptWithContentAsync,
  RunScriptAsync,
  RunScriptWithContentAsync,
  RunScriptWithArgsAsync,
  DeployScriptWithLogAsync,
  RunScriptWithLogAsync,
  GetModalAppByID,
  GetModalAppList,
  DeployScriptToAppAsync,
  RunScriptToAppAsync,
  // App 相关
  ModalAppListWithTokenPair,
  ModalAppStopWithTokenPair,
  ModalAppLogsWithTokenPair,
  ModalAppDescribeWithTokenPair,
  ModalAppStatsWithTokenPair,
  ModalAppHistoryWithTokenPair,
  ModalAppDeleteWithTokenPair,
  // Volume 相关
  ModalVolumeListWithTokenPair,
  ModalVolumeGetWithTokenPair,
  ModalVolumeLsWithTokenPair,
  ModalVolumeDeleteWithTokenPair,
  ModalVolumeRmWithTokenPair,
  ModalVolumePutWithTokenPair,
  // Secret/Container 相关
  ModalSecretListWithTokenPair,
  ModalContainerListWithTokenPair,
  ModalContainerStopWithTokenPair,
  // 其他
  ModalProfileWithTokenPair,
  ModalEnvironmentListWithTokenPair,
  ModalNfsListWithTokenPair,
  // 执行日志
  GetExecutionLogs,
  CreateScript,
  DeleteScript,
  MoveScript,
  UpdateScript,
  ReadScriptContent,
  CancelRunningCommand
} from '../../wailsjs/go/main/App';
import { EventsOn, EventsOff } from '../../wailsjs/runtime/runtime';

export default function ProjectPanel() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<main.Project | null>(null);
  const [modalApp, setModalApp] = useState<main.ModalApp | null>(null);
  const [scripts, setScripts] = useState<main.Script[]>([]);
  const [selectedScript, setSelectedScript] = useState<main.Script | null>(null);
  const [output, setOutput] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [showEditor, setShowEditor] = useState(false);
  const [showOpsPanel, setShowOpsPanel] = useState(false);
  const [opsLoading, setOpsLoading] = useState(false);
  const [opsOutput, setOpsOutput] = useState('');
  const [showProjectLogs, setShowProjectLogs] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showVariablesDialog, setShowVariablesDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [scriptToDelete, setScriptToDelete] = useState<main.Script | null>(null);
  const [showCodePreview, setShowCodePreview] = useState(false);
  const [previewCode, setPreviewCode] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  // 代码搜索相关状态
  const [searchKeyword, setSearchKeyword] = useState('');
  const [searchMatchCount, setSearchMatchCount] = useState(0);
  const [currentMatchIndex, setCurrentMatchIndex] = useState(0);
  const codePreviewRef = useRef<ReactCodeMirrorRef>(null);
  // 控制台搜索相关状态
  const [consoleSearchKeyword, setConsoleSearchKeyword] = useState('');
  const [showConsoleSearch, setShowConsoleSearch] = useState(false);
  // 模板脚本执行相关状态
  const [showVariableDialog, setShowVariableDialog] = useState(false);
  const [currentScriptContent, setCurrentScriptContent] = useState('');
  const [nameCopied, setNameCopied] = useState(false);
  const outputRef = useRef<HTMLDivElement>(null);
  // 命令行参数对话框状态
  const [showArgsDialog, setShowArgsDialog] = useState(false);
  // 执行确认对话框状态
  const [showExecuteConfirm, setShowExecuteConfirm] = useState(false);
  const [pendingExecuteMode, setPendingExecuteMode] = useState<'deploy' | 'run'>('deploy');
  // 多环境部署相关状态
  const [modalApps, setModalApps] = useState<main.ModalApp[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string>('');

  useEffect(() => {
    loadProject();

    EventsOn('command:start', (cmd: string) => {
      setIsRunning(true);
      setOutput((prev) => [...prev, `> modal ${cmd}`]);
    });

    // 实时接收命令输出
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
  }, [id]);

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output]);

  const loadProject = async () => {
    const projects = await GetProjects();
    const found = projects?.find((p: main.Project) => p.id === id);
    if (found) {
      setProject(found);

      // 加载所有 Modal Apps（用于环境选择）
      const apps = await GetModalAppList();
      setModalApps(apps || []);

      // 加载关联的 Modal App
      if (found.appId) {
        const app = await GetModalAppByID(found.appId);
        setModalApp(app);
        // 设置默认选中的环境
        setSelectedAppId(found.appId);
      } else if (apps && apps.length > 0) {
        // 如果项目没有关联的 App，默认选择第一个
        setSelectedAppId(apps[0].id);
      }

      const scriptList = await GetScripts(found.path);
      setScripts(scriptList || []);
      if (scriptList && scriptList.length > 0) {
        setSelectedScript(scriptList[0]);
      }
    }
  };

  // 执行模式：deploy 或 run（自动判断）
  const [executeMode, setExecuteMode] = useState<'deploy' | 'run'>('deploy');

  // 判断脚本应该用 deploy 还是 run
  // - 包含 web_server、asgi_app、wsgi_app 等服务装饰器 → deploy（持久化服务）
  // - 只有 local_entrypoint → run（一次性任务）
  const detectExecuteMode = (content: string): 'deploy' | 'run' => {
    // 检测是否包含服务类装饰器（需要 deploy）
    const servicePatterns = [
      /@modal\.web_server/,
      /@modal\.asgi_app/,
      /@modal\.wsgi_app/,
      /\.web_server\(/,
      /\.asgi_app\(/,
      /\.wsgi_app\(/,
    ];

    for (const pattern of servicePatterns) {
      if (pattern.test(content)) {
        return 'deploy';
      }
    }

    // 检测是否只有 local_entrypoint（一次性任务，用 run）
    if (/@app\.local_entrypoint|\.local_entrypoint\(/.test(content)) {
      return 'run';
    }

    // 默认使用 deploy
    return 'deploy';
  };

  const handleExecute = async () => {
    if (isRunning || !project || !selectedScript) return;

    try {
      // 读取脚本内容，检测执行模式
      const content = await ReadScriptContent(selectedScript.fullPath);
      const mode = detectExecuteMode(content);
      setExecuteMode(mode);
      setCurrentScriptContent(content);
      setPendingExecuteMode(mode);

      console.log('[Execute] 准备执行脚本:', {
        scriptName: selectedScript.name,
        mode,
        targetAppId: selectedAppId
      });

      // 检查是否需要特殊对话框
      if (hasModalArgs(content)) {
        // 脚本包含 @modal-args 定义：弹出参数配置对话框
        console.log('[Execute] 检测到 @modal-args, 打开参数配置对话框');
        setShowArgsDialog(true);
      } else if (hasTemplateVariables(content)) {
        // 模板脚本：弹出变量表单
        console.log('[Execute] 检测到模板变量, 打开变量配置对话框');
        setShowVariableDialog(true);
      } else {
        // 普通脚本：显示执行确认对话框
        setShowExecuteConfirm(true);
      }
    } catch (err: any) {
      console.error('[Execute] 读取脚本失败:', err);
      const errorMessage = typeof err === 'string' ? err : (err.message || err.toString() || '未知错误');
      setOutput((prev) => [...prev, `✗ 读取脚本失败: ${errorMessage}`]);
    }
  };

  // 确认执行后调用
  const confirmExecute = async () => {
    if (!project || !selectedScript) return;

    const selectedEnv = modalApps.find(app => app.id === selectedAppId);
    const envLabel = selectedEnv ? ` → ${selectedEnv.name}${selectedEnv.suffix ? ` (${selectedEnv.suffix})` : ''}` : '';
    const mode = pendingExecuteMode;
    const actionLabel = mode === 'deploy' ? '部署' : '运行';

    console.log('[Execute] 用户确认执行:', {
      projectId: project.id,
      scriptName: selectedScript.name,
      mode,
      targetAppId: selectedAppId,
      targetEnv: selectedEnv?.name
    });

    if (selectedAppId && selectedEnv) {
      // 使用指定环境部署
      console.log(`[Execute] 使用指定环境${actionLabel}: 目标环境 = ${selectedEnv.name}, 后缀 = ${selectedEnv.suffix || '(无)'}`);
      setOutput((prev) => [...prev, `${actionLabel}脚本${envLabel}: ${selectedScript.name}`]);
      try {
        if (mode === 'deploy') {
          await DeployScriptToAppAsync(selectedScript.path, project.path, selectedAppId);
        } else {
          await RunScriptToAppAsync(selectedScript.path, project.path, selectedAppId);
        }
      } catch (err: any) {
        setOutput((prev) => [...prev, `✗ ${actionLabel}失败: ${err.message || err}`]);
      }
    } else {
      // 使用默认环境
      console.log(`[Execute] 使用默认环境${actionLabel}`);
      setOutput((prev) => [...prev, `${actionLabel}脚本${envLabel}: ${selectedScript.name}`]);
      if (mode === 'deploy') {
        DeployScriptAsync(selectedScript.path, project.path);
      } else {
        RunScriptAsync(selectedScript.path, project.path);
      }
    }
  };

  // 处理带命令行参数的脚本执行
  const handleExecuteWithArgs = async (argsString: string) => {
    if (!project || !selectedScript) return;

    console.log('[Deploy] 带参数脚本执行:', {
      scriptName: selectedScript.name,
      args: argsString
    });

    setShowArgsDialog(false);
    setOutput((prev) => [...prev, `执行脚本: ${selectedScript.name} ${argsString}`]);

    try {
      await RunScriptWithArgsAsync(selectedScript.path, project.path, argsString);
      console.log('[Deploy] 带参数脚本执行请求已发送');
    } catch (err: any) {
      console.error('[Deploy] 带参数脚本执行失败:', err);
      const errorMessage = typeof err === 'string' ? err : (err.message || err.toString() || '未知错误');
      setOutput((prev) => [...prev, `✗ 执行失败: ${errorMessage}`]);
    }
  };

  // 处理模板脚本执行（变量已替换）
  const handleExecuteWithVariables = async (finalContent: string, filledVariables?: Record<string, string>) => {
    if (!project || !selectedScript) return;

    const actionLabel = executeMode === 'deploy' ? '部署' : '运行';
    console.log(`[${executeMode}] 模板脚本变量已配置, 开始${actionLabel}:`, {
      scriptName: selectedScript.name,
      contentLength: finalContent.length,
      variables: filledVariables
    });

    setShowVariableDialog(false);
    setOutput((prev) => [...prev, `${actionLabel}模板脚本: ${selectedScript.name}`]);

    try {
      // 使用带日志的异步执行函数
      if (executeMode === 'deploy') {
        await DeployScriptWithLogAsync(
          selectedScript.path,
          project.path,
          finalContent,
          project.id,
          project.name,
          selectedScript.name,
          filledVariables || {}
        );
      } else {
        await RunScriptWithLogAsync(
          selectedScript.path,
          project.path,
          finalContent,
          project.id,
          project.name,
          selectedScript.name,
          filledVariables || {}
        );
      }
      console.log(`[${executeMode}] 模板脚本${actionLabel}请求已发送`);
    } catch (err: any) {
      console.error(`[${executeMode}] 模板脚本${actionLabel}失败:`, err);
      // 提取详细错误信息
      const errorMessage = typeof err === 'string' ? err : (err.message || err.toString() || '未知错误');
      setOutput((prev) => [...prev, `✗ 执行失败: ${errorMessage}`]);
    }
  };

  const clearOutput = () => setOutput([]);

  const handleSaveScript = async () => {
    // 脚本保存逻辑已移到 ScriptEditor 组件内部
    // 这里只需要重新加载项目数据
    await loadProject();
  };

  const handleCreateScript = async (name: string, fileName: string, description: string, template: string) => {
    if (!project) return;

    console.log('[ProjectPanel] 开始创建脚本:', {
      projectId: project.id,
      name,
      fileName,
      templateLength: template.length
    });

    try {
      await CreateScript(project.id, name, fileName, description, template);
      console.log('[ProjectPanel] 脚本创建成功:', fileName);
      setOutput((prev) => [...prev, `✓ 脚本创建成功: ${name}`]);
      await loadProject();
    } catch (err: any) {
      console.error('[ProjectPanel] 脚本创建失败:', err);
      // 提取详细错误信息
      const errorMessage = typeof err === 'string' ? err : (err.message || err.toString() || '未知错误');
      setOutput((prev) => [...prev, `✗ 创建失败: ${errorMessage}`]);
      throw err;
    }
  };

  const handleDeleteScript = async (deleteFile: boolean) => {
    if (!project || !scriptToDelete) return;

    console.log('[ProjectPanel] 开始删除脚本:', {
      projectId: project.id,
      scriptPath: scriptToDelete.path,
      deleteFile
    });

    try {
      await DeleteScript(project.id, scriptToDelete.path, deleteFile);
      console.log('[ProjectPanel] 脚本删除成功:', scriptToDelete.name);
      setOutput((prev) => [...prev, `✓ 脚本删除成功: ${scriptToDelete.name}`]);

      // 如果删除的是当前选中的脚本，清空选中状态
      if (selectedScript?.path === scriptToDelete.path) {
        setSelectedScript(null);
      }

      await loadProject();
    } catch (err: any) {
      console.error('[ProjectPanel] 脚本删除失败:', err);
      // 提取详细错误信息
      const errorMessage = typeof err === 'string' ? err : (err.message || err.toString() || '未知错误');
      setOutput((prev) => [...prev, `✗ 删除失败: ${errorMessage}`]);
      throw err;
    }
  };

  const handleMoveScript = async (scriptPath: string, direction: string) => {
    if (!project) return;

    try {
      await MoveScript(project.id, scriptPath, direction);
      await loadProject();
    } catch (err: any) {
      setOutput((prev) => [...prev, `✗ 移动失败: ${err.message || err}`]);
    }
  };

  const openDeleteDialog = (script: main.Script) => {
    setScriptToDelete(script);
    setShowDeleteDialog(true);
  };

  const handleShowCode = async () => {
    if (!selectedScript) return;

    setShowCodePreview(true);
    setPreviewLoading(true);
    setPreviewCode('');

    try {
      const code = await ReadScriptContent(selectedScript.fullPath);
      setPreviewCode(code);
    } catch (err: any) {
      setPreviewCode(`// 读取失败: ${err.message || err}`);
    } finally {
      setPreviewLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-green-100 text-green-700';
      case 'deploying':
        return 'bg-yellow-100 text-yellow-700';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  const getStatusText = (status: string) => {
    const map: Record<string, string> = { running: '运行中', stopped: '已停止', deploying: '部署中' };
    return map[status] || status;
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

  const openOpsPanel = () => {
    if (!project?.appId) {
      alert('该项目未关联 Modal 应用，无法执行服务器操作');
      return;
    }
    setOpsOutput('');
    setShowOpsPanel(true);
  };

  if (!project) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-500 text-sm">加载中...</p>
      </div>
    );
  }


  return (
    <div className="animate-fade-in h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4 shrink-0">
        <button
          onClick={() => navigate('/')}
          className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-base font-bold text-gray-800">{project.name}</h1>
        </div>
        <button
          onClick={() => setShowVariablesDialog(true)}
          className="p-1.5 text-gray-500 hover:text-violet-500 hover:bg-violet-50 rounded-md transition-colors"
          title="项目变量"
        >
          <Cog className="w-4 h-4" />
        </button>
        <button
          onClick={openOpsPanel}
          className="p-1.5 text-gray-500 hover:text-primary-500 hover:bg-primary-50 rounded-md transition-colors"
          title="服务器操作"
        >
          <Settings className="w-4 h-4" />
        </button>
        <span className={clsx('px-2 py-0.5 rounded-full text-xs font-medium shrink-0', getStatusColor(project.status))}>
          {getStatusText(project.status)}
        </span>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Left: Script List */}
        <Card className="w-56 shrink-0 p-3 flex flex-col">
          <div className="flex justify-between items-center mb-2 shrink-0">
            <h2 className="text-sm font-semibold text-gray-800 flex items-center gap-1.5">
              <FileCode className="w-4 h-4 text-primary-500" />
              脚本列表
            </h2>
            <button
              onClick={loadProject}
              className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* 新建脚本按钮 */}
          <button
            onClick={() => setShowCreateDialog(true)}
            className="w-full mb-2 p-2 flex items-center justify-center gap-2 text-sm text-primary-600 bg-primary-50 hover:bg-primary-100 rounded-md transition-colors border border-primary-200"
          >
            <Plus className="w-4 h-4" />
            <span>新建脚本</span>
          </button>

          <div className="flex-1 overflow-y-auto space-y-1">
            {scripts.length === 0 ? (
              <p className="text-gray-400 text-center py-4 text-xs">没有找到脚本</p>
            ) : (
              scripts.map((script, index) => (
                <div
                  key={index}
                  className={clsx(
                    'group flex items-center gap-1.5 p-2 rounded-md transition-colors text-sm relative',
                    selectedScript?.path === script.path
                      ? 'bg-primary-500 text-white'
                      : 'hover:bg-gray-100 text-gray-700'
                  )}
                >
                  <div
                    onClick={() => setSelectedScript(script)}
                    className="flex items-center gap-2 flex-1 min-w-0 cursor-pointer"
                  >
                    <File className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">{script.name}</span>
                  </div>

                  {/* 操作按钮 */}
                  <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    {/* 向上移动 */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMoveScript(script.path, 'up');
                      }}
                      disabled={index === 0}
                      className={clsx(
                        'p-0.5 rounded transition-colors',
                        selectedScript?.path === script.path
                          ? 'hover:bg-primary-600 text-white'
                          : 'hover:bg-gray-200 text-gray-600',
                        index === 0 && 'opacity-30 cursor-not-allowed'
                      )}
                      title="向上移动"
                    >
                      <ChevronUp className="w-3.5 h-3.5" />
                    </button>

                    {/* 向下移动 */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMoveScript(script.path, 'down');
                      }}
                      disabled={index === scripts.length - 1}
                      className={clsx(
                        'p-0.5 rounded transition-colors',
                        selectedScript?.path === script.path
                          ? 'hover:bg-primary-600 text-white'
                          : 'hover:bg-gray-200 text-gray-600',
                        index === scripts.length - 1 && 'opacity-30 cursor-not-allowed'
                      )}
                      title="向下移动"
                    >
                      <ChevronDown className="w-3.5 h-3.5" />
                    </button>

                    {/* 删除 */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        openDeleteDialog(script);
                      }}
                      className={clsx(
                        'p-0.5 rounded transition-colors',
                        selectedScript?.path === script.path
                          ? 'hover:bg-red-600 text-white'
                          : 'hover:bg-red-100 text-red-600'
                      )}
                      title="删除脚本"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>

        {/* Right: Script Detail + Console */}
        <div className="flex-1 flex flex-col gap-4 min-w-0">
          {/* Script Detail */}
          <Card className="p-3 shrink-0">
            {selectedScript ? (
              <>
                <div className="flex justify-between items-start mb-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold text-gray-800">{selectedScript.name}</h3>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(selectedScript.name);
                          setNameCopied(true);
                          setTimeout(() => setNameCopied(false), 2000);
                        }}
                        className="p-1 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded transition-colors"
                        title="复制脚本名称"
                      >
                        {nameCopied ? (
                          <Check className="w-3.5 h-3.5 text-green-500" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                    <p className="text-xs text-gray-500 truncate mt-0.5">{selectedScript.fullPath}</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  {/* 目标环境选择器 */}
                  {modalApps.length > 0 && (
                    <div className="flex items-center gap-2 mr-2">
                      <span className="text-xs text-gray-500 whitespace-nowrap">🎯 目标:</span>
                      <select
                        value={selectedAppId}
                        onChange={(e) => setSelectedAppId(e.target.value)}
                        className="text-xs px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 bg-white min-w-[120px]"
                      >
                        <option value="">默认环境</option>
                        {modalApps.map((app) => (
                          <option key={app.id} value={app.id}>
                            {app.name}{app.suffix ? ` (${app.suffix})` : ''}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                  <Button size="sm" variant="success" onClick={handleExecute} disabled={isRunning}>
                    <Play className="w-3 h-3 mr-1" />
                    执行
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={handleShowCode}
                  >
                    <Code className="w-3 h-3 mr-1" />
                    展示代码
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      if (selectedScript && project) {
                        const encodedScriptPath = encodeURIComponent(selectedScript.path);
                        navigate(`/script-editor/${project.id}/${encodedScriptPath}`);
                      }
                    }}
                  >
                    <Info className="w-3 h-3 mr-1" />
                    编辑脚本
                  </Button>
                </div>
              </>
            ) : (
              <p className="text-gray-400 text-sm text-center py-4">请从左侧选择一个脚本</p>
            )}
          </Card>

          {/* Console Output */}
          <Card className="flex-1 p-3 flex flex-col min-h-0">
            <div className="flex justify-between items-center mb-2 shrink-0">
              <h2 className="text-sm font-semibold text-gray-800">💻 控制台</h2>
              <div className="flex items-center gap-1">
                {/* 搜索按钮 */}
                <button
                  onClick={() => setShowConsoleSearch(!showConsoleSearch)}
                  className={clsx(
                    "p-1 rounded transition-colors",
                    showConsoleSearch
                      ? "text-primary-500 bg-primary-50"
                      : "text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                  )}
                  title="搜索控制台"
                >
                  <Search className="w-3.5 h-3.5" />
                </button>
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
                    <StopCircle className="w-3.5 h-3.5" />
                    中止
                  </button>
                )}
                <button
                  onClick={clearOutput}
                  className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                  title="清空输出"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* 控制台搜索栏 */}
            {showConsoleSearch && (
              <div className="flex items-center gap-2 mb-2 shrink-0">
                <div className="relative flex-1">
                  <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                  <input
                    type="text"
                    placeholder="搜索控制台内容..."
                    value={consoleSearchKeyword}
                    onChange={(e) => setConsoleSearchKeyword(e.target.value)}
                    className="w-full pl-7 pr-3 py-1.5 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-primary-500"
                    autoFocus
                  />
                </div>
                {consoleSearchKeyword && (
                  <span className="text-xs text-gray-500">
                    {output.filter(line => line.toLowerCase().includes(consoleSearchKeyword.toLowerCase())).length} 条匹配
                  </span>
                )}
                <button
                  onClick={() => { setConsoleSearchKeyword(''); setShowConsoleSearch(false); }}
                  className="p-1 text-gray-400 hover:text-gray-600 rounded"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            <div
              ref={outputRef}
              className="flex-1 bg-gray-900 rounded-md p-3 overflow-y-auto font-mono text-xs min-h-0"
            >
              {output.length === 0 ? (
                <span className="text-gray-500">等待命令执行...</span>
              ) : (
                output.map((line, i) => {
                  // 如果有搜索关键字，高亮匹配内容
                  if (consoleSearchKeyword && line.toLowerCase().includes(consoleSearchKeyword.toLowerCase())) {
                    const regex = new RegExp(`(${consoleSearchKeyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
                    const parts = line.split(regex);
                    return (
                      <div key={i} className="text-green-400 whitespace-pre-wrap bg-yellow-900/30">
                        {parts.map((part, j) =>
                          regex.test(part) ? (
                            <span key={j} className="bg-yellow-500 text-black px-0.5 rounded">{part}</span>
                          ) : (
                            <span key={j}>{part}</span>
                          )
                        )}
                      </div>
                    );
                  }
                  // 如果有搜索关键字但不匹配，显示为暗色
                  if (consoleSearchKeyword && !line.toLowerCase().includes(consoleSearchKeyword.toLowerCase())) {
                    return (
                      <div key={i} className="text-gray-600 whitespace-pre-wrap">
                        {line}
                      </div>
                    );
                  }
                  // 无搜索关键字时正常显示
                  return (
                    <div key={i} className="text-green-400 whitespace-pre-wrap">
                      {line}
                    </div>
                  );
                })
              )}
              {isRunning && <span className="text-green-400 animate-pulse">▋</span>}
            </div>
          </Card>
        </div>
      </div>

      {/* Script Editor Modal */}
      {showEditor && selectedScript && project && (
        <ScriptEditor
          projectId={project.id}
          script={selectedScript}
          onClose={() => setShowEditor(false)}
          onSave={handleSaveScript}
        />
      )}

      {/* Create Script Dialog */}
      {showCreateDialog && project && (
        <CreateScriptDialog
          projectId={project.id}
          projectName={project.name}
          onClose={() => setShowCreateDialog(false)}
          onCreate={handleCreateScript}
        />
      )}

      {/* Project Variables Dialog */}
      {showVariablesDialog && project && (
        <ProjectVariablesDialog
          projectId={project.id}
          projectName={project.name}
          projectPath={project.path}
          onClose={() => setShowVariablesDialog(false)}
        />
      )}

      {/* Delete Confirm Dialog */}
      {showDeleteDialog && scriptToDelete && (
        <DeleteConfirmDialog
          scriptName={scriptToDelete.name}
          scriptPath={scriptToDelete.path}
          onClose={() => {
            setShowDeleteDialog(false);
            setScriptToDelete(null);
          }}
          onConfirm={handleDeleteScript}
        />
      )}

      {/* Execute Confirm Dialog */}
      {showExecuteConfirm && selectedScript && project && (
        <ExecuteConfirmDialog
          script={selectedScript}
          project={project}
          targetApp={modalApps.find(app => app.id === selectedAppId) || null}
          executeMode={pendingExecuteMode}
          onClose={() => setShowExecuteConfirm(false)}
          onConfirm={confirmExecute}
        />
      )}

      {/* 模板脚本变量表单 */}
      {showVariableDialog && selectedScript && currentScriptContent && project && (
        <ExecuteVariableDialog
          scriptName={selectedScript.name}
          scriptContent={currentScriptContent}
          projectId={project.id}
          onClose={() => {
            setShowVariableDialog(false);
            setCurrentScriptContent('');
          }}
          onExecute={handleExecuteWithVariables}
        />
      )}

      {/* 命令行参数配置对话框 */}
      {showArgsDialog && selectedScript && currentScriptContent && (
        <DeployArgsDialog
          scriptName={selectedScript.name}
          scriptPath={selectedScript.path}
          scriptContent={currentScriptContent}
          onClose={() => {
            setShowArgsDialog(false);
            setCurrentScriptContent('');
          }}
          onExecute={handleExecuteWithArgs}
        />
      )}

      {/* 服务器操作面板 */}
      {showOpsPanel && modalApp && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowOpsPanel(false)}>
          <Card className="w-full max-w-3xl animate-slide-in max-h-[85vh] flex flex-col" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4 shrink-0">
              <div className="flex items-center gap-2">
                <Server className="w-5 h-5 text-primary-500" />
                <h2 className="text-base font-bold text-gray-800">项目操作 - {project.name}</h2>
              </div>
              <button onClick={() => setShowOpsPanel(false)} className="p-0.5 hover:bg-gray-100 rounded">
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>

            {/* Token 提示 */}
            {!modalApp.tokenId && !modalApp.tokenSecret && (
              <div className="mb-3 p-2 bg-yellow-50 text-yellow-700 text-xs rounded-md flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                未配置 Token，将使用系统默认认证。如需独立 Token，请编辑应用配置。
              </div>
            )}

            {/* 分类操作按钮 */}
            <div className="space-y-4 mb-4 shrink-0 overflow-y-auto max-h-[40vh] pr-1">
              {/* 应用管理 */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-1 h-4 bg-blue-500 rounded"></div>
                  <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">应用管理</span>
                </div>
                <div className="grid grid-cols-4 gap-2">
                  <button
                    onClick={() => runOpsCommand(() => ModalAppListWithTokenPair(modalApp.tokenId || '', modalApp.tokenSecret || ''), 'modal app list')}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-blue-50 hover:border-blue-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <List className="w-5 h-5 text-blue-500" />
                    <span className="text-gray-700">应用列表</span>
                  </button>
                  <button
                    onClick={() => runOpsCommand(() => ModalAppDescribeWithTokenPair(modalApp.appName, modalApp.tokenId || '', modalApp.tokenSecret || ''), `modal app describe ${modalApp.appName}`)}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-blue-50 hover:border-blue-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <Info className="w-5 h-5 text-blue-500" />
                    <span className="text-gray-700">应用详情</span>
                  </button>
                  <button
                    onClick={() => runOpsCommand(() => ModalAppLogsWithTokenPair(modalApp.appName, modalApp.tokenId || '', modalApp.tokenSecret || ''), `modal app logs ${modalApp.appName}`)}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-blue-50 hover:border-blue-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <FileCode className="w-5 h-5 text-blue-500" />
                    <span className="text-gray-700">应用日志</span>
                  </button>
                  <button
                    onClick={() => runOpsCommand(() => ModalAppStatsWithTokenPair(modalApp.appName, modalApp.tokenId || '', modalApp.tokenSecret || ''), `modal app stats ${modalApp.appName}`)}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-blue-50 hover:border-blue-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <BarChart3 className="w-5 h-5 text-blue-500" />
                    <span className="text-gray-700">应用统计</span>
                  </button>
                  <button
                    onClick={() => runOpsCommand(() => ModalAppHistoryWithTokenPair(modalApp.appName, modalApp.tokenId || '', modalApp.tokenSecret || ''), `modal app history ${modalApp.appName}`)}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-blue-50 hover:border-blue-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <History className="w-5 h-5 text-blue-500" />
                    <span className="text-gray-700">执行历史</span>
                  </button>
                  <button
                    onClick={() => runOpsCommand(() => ModalAppStopWithTokenPair(modalApp.appName, modalApp.tokenId || '', modalApp.tokenSecret || ''), `modal app stop ${modalApp.appName}`)}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-orange-50 hover:border-orange-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <StopCircle className="w-5 h-5 text-orange-500" />
                    <span className="text-gray-700">停止应用</span>
                  </button>
                  <button
                    onClick={() => {
                      if (window.confirm(`确定要删除应用 "${modalApp.appName}" 吗？此操作不可撤销！`)) {
                        runOpsCommand(() => ModalAppDeleteWithTokenPair(modalApp.appName, modalApp.tokenId || '', modalApp.tokenSecret || ''), `modal app delete ${modalApp.appName}`);
                      }
                    }}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-red-50 hover:border-red-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <Trash2 className="w-5 h-5 text-red-500" />
                    <span className="text-gray-700">删除应用</span>
                  </button>
                </div>
              </div>

              {/* Volume 存储 */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-1 h-4 bg-purple-500 rounded"></div>
                  <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Volume 存储</span>
                </div>
                <div className="grid grid-cols-4 gap-2">
                  <button
                    onClick={() => runOpsCommand(() => ModalVolumeListWithTokenPair(modalApp.tokenId || '', modalApp.tokenSecret || ''), 'modal volume list')}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-purple-50 hover:border-purple-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <HardDrive className="w-5 h-5 text-purple-500" />
                    <span className="text-gray-700">Volume 列表</span>
                  </button>
                  <button
                    onClick={() => {
                      const volumeName = window.prompt('请输入 Volume 名称:', project?.variables?.VOLUME_NAME || '');
                      if (volumeName) {
                        runOpsCommand(() => ModalVolumeGetWithTokenPair(volumeName, modalApp.tokenId || '', modalApp.tokenSecret || ''), `modal volume get ${volumeName}`);
                      }
                    }}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-purple-50 hover:border-purple-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <Info className="w-5 h-5 text-purple-500" />
                    <span className="text-gray-700">Volume 详情</span>
                  </button>
                  <button
                    onClick={() => {
                      const volumeName = window.prompt('请输入 Volume 名称:', project?.variables?.VOLUME_NAME || '');
                      if (volumeName) {
                        const path = window.prompt('请输入要列出的目录路径:', '/');
                        runOpsCommand(() => ModalVolumeLsWithTokenPair(volumeName, path || '/', modalApp.tokenId || '', modalApp.tokenSecret || ''), `modal volume ls ${volumeName} ${path || '/'}`);
                      }
                    }}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-purple-50 hover:border-purple-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <FolderOpen className="w-5 h-5 text-purple-500" />
                    <span className="text-gray-700">浏览文件</span>
                  </button>
                  <button
                    onClick={() => {
                      const volumeName = window.prompt('请输入 Volume 名称:');
                      if (volumeName) {
                        const filePath = window.prompt('请输入要删除的文件路径:');
                        if (filePath && window.confirm(`确定要删除 ${volumeName}:${filePath} 吗？`)) {
                          runOpsCommand(() => ModalVolumeRmWithTokenPair(volumeName, filePath, modalApp.tokenId || '', modalApp.tokenSecret || ''), `modal volume rm ${volumeName} ${filePath}`);
                        }
                      }
                    }}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-red-50 hover:border-red-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <Trash2 className="w-5 h-5 text-red-400" />
                    <span className="text-gray-700">删除文件</span>
                  </button>
                  <button
                    onClick={() => {
                      const volumeName = window.prompt('请输入 Volume 名称:', project?.variables?.VOLUME_NAME || '');
                      if (!volumeName) return;

                      const localPath = window.prompt('请输入本地文件路径:', 'D:/models/model.safetensors');
                      if (!localPath) return;

                      const modelTypes = ['checkpoints', 'loras', 'vae', 'clip', 'text_encoders', 'diffusion_models', 'controlnet', 'upscale_models', 'embeddings'];
                      const modelType = window.prompt(`请选择模型类型:\n${modelTypes.map((t, i) => `${i + 1}. ${t}`).join('\n')}\n\n输入数字或类型名:`, 'loras');
                      if (!modelType) return;

                      // 解析模型类型
                      let finalModelType = modelType;
                      const typeIndex = parseInt(modelType) - 1;
                      if (!isNaN(typeIndex) && typeIndex >= 0 && typeIndex < modelTypes.length) {
                        finalModelType = modelTypes[typeIndex];
                      }
                      if (!modelTypes.includes(finalModelType)) {
                        alert('无效的模型类型');
                        return;
                      }

                      // 提取文件名
                      const filename = localPath.split(/[/\\]/).pop() || 'model.safetensors';
                      const remotePath = `/models/${finalModelType}/${filename}`;

                      if (window.confirm(`确认上传?\n\n本地: ${localPath}\n远程: ${volumeName}:${remotePath}`)) {
                        runOpsCommand(
                          () => ModalVolumePutWithTokenPair(volumeName, localPath, remotePath, modalApp.tokenId || '', modalApp.tokenSecret || ''),
                          `modal volume put ${volumeName} "${localPath}" ${remotePath}`
                        );
                      }
                    }}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-green-50 hover:border-green-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <UploadCloud className="w-5 h-5 text-green-500" />
                    <span className="text-gray-700">上传模型</span>
                  </button>
                </div>
              </div>

              {/* 容器与 Secret */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-1 h-4 bg-cyan-500 rounded"></div>
                  <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">容器与密钥</span>
                </div>
                <div className="grid grid-cols-4 gap-2">
                  <button
                    onClick={() => runOpsCommand(() => ModalContainerListWithTokenPair(modalApp.tokenId || '', modalApp.tokenSecret || ''), 'modal container list')}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-cyan-50 hover:border-cyan-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <Box className="w-5 h-5 text-cyan-500" />
                    <span className="text-gray-700">容器列表</span>
                  </button>
                  <button
                    onClick={() => {
                      const containerId = window.prompt('请输入容器 ID:');
                      if (containerId && window.confirm(`确定要停止容器 ${containerId} 吗？`)) {
                        runOpsCommand(() => ModalContainerStopWithTokenPair(containerId, modalApp.tokenId || '', modalApp.tokenSecret || ''), `modal container stop ${containerId}`);
                      }
                    }}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-orange-50 hover:border-orange-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <StopCircle className="w-5 h-5 text-orange-500" />
                    <span className="text-gray-700">停止容器</span>
                  </button>
                  <button
                    onClick={() => runOpsCommand(() => ModalSecretListWithTokenPair(modalApp.tokenId || '', modalApp.tokenSecret || ''), 'modal secret list')}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-cyan-50 hover:border-cyan-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <Key className="w-5 h-5 text-yellow-500" />
                    <span className="text-gray-700">Secret 列表</span>
                  </button>
                </div>
              </div>

              {/* 系统信息 */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-1 h-4 bg-green-500 rounded"></div>
                  <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">系统信息</span>
                </div>
                <div className="grid grid-cols-4 gap-2">
                  <button
                    onClick={() => runOpsCommand(() => ModalProfileWithTokenPair(modalApp.tokenId || '', modalApp.tokenSecret || ''), 'modal profile current')}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-green-50 hover:border-green-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <User className="w-5 h-5 text-green-500" />
                    <span className="text-gray-700">当前配置</span>
                  </button>
                  <button
                    onClick={() => runOpsCommand(() => ModalEnvironmentListWithTokenPair(modalApp.tokenId || '', modalApp.tokenSecret || ''), 'modal environment list')}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-green-50 hover:border-green-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <Layers className="w-5 h-5 text-green-500" />
                    <span className="text-gray-700">环境列表</span>
                  </button>
                  <button
                    onClick={() => runOpsCommand(() => ModalNfsListWithTokenPair(modalApp.tokenId || '', modalApp.tokenSecret || ''), 'modal nfs list')}
                    disabled={opsLoading}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-green-50 hover:border-green-200 border border-transparent rounded-lg transition-all disabled:opacity-50"
                  >
                    <Database className="w-5 h-5 text-green-500" />
                    <span className="text-gray-700">NFS 列表</span>
                  </button>
                  <button
                    onClick={() => {
                      setShowOpsPanel(false);
                      setShowProjectLogs(true);
                    }}
                    className="flex flex-col items-center gap-1 p-2.5 text-xs bg-gray-50 hover:bg-amber-50 hover:border-amber-200 border border-transparent rounded-lg transition-all"
                  >
                    <ScrollText className="w-5 h-5 text-amber-500" />
                    <span className="text-gray-700">执行日志</span>
                  </button>
                </div>
              </div>
            </div>

            {/* 输出区域 */}
            <div className="flex-1 min-h-0">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <Terminal className="w-4 h-4" />
                  <span>命令输出</span>
                </div>
                {opsOutput && (
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(opsOutput);
                    }}
                    className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1"
                  >
                    <Copy className="w-3 h-3" />
                    复制
                  </button>
                )}
              </div>
              <div className="bg-gray-900 rounded-lg p-3 h-52 overflow-y-auto font-mono text-xs">
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

      {/* 项目执行日志弹窗 */}
      {showProjectLogs && project && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowProjectLogs(false)}>
          <Card className="w-full max-w-4xl animate-slide-in max-h-[85vh] flex flex-col" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4 shrink-0">
              <div className="flex items-center gap-2">
                <ScrollText className="w-5 h-5 text-amber-500" />
                <h2 className="text-base font-bold text-gray-800">执行日志 - {project.name}</h2>
              </div>
              <button onClick={() => setShowProjectLogs(false)} className="p-0.5 hover:bg-gray-100 rounded">
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              <ExecutionLogs projectId={project.id} projectName={project.name} compact />
            </div>
          </Card>
        </div>
      )}

      {/* 代码预览弹窗 */}
      {showCodePreview && selectedScript && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={() => { setShowCodePreview(false); setSearchKeyword(''); }}>
          <Card className="w-full max-w-5xl max-h-[90vh] flex flex-col animate-slide-in" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200 shrink-0">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary-100 rounded-lg">
                  <Code className="w-5 h-5 text-primary-600" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-gray-800">代码预览</h2>
                  <p className="text-xs text-gray-500">{selectedScript.name}</p>
                </div>
              </div>
              <button
                onClick={() => { setShowCodePreview(false); setSearchKeyword(''); }}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* 搜索栏 */}
            <div className="px-4 py-2 border-b border-gray-200 bg-gray-50 shrink-0">
              <div className="flex items-center gap-3">
                <div className="relative flex-1 max-w-md">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="搜索代码内容... (Ctrl+F 也可以)"
                    value={searchKeyword}
                    onChange={(e) => {
                      const keyword = e.target.value;
                      setSearchKeyword(keyword);
                      // 计算匹配数量
                      if (keyword && previewCode) {
                        const regex = new RegExp(keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
                        const matches = previewCode.match(regex);
                        const matchCount = matches ? matches.length : 0;
                        setSearchMatchCount(matchCount);

                        // 自动跳转到第一个匹配项
                        if (matchCount > 0) {
                          setCurrentMatchIndex(1);
                          const view = codePreviewRef.current?.view;
                          if (view) {
                            const query = new SearchQuery({
                              search: keyword,
                              caseSensitive: false,
                              regexp: false,
                              wholeWord: false,
                            });
                            view.dispatch({ effects: setSearchQuery.of(query) });
                            // 跳转到第一个匹配
                            findNext(view);
                            // 高亮当前行
                            setTimeout(() => {
                              const pos = view.state.selection.main.head;
                              view.dispatch({ effects: highlightLineEffect.of(pos) });
                            }, 10);
                          }
                        } else {
                          setCurrentMatchIndex(0);
                          // 清除高亮
                          const view = codePreviewRef.current?.view;
                          if (view) {
                            view.dispatch({ effects: clearHighlightEffect.of(null) });
                          }
                        }
                      } else {
                        setSearchMatchCount(0);
                        setCurrentMatchIndex(0);
                        // 清除高亮
                        const view = codePreviewRef.current?.view;
                        if (view) {
                          view.dispatch({ effects: clearHighlightEffect.of(null) });
                        }
                      }
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && searchKeyword && searchMatchCount > 0) {
                        e.preventDefault();
                        const view = codePreviewRef.current?.view;
                        if (view) {
                          const query = new SearchQuery({
                            search: searchKeyword,
                            caseSensitive: false,
                            regexp: false,
                            wholeWord: false,
                          });
                          view.dispatch({ effects: setSearchQuery.of(query) });

                          if (e.shiftKey) {
                            // Shift+Enter: 上一处
                            findPrevious(view);
                            setCurrentMatchIndex(prev => prev > 1 ? prev - 1 : searchMatchCount);
                          } else {
                            // Enter: 下一处
                            findNext(view);
                            setCurrentMatchIndex(prev => prev < searchMatchCount ? prev + 1 : 1);
                          }
                          // 高亮当前行
                          setTimeout(() => {
                            const pos = view.state.selection.main.head;
                            view.dispatch({ effects: highlightLineEffect.of(pos) });
                          }, 10);
                        }
                      }
                    }}
                    className="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
                {searchKeyword && (
                  <div className="flex items-center gap-2 text-sm">
                    {searchMatchCount > 0 ? (
                      <>
                        <span className="text-green-600 font-medium">
                          {currentMatchIndex}/{searchMatchCount} 处匹配
                        </span>
                        {/* 上一处/下一处导航按钮 */}
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => {
                              const view = codePreviewRef.current?.view;
                              if (view) {
                                // 设置搜索查询
                                const query = new SearchQuery({
                                  search: searchKeyword,
                                  caseSensitive: false,
                                  regexp: false,
                                  wholeWord: false,
                                });
                                view.dispatch({ effects: setSearchQuery.of(query) });
                                // 跳转到上一处
                                findPrevious(view);
                                // 高亮当前行
                                setTimeout(() => {
                                  const pos = view.state.selection.main.head;
                                  view.dispatch({ effects: highlightLineEffect.of(pos) });
                                }, 10);
                                // 更新索引
                                setCurrentMatchIndex(prev => prev > 1 ? prev - 1 : searchMatchCount);
                              }
                            }}
                            className="p-1.5 hover:bg-gray-200 rounded transition-colors"
                            title="上一处 (Shift+Enter)"
                          >
                            <ChevronUp className="w-4 h-4 text-gray-600" />
                          </button>
                          <button
                            onClick={() => {
                              const view = codePreviewRef.current?.view;
                              if (view) {
                                // 设置搜索查询
                                const query = new SearchQuery({
                                  search: searchKeyword,
                                  caseSensitive: false,
                                  regexp: false,
                                  wholeWord: false,
                                });
                                view.dispatch({ effects: setSearchQuery.of(query) });
                                // 跳转到下一处
                                findNext(view);
                                // 高亮当前行
                                setTimeout(() => {
                                  const pos = view.state.selection.main.head;
                                  view.dispatch({ effects: highlightLineEffect.of(pos) });
                                }, 10);
                                // 更新索引
                                setCurrentMatchIndex(prev => prev < searchMatchCount ? prev + 1 : 1);
                              }
                            }}
                            className="p-1.5 hover:bg-gray-200 rounded transition-colors"
                            title="下一处 (Enter)"
                          >
                            <ChevronDown className="w-4 h-4 text-gray-600" />
                          </button>
                        </div>
                      </>
                    ) : (
                      <span className="text-gray-500">
                        未找到匹配
                      </span>
                    )}
                    <button
                      onClick={() => {
                        setSearchKeyword('');
                        setSearchMatchCount(0);
                        setCurrentMatchIndex(0);
                        // 清除高亮
                        const view = codePreviewRef.current?.view;
                        if (view) {
                          view.dispatch({ effects: clearHighlightEffect.of(null) });
                        }
                      }}
                      className="p-1 hover:bg-gray-200 rounded transition-colors"
                      title="清除搜索"
                    >
                      <X className="w-4 h-4 text-gray-400" />
                    </button>
                  </div>
                )}
                <p className="text-xs text-gray-400">
                  提示: 按 Ctrl+F 使用内置搜索
                </p>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden p-4">
              {previewLoading ? (
                <div className="w-full h-full flex items-center justify-center bg-gray-50 rounded-lg border border-gray-300">
                  <div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-2"></div>
                    <p className="text-sm text-gray-500">加载中...</p>
                  </div>
                </div>
              ) : (
                <div className="h-full border border-gray-700 rounded-lg overflow-hidden shadow-lg">
                  <CodeMirror
                    ref={codePreviewRef}
                    value={previewCode}
                    height="calc(90vh - 240px)"
                    theme={vscodeDark}
                    extensions={[
                      python(),
                      search({
                        top: true,
                      }),
                      highlightSelectionMatches(),
                      searchHighlightField,
                      searchHighlightTheme,
                    ]}
                    editable={false}
                    style={{
                      fontSize: '14px',
                    }}
                    basicSetup={{
                      lineNumbers: true,
                      highlightActiveLineGutter: false,
                      highlightSpecialChars: true,
                      foldGutter: true,
                      drawSelection: true,
                      dropCursor: false,
                      allowMultipleSelections: false,
                      indentOnInput: false,
                      bracketMatching: true,
                      closeBrackets: false,
                      autocompletion: false,
                      rectangularSelection: false,
                      crosshairCursor: false,
                      highlightActiveLine: false,
                      highlightSelectionMatches: true,
                      closeBracketsKeymap: false,
                      searchKeymap: true,
                      foldKeymap: true,
                      completionKeymap: false,
                      lintKeymap: false,
                    }}
                  />
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between p-4 border-t border-gray-200 bg-gray-50 shrink-0">
              <p className="text-xs text-gray-500">
                只读模式 - 如需编辑请点击"查询详情"按钮
              </p>
              <Button variant="secondary" size="sm" onClick={() => { setShowCodePreview(false); setSearchKeyword(''); }}>
                关闭
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
