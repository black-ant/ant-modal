import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  Save, 
  Code, 
  FileText, 
  Info, 
  Wand2, 
  ExternalLink, 
  Sparkles, 
  ChevronDown, 
  ChevronUp, 
  Copy
} from 'lucide-react';
import Button from '../components/Button';
import IDESelector from '../components/IDESelector';
import CodeSnippetsPanel from '../components/CodeSnippetsPanel';
import { IDEConfig } from '../types';
import { codeSnippetCategories } from '../data/codeSnippets';
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
  AnalyzeCode,
  GetProjects,
  GetScripts
} from '../../wailsjs/go/main/App';
import { main } from '../../wailsjs/go/models';

export default function ScriptEditorPage() {
  const { projectId, scriptPath } = useParams<{ projectId: string; scriptPath: string }>();
  const navigate = useNavigate();
  
  const [project, setProject] = useState<main.Project | null>(null);
  const [script, setScript] = useState<main.Script | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
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
    loadProjectAndScript();
    loadIDEs();
  }, [projectId, scriptPath]);

  const loadProjectAndScript = async () => {
    if (!projectId || !scriptPath) {
      setError('缺少项目ID或脚本路径');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError('');
    
    try {
      // 解码脚本路径
      const decodedScriptPath = decodeURIComponent(scriptPath);
      
      // 加载项目
      const projects = await GetProjects();
      const foundProject = projects?.find((p: main.Project) => p.id === projectId);
      
      if (!foundProject) {
        setError('项目不存在');
        setIsLoading(false);
        return;
      }
      
      setProject(foundProject);
      
      // 加载脚本列表
      const scripts = await GetScripts(foundProject.path);
      const foundScript = scripts?.find((s: main.Script) => s.path === decodedScriptPath);
      
      if (!foundScript) {
        setError('脚本不存在');
        setIsLoading(false);
        return;
      }
      
      setScript(foundScript);
      setName(foundScript.name);
      setDescription(foundScript.description || '');
      
      // 加载脚本内容
      const scriptContent = await ReadScriptContent(foundScript.fullPath);
      setContent(scriptContent);
    } catch (err: any) {
      setError(`加载失败: ${err.message || err}`);
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
    if (!project || !script) return;
    
    setIsSaving(true);
    setError('');
    
    try {
      // 保存脚本内容到文件
      await SaveScriptContent(script.fullPath, content);
      
      // 更新脚本元数据
      await UpdateScript(projectId!, script.path, name, description);
      
      // 返回项目面板
      navigate(`/project/${projectId}`);
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
    if (!script) return;
    
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

  // 插入代码片段到内容末尾
  const handleInsertSnippet = (code: string) => {
    // 在内容末尾添加代码片段（带换行）
    const separator = content.endsWith('\n') ? '\n' : '\n\n';
    setContent(content + separator + code + '\n');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mb-2"></div>
          <p className="text-sm text-gray-500">加载中...</p>
        </div>
      </div>
    );
  }

  if (error && !script) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-sm text-red-600 mb-4">{error}</p>
          <Button onClick={() => navigate(`/project/${projectId}`)}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回项目
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="absolute inset-0 flex flex-col bg-white">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 shrink-0">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <button
            onClick={() => navigate(`/project/${projectId}`)}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors shrink-0"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="p-2 bg-primary-100 rounded-lg shrink-0">
            <Code className="w-5 h-5 text-primary-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-bold text-gray-800">脚本编辑器</h2>
            <p className="text-xs text-gray-500 truncate">{script?.path}</p>
          </div>
        </div>
        
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleFormat}
            disabled={isFormatting || isLoading}
            className="flex items-center gap-1.5 px-3 py-2 text-sm bg-purple-50 hover:bg-purple-100 text-purple-600 rounded-lg transition-colors disabled:opacity-50"
            title="使用Black格式化代码"
          >
            <Wand2 className="w-4 h-4" />
            {isFormatting ? '格式化中...' : '格式化'}
          </button>
          <button
            onClick={() => setShowIDESelector(true)}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-2 text-sm bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-lg transition-colors disabled:opacity-50"
            title="在IDE中打开"
          >
            <ExternalLink className="w-4 h-4" />
            打开IDE
          </button>
          <button
            onClick={handleAIAnalyze}
            disabled={isAnalyzing || isLoading}
            className="flex items-center gap-1.5 px-3 py-2 text-sm bg-gradient-to-r from-purple-50 to-pink-50 hover:from-purple-100 hover:to-pink-100 text-purple-600 rounded-lg transition-colors disabled:opacity-50"
            title="AI代码分析"
          >
            <Sparkles className="w-4 h-4" />
            {isAnalyzing ? 'AI分析中...' : 'AI分析'}
          </button>
          <Button onClick={handleSave} disabled={isSaving || isLoading}>
            <Save className="w-4 h-4 mr-1.5" />
            {isSaving ? '保存中...' : '保存'}
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Code Snippets Panel */}
        <div className="w-80 border-r border-gray-200 overflow-y-auto">
          <CodeSnippetsPanel
            categories={codeSnippetCategories}
            onInsertSnippet={handleInsertSnippet}
          />
        </div>

        {/* Right: Editor Area */}
        <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-6xl mx-auto space-y-6">
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
                      value={script?.path || ''}
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
                        history: true,
                        foldGutter: true,
                        drawSelection: true,
                        dropCursor: true,
                        allowMultipleSelections: true,
                        indentOnInput: true,
                        syntaxHighlighting: true,
                        bracketMatching: true,
                        closeBrackets: true,
                        autocompletion: true,
                        rectangularSelection: true,
                        crosshairCursor: true,
                        highlightActiveLine: true,
                        highlightSelectionMatches: true,
                        closeBracketsKeymap: true,
                        defaultKeymap: true,
                        searchKeymap: true,
                        historyKeymap: true,
                        foldKeymap: true,
                        completionKeymap: true,
                        lintKeymap: true,
                      }}
                      placeholder="# 在这里编写你的 Python 代码"
                    />
                    <div className="absolute bottom-3 right-3 text-xs text-gray-400 bg-gray-800/80 px-2 py-1 rounded pointer-events-none">
                      {content.split('\n').length} 行
                    </div>
                  </div>
                  <p className="mt-2 text-xs text-gray-500 flex items-start gap-1">
                    <span>💡</span>
                    <span>从左侧选择代码片段可快速插入常用代码，支持自动缩进和语法高亮</span>
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
                      <div className="prose prose-sm max-w-none">
                        <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans">
                          {aiAnalysis}
                        </pre>
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
          </div>
        </div>

      {/* IDE Selector Modal */}
      {showIDESelector && script && (
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

