import { Github, Globe, ArrowLeft, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function AuthorInfo() {
  // 作者信息配置 - 可以直接修改这里的内容
  const authorInfo = {
    name: 'Modal Manager',
    avatar: null, // 如果有头像图片可以填写路径
    title: '开发者',
    bio: '热爱开源，专注于云计算和 AI 应用开发。Modal Manager 是一个用于管理 Modal 云平台项目的桌面应用，帮助开发者更高效地部署和管理云端应用。',
    github: 'https://github.com/your-username',
    website: 'https://your-website.com',
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* 页面头部 */}
      <div className="bg-white shadow-sm px-6 py-4">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">作者信息</h1>
            <p className="text-sm text-gray-500 mt-1">关于项目作者</p>
          </div>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto">
          {/* 作者卡片 */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            {/* 头部背景 */}
            <div className="h-32 bg-gradient-to-r from-primary-500 to-primary-600 relative">
              <div className="absolute -bottom-12 left-6">
                <div className="w-24 h-24 bg-white rounded-full border-4 border-white shadow-lg flex items-center justify-center">
                  {authorInfo.avatar ? (
                    <img
                      src={authorInfo.avatar}
                      alt={authorInfo.name}
                      className="w-full h-full rounded-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center">
                      <span className="text-3xl font-bold text-white">
                        {authorInfo.name.charAt(0).toUpperCase()}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* 作者信息 */}
            <div className="pt-16 px-6 pb-6">
              <h2 className="text-2xl font-bold text-gray-900">{authorInfo.name}</h2>
              <p className="text-primary-600 font-medium mt-1">{authorInfo.title}</p>

              {/* 个人介绍 */}
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  个人介绍
                </h3>
                <p className="text-gray-700 leading-relaxed">{authorInfo.bio}</p>
              </div>

              {/* 链接区域 */}
              <div className="mt-8 space-y-3">
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  相关链接
                </h3>

                {/* GitHub */}
                <a
                  href={authorInfo.github}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-4 p-4 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors group"
                >
                  <div className="w-12 h-12 bg-gray-900 rounded-lg flex items-center justify-center">
                    <Github className="w-6 h-6 text-white" />
                  </div>
                  <div className="flex-1">
                    <p className="font-semibold text-gray-900">GitHub</p>
                    <p className="text-sm text-gray-500 truncate">{authorInfo.github}</p>
                  </div>
                  <ExternalLink className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
                </a>

                {/* 个人网站 */}
                <a
                  href={authorInfo.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-4 p-4 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors group"
                >
                  <div className="w-12 h-12 bg-primary-500 rounded-lg flex items-center justify-center">
                    <Globe className="w-6 h-6 text-white" />
                  </div>
                  <div className="flex-1">
                    <p className="font-semibold text-gray-900">个人网站</p>
                    <p className="text-sm text-gray-500 truncate">{authorInfo.website}</p>
                  </div>
                  <ExternalLink className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
                </a>
              </div>
            </div>
          </div>

          {/* 项目信息 */}
          <div className="mt-6 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">关于 Modal Manager</h3>
            <p className="text-gray-700 leading-relaxed">
              Modal Manager 是一个现代化的桌面应用，专为 Modal 云平台用户设计。
              它提供了直观的界面来管理项目、部署应用、配置 AI 服务等功能，
              让云端开发变得更加简单高效。
            </p>
            <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
              <span>版本: 1.0.0</span>
              <span>•</span>
              <span>使用 Wails + React + TypeScript 构建</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

