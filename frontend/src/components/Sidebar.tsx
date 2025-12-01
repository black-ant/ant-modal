import { Link, useLocation } from 'react-router-dom';
import { Package, Cloud, Bot, BookTemplate, Zap, Palette, Globe, History } from 'lucide-react';
import clsx from 'clsx';

const navItems = [
  {
    title: '项目管理',
    items: [
      { name: '我的项目', path: '/', icon: Package },
      { name: 'Modal Apps', path: '/apps', icon: Cloud },
    ],
  },
  {
    title: '工具',
    items: [
      { name: 'ComfyUI 工具箱', path: '/comfyui-toolbox', icon: Palette },
      { name: '快捷操作', path: '/quick-actions', icon: Zap },
      { name: '执行日志', path: '/execution-logs', icon: History },
      { name: 'AI 配置', path: '/ai-config', icon: Bot },
      { name: '模板库', path: '/templates', icon: BookTemplate },
    ],
  },
  {
    title: '配置',
    items: [
      { name: '全局变量', path: '/global-variables', icon: Globe },
    ],
  },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="w-52 bg-white shadow-md flex flex-col h-screen">
      {/* Logo - 固定在顶部 */}
      <div className="px-4 py-4 border-b border-gray-200 flex-shrink-0">
        <h2 className="text-base font-bold text-primary-500 flex items-center gap-2">
          <Package className="w-5 h-5" />
          Modal Manager
        </h2>
      </div>

      {/* Navigation - 可滚动区域 */}
      <nav className="flex-1 px-2 pt-4 space-y-4 overflow-y-auto">
        {navItems.map((section) => (
          <div key={section.title}>
            <h3 className="px-2 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">
              {section.title}
            </h3>
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;

                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={clsx(
                      'flex items-center rounded-md transition-colors text-sm px-2 py-1.5',
                      isActive ? 'bg-primary-500 text-white' : 'text-gray-600 hover:bg-gray-100'
                    )}
                  >
                    <Icon className="w-4 h-4 mr-2" />
                    <span className="font-medium">{item.name}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
    </aside>
  );
}
