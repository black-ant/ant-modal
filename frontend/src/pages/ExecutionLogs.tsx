import { useState, useEffect } from 'react';
import { History, ChevronDown, ChevronRight, Trash2, Code, Clock, Play, Upload, RefreshCw, X, Filter, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import Card from '../components/Card';
import Button from '../components/Button';
import { GetExecutionLogs, GetProjects, DeleteExecutionLog, ClearExecutionLogs } from '../../wailsjs/go/main/App';
import { main } from '../../wailsjs/go/models';

interface ExecutionLog {
  id: string;
  projectId: string;
  projectName: string;
  scriptName: string;
  scriptPath: string;
  scriptContent: string;
  command: string;
  variables: Record<string, string>;
  startTime: number;
  endTime: number;
  status: string;
  output: string;
}

interface ExecutionLogsProps {
  projectId?: string;
  projectName?: string;
  compact?: boolean;
}

export default function ExecutionLogs({ projectId, projectName, compact = false }: ExecutionLogsProps) {
  const [logs, setLogs] = useState<ExecutionLog[]>([]);
  const [projects, setProjects] = useState<main.Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(projectId || '');
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
  const [expandedSections, setExpandedSections] = useState<Record<string, 'script' | 'output' | 'variables' | null>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (projectId) {
      setSelectedProjectId(projectId);
    }
  }, [projectId]);

  useEffect(() => {
    loadLogs();
  }, [selectedProjectId]);

  const loadData = async () => {
    try {
      const [projectsData] = await Promise.all([
        GetProjects()
      ]);
      setProjects(projectsData || []);
      await loadLogs();
    } catch (err) {
      console.error('加载数据失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadLogs = async () => {
    try {
      setRefreshing(true);
      const logsData = await GetExecutionLogs(selectedProjectId, 100);
      setLogs(logsData || []);
    } catch (err) {
      console.error('加载执行日志失败:', err);
    } finally {
      setRefreshing(false);
    }
  };

  const handleDeleteLog = async (logId: string) => {
    if (!window.confirm('确定要删除这条执行日志吗？')) return;
    
    try {
      await DeleteExecutionLog(logId);
      await loadLogs();
    } catch (err) {
      console.error('删除日志失败:', err);
    }
  };

  const handleClearLogs = async () => {
    const msg = selectedProjectId 
      ? '确定要清空该项目的所有执行日志吗？' 
      : '确定要清空所有执行日志吗？此操作不可撤销！';
    if (!window.confirm(msg)) return;
    
    try {
      await ClearExecutionLogs(selectedProjectId);
      await loadLogs();
    } catch (err) {
      console.error('清空日志失败:', err);
    }
  };

  const toggleExpand = (logId: string) => {
    const newExpanded = new Set(expandedLogs);
    if (newExpanded.has(logId)) {
      newExpanded.delete(logId);
    } else {
      newExpanded.add(logId);
    }
    setExpandedLogs(newExpanded);
  };

  const toggleSection = (logId: string, section: 'script' | 'output' | 'variables') => {
    setExpandedSections(prev => ({
      ...prev,
      [logId]: prev[logId] === section ? null : section
    }));
  };

  const formatTime = (timestamp: number) => {
    if (!timestamp) return '-';
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const formatDuration = (start: number, end: number) => {
    if (!start || !end) return '-';
    const duration = end - start;
    if (duration < 60) return `${duration}秒`;
    if (duration < 3600) return `${Math.floor(duration / 60)}分${duration % 60}秒`;
    return `${Math.floor(duration / 3600)}时${Math.floor((duration % 3600) / 60)}分`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Loader className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'running': return '执行中';
      case 'success': return '成功';
      case 'failed': return '失败';
      default: return '未知';
    }
  };

  const getCommandIcon = (command: string) => {
    switch (command) {
      case 'deploy':
        return <Upload className="w-3.5 h-3.5" />;
      case 'run':
        return <Play className="w-3.5 h-3.5" />;
      default:
        return <Code className="w-3.5 h-3.5" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader className="w-8 h-8 text-primary-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className={compact ? '' : 'p-6'}>
      {!compact && (
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-primary-100 rounded-lg">
              <History className="w-6 h-6 text-primary-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">执行日志</h1>
              <p className="text-sm text-gray-500">查看脚本执行历史和详情</p>
            </div>
          </div>
        </div>
      )}

      <Card className={compact ? 'p-3' : ''}>
        {/* 筛选和操作栏 */}
        <div className="flex items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-3">
            {!projectId && (
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-gray-400" />
                <select
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">全部项目</option>
                  {projects.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
            )}
            {projectName && (
              <span className="text-sm text-gray-500">项目: {projectName}</span>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={loadLogs}
              disabled={refreshing}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:text-primary-600 hover:bg-gray-50 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              刷新
            </button>
            {logs.length > 0 && (
              <button
                onClick={handleClearLogs}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                清空
              </button>
            )}
          </div>
        </div>

        {/* 日志列表 */}
        {logs.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>暂无执行日志</p>
          </div>
        ) : (
          <div className="space-y-2">
            {logs.map(log => (
              <div 
                key={log.id}
                className="border border-gray-100 rounded-lg overflow-hidden hover:border-gray-200 transition-colors"
              >
                {/* 日志头部 */}
                <div 
                  className="flex items-center gap-3 px-4 py-3 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => toggleExpand(log.id)}
                >
                  <button className="text-gray-400">
                    {expandedLogs.has(log.id) ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </button>
                  
                  {getStatusIcon(log.status)}
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-800 truncate">{log.scriptName}</span>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded ${
                        log.command === 'deploy' 
                          ? 'bg-blue-100 text-blue-700' 
                          : 'bg-green-100 text-green-700'
                      }`}>
                        {getCommandIcon(log.command)}
                        {log.command}
                      </span>
                    </div>
                    {!projectId && (
                      <div className="text-xs text-gray-500 mt-0.5">{log.projectName}</div>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatTime(log.startTime)}
                    </span>
                    {log.endTime > 0 && (
                      <span className="text-gray-400">
                        耗时: {formatDuration(log.startTime, log.endTime)}
                      </span>
                    )}
                  </div>
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteLog(log.id);
                    }}
                    className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                
                {/* 展开详情 */}
                {expandedLogs.has(log.id) && (
                  <div className="border-t border-gray-100">
                    {/* 标签页 */}
                    <div className="flex border-b border-gray-100">
                      <button
                        onClick={() => toggleSection(log.id, 'script')}
                        className={`flex items-center gap-1 px-4 py-2 text-sm transition-colors ${
                          expandedSections[log.id] === 'script'
                            ? 'text-primary-600 border-b-2 border-primary-500 -mb-px'
                            : 'text-gray-500 hover:text-gray-700'
                        }`}
                      >
                        <Code className="w-4 h-4" />
                        脚本内容
                      </button>
                      <button
                        onClick={() => toggleSection(log.id, 'output')}
                        className={`flex items-center gap-1 px-4 py-2 text-sm transition-colors ${
                          expandedSections[log.id] === 'output'
                            ? 'text-primary-600 border-b-2 border-primary-500 -mb-px'
                            : 'text-gray-500 hover:text-gray-700'
                        }`}
                      >
                        <History className="w-4 h-4" />
                        执行输出
                      </button>
                      {log.variables && Object.keys(log.variables).length > 0 && (
                        <button
                          onClick={() => toggleSection(log.id, 'variables')}
                          className={`flex items-center gap-1 px-4 py-2 text-sm transition-colors ${
                            expandedSections[log.id] === 'variables'
                              ? 'text-primary-600 border-b-2 border-primary-500 -mb-px'
                              : 'text-gray-500 hover:text-gray-700'
                          }`}
                        >
                          变量 ({Object.keys(log.variables).length})
                        </button>
                      )}
                    </div>
                    
                    {/* 内容区域 */}
                    <div className="p-4">
                      {expandedSections[log.id] === 'script' && (
                        <div className="bg-gray-900 rounded-lg p-4 max-h-96 overflow-auto">
                          <pre className="text-sm text-green-400 font-mono whitespace-pre-wrap">
                            {log.scriptContent || '无脚本内容'}
                          </pre>
                        </div>
                      )}
                      
                      {expandedSections[log.id] === 'output' && (
                        <div className="bg-gray-900 rounded-lg p-4 max-h-96 overflow-auto">
                          <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">
                            {log.output || '无输出'}
                          </pre>
                        </div>
                      )}
                      
                      {expandedSections[log.id] === 'variables' && log.variables && (
                        <div className="bg-gray-50 rounded-lg p-4">
                          <div className="grid grid-cols-2 gap-2">
                            {Object.entries(log.variables).map(([key, value]) => (
                              <div key={key} className="flex items-start gap-2 text-sm">
                                <span className="font-mono text-primary-600">{key}:</span>
                                <span className="text-gray-700 break-all">{value}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {!expandedSections[log.id] && (
                        <div className="text-center text-gray-400 py-4">
                          点击上方标签查看详情
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

