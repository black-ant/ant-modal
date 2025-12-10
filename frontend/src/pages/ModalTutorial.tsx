import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';
import { ChevronRight, ChevronDown, Book, Menu, X, Home, ArrowLeft, User } from 'lucide-react';
import { tutorialSections, type Tutorial } from '../data/modalTutorials';
import clsx from 'clsx';

export default function ModalTutorial() {
  const navigate = useNavigate();
  const [selectedTutorial, setSelectedTutorial] = useState<Tutorial>(
    tutorialSections[0]?.children[0]
  );
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['getting-started'])
  );
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
      }
      return newSet;
    });
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* 顶部标题栏 */}
      <div className="bg-white shadow-sm border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <button
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          {isSidebarOpen ? (
            <X className="w-5 h-5 text-gray-600" />
          ) : (
            <Menu className="w-5 h-5 text-gray-600" />
          )}
        </button>
        <div className="flex items-center gap-3">
          <Book className="w-6 h-6 text-primary-500" />
          <div>
            <h1 className="text-xl font-bold text-gray-900">Modal 使用教程</h1>
            <p className="text-sm text-gray-500">完整的 Modal 使用指南和最佳实践</p>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* 左侧文档列表 */}
        <div
          className={clsx(
            'bg-white border-r border-gray-200 transition-all duration-300 flex flex-col',
            isSidebarOpen ? 'w-80' : 'w-0'
          )}
        >
          {isSidebarOpen && (
            <>
              {/* 文档列表 - 可滚动区域 */}
              <nav className="flex-1 overflow-y-auto p-4 space-y-2">
                {tutorialSections.map((section) => (
                  <div key={section.id} className="space-y-1">
                    {/* 分类标题 */}
                    <button
                      onClick={() => toggleSection(section.id)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
                    >
                      {expandedSections.has(section.id) ? (
                        <ChevronDown className="w-4 h-4 flex-shrink-0" />
                      ) : (
                        <ChevronRight className="w-4 h-4 flex-shrink-0" />
                      )}
                      <span>{section.title}</span>
                    </button>

                    {/* 文档列表 */}
                    {expandedSections.has(section.id) && (
                      <div className="ml-4 space-y-0.5">
                        {section.children.map((tutorial) => (
                          <button
                            key={tutorial.id}
                            onClick={() => setSelectedTutorial(tutorial)}
                            className={clsx(
                              'w-full text-left px-3 py-2 text-sm rounded-lg transition-colors',
                              selectedTutorial?.id === tutorial.id
                                ? 'bg-primary-50 text-primary-700 font-medium'
                                : 'text-gray-600 hover:bg-gray-50'
                            )}
                          >
                            {tutorial.title}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </nav>

              {/* 底部导航按钮 */}
              <div className="border-t border-gray-200 p-4 space-y-2 flex-shrink-0">
                <button
                  onClick={() => navigate(-1)}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm text-gray-700 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>返回上一页</span>
                </button>
                <button
                  onClick={() => navigate('/')}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm bg-primary-500 text-white hover:bg-primary-600 rounded-lg transition-colors"
                >
                  <Home className="w-4 h-4" />
                  <span>返回首页</span>
                </button>
                
                {/* 分隔线 */}
                <div className="pt-2 border-t border-gray-200">
                  <button
                    onClick={() => navigate('/author')}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm text-primary-600 bg-primary-50 hover:bg-primary-100 rounded-lg transition-colors"
                  >
                    <User className="w-4 h-4" />
                    <span>关于作者</span>
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* 右侧文档内容 */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-8 py-8">
            {selectedTutorial ? (
              <article className="prose prose-slate max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({ className, children, ...props }: any) {
                      const match = /language-(\w+)/.exec(className || '');
                      const isInline = !match;
                      
                      return !isInline ? (
                        <SyntaxHighlighter
                          style={vscDarkPlus as any}
                          language={match[1]}
                          PreTag="div"
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      ) : (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      );
                    },
                  }}
                >
                  {selectedTutorial.content}
                </ReactMarkdown>
              </article>
            ) : (
              <div className="text-center py-12 text-gray-500">
                <Book className="w-16 h-16 mx-auto mb-4 opacity-20" />
                <p>请从左侧选择一个教程</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
