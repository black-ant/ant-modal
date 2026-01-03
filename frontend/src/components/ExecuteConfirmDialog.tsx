import { Play, X, FileCode, Server, Cloud, ArrowRight } from 'lucide-react';
import Button from './Button';
import { main } from '../../wailsjs/go/models';

interface ExecuteConfirmDialogProps {
    script: main.Script;
    project: main.Project;
    targetApp: main.ModalApp | null;
    executeMode: 'deploy' | 'run';
    onClose: () => void;
    onConfirm: () => void;
}

export default function ExecuteConfirmDialog({
    script,
    project,
    targetApp,
    executeMode,
    onClose,
    onConfirm,
}: ExecuteConfirmDialogProps) {
    const actionLabel = executeMode === 'deploy' ? '部署' : '运行';
    const actionColor = executeMode === 'deploy' ? 'primary' : 'success';

    return (
        <div
            className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4"
            onClick={onClose}
        >
            <div
                className="w-full max-w-md bg-white rounded-lg shadow-2xl animate-slide-in"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-gray-200">
                    <div className="flex items-center gap-3">
                        <div className={`p-2 ${executeMode === 'deploy' ? 'bg-primary-100' : 'bg-green-100'} rounded-lg`}>
                            <Play className={`w-5 h-5 ${executeMode === 'deploy' ? 'text-primary-600' : 'text-green-600'}`} />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-gray-800">确认{actionLabel}</h2>
                            <p className="text-xs text-gray-500">请确认以下执行信息</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-5 space-y-4">
                    {/* 脚本信息 */}
                    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                        <div className="flex items-start gap-3">
                            <FileCode className="w-5 h-5 text-primary-500 mt-0.5 shrink-0" />
                            <div className="flex-1 min-w-0">
                                <p className="text-xs text-gray-500 mb-1">执行脚本</p>
                                <p className="text-sm font-medium text-gray-800">{script.name}</p>
                                <p className="text-xs text-gray-400 mt-1 font-mono truncate">
                                    {script.path}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* 项目信息 */}
                    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                        <div className="flex items-start gap-3">
                            <Server className="w-5 h-5 text-violet-500 mt-0.5 shrink-0" />
                            <div className="flex-1 min-w-0">
                                <p className="text-xs text-gray-500 mb-1">所属项目</p>
                                <p className="text-sm font-medium text-gray-800">{project.name}</p>
                            </div>
                        </div>
                    </div>

                    {/* 目标环境 */}
                    <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                        <div className="flex items-start gap-3">
                            <Cloud className="w-5 h-5 text-blue-500 mt-0.5 shrink-0" />
                            <div className="flex-1 min-w-0">
                                <p className="text-xs text-blue-600 mb-1">目标环境</p>
                                {targetApp ? (
                                    <>
                                        <p className="text-sm font-medium text-gray-800">
                                            {targetApp.name}
                                            {targetApp.suffix && (
                                                <span className="ml-2 px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">
                                                    {targetApp.suffix}
                                                </span>
                                            )}
                                        </p>
                                        <p className="text-xs text-gray-500 mt-1">
                                            App: {targetApp.appName}
                                            {targetApp.workspace && ` · Workspace: ${targetApp.workspace}`}
                                        </p>
                                    </>
                                ) : (
                                    <p className="text-sm font-medium text-gray-600">使用默认环境</p>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* 执行模式提示 */}
                    <div className={`p-3 rounded-lg ${executeMode === 'deploy' ? 'bg-primary-50 border border-primary-200' : 'bg-green-50 border border-green-200'}`}>
                        <div className="flex items-center gap-2 text-sm">
                            <ArrowRight className={`w-4 h-4 ${executeMode === 'deploy' ? 'text-primary-500' : 'text-green-500'}`} />
                            <span className={executeMode === 'deploy' ? 'text-primary-700' : 'text-green-700'}>
                                {executeMode === 'deploy'
                                    ? '将部署为持久化服务（web_server/asgi_app）'
                                    : '将作为一次性任务运行（local_entrypoint）'}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 bg-gray-50">
                    <Button variant="secondary" onClick={onClose}>
                        取消
                    </Button>
                    <Button
                        variant={actionColor}
                        onClick={() => {
                            onConfirm();
                            onClose();
                        }}
                    >
                        <Play className="w-4 h-4 mr-1.5" />
                        确认{actionLabel}
                    </Button>
                </div>
            </div>
        </div>
    );
}
