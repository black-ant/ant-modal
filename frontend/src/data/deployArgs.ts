/**
 * 部署参数解析工具
 * 
 * 解析脚本中的 @modal-args 块，支持以下格式：
 * 
 * # @modal-args
 * # {{action|操作类型|list|select|list,hf,url,delete,reload}}
 * # {{repo_id|HuggingFace仓库ID||text}}
 * # {{filename|文件名||text}}
 * # {{type|模型类型|checkpoints|select|checkpoints,loras,vae}}
 * # {{no_reload|跳过热加载|false|bool}}
 * # @modal-args-end
 * 
 * 格式：{{参数名|标签|默认值|类型|选项列表}}
 * 类型：text(默认), select, bool, number
 */

export interface DeployArg {
  name: string;           // 参数名（用于命令行 --name=value）
  label: string;          // 显示标签
  defaultValue: string;   // 默认值
  type: 'text' | 'select' | 'bool' | 'number';  // 输入类型
  options: string[];      // 选项列表（select 类型使用）
  required: boolean;      // 是否必填
}

/**
 * 检测脚本是否包含 @modal-args 块
 */
export function hasModalArgs(content: string): boolean {
  return content.includes('@modal-args') && content.includes('@modal-args-end');
}

/**
 * 解析脚本中的 @modal-args 块
 */
export function parseModalArgs(content: string): DeployArg[] {
  const args: DeployArg[] = [];
  
  // 提取 @modal-args 块
  const startMarker = '@modal-args';
  const endMarker = '@modal-args-end';
  
  const startIdx = content.indexOf(startMarker);
  const endIdx = content.indexOf(endMarker);
  
  if (startIdx === -1 || endIdx === -1 || endIdx <= startIdx) {
    return args;
  }
  
  const argsBlock = content.substring(startIdx + startMarker.length, endIdx);
  
  // 匹配 {{...}} 格式的变量定义
  const varRegex = /\{\{([^}]+)\}\}/g;
  let match;
  
  while ((match = varRegex.exec(argsBlock)) !== null) {
    const parts = match[1].split('|').map(p => p.trim());
    
    if (parts.length < 2) continue;
    
    const name = parts[0];
    const label = parts[1];
    const defaultValue = parts[2] || '';
    const type = (parts[3] || 'text') as DeployArg['type'];
    const optionsStr = parts[4] || '';
    const options = optionsStr ? optionsStr.split(',').map(o => o.trim()) : [];
    
    // 判断是否必填（没有默认值且不是 bool 类型的视为必填）
    const required = !defaultValue && type !== 'bool';
    
    args.push({
      name,
      label,
      defaultValue,
      type,
      options,
      required,
    });
  }
  
  return args;
}

/**
 * 生成命令行参数字符串
 */
export function generateArgsString(args: DeployArg[], values: Record<string, string>): string {
  const parts: string[] = [];
  
  for (const arg of args) {
    const value = values[arg.name];
    
    // 跳过空值（非 bool 类型）
    if (arg.type !== 'bool' && (!value || value.trim() === '')) {
      continue;
    }
    
    // 处理不同类型
    if (arg.type === 'bool') {
      // bool 类型：只有 true 时才添加
      if (value === 'true') {
        parts.push(`--${arg.name}`);
      }
    } else {
      // 其他类型：--name=value 格式
      // 如果值包含空格，需要加引号
      const formattedValue = value.includes(' ') ? `"${value}"` : value;
      parts.push(`--${arg.name}=${formattedValue}`);
    }
  }
  
  return parts.join(' ');
}

/**
 * 生成完整的 modal run 命令
 */
export function generateModalRunCommand(
  scriptPath: string, 
  args: DeployArg[], 
  values: Record<string, string>
): string {
  const argsStr = generateArgsString(args, values);
  const scriptName = scriptPath.split('/').pop() || scriptPath;
  
  if (argsStr) {
    return `modal run ${scriptName} ${argsStr}`;
  }
  return `modal run ${scriptName}`;
}

/**
 * 初始化参数值（使用默认值）
 */
export function initArgValues(args: DeployArg[]): Record<string, string> {
  const values: Record<string, string> = {};
  
  for (const arg of args) {
    values[arg.name] = arg.defaultValue;
  }
  
  return values;
}

/**
 * 验证参数值
 */
export function validateArgValues(
  args: DeployArg[], 
  values: Record<string, string>
): Record<string, string> {
  const errors: Record<string, string> = {};
  
  for (const arg of args) {
    if (arg.required && (!values[arg.name] || values[arg.name].trim() === '')) {
      errors[arg.name] = `${arg.label} 为必填项`;
    }
    
    // 验证 number 类型
    if (arg.type === 'number' && values[arg.name]) {
      const num = Number(values[arg.name]);
      if (isNaN(num)) {
        errors[arg.name] = `${arg.label} 必须是数字`;
      }
    }
  }
  
  return errors;
}

