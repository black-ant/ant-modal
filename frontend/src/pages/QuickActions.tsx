import { useState, useEffect } from 'react';
import { 
  Zap, Play, Square, FileText, 
  Database, Key, BookOpen, Server, 
  FolderOpen, Trash2, Plus,
  Terminal, CheckCircle,
  User, ChevronDown, ExternalLink,
  ScrollText, History, HardDrive, Globe,
  Settings, Shield, Box, Layers, Clock
} from 'lucide-react';
import clsx from 'clsx';
import Card from '../components/Card';
import Button from '../components/Button';
import CommandExecuteDialog from '../components/CommandExecuteDialog';
import { ExecuteModalCommandWithToken, GetModalAppList } from '../../wailsjs/go/main/App';

interface ModalApp {
  id: string;
  name: string;
  tokenId: string;
  tokenSecret: string;
}

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

const actionCategories = [
  {
    title: '应用管理',
    icon: Play,
    actions: [
      {
        id: 'app-list',
        name: '列出应用',
        description: '查看所有已部署的应用',
        command: 'modal app list',
        icon: FileText,
        color: 'blue'
      },
      {
        id: 'app-logs',
        name: '查看日志',
        description: '查看应用的运行日志',
        command: 'modal app logs',
        icon: ScrollText,
        color: 'blue',
        needsInput: true,
        inputLabel: '应用名称',
        inputPlaceholder: '输入应用名称'
      },
      {
        id: 'app-history',
        name: '部署历史',
        description: '查看应用的部署历史',
        command: 'modal app history',
        icon: History,
        color: 'blue',
        needsInput: true,
        inputLabel: '应用名称',
        inputPlaceholder: '输入应用名称'
      },
      {
        id: 'app-stop',
        name: '停止应用',
        description: '停止指定的应用',
        command: 'modal app stop',
        icon: Square,
        color: 'red',
        needsInput: true,
        inputLabel: '应用名称',
        inputPlaceholder: '输入要停止的应用名称'
      },
    ]
  },
  {
    title: 'Volume 存储',
    icon: Database,
    actions: [
      {
        id: 'volume-list',
        name: '列出 Volume',
        description: '查看所有 Volume 存储',
        command: 'modal volume list',
        icon: Database,
        color: 'green'
      },
      {
        id: 'volume-create',
        name: '创建 Volume',
        description: '创建新的持久化存储',
        command: 'modal volume create',
        icon: Plus,
        color: 'green',
        needsInput: true,
        inputLabel: 'Volume 名称',
        inputPlaceholder: '输入 Volume 名称'
      },
      {
        id: 'volume-ls',
        name: '浏览 Volume',
        description: '查看 Volume 中的文件',
        command: 'modal volume ls',
        icon: FolderOpen,
        color: 'green',
        needsInput: true,
        inputLabel: 'Volume 名称',
        inputPlaceholder: '输入 Volume 名称'
      },
      {
        id: 'volume-delete',
        name: '删除 Volume',
        description: '删除指定的 Volume',
        command: 'modal volume delete',
        icon: Trash2,
        color: 'red',
        needsInput: true,
        inputLabel: 'Volume 名称',
        inputPlaceholder: '输入要删除的 Volume 名称'
      },
    ]
  },
  {
    title: 'Secret 密钥',
    icon: Key,
    actions: [
      {
        id: 'secret-list',
        name: '列出 Secret',
        description: '查看所有密钥',
        command: 'modal secret list',
        icon: Key,
        color: 'yellow'
      },
      {
        id: 'secret-create',
        name: '创建 Secret',
        description: '创建新的密钥',
        command: 'modal secret create',
        icon: Plus,
        color: 'yellow',
        needsInput: true,
        inputLabel: '格式: name KEY=VALUE',
        inputPlaceholder: 'my-secret API_KEY=xxx'
      },
      {
        id: 'secret-delete',
        name: '删除 Secret',
        description: '删除指定的密钥',
        command: 'modal secret delete',
        icon: Trash2,
        color: 'red',
        needsInput: true,
        inputLabel: 'Secret 名称',
        inputPlaceholder: '输入要删除的 Secret 名称'
      },
    ]
  },
  {
    title: 'Dict 字典',
    icon: BookOpen,
    actions: [
      {
        id: 'dict-list',
        name: '列出 Dict',
        description: '查看所有字典存储',
        command: 'modal dict list',
        icon: BookOpen,
        color: 'purple'
      },
      {
        id: 'dict-create',
        name: '创建 Dict',
        description: '创建新的字典',
        command: 'modal dict create',
        icon: Plus,
        color: 'purple',
        needsInput: true,
        inputLabel: 'Dict 名称',
        inputPlaceholder: '输入 Dict 名称'
      },
      {
        id: 'dict-delete',
        name: '删除 Dict',
        description: '删除指定的字典',
        command: 'modal dict delete',
        icon: Trash2,
        color: 'red',
        needsInput: true,
        inputLabel: 'Dict 名称',
        inputPlaceholder: '输入要删除的 Dict 名称'
      },
    ]
  },
  {
    title: 'Queue 队列',
    icon: Server,
    actions: [
      {
        id: 'queue-list',
        name: '列出队列',
        description: '查看所有消息队列',
        command: 'modal queue list',
        icon: Server,
        color: 'indigo'
      },
      {
        id: 'queue-create',
        name: '创建队列',
        description: '创建新的消息队列',
        command: 'modal queue create',
        icon: Plus,
        color: 'indigo',
        needsInput: true,
        inputLabel: 'Queue 名称',
        inputPlaceholder: '输入队列名称'
      },
      {
        id: 'queue-delete',
        name: '删除队列',
        description: '删除指定的队列',
        command: 'modal queue delete',
        icon: Trash2,
        color: 'red',
        needsInput: true,
        inputLabel: 'Queue 名称',
        inputPlaceholder: '输入要删除的队列名称'
      },
    ]
  },
  {
    title: '容器管理',
    icon: Terminal,
    actions: [
      {
        id: 'container-list',
        name: '列出容器',
        description: '查看运行中的容器',
        command: 'modal container list',
        icon: Terminal,
        color: 'gray'
      },
      {
        id: 'container-stop',
        name: '停止容器',
        description: '停止指定的容器',
        command: 'modal container stop',
        icon: Square,
        color: 'red',
        needsInput: true,
        inputLabel: '容器 ID',
        inputPlaceholder: '输入容器 ID'
      },
      {
        id: 'container-exec',
        name: '进入容器',
        description: '在容器中执行命令',
        command: 'modal container exec',
        icon: Terminal,
        color: 'gray',
        needsInput: true,
        inputLabel: '容器 ID',
        inputPlaceholder: '输入容器 ID'
      },
    ]
  },
  {
    title: 'NFS 文件系统',
    icon: HardDrive,
    actions: [
      {
        id: 'nfs-list',
        name: '列出 NFS',
        description: '查看所有网络文件系统',
        command: 'modal nfs list',
        icon: HardDrive,
        color: 'cyan'
      },
      {
        id: 'nfs-create',
        name: '创建 NFS',
        description: '创建新的网络文件系统',
        command: 'modal nfs create',
        icon: Plus,
        color: 'cyan',
        needsInput: true,
        inputLabel: 'NFS 名称',
        inputPlaceholder: '输入 NFS 名称'
      },
      {
        id: 'nfs-delete',
        name: '删除 NFS',
        description: '删除指定的 NFS',
        command: 'modal nfs delete',
        icon: Trash2,
        color: 'red',
        needsInput: true,
        inputLabel: 'NFS 名称',
        inputPlaceholder: '输入要删除的 NFS 名称'
      },
    ]
  },
  {
    title: '环境管理',
    icon: Globe,
    actions: [
      {
        id: 'environment-list',
        name: '列出环境',
        description: '查看所有环境',
        command: 'modal environment list',
        icon: Globe,
        color: 'teal'
      },
      {
        id: 'environment-create',
        name: '创建环境',
        description: '创建新的隔离环境',
        command: 'modal environment create',
        icon: Plus,
        color: 'teal',
        needsInput: true,
        inputLabel: '环境名称',
        inputPlaceholder: '输入环境名称'
      },
      {
        id: 'environment-delete',
        name: '删除环境',
        description: '删除指定的环境',
        command: 'modal environment delete',
        icon: Trash2,
        color: 'red',
        needsInput: true,
        inputLabel: '环境名称',
        inputPlaceholder: '输入要删除的环境名称'
      },
    ]
  },
  {
    title: '配置管理',
    icon: Settings,
    actions: [
      {
        id: 'profile-list',
        name: '列出配置',
        description: '查看所有配置文件',
        command: 'modal profile list',
        icon: Settings,
        color: 'slate'
      },
      {
        id: 'profile-current',
        name: '当前配置',
        description: '查看当前使用的配置',
        command: 'modal profile current',
        icon: CheckCircle,
        color: 'slate'
      },
      {
        id: 'token-new',
        name: '创建 Token',
        description: '创建新的认证令牌',
        command: 'modal token new',
        icon: Shield,
        color: 'slate'
      },
    ]
  },
  {
    title: 'Sandbox 沙箱',
    icon: Box,
    actions: [
      {
        id: 'sandbox-list',
        name: '列出沙箱',
        description: '查看所有沙箱实例',
        command: 'modal sandbox list',
        icon: Box,
        color: 'orange'
      },
      {
        id: 'sandbox-terminate',
        name: '终止沙箱',
        description: '终止指定的沙箱',
        command: 'modal sandbox terminate',
        icon: Square,
        color: 'red',
        needsInput: true,
        inputLabel: '沙箱 ID',
        inputPlaceholder: '输入沙箱 ID'
      },
    ]
  },
  {
    title: 'Cls 类管理',
    icon: Layers,
    actions: [
      {
        id: 'cls-list',
        name: '列出类',
        description: '查看所有已部署的类',
        command: 'modal cls list',
        icon: Layers,
        color: 'pink'
      },
      {
        id: 'cls-stop',
        name: '停止类',
        description: '停止指定的类实例',
        command: 'modal cls stop',
        icon: Square,
        color: 'red',
        needsInput: true,
        inputLabel: '类名称',
        inputPlaceholder: '输入类名称'
      },
    ]
  },
  {
    title: '定时任务',
    icon: Clock,
    actions: [
      {
        id: 'cron-list',
        name: '列出定时任务',
        description: '查看所有定时任务',
        command: 'modal cron list',
        icon: Clock,
        color: 'amber'
      },
    ]
  },
];

const colorClasses: Record<string, { bg: string; text: string; hover: string; border: string }> = {
  blue: { bg: 'bg-blue-100', text: 'text-blue-600', hover: 'hover:bg-blue-200', border: 'border-blue-200' },
  green: { bg: 'bg-green-100', text: 'text-green-600', hover: 'hover:bg-green-200', border: 'border-green-200' },
  yellow: { bg: 'bg-yellow-100', text: 'text-yellow-600', hover: 'hover:bg-yellow-200', border: 'border-yellow-200' },
  purple: { bg: 'bg-purple-100', text: 'text-purple-600', hover: 'hover:bg-purple-200', border: 'border-purple-200' },
  indigo: { bg: 'bg-indigo-100', text: 'text-indigo-600', hover: 'hover:bg-indigo-200', border: 'border-indigo-200' },
  red: { bg: 'bg-red-100', text: 'text-red-600', hover: 'hover:bg-red-200', border: 'border-red-200' },
  gray: { bg: 'bg-gray-100', text: 'text-gray-600', hover: 'hover:bg-gray-200', border: 'border-gray-200' },
  cyan: { bg: 'bg-cyan-100', text: 'text-cyan-600', hover: 'hover:bg-cyan-200', border: 'border-cyan-200' },
  teal: { bg: 'bg-teal-100', text: 'text-teal-600', hover: 'hover:bg-teal-200', border: 'border-teal-200' },
  slate: { bg: 'bg-slate-100', text: 'text-slate-600', hover: 'hover:bg-slate-200', border: 'border-slate-200' },
  orange: { bg: 'bg-orange-100', text: 'text-orange-600', hover: 'hover:bg-orange-200', border: 'border-orange-200' },
  pink: { bg: 'bg-pink-100', text: 'text-pink-600', hover: 'hover:bg-pink-200', border: 'border-pink-200' },
  amber: { bg: 'bg-amber-100', text: 'text-amber-600', hover: 'hover:bg-amber-200', border: 'border-amber-200' },
};

export default function QuickActions() {
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [modalApps, setModalApps] = useState<ModalApp[]>([]);
  const [selectedApp, setSelectedApp] = useState<ModalApp | null>(null);
  const [showAppDropdown, setShowAppDropdown] = useState(false);
  const [selectedAction, setSelectedAction] = useState<QuickAction | null>(null);

  useEffect(() => {
    loadModalApps();
  }, []);

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

  const handleExecuteCommand = async (command: string): Promise<string> => {
    const tokenId = selectedApp?.tokenId || '';
    const tokenSecret = selectedApp?.tokenSecret || '';
    return await ExecuteModalCommandWithToken(command, tokenId, tokenSecret);
  };

  const filteredCategories = activeCategory === 'all' 
    ? actionCategories 
    : actionCategories.filter(c => c.title === activeCategory);

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h1 className="text-lg font-bold text-gray-800 flex items-center gap-2">
            <Zap className="w-5 h-5 text-primary-500" />
            快捷操作
          </h1>
          <p className="text-gray-500 text-xs">一键执行 Modal CLI 命令</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Modal App 选择器 */}
          <div className="relative">
            <button
              onClick={() => setShowAppDropdown(!showAppDropdown)}
              className="flex items-center gap-2 px-3 py-1.5 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm"
            >
              <User className="w-4 h-4 text-gray-500" />
              <span className="text-gray-700 max-w-[120px] truncate">
                {selectedApp ? selectedApp.name : '选择账号'}
              </span>
              <ChevronDown className={clsx(
                'w-4 h-4 text-gray-400 transition-transform',
                showAppDropdown && 'rotate-180'
              )} />
            </button>
            
            {showAppDropdown && (
              <div className="absolute right-0 top-full mt-1 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
                {modalApps.length === 0 ? (
                  <div className="px-3 py-2 text-sm text-gray-500">
                    暂无 Modal App，请先在 Modal Apps 页面添加
                  </div>
                ) : (
                  <>
                    <div className="px-3 py-2 text-xs text-gray-400 border-b">选择 Modal 账号</div>
                    {modalApps.map(app => (
                      <button
                        key={app.id}
                        onClick={() => {
                          setSelectedApp(app);
                          setShowAppDropdown(false);
                        }}
                        className={clsx(
                          'w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center justify-between',
                          selectedApp?.id === app.id && 'bg-primary-50 text-primary-600'
                        )}
                      >
                        <span className="truncate">{app.name}</span>
                        {selectedApp?.id === app.id && (
                          <CheckCircle className="w-4 h-4 text-primary-500" />
                        )}
                      </button>
                    ))}
                  </>
                )}
              </div>
            )}
          </div>
          
          <Button 
            size="sm" 
            variant="secondary"
            onClick={() => window.open('https://modal.com/docs/reference/cli', '_blank')}
          >
            <ExternalLink className="w-3 h-3 mr-1" />
            CLI 文档
          </Button>
        </div>
      </div>

      {/* Category Filter */}
      <div className="flex gap-2 mb-4 flex-wrap">
        <button
          onClick={() => setActiveCategory('all')}
          className={clsx(
            'px-3 py-1.5 text-sm rounded-lg transition-colors',
            activeCategory === 'all'
              ? 'bg-primary-500 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          )}
        >
          全部
        </button>
        {actionCategories.map(cat => (
          <button
            key={cat.title}
            onClick={() => setActiveCategory(cat.title)}
            className={clsx(
              'px-3 py-1.5 text-sm rounded-lg transition-colors',
              activeCategory === cat.title
                ? 'bg-primary-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            )}
          >
            {cat.title}
          </button>
        ))}
      </div>

      {/* Actions Grid - 全宽显示 */}
      <div className="space-y-4">
        {filteredCategories.map(category => (
          <Card key={category.title} className="p-4">
            <div className="flex items-center gap-2 mb-3">
              <category.icon className="w-4 h-4 text-gray-500" />
              <h2 className="text-sm font-semibold text-gray-700">{category.title}</h2>
              <span className="text-xs text-gray-400">({category.actions.length})</span>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {category.actions.map(action => {
                const colors = colorClasses[action.color];
                
                return (
                  <button
                    key={action.id}
                    onClick={() => setSelectedAction(action)}
                    className={clsx(
                      'p-4 rounded-xl text-left transition-all border-2',
                      colors.bg,
                      colors.border,
                      'hover:shadow-md hover:scale-[1.02] active:scale-[0.98]'
                    )}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <div className={clsx('p-2 rounded-lg bg-white/80')}>
                        <action.icon className={clsx('w-4 h-4', colors.text)} />
                      </div>
                    </div>
                    <span className="text-sm font-semibold text-gray-800 block mb-1">
                      {action.name}
                    </span>
                    <p className="text-xs text-gray-500 line-clamp-2">{action.description}</p>
                  </button>
                );
              })}
            </div>
          </Card>
        ))}
      </div>

      {/* 执行弹窗 */}
      {selectedAction && (
        <CommandExecuteDialog
          action={selectedAction}
          onClose={() => setSelectedAction(null)}
          onExecute={handleExecuteCommand}
          selectedAppName={selectedApp?.name}
        />
      )}
    </div>
  );
}
