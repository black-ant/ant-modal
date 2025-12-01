import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, FileCode, Plus, BookTemplate, ChevronRight, ArrowLeft, Zap, Clock, AlertCircle, Upload } from 'lucide-react';
import clsx from 'clsx';
import Button from './Button';
import { scriptTemplates, ScriptTemplate, parseTemplateVariables, replaceTemplateVariables, TemplateVariable } from '../data/scriptTemplates';
import { SelectModelFile, GetProjectVariables } from '../../wailsjs/go/main/App';

interface CreateScriptDialogProps {
  projectId: string;
  projectName: string;
  onClose: () => void;
  onCreate: (name: string, fileName: string, description: string, template: string) => Promise<void>;
}

export default function CreateScriptDialog({
  projectId,
  projectName,
  onClose,
  onCreate,
}: CreateScriptDialogProps) {
  const navigate = useNavigate();
  
  // 创建模式：'blank' 空白创建, 'template' 从模板创建
  const [mode, setMode] = useState<'blank' | 'template'>('blank');
  
  // 空白创建状态
  const [name, setName] = useState('');
  const [fileName, setFileName] = useState('');
  const [description, setDescription] = useState('');
  const [template, setTemplate] = useState('blank');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');
  
  // 模板创建状态
  const [selectedTemplate, setSelectedTemplate] = useState<ScriptTemplate | null>(null);
  
  // A/B 模式选择状态
  const [createMode, setCreateMode] = useState<'A' | 'B' | null>(null);
  
  // A模式：变量值
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});
  const [variableErrors, setVariableErrors] = useState<Record<string, string>>({});
  
  // 解析的变量列表（只包含 script scope，需要用户填写）
  const [parsedVariables, setParsedVariables] = useState<TemplateVariable[]>([]);
  // 所有变量（包含 project scope，用于最终替换）
  const [allVariables, setAllVariables] = useState<TemplateVariable[]>([]);
  // 项目变量
  const [projectVars, setProjectVars] = useState<Record<string, string>>({});

  // 当选择模板后，解析变量并加载项目变量
  useEffect(() => {
    if (selectedTemplate) {
      // 优先使用模板定义的 variables（包含 inputType, options 等属性）
      const vars = selectedTemplate.variables.length > 0 
        ? selectedTemplate.variables 
        : parseTemplateVariables(selectedTemplate.content);
      
      setAllVariables(vars);
      
      // 只显示 script scope 的变量（过滤掉 project 和 global scope）
      const scriptVars = vars.filter(v => !v.scope || v.scope === 'script');
      setParsedVariables(scriptVars);
      
      // 初始化变量默认值（只针对 script scope）
      const initial: Record<string, string> = {};
      scriptVars.forEach(v => {
        initial[v.name] = v.defaultValue;
      });
      setVariableValues(initial);
      
      // 加载项目变量
      GetProjectVariables(projectId).then(vars => {
        setProjectVars(vars || {});
      }).catch(err => {
        console.error('加载项目变量失败:', err);
      });
    }
  }, [selectedTemplate, projectId]);

  // 根据中文名称自动生成文件名
  const handleNameChange = (value: string) => {
    setName(value);
    if (!fileName) {
      const autoFileName = value
        .toLowerCase()
        .replace(/\s+/g, '_')
        .replace(/[^a-z0-9_\u4e00-\u9fa5]/g, '');
      setFileName(autoFileName);
    }
  };

  // 空白创建
  const handleCreate = async () => {
    if (!name.trim()) {
      setError('请输入脚本名称');
      return;
    }
    if (!fileName.trim()) {
      setError('请输入文件名');
      return;
    }

    setError('');
    setIsCreating(true);

    console.log('[CreateScript] 开始创建空白脚本:', { 
      projectId, 
      name: name.trim(), 
      fileName: fileName.trim(), 
      template 
    });

    try {
      await onCreate(name.trim(), fileName.trim(), description.trim(), template);
      
      const scriptFileName = fileName.trim().endsWith('.py') ? fileName.trim() : `${fileName.trim()}.py`;
      const encodedScriptPath = encodeURIComponent(scriptFileName);
      
      console.log('[CreateScript] 脚本创建成功:', scriptFileName);
      navigate(`/script-editor/${projectId}/${encodedScriptPath}`);
      onClose();
    } catch (err: any) {
      console.error('[CreateScript] 创建失败:', err);
      // 提取详细错误信息：优先使用字符串形式的错误
      const errorMessage = typeof err === 'string' ? err : (err.message || err.toString() || '创建失败');
      setError(errorMessage);
    } finally {
      setIsCreating(false);
    }
  };

  // 选择模板 - 进入模式选择
  const handleSelectTemplate = (tmpl: ScriptTemplate) => {
    console.log('[CreateScript] 选择模板:', { id: tmpl.id, name: tmpl.name, variableCount: tmpl.variables.length });
    setSelectedTemplate(tmpl);
    setFileName(tmpl.id.replace(/-/g, '_'));
    setName(tmpl.name);
    setDescription(tmpl.description);
    setCreateMode(null); // 重置模式选择
    setVariableErrors({});
    setError('');
  };

  // 更新变量值
  const handleVariableChange = (varName: string, value: string) => {
    setVariableValues(prev => ({ ...prev, [varName]: value }));
    // 清除该变量的错误
    if (variableErrors[varName]) {
      setVariableErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[varName];
        return newErrors;
      });
    }
  };

  // 验证变量表单
  const validateVariables = (): boolean => {
    const errors: Record<string, string> = {};
    
    parsedVariables.forEach(v => {
      if (v.required && !variableValues[v.name]?.trim()) {
        errors[v.name] = `${v.label} 为必填项`;
      }
    });
    
    setVariableErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // 创建模板脚本
  const handleCreateTemplateScript = async () => {
    if (!selectedTemplate || !createMode) return;

    if (!name.trim()) {
      setError('请输入脚本名称');
      return;
    }
    if (!fileName.trim()) {
      setError('请输入文件名');
      return;
    }

    // A模式需要验证变量
    if (createMode === 'A' && !validateVariables()) {
      console.warn('[CreateScript] 变量验证失败');
      return;
    }

    setIsCreating(true);
    setError('');

    console.log('[CreateScript] 开始从模板创建脚本:', { 
      projectId,
      templateId: selectedTemplate.id,
      templateName: selectedTemplate.name,
      name: name.trim(), 
      fileName: fileName.trim(),
      createMode,
      variableCount: parsedVariables.length
    });

    try {
      const scriptFileName = fileName.trim().endsWith('.py') ? fileName.trim() : `${fileName.trim()}.py`;
      
      let finalContent: string;
      let finalDescription: string;
      
      if (createMode === 'A') {
        // A模式：替换变量，生成独立脚本
        // 合并项目变量和用户输入的变量（用户输入优先）
        const mergedValues = { ...projectVars, ...variableValues };
        console.log('[CreateScript] A模式: 替换变量值:', mergedValues);
        finalContent = replaceTemplateVariables(selectedTemplate.content, mergedValues);
        finalDescription = description.trim() || selectedTemplate.description;
      } else {
        // B模式：保留变量占位符
        console.log('[CreateScript] B模式: 保留模板变量');
        finalContent = selectedTemplate.content;
        finalDescription = `[模板脚本] ${description.trim() || selectedTemplate.description}`;
      }
      
      console.log('[CreateScript] 调用后端创建脚本, 内容长度:', finalContent.length);
      
      await onCreate(
        name.trim(),
        scriptFileName,
        finalDescription,
        finalContent
      );

      console.log('[CreateScript] 模板脚本创建成功:', scriptFileName);
      // 创建成功后直接关闭
      onClose();
    } catch (err: any) {
      console.error('[CreateScript] 模板脚本创建失败:', err);
      // 提取详细错误信息：优先使用字符串形式的错误
      const errorMessage = typeof err === 'string' ? err : (err.message || err.toString() || '创建失败');
      setError(errorMessage);
    } finally {
      setIsCreating(false);
    }
  };

  // 返回模板列表
  const handleBackToTemplateList = () => {
    setSelectedTemplate(null);
    setCreateMode(null);
    setError('');
    setVariableErrors({});
  };

  // 返回模式选择
  const handleBackToModeSelect = () => {
    setCreateMode(null);
    setError('');
    setVariableErrors({});
  };

  // ========== 显示模板配置页面（选择模板后） ==========
  if (selectedTemplate) {
    return (
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        onClick={handleBackToTemplateList}
      >
        <div
          className="w-full max-w-xl bg-white rounded-lg shadow-2xl animate-slide-in max-h-[90vh] overflow-hidden flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 shrink-0">
            <div className="flex items-center gap-3">
              <button
                onClick={createMode ? handleBackToModeSelect : handleBackToTemplateList}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div className="p-2 bg-amber-100 rounded-lg">
                <BookTemplate className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <h2 className="text-base font-bold text-gray-800">从模板创建</h2>
                <p className="text-xs text-gray-500">{selectedTemplate.name}</p>
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
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* 模板信息预览 */}
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <p className="text-xs text-amber-700 leading-relaxed">
                {selectedTemplate.description}
              </p>
              <div className="flex flex-wrap gap-1 mt-2">
                {selectedTemplate.tags.slice(0, 4).map(tag => (
                  <span key={tag} className="px-1.5 py-0.5 bg-amber-100 text-amber-600 text-xs rounded">
                    {tag}
                  </span>
                ))}
                {parsedVariables.length > 0 && (
                  <span className="px-1.5 py-0.5 bg-white border border-amber-200 text-amber-600 text-xs rounded">
                    {parsedVariables.length} 个参数
                  </span>
                )}
              </div>
            </div>

            {/* ========== A/B 模式选择 ========== */}
            {!createMode && (
              <div className="space-y-3">
                <label className="block text-sm font-medium text-gray-700">
                  选择创建方式
                </label>
                
                {/* A模式：立即配置 */}
                <div
                  onClick={() => setCreateMode('A')}
                  className="p-4 border-2 border-gray-200 rounded-lg hover:border-emerald-400 hover:bg-emerald-50/50 cursor-pointer transition-all group"
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-emerald-100 rounded-lg group-hover:bg-emerald-200 transition-colors">
                      <Zap className="w-5 h-5 text-emerald-600" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-semibold text-gray-800 group-hover:text-emerald-700">
                          A. 立即配置
                        </h4>
                        <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-600 text-xs rounded">
                          推荐
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                        现在填写所有变量，创建后生成<strong>独立脚本</strong>。部署时无需再次配置，可直接执行。
                      </p>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-emerald-500 shrink-0" />
                  </div>
                </div>

                {/* B模式：部署时配置 */}
                <div
                  onClick={() => setCreateMode('B')}
                  className="p-4 border-2 border-gray-200 rounded-lg hover:border-blue-400 hover:bg-blue-50/50 cursor-pointer transition-all group"
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-blue-100 rounded-lg group-hover:bg-blue-200 transition-colors">
                      <Clock className="w-5 h-5 text-blue-600" />
                    </div>
                    <div className="flex-1">
                      <h4 className="text-sm font-semibold text-gray-800 group-hover:text-blue-700">
                        B. 部署时配置
                      </h4>
                      <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                        保留模板变量，创建后生成<strong>模板脚本</strong>。每次部署时弹窗填写变量，适合多次使用不同配置。
                      </p>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-blue-500 shrink-0" />
                  </div>
                </div>
              </div>
            )}

            {/* ========== 选择模式后显示配置表单 ========== */}
            {createMode && (
              <>
                {/* 模式标识 */}
                <div className={clsx(
                  'flex items-center gap-2 p-2 rounded-lg',
                  createMode === 'A' ? 'bg-emerald-50 border border-emerald-200' : 'bg-blue-50 border border-blue-200'
                )}>
                  {createMode === 'A' ? (
                    <>
                      <Zap className="w-4 h-4 text-emerald-600" />
                      <span className="text-xs font-medium text-emerald-700">A. 立即配置 - 创建独立脚本</span>
                    </>
                  ) : (
                    <>
                      <Clock className="w-4 h-4 text-blue-600" />
                      <span className="text-xs font-medium text-blue-700">B. 部署时配置 - 创建模板脚本</span>
                    </>
                  )}
                </div>

                {/* 脚本名称 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    脚本名称 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="例如：ComfyUI 自定义节点安装"
                    className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                    disabled={isCreating}
                  />
                </div>

                {/* 文件名 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    文件名 <span className="text-red-500">*</span>
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={fileName}
                      onChange={(e) => setFileName(e.target.value)}
                      placeholder="add_custom_node"
                      className="flex-1 px-4 py-2.5 text-sm font-mono border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                      disabled={isCreating}
                    />
                    <div className="flex items-center px-3 bg-gray-100 text-gray-600 text-sm rounded-lg border border-gray-300">
                      .py
                    </div>
                  </div>
                </div>

                {/* 描述 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">描述</label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="简要描述这个脚本的功能..."
                    rows={2}
                    className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all resize-none"
                    disabled={isCreating}
                  />
                </div>

                {/* ========== A模式：变量配置表单 ========== */}
                {createMode === 'A' && (
                  <div className="space-y-3 pt-2 border-t border-gray-200">
                    {/* 项目变量提示 */}
                    {allVariables.some(v => v.scope === 'project') && (
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-2.5 text-xs text-blue-700">
                        <span className="font-medium">💡 项目变量自动填充：</span>
                        {allVariables.filter(v => v.scope === 'project').map(v => (
                          <span key={v.name} className="ml-2 px-1.5 py-0.5 bg-blue-100 rounded">
                            {v.label} = {projectVars[v.name] || <span className="text-blue-400">未配置</span>}
                          </span>
                        ))}
                      </div>
                    )}
                    
                    {parsedVariables.length > 0 && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-700">变量配置</span>
                        <span className="text-xs text-gray-500">({parsedVariables.length} 个参数)</span>
                      </div>
                    )}
                    
                    {parsedVariables.map((variable) => (
                      <div key={variable.name}>
                        <label className="block text-sm font-medium text-gray-700 mb-1.5">
                          {variable.label}
                          {variable.required && <span className="text-red-500 ml-1">*</span>}
                        </label>
                        {/* 文件选择类型 */}
                        {variable.inputType === 'file' ? (
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={variableValues[variable.name] || ''}
                              onChange={(e) => handleVariableChange(variable.name, e.target.value)}
                              placeholder="点击右侧按钮选择文件"
                              className={clsx(
                                'flex-1 px-3 py-2 text-sm border rounded-lg transition-all',
                                'focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent',
                                variableErrors[variable.name]
                                  ? 'border-red-300 bg-red-50'
                                  : 'border-gray-300 hover:border-gray-400'
                              )}
                              disabled={isCreating}
                            />
                            <button
                              type="button"
                              onClick={async () => {
                                try {
                                  const filePath = await SelectModelFile();
                                  if (filePath) {
                                    // Windows 路径转换：反斜杠转正斜杠，避免 Python 转义问题
                                    const normalizedPath = filePath.replace(/\\/g, '/');
                                    handleVariableChange(variable.name, normalizedPath);
                                  }
                                } catch (err) {
                                  console.error('选择文件失败:', err);
                                }
                              }}
                              disabled={isCreating}
                              className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50"
                            >
                              <Upload className="w-4 h-4" />
                              选择文件
                            </button>
                          </div>
                        ) : variable.options ? (
                          /* 下拉选择类型 */
                          <select
                            value={variableValues[variable.name] || variable.defaultValue}
                            onChange={(e) => handleVariableChange(variable.name, e.target.value)}
                            className={clsx(
                              'w-full px-3 py-2 text-sm border rounded-lg transition-all',
                              'focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent',
                              variableErrors[variable.name]
                                ? 'border-red-300 bg-red-50'
                                : 'border-gray-300 hover:border-gray-400'
                            )}
                            disabled={isCreating}
                          >
                            {variable.options.map((option) => (
                              <option key={option} value={option}>{option}</option>
                            ))}
                          </select>
                        ) : (
                          /* 文本输入类型 */
                          <input
                            type="text"
                            value={variableValues[variable.name] || ''}
                            onChange={(e) => handleVariableChange(variable.name, e.target.value)}
                            placeholder={variable.defaultValue || `请输入 ${variable.label}`}
                            className={clsx(
                              'w-full px-3 py-2 text-sm border rounded-lg transition-all',
                              'focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent',
                              variableErrors[variable.name]
                                ? 'border-red-300 bg-red-50'
                                : 'border-gray-300 hover:border-gray-400'
                            )}
                            disabled={isCreating}
                          />
                        )}
                        {variableErrors[variable.name] && (
                          <p className="mt-1 text-xs text-red-500 flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" />
                            {variableErrors[variable.name]}
                          </p>
                        )}
                        {variable.defaultValue && !variableErrors[variable.name] && !variable.options && variable.inputType !== 'file' && (
                          <p className="mt-1 text-xs text-gray-400">
                            默认值: {variable.defaultValue}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* B模式：提示信息 */}
                {createMode === 'B' && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <p className="text-xs text-blue-700 leading-relaxed">
                      脚本将保留 {parsedVariables.length} 个模板变量。每次点击「部署」时会弹出配置窗口，填写变量后再执行。
                    </p>
                  </div>
                )}

                {/* 错误提示 */}
                {error && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-600">{error}</p>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 bg-gray-50 shrink-0">
            {!createMode ? (
              <Button variant="secondary" onClick={handleBackToTemplateList} disabled={isCreating}>
                返回
              </Button>
            ) : (
              <>
                <Button variant="secondary" onClick={handleBackToModeSelect} disabled={isCreating}>
                  返回
                </Button>
                <Button 
                  onClick={handleCreateTemplateScript} 
                  disabled={isCreating}
                  className={createMode === 'A' ? 'bg-emerald-500 hover:bg-emerald-600' : ''}
                >
                  <BookTemplate className="w-4 h-4 mr-1.5" />
                  {isCreating ? '创建中...' : '创建脚本'}
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg bg-white rounded-lg shadow-2xl animate-slide-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-100 rounded-lg">
              <Plus className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-800">新建脚本</h2>
              <p className="text-xs text-gray-500">为 {projectName} 创建新的脚本文件</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mode Tabs */}
        <div className="flex border-b border-gray-200">
          <button
            onClick={() => setMode('blank')}
            className={clsx(
              'flex-1 px-4 py-3 text-sm font-medium transition-colors border-b-2',
              mode === 'blank'
                ? 'text-primary-600 border-primary-500 bg-primary-50/50'
                : 'text-gray-500 border-transparent hover:text-gray-700 hover:bg-gray-50'
            )}
          >
            <FileCode className="w-4 h-4 inline mr-2" />
            空白脚本
          </button>
          <button
            onClick={() => setMode('template')}
            className={clsx(
              'flex-1 px-4 py-3 text-sm font-medium transition-colors border-b-2',
              mode === 'template'
                ? 'text-primary-600 border-primary-500 bg-primary-50/50'
                : 'text-gray-500 border-transparent hover:text-gray-700 hover:bg-gray-50'
            )}
          >
            <BookTemplate className="w-4 h-4 inline mr-2" />
            从模板创建
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {mode === 'blank' ? (
            // ========== 空白创建模式 ==========
            <div className="space-y-4">
              {/* 脚本名称 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  脚本名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => handleNameChange(e.target.value)}
                  placeholder="例如：部署生产环境"
                  className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  disabled={isCreating}
                />
              </div>

              {/* 文件名 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  文件名 <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={fileName}
                    onChange={(e) => setFileName(e.target.value)}
                    placeholder="deploy_production"
                    className="flex-1 px-4 py-2.5 text-sm font-mono border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                    disabled={isCreating}
                  />
                  <div className="flex items-center px-3 bg-gray-100 text-gray-600 text-sm rounded-lg border border-gray-300">
                    .py
                  </div>
                </div>
              </div>

              {/* 描述 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">描述</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="简要描述这个脚本的功能..."
                  rows={2}
                  className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all resize-none"
                  disabled={isCreating}
                />
              </div>

              {/* 基础模板选择 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">基础模板</label>
                <select
                  value={template}
                  onChange={(e) => setTemplate(e.target.value)}
                  className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  disabled={isCreating}
                >
                  <option value="blank">空白脚本</option>
                  <option value="deploy">Modal Deploy 模板</option>
                  <option value="run">Modal Run 模板</option>
                </select>
              </div>

              {/* 错误提示 */}
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}
            </div>
          ) : (
            // ========== 模板选择模式 ==========
            <div className="space-y-3 max-h-80 overflow-y-auto">
              <p className="text-sm text-gray-500 mb-3">
                选择一个模板快速创建脚本
              </p>
              
              {scriptTemplates.map((tmpl) => (
                <div
                  key={tmpl.id}
                  onClick={() => handleSelectTemplate(tmpl)}
                  className="p-3 border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50/30 cursor-pointer transition-all group"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-medium text-gray-800 group-hover:text-primary-600">
                        {tmpl.name}
                      </h4>
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                        {tmpl.description}
                      </p>
                      <div className="flex gap-1 mt-2">
                        {tmpl.tags.slice(0, 3).map(tag => (
                          <span key={tag} className="px-1.5 py-0.5 bg-gray-100 text-gray-500 text-xs rounded">
                            {tag}
                          </span>
                        ))}
                        <span className="px-1.5 py-0.5 bg-amber-100 text-amber-600 text-xs rounded">
                          {tmpl.variables.length} 个参数
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400 group-hover:text-primary-500 shrink-0 ml-2" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer - 只在空白模式显示 */}
        {mode === 'blank' && (
          <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 bg-gray-50">
            <Button variant="secondary" onClick={onClose} disabled={isCreating}>
              取消
            </Button>
            <Button onClick={handleCreate} disabled={isCreating}>
              <FileCode className="w-4 h-4 mr-1.5" />
              {isCreating ? '创建中...' : '创建脚本'}
            </Button>
          </div>
        )}

        {/* Footer - 模板模式 */}
        {mode === 'template' && (
          <div className="flex items-center justify-between p-4 border-t border-gray-200 bg-gray-50">
            <p className="text-xs text-gray-500">
              点击模板进入配置
            </p>
            <Button variant="secondary" onClick={onClose}>
              取消
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
