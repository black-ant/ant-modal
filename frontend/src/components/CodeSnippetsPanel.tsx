import { useState } from 'react';
import { Search, ChevronDown, ChevronRight, Copy, Check } from 'lucide-react';
import { CodeSnippetCategory, CodeSnippet } from '../types';
import clsx from 'clsx';

interface CodeSnippetsPanelProps {
  categories: CodeSnippetCategory[];
  onInsertSnippet: (code: string) => void;
}

export default function CodeSnippetsPanel({ categories, onInsertSnippet }: CodeSnippetsPanelProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['modal-basics']));
  const [copiedSnippetId, setCopiedSnippetId] = useState<string | null>(null);

  const toggleCategory = (categoryId: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(categoryId)) {
      newExpanded.delete(categoryId);
    } else {
      newExpanded.add(categoryId);
    }
    setExpandedCategories(newExpanded);
  };

  const handleInsertSnippet = (snippet: CodeSnippet) => {
    onInsertSnippet(snippet.code);
    
    // 显示复制反馈
    setCopiedSnippetId(snippet.id);
    setTimeout(() => setCopiedSnippetId(null), 2000);
  };

  const filteredCategories = categories.map(category => ({
    ...category,
    snippets: category.snippets.filter(snippet =>
      searchQuery === '' ||
      snippet.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      snippet.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      snippet.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
    ),
  })).filter(category => category.snippets.length > 0);

  return (
    <div className="h-full flex flex-col bg-gray-50 border-r border-gray-200">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-white shrink-0">
        <h2 className="text-sm font-bold text-gray-800 mb-3">代码片段库</h2>
        
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索代码片段..."
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Categories and Snippets */}
      <div className="flex-1 overflow-y-auto p-2">
        {filteredCategories.length === 0 ? (
          <div className="text-center py-8 text-gray-400 text-sm">
            未找到匹配的代码片段
          </div>
        ) : (
          <div className="space-y-2">
            {filteredCategories.map((category) => (
              <div key={category.id} className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                {/* Category Header */}
                <button
                  onClick={() => toggleCategory(category.id)}
                  className="w-full flex items-center gap-2 p-3 hover:bg-gray-50 transition-colors"
                >
                  {expandedCategories.has(category.id) ? (
                    <ChevronDown className="w-4 h-4 text-gray-500 shrink-0" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-500 shrink-0" />
                  )}
                  <span className="text-lg shrink-0">{category.icon}</span>
                  <div className="flex-1 text-left min-w-0">
                    <div className="text-sm font-semibold text-gray-800">{category.name}</div>
                    <div className="text-xs text-gray-500 truncate">{category.description}</div>
                  </div>
                  <span className="text-xs text-gray-400 shrink-0">
                    {category.snippets.length}
                  </span>
                </button>

                {/* Snippets */}
                {expandedCategories.has(category.id) && (
                  <div className="border-t border-gray-200">
                    {category.snippets.map((snippet) => (
                      <div
                        key={snippet.id}
                        className="border-b border-gray-100 last:border-b-0 hover:bg-gray-50 transition-colors"
                      >
                        <div className="p-3">
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <div className="flex-1 min-w-0">
                              <h4 className="text-sm font-medium text-gray-800 mb-1">
                                {snippet.title}
                              </h4>
                              <p className="text-xs text-gray-500 line-clamp-2">
                                {snippet.description}
                              </p>
                            </div>
                            <button
                              onClick={() => handleInsertSnippet(snippet)}
                              className={clsx(
                                'shrink-0 p-1.5 rounded transition-colors',
                                copiedSnippetId === snippet.id
                                  ? 'bg-green-100 text-green-600'
                                  : 'bg-primary-100 text-primary-600 hover:bg-primary-200'
                              )}
                              title="插入代码"
                            >
                              {copiedSnippetId === snippet.id ? (
                                <Check className="w-4 h-4" />
                              ) : (
                                <Copy className="w-4 h-4" />
                              )}
                            </button>
                          </div>
                          
                          {/* Tags */}
                          {snippet.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {snippet.tags.map((tag, idx) => (
                                <span
                                  key={idx}
                                  className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
                                >
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

