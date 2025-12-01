import { Search, User, RefreshCw, Terminal } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useLogs } from '../context/LogContext';

export default function Topbar() {
  const { toggleVisibility, isVisible } = useLogs();

  return (
    <header className="bg-white shadow-sm px-4 py-2 flex items-center justify-between">
      {/* Search */}
      <div className="relative w-72">
        <input
          type="text"
          placeholder="搜索项目..."
          className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-transparent"
        />
        <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
      </div>

      {/* Right section */}
      <div className="flex items-center gap-3">
        <button 
          onClick={toggleVisibility}
          className={`flex items-center gap-1.5 px-2 py-1 rounded-md transition-colors text-sm ${isVisible ? 'bg-gray-800 text-white' : 'text-gray-500 hover:bg-gray-100'}`}
          title="系统日志"
        >
          <Terminal className="w-3.5 h-3.5" />
          <span>日志</span>
        </button>

        <button className="flex items-center gap-1.5 px-2 py-1 text-gray-500 hover:bg-gray-100 rounded-md transition-colors text-sm">
          <RefreshCw className="w-3.5 h-3.5" />
          <span>刷新</span>
        </button>

        <Link
          to="/author"
          className="flex items-center gap-2 pl-3 border-l border-gray-200 hover:opacity-80 transition-opacity cursor-pointer"
          title="作者信息"
        >
          <span className="text-xs text-gray-500">Modal Manager</span>
          <div className="w-7 h-7 bg-primary-500 rounded-full flex items-center justify-center">
            <User className="w-4 h-4 text-white" />
          </div>
        </Link>
      </div>
    </header>
  );
}
