import { useState, useEffect } from 'react';
import { X, Save, Code, FileText, Info, Wand2, ExternalLink, Sparkles, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';
import Button from './Button';
import IDESelector from './IDESelector';
import { IDEConfig } from '../types';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';
import CodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { vscodeDark } from '@uiw/codemirror-theme-vscode';
import { 
  ReadScriptContent, 
  SaveScriptContent, 
  UpdateScript, 
  FormatPythonCode,
  DetectInstalledIDEs,
  OpenInIDE,
  AnalyzeCode
} from '../../wailsjs/go/main/App';

interface ScriptEditorProps {
  projectId: string;
  script: {
    name: string;
    path: string;
    fullPath: string;
    description?: string;
  };
  onClose: () => void;
  onSave: () => void;
}

const CodeRenderer = ({ node, inline, className, children, ...props }: any) => {
  const match = /language-(\w+)/.exec(className || '');
  const [copied, setCopied] = useState(false);

  if (inline || !match) {
    return (
      <code className={`${className} bg-gray-100 px-1 py-0.5 rounded text-sm text-pink-500 font-mono`} {...props}>
        {children}
      </code>
    );
  }

  const language = match[1];
  const value = String(children).replace(/\n$/, '');

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group rounded-lg overflow-hidden my-4 shadow-lg border border-gray-700">
      <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 p-1.5 bg-gray-700/80 text-white hover:bg-gray-600 rounded-md transition-colors backdrop-blur-sm"
          title="复制代码"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
          {copied && <span className="text-xs text-green-400 font-sans">已复制</span>}
        </button>
      </div>
      <div className="bg-[#1e1e1e] px-4 py-1.5 text-xs text-gray-400 border-b border-gray-700 font-mono flex items-center gap-2">
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-red-500/20"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/20"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-green-500/20"></div>
        </div>
        <span className="ml-2">{language}</span>
      </div>
      <SyntaxHighlighter
        style={vscDarkPlus}
        language={language}
        PreTag="div"
        customStyle={{ margin: 0, borderTopLeftRadius: 0, borderTopRightRadius: 0 }}
        {...props}
      >
        {value}
      </SyntaxHighlighter>
    </div>
  );
};

export default function ScriptEditor({ projectId, script, onClose, onSave }: ScriptEditorProps) {
  const [name, setName] = useState(script.name);
  const [description, setDescription] = useState(script.description || '');
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isFormatting, setIsFormatting] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const [showIDESelector, setShowIDESelector] = useState(false);
  const [ides, setIdes] = useState<IDEConfig[]>([]);
  const [aiAnalysis, setAiAnalysis] = useState('');
  const [showAIPanel, setShowAIPanel] = useState(false);

  useEffect(() => {
    loadScriptContent();
    loadIDEs();
  }, [script.fullPath]);

  const loadScriptContent = async () => {
    setIsLoading(true);
    setError('');
    try {
      const scriptContent = await ReadScriptContent(script.fullPath);
      setContent(scriptContent);
    } catch (err: any) {
      setError(`读取脚本失败: ${err.message || err}`);
      setContent('');
    } finally {
      setIsLoading(false);
    }
  };

  const loadIDEs = async () => {
    try {
      const detectedIDEs = await DetectInstalledIDEs();
      setIdes(detectedIDEs || []);
    } catch (err) {
      console.error('检测IDE失败:', err);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError('');
    
    try {
      // 保存脚本内容到文件
      await SaveScriptContent(script.fullPath, content);
      
      // 更新脚本元数据
      await UpdateScript(projectId, script.path, name, description);
      
      onSave();
      onClose();
    } catch (err: any) {
      setError(`保存失败: ${err.message || err}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleFormat = async () => {
    setIsFormatting(true);
    setError('');
    
    try {
      const formatted = await FormatPythonCode(content);
      setContent(formatted);
    } catch (err: any) {
      setError(`格式化失败: ${err.message || err}`);
    } finally {
      setIsFormatting(false);
    }
  };

  const handleOpenIDE = async (ide: IDEConfig) => {
    try {
      await OpenInIDE(ide.path, script.fullPath);
      setShowIDESelector(false);
    } catch (err: any) {
      setError(`打开IDE失败: ${err.message || err}`);
    }
  };

  const handleAIAnalyze = async () => {
    setIsAnalyzing(true);
    setError('');
    setShowAIPanel(true);
    setAiAnalysis('');
    
    try {
      const result = await AnalyzeCode(content, '');
      setAiAnalysis(result);
    } catch (err: any) {
      setError(`AI分析失败: ${err.message || err}`);
      setAiAnalysis('分析失败，请检查AI配置。');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const copyAIAnalysis = () => {
    navigator.clipboard.writeText(aiAnalysis);
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div 
        className="w-full max-w-6xl max-h-[90vh] flex flex-col bg-white rounded-lg shadow-2xl animate-slide-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-100 rounded-lg">
              <Code className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-800">脚本编辑器</h2>
              <p className="text-xs text-gray-500">{script.path}</p>
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
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* 基本信息 */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
              <Info className="w-4 h-4 text-primary-500" />
              基本信息
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  脚本名称
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  placeholder="输入脚本名称"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  文件路径
                </label>
                <input
                  type="text"
                  value={script.path}
                  disabled
                  className="w-full px-4 py-2.5 text-sm border border-gray-200 rounded-lg bg-gray-50 text-gray-500 cursor-not-allowed font-mono"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                脚本描述
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                className="w-full px-4 py-3 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all resize-none"
                placeholder="描述这个脚本的功能..."
              />
            </div>
          </div>

          {/* Python代码编辑器 */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                <FileText className="w-4 h-4 text-primary-500" />
                Python 代码
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleFormat}
                  disabled={isFormatting || isLoading}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-purple-50 hover:bg-purple-100 text-purple-600 rounded-lg transition-colors disabled:opacity-50"
                  title="使用Black格式化代码"
                >
                  <Wand2 className="w-3.5 h-3.5" />
                  {isFormatting ? '格式化中...' : '格式化'}
                </button>
                <button
                  onClick={() => setShowIDESelector(true)}
                  disabled={isLoading}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-lg transition-colors disabled:opacity-50"
                  title="在IDE中打开"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  打开IDE
                </button>
                <button
                  onClick={handleAIAnalyze}
                  disabled={isAnalyzing || isLoading}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-gradient-to-r from-purple-50 to-pink-50 hover:from-purple-100 hover:to-pink-100 text-purple-600 rounded-lg transition-colors disabled:opacity-50"
                  title="AI代码分析"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  {isAnalyzing ? 'AI分析中...' : 'AI分析'}
                </button>
              </div>
            </div>
            
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                代码内容
              </label>
              {isLoading ? (
                <div className="w-full h-96 flex items-center justify-center bg-gray-50 rounded-lg border border-gray-300">
                  <div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-2"></div>
                    <p className="text-sm text-gray-500">加载中...</p>
                  </div>
                </div>
              ) : (
                <div className="relative border border-gray-700 rounded-lg overflow-hidden shadow-lg">
                  <CodeMirror
                    value={content}
                    height="500px"
                    theme={vscodeDark}
                    extensions={[python()]}
                    onChange={(value) => setContent(value)}
                    style={{
                      fontSize: '14px',
                    }}
                    basicSetup={{
                      lineNumbers: true,
                      highlightActiveLineGutter: true,
                      highlightSpecialChars: true,
                      foldGutter: true,
                      drawSelection: true,
                      dropCursor: true,
                      allowMultipleSelections: true,
                      indentOnInput: true,
                      bracketMatching: true,
                      closeBrackets: true,
                      autocompletion: true,
                      rectangularSelection: true,
                      crosshairCursor: true,
                      highlightActiveLine: true,
                      highlightSelectionMatches: true,
                      closeBracketsKeymap: true,
                      searchKeymap: true,
                      foldKeymap: true,
                      completionKeymap: true,
                      lintKeymap: true,
                    }}
                  />
                  <div className="absolute bottom-2 right-2 text-xs text-gray-400 bg-gray-800/90 px-2 py-1 rounded backdrop-blur-sm pointer-events-none">
                    {content.split('\n').length} 行
                  </div>
                </div>
              )}
              <p className="mt-2 text-xs text-gray-500 flex items-start gap-1">
                <span>💡</span>
                <span>编辑完成后点击保存按钮，将直接覆盖原文件内容</span>
              </p>
            </div>
          </div>

          {/* AI分析面板 */}
          {showAIPanel && (
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <button
                onClick={() => setShowAIPanel(!showAIPanel)}
                className="w-full flex items-center justify-between p-3 bg-gradient-to-r from-purple-50 to-pink-50 hover:from-purple-100 hover:to-pink-100 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-600" />
                  <span className="text-sm font-semibold text-gray-700">AI代码分析</span>
                </div>
                <div className="flex items-center gap-2">
                  {aiAnalysis && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        copyAIAnalysis();
                      }}
                      className="p-1 hover:bg-white/50 rounded transition-colors"
                      title="复制分析结果"
                    >
                      <Copy className="w-4 h-4 text-purple-600" />
                    </button>
                  )}
                  {showAIPanel ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </div>
              </button>
              
              <div className="p-4 bg-white max-h-96 overflow-y-auto">
                {isAnalyzing ? (
                  <div className="text-center py-8">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mb-2"></div>
                    <p className="text-sm text-gray-500">AI正在分析代码...</p>
                  </div>
                ) : aiAnalysis ? (
                  <div className="prose prose-sm max-w-none p-1">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        code: CodeRenderer
                      }}
                    >
                      {aiAnalysis}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 text-center py-4">
                    点击上方"AI分析"按钮开始分析代码
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-gray-200 bg-gray-50 shrink-0">
          <p className="text-xs text-gray-500">
            修改后请点击保存按钮
          </p>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={onClose} disabled={isSaving}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={isSaving || isLoading}>
              <Save className="w-4 h-4 mr-1.5" />
              {isSaving ? '保存中...' : '保存更改'}
            </Button>
          </div>
        </div>
      </div>

      {/* IDE Selector Modal */}
      {showIDESelector && (
        <IDESelector
          ides={ides}
          filePath={script.fullPath}
          onClose={() => setShowIDESelector(false)}
          onSelect={handleOpenIDE}
        />
      )}
    </div>
  );
}
