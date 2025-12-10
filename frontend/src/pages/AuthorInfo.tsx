import { Github, Globe, ArrowLeft, ExternalLink, BookOpen } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function AuthorInfo() {
  // 作者信息配置 - 可以直接修改这里的内容
  const authorInfo = {
    name: '志字辈小蚂蚁',
    avatar: 'data:image/png;base64,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', // 使用 base64 编码的头像
    title: '程序员奶爸',
    bio: '努力赚奶币中 💪\n\n热爱开源，专注于云计算和 AI 应用开发。Modal Manager 是一个用于管理 Modal 云平台项目的桌面应用，帮助开发者更高效地部署和管理云端应用。',
    github: 'https://github.com/black-ant',
    juejin: 'https://juejin.cn/user/3790771822007822',
    website: 'https://github.com/black-ant',
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
                  关注作者
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
                    <p className="text-sm text-gray-500">@black-ant</p>
                  </div>
                  <ExternalLink className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
                </a>

                {/* 掘金 */}
                <a
                  href={authorInfo.juejin}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-4 p-4 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors group"
                >
                  <div className="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center">
                    <BookOpen className="w-6 h-6 text-white" />
                  </div>
                  <div className="flex-1">
                    <p className="font-semibold text-gray-900">掘金</p>
                    <p className="text-sm text-gray-500">技术文章分享</p>
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

