import { useState, useEffect } from 'react';
import { X, Play, FileCode, AlertCircle, Upload } from 'lucide-react';
import clsx from 'clsx';
import Button from './Button';
import Card from './Card';
import { TemplateVariable, replaceTemplateVariables } from '../data/scriptTemplates';
import { SelectModelFile } from '../../wailsjs/go/main/App';

interface VariableFormDialogProps {
  templateName: string;
  templateContent: string;
  variables: TemplateVariable[];
  onClose: () => void;
  onConfirm: (finalContent: string, values: Record<string, string>) => void;
}

export default function VariableFormDialog({
  templateName,
  templateContent,
  variables,
  onClose,
  onConfirm,
}: VariableFormDialogProps) {
  // 初始化变量值（使用默认值）
  const [values, setValues] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    variables.forEach(v => {
      initial[v.name] = v.defaultValue;
    });
    return initial;
  });
  
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showPreview, setShowPreview] = useState(false);

  // 更新变量值
  const handleValueChange = (name: string, value: string) => {
    setValues(prev => ({ ...prev, [name]: value }));
    // 清除错误
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  // 验证表单
  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    variables.forEach(v => {
      if (v.required && !values[v.name]?.trim()) {
        newErrors[v.name] = `${v.label} 为必填项`;
      }
    });
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // 提交表单
  const handleSubmit = () => {
    if (!validate()) return;
    
    const finalContent = replaceTemplateVariables(templateContent, values);
    onConfirm(finalContent, values);
  };

  // 生成预览内容
  const previewContent = replaceTemplateVariables(templateContent, values);

  return (
    <div 
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <Card 
        className="w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col animate-slide-in"
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gradient-to-r from-primary-50 to-white">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-100 rounded-lg">
              <FileCode className="w-5 h-5 text-primary-600" />
            </div>
            <div>
              <h2 className="text-base font-bold text-gray-800">配置模板参数</h2>
              <p className="text-xs text-gray-500">{templateName}</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* Variables Form */}
          <div className="space-y-4 mb-4">
            <p className="text-sm text-gray-600">
              请填写以下参数，完成后将生成最终脚本：
            </p>
            
            {variables.map((variable) => (
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
                      value={values[variable.name] || ''}
                      onChange={(e) => handleValueChange(variable.name, e.target.value)}
                      placeholder="点击右侧按钮选择文件"
                      className={clsx(
                        'flex-1 px-3 py-2 text-sm border rounded-lg transition-all',
                        'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                        errors[variable.name]
                          ? 'border-red-300 bg-red-50'
                          : 'border-gray-300 hover:border-gray-400'
                      )}
                    />
                    <button
                      type="button"
                      onClick={async () => {
                        try {
                          const filePath = await SelectModelFile();
                          if (filePath) {
                            // Windows 路径转换：反斜杠转正斜杠，避免 Python 转义问题
                            const normalizedPath = filePath.replace(/\\/g, '/');
                            handleValueChange(variable.name, normalizedPath);
                          }
                        } catch (err) {
                          console.error('选择文件失败:', err);
                        }
                      }}
                      className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors flex items-center gap-1.5"
                    >
                      <Upload className="w-4 h-4" />
                      选择文件
                    </button>
                  </div>
                ) : variable.options ? (
                  /* 下拉选择类型 */
                  <select
                    value={values[variable.name] || variable.defaultValue}
                    onChange={(e) => handleValueChange(variable.name, e.target.value)}
                    className={clsx(
                      'w-full px-3 py-2 text-sm border rounded-lg transition-all',
                      'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                      errors[variable.name]
                        ? 'border-red-300 bg-red-50'
                        : 'border-gray-300 hover:border-gray-400'
                    )}
                  >
                    {variable.options.map((option) => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                ) : (
                  /* 文本输入类型 */
                  <input
                    type="text"
                    value={values[variable.name] || ''}
                    onChange={(e) => handleValueChange(variable.name, e.target.value)}
                    placeholder={variable.defaultValue || `请输入 ${variable.label}`}
                    className={clsx(
                      'w-full px-3 py-2 text-sm border rounded-lg transition-all',
                      'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                      errors[variable.name]
                        ? 'border-red-300 bg-red-50'
                        : 'border-gray-300 hover:border-gray-400'
                    )}
                  />
                )}
                {errors[variable.name] && (
                  <p className="mt-1 text-xs text-red-500 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    {errors[variable.name]}
                  </p>
                )}
                {variable.defaultValue && !errors[variable.name] && !variable.options && variable.inputType !== 'file' && (
                  <p className="mt-1 text-xs text-gray-400">
                    默认值: {variable.defaultValue}
                  </p>
                )}
              </div>
            ))}
          </div>

          {/* Preview Toggle */}
          <div className="border-t border-gray-200 pt-4">
            <button
              onClick={() => setShowPreview(!showPreview)}
              className="text-sm text-primary-600 hover:text-primary-700 font-medium"
            >
              {showPreview ? '隐藏预览' : '预览生成的脚本'}
            </button>
            
            {showPreview && (
              <div className="mt-3 bg-gray-900 rounded-lg p-4 overflow-x-auto">
                <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">
                  {previewContent.slice(0, 2000)}
                  {previewContent.length > 2000 && '\n\n... (内容已截断)'}
                </pre>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 bg-gray-50">
          <Button variant="secondary" onClick={onClose}>
            取消
          </Button>
          <Button onClick={handleSubmit}>
            <Play className="w-4 h-4 mr-1" />
            确认创建
          </Button>
        </div>
      </Card>
    </div>
  );
}


