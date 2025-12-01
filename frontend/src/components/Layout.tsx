import { ReactNode } from 'react';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import LogPanel from './LogPanel';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* 左侧侧边栏 - 独立滚动 */}
      <Sidebar />
      
      {/* 右侧主内容区 - 独立滚动 */}
      <div className="flex flex-1 flex-col h-screen overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-4">{children}</main>
        <LogPanel />
      </div>
    </div>
  );
}
