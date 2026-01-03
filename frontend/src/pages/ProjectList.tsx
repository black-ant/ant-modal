import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Folder, Trash2, ArrowRight, X, Cloud, Pencil, RefreshCw } from 'lucide-react';
import clsx from 'clsx';
import Card from '../components/Card';
import Button from '../components/Button';
import { main } from '../../wailsjs/go/models';
import { GetProjects, CreateProject, DeleteProject, UpdateProject, GetModalAppList } from '../../wailsjs/go/main/App';

export default function ProjectList() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<main.Project[]>([]);
  const [apps, setApps] = useState<main.ModalApp[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [newProject, setNewProject] = useState({ name: '', description: '', appId: '' });
  const [editProject, setEditProject] = useState({ id: '', name: '', description: '', appId: '' });

  useEffect(() => {
    loadProjects();
    loadApps();
  }, []);

  useEffect(() => {
    // 如果只有一个应用且模态框已打开，自动选择
    if (showModal && apps.length === 1 && !newProject.appId) {
      setNewProject(prev => ({ ...prev, appId: apps[0].id }));
    }
  }, [showModal, apps]);

  const loadProjects = async () => {
    setIsRefreshing(true);
    try {
      const data = await GetProjects();
      setProjects(data || []);
    } finally {
      setIsRefreshing(false);
    }
  };

  const loadApps = async () => {
    const data = await GetModalAppList();
    setApps(data || []);
  };

  const getAppName = (appId: string) => {
    const app = apps.find((a) => a.id === appId);
    return app?.name || '';
  };

  const handleCreate = async () => {
    // 验证必填项
    if (!newProject.name) {
      alert('请输入项目名称');
      return;
    }
    if (!newProject.appId) {
      alert('请选择关联应用');
      return;
    }

    // 不需要项目路径，传空字符串
    await CreateProject(newProject.name, '', newProject.description, newProject.appId);
    setShowModal(false);
    setNewProject({ name: '', description: '', appId: apps.length === 1 ? apps[0].id : '' });
    loadProjects();
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('确定要删除这个项目吗？')) {
      await DeleteProject(id);
      loadProjects();
    }
  };

  const handleEdit = (project: main.Project, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditProject({
      id: project.id,
      name: project.name,
      description: project.description || '',
      appId: project.appId || '',
    });
    setShowEditModal(true);
  };

  const handleUpdate = async () => {
    if (!editProject.name) {
      alert('请输入项目名称');
      return;
    }
    if (!editProject.appId) {
      alert('请选择关联应用');
      return;
    }
    await UpdateProject(editProject.id, editProject.name, editProject.description, editProject.appId);
    setShowEditModal(false);
    loadProjects();
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

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <div>
            <h1 className="text-lg font-bold text-gray-800">我的项目</h1>
            <p className="text-gray-500 text-xs">管理你的 Modal 云端项目</p>
          </div>
          <button
            onClick={loadProjects}
            disabled={isRefreshing}
            className={clsx(
              "p-1.5 rounded-md transition-colors",
              isRefreshing
                ? "text-gray-300 cursor-not-allowed"
                : "text-gray-400 hover:text-primary-500 hover:bg-primary-50"
            )}
            title="刷新项目列表"
          >
            <RefreshCw className={clsx("w-4 h-4", isRefreshing && "animate-spin")} />
          </button>
        </div>
        <Button onClick={() => setShowModal(true)}>
          <Plus className="w-4 h-4 mr-1" />
          新建项目
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <Card gradient="green" className="p-3">
          <div className="text-xl font-bold">{projects.length}</div>
          <div className="text-xs opacity-90">总项目数</div>
        </Card>
        <Card gradient="yellow" className="p-3">
          <div className="text-xl font-bold">{projects.filter((p) => p.status === 'running').length}</div>
          <div className="text-xs opacity-90">运行中</div>
        </Card>
        <Card gradient="orange" className="p-3">
          <div className="text-xl font-bold">{projects.filter((p) => p.status === 'stopped').length}</div>
          <div className="text-xs opacity-90">已停止</div>
        </Card>
      </div>

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {projects.length === 0 ? (
          <Card className="col-span-full text-center py-8">
            <Folder className="w-12 h-12 mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500 text-sm">还没有项目，点击上方按钮创建一个吧</p>
          </Card>
        ) : (
          projects.map((project) => (
            <Card
              key={project.id}
              className="cursor-pointer hover:-translate-y-0.5 transition-transform p-3"
              onClick={() => navigate(`/project/${project.id}`)}
            >
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-sm font-semibold text-gray-800 truncate flex-1 mr-2">{project.name}</h3>
                <span className={clsx('px-2 py-0.5 rounded-full text-xs font-medium shrink-0', getStatusColor(project.status))}>
                  {getStatusText(project.status)}
                </span>
              </div>
              <p className="text-gray-500 text-xs mb-1 line-clamp-2">{project.description || '暂无描述'}</p>
              {project.appId && (
                <p className="text-xs text-primary-500 mb-3 flex items-center gap-1">
                  <Cloud className="w-3 h-3" />
                  {getAppName(project.appId)}
                </p>
              )}
              <div className="flex justify-between items-center pt-2 border-t border-gray-100">
                <div className="flex gap-1">
                  <button
                    onClick={(e) => handleEdit(project, e)}
                    className="p-1 text-gray-400 hover:text-primary-500 hover:bg-primary-50 rounded transition-colors"
                    title="编辑项目"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={(e) => handleDelete(project.id, e)}
                    className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                    title="删除项目"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/project/${project.id}`);
                  }}
                  className="flex items-center gap-0.5 text-primary-500 hover:text-primary-600 text-xs font-medium"
                >
                  进入 <ArrowRight className="w-3 h-3" />
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
              <h2 className="text-base font-bold text-gray-800">新建项目</h2>
              <button onClick={() => setShowModal(false)} className="p-0.5 hover:bg-gray-100 rounded">
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">项目名称 *</label>
                <input
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-transparent"
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  placeholder="输入项目名称"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">关联应用 *</label>
                <select
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-transparent"
                  value={newProject.appId}
                  onChange={(e) => setNewProject({ ...newProject, appId: e.target.value })}
                >
                  <option value="">请选择应用</option>
                  {apps.map((app) => (
                    <option key={app.id} value={app.id}>
                      {app.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">描述</label>
                <input
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-transparent"
                  value={newProject.description}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  placeholder="项目描述（可选）"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-4">
              <Button variant="secondary" size="sm" onClick={() => setShowModal(false)}>
                取消
              </Button>
              <Button size="sm" onClick={handleCreate}>创建</Button>
            </div>
          </Card>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowEditModal(false)}>
          <Card className="w-full max-w-sm animate-slide-in" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-base font-bold text-gray-800">编辑项目</h2>
              <button onClick={() => setShowEditModal(false)} className="p-0.5 hover:bg-gray-100 rounded">
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">项目名称 *</label>
                <input
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-transparent"
                  value={editProject.name}
                  onChange={(e) => setEditProject({ ...editProject, name: e.target.value })}
                  placeholder="输入项目名称"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">关联应用 *</label>
                <select
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-transparent"
                  value={editProject.appId}
                  onChange={(e) => setEditProject({ ...editProject, appId: e.target.value })}
                >
                  <option value="">请选择应用</option>
                  {apps.map((app) => (
                    <option key={app.id} value={app.id}>
                      {app.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">描述</label>
                <input
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-transparent"
                  value={editProject.description}
                  onChange={(e) => setEditProject({ ...editProject, description: e.target.value })}
                  placeholder="项目描述（可选）"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-4">
              <Button variant="secondary" size="sm" onClick={() => setShowEditModal(false)}>
                取消
              </Button>
              <Button size="sm" onClick={handleUpdate}>保存</Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
