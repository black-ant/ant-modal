/**
 * 脚本模板库
 * 
 * 变量格式:
 * - {{VARIABLE_NAME}} - 基础变量
 * - {{VARIABLE_NAME:描述}} - 带描述的变量
 * - {{VARIABLE_NAME:描述:默认值}} - 带描述和默认值的变量
 */

export interface TemplateVariable {
  name: string;       // 变量名
  label: string;      // 显示标签/描述
  defaultValue: string; // 默认值
  required: boolean;  // 是否必填
  options?: string[]; // 可选的下拉选项
  scope?: 'global' | 'project' | 'script'; // 变量作用域：全局/项目/脚本（默认 script）
  inputType?: 'text' | 'file' | 'select'; // 输入类型：文本/文件选择/下拉框
}

export interface ScriptTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  variables: TemplateVariable[];
  content: string;
}

// 解析模板中的变量
export function parseTemplateVariables(content: string): TemplateVariable[] {
  const regex = /\{\{([^}]+)\}\}/g;
  const variables: TemplateVariable[] = [];
  const seen = new Set<string>();
  
  let match;
  while ((match = regex.exec(content)) !== null) {
    const parts = match[1].split(':');
    const name = parts[0].trim();
    
    if (seen.has(name)) continue;
    seen.add(name);
    
    variables.push({
      name,
      label: parts[1]?.trim() || name,
      defaultValue: parts[2]?.trim() || '',
      required: !parts[2], // 没有默认值则为必填
    });
  }
  
  return variables;
}

// 替换模板中的变量
export function replaceTemplateVariables(
  content: string, 
  values: Record<string, string>
): string {
  let result = content;
  
  // 替换所有变量占位符
  const regex = /\{\{([^}]+)\}\}/g;
  result = result.replace(regex, (match, varDef) => {
    const parts = varDef.split(':');
    const name = parts[0].trim();
    return values[name] || parts[2]?.trim() || '';
  });
  
  return result;
}

// ============================================================================
// 脚本模板定义
// ============================================================================

export const scriptTemplates: ScriptTemplate[] = [
  // --------------------------------------------------------------------------
  // 图像生成相关
  // --------------------------------------------------------------------------
  {
    id: 'comfyui-add-node',
    name: 'ComfyUI 添加节点',
    description: '安装自定义节点到已部署的 ComfyUI，通过 git clone 方式添加到 custom_nodes 目录',
    category: '图像生成',
    tags: ['ComfyUI', 'Custom Node', 'Git', '节点安装'],
    variables: [
      { name: 'GIT_REPO_URL', label: '节点 Git 仓库地址', defaultValue: 'https://github.com/ltdrdata/ComfyUI-Manager.git', required: true, scope: 'script' },
      { name: 'BRANCH', label: 'Git 分支', defaultValue: 'main', required: false, scope: 'script' },
      { name: 'VOLUME_NAME', label: 'Volume 名称', defaultValue: 'comfyui-cache', required: false, scope: 'project' },
    ],
    content: `"""
=============================================================================
ComfyUI 添加自定义节点
=============================================================================
将指定的 Git 仓库克隆到 ComfyUI 的 custom_nodes 目录

使用方法:
    modal run <脚本名>.py
=============================================================================
"""
import modal
import os
import subprocess
import json
import shutil
from pathlib import Path
from datetime import datetime

# 配置参数（由模板变量填充）
GIT_REPO_URL = "{{GIT_REPO_URL:节点 Git 仓库地址:https://github.com/ltdrdata/ComfyUI-Manager.git}}"
BRANCH = "{{BRANCH:Git 分支:main}}"
VOLUME_NAME = "{{VOLUME_NAME:Volume 名称:comfyui-cache}}"

# 复用 ComfyUI 的 Volume
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

# 包含 git 的镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install("requests")
)

app = modal.App("comfyui-add-node", image=image)

# Custom Nodes 存储路径
CUSTOM_NODES_PATH = "/cache/custom_nodes"


@app.function(
    volumes={"/cache": vol},
    timeout=600
)
def install_node():
    """
    安装 Custom Node 到共享 Volume
    """
    repo_url = GIT_REPO_URL
    branch = BRANCH
    
    node_name = repo_url.split("/")[-1].replace(".git", "")
    node_path = f"{CUSTOM_NODES_PATH}/{node_name}"
    
    print(f"{'='*60}")
    print(f"📦 安装 Custom Node: {node_name}")
    print(f"{'='*60}")
    print(f"仓库: {repo_url}")
    print(f"分支: {branch}")
    print(f"{'='*60}\\n")
    
    # 确保目录存在
    os.makedirs(CUSTOM_NODES_PATH, exist_ok=True)
    
    # 检查是否已存在
    if os.path.exists(node_path):
        print(f"⚠️ 节点已存在: {node_name}")
        print("正在更新节点...")
        try:
            result = subprocess.run(
                ["git", "pull"],
                cwd=node_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                print(f"✅ 节点更新成功")
            else:
                print(f"⚠️ 更新失败: {result.stderr}")
        except Exception as e:
            print(f"❌ 更新出错: {e}")
        
        vol.commit()
        return {
            "success": True,
            "action": "updated",
            "node_name": node_name
        }
    
    try:
        # 步骤 1: 克隆仓库
        print("[1/3] 克隆仓库...")
        clone_cmd = ["git", "clone", "-b", branch, "--depth", "1", repo_url, node_path]
        result = subprocess.run(clone_cmd, capture_output=True, text=True, timeout=180)
        
        if result.returncode != 0:
            raise Exception(f"克隆失败: {result.stderr}")
        print("✓ 克隆成功\\n")
        
        # 步骤 2: 检查依赖文件（依赖将在 ComfyUI 启动时自动安装）
        requirements_file = f"{node_path}/requirements.txt"
        if os.path.exists(requirements_file):
            print("[2/3] 检测到依赖文件...")
            print("   ℹ️ 依赖将在 ComfyUI 启动时自动安装")
            # 读取依赖列表供参考
            with open(requirements_file, 'r') as f:
                deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                if deps:
                    print(f"   📦 依赖项: {', '.join(deps[:5])}" + ("..." if len(deps) > 5 else ""))
            print()
        else:
            print("[2/3] 无依赖文件\\n")
        
        # 步骤 3: 记录安装信息并持久化
        print("[3/3] 记录安装信息并持久化...")
        install_info = {
            "node_name": node_name,
            "repo_url": repo_url,
            "branch": branch,
            "installed_at": datetime.now().isoformat(),
            "has_requirements": os.path.exists(requirements_file)
        }
        
        info_file = f"{node_path}/.install_info.json"
        with open(info_file, 'w') as f:
            json.dump(install_info, f, indent=2)
        
        vol.commit()
        print("✓ 已保存到 Volume\\n")
        
        print(f"{'='*60}")
        print(f"✅ Custom Node {node_name} 安装成功!")
        print(f"{'='*60}")
        print(f"\\n📌 后续步骤:")
        print(f"   1. 运行: modal app stop comfyui-app")
        print(f"   2. 访问 ComfyUI URL，服务会自动重启")
        print(f"   3. 重启时会自动链接节点并安装依赖")
        
        return {
            "success": True,
            "action": "installed",
            "node_name": node_name,
            "node_path": node_path,
            "install_info": install_info
        }
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "操作超时", "node_name": node_name}
    except Exception as e:
        # 清理失败的安装
        if os.path.exists(node_path):
            shutil.rmtree(node_path)
        return {"success": False, "error": str(e), "node_name": node_name}


@app.local_entrypoint()
def main():
    """
    本地入口
    """
    print(f"\\n{'='*60}")
    print("ComfyUI 添加自定义节点")
    print(f"{'='*60}")
    print(f"仓库: {GIT_REPO_URL}")
    print(f"分支: {BRANCH}")
    print(f"{'='*60}\\n")
    
    result = install_node.remote()
    
    if result.get("success"):
        print(f"\\n✅ 操作完成: {result.get('action')}")
    else:
        print(f"\\n❌ 操作失败: {result.get('error')}")
`
  },
  
  {
    id: 'comfyui-add-model-hf',
    name: 'ComfyUI 添加模型 (HuggingFace)',
    description: '从 HuggingFace 下载模型到已部署的 ComfyUI',
    category: '图像生成',
    tags: ['ComfyUI', 'HuggingFace', '模型下载', 'LoRA', 'Checkpoint'],
    variables: [
      { name: 'HF_REPO_ID', label: 'HuggingFace 仓库 ID', defaultValue: 'Comfy-Org/flux1-dev', required: true, scope: 'script' },
      { name: 'HF_FILENAME', label: '文件名', defaultValue: 'flux1-dev-fp8.safetensors', required: true, scope: 'script' },
      { name: 'MODEL_TYPE', label: '模型类型', defaultValue: 'checkpoints', required: false, options: ['checkpoints', 'loras', 'vae', 'clip', 'text_encoders', 'diffusion_models', 'controlnet', 'upscale_models', 'embeddings'], scope: 'script' },
      { name: 'VOLUME_NAME', label: 'Volume 名称', defaultValue: 'comfyui-cache', required: false, scope: 'project' },
    ],
    content: `"""
=============================================================================
ComfyUI 添加模型 (HuggingFace)
=============================================================================
从 HuggingFace 下载模型到 ComfyUI 的模型目录

使用方法:
    modal run <脚本名>.py
=============================================================================
"""
import modal
import os
import subprocess
from pathlib import Path

# 配置参数（由模板变量填充）
HF_REPO_ID = "{{HF_REPO_ID:HuggingFace 仓库 ID:Comfy-Org/flux1-dev}}"
HF_FILENAME = "{{HF_FILENAME:文件名:flux1-dev-fp8.safetensors}}"
MODEL_TYPE = "{{MODEL_TYPE:模型类型 (checkpoints/loras/vae/clip):checkpoints}}"
VOLUME_NAME = "{{VOLUME_NAME:Volume 名称:comfyui-cache}}"

# 复用 ComfyUI 的 Volume
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

# HuggingFace Secret (可选)
try:
    hf_secret = modal.Secret.from_name("huggingface-secret")
except modal.exception.NotFoundError:
    hf_secret = None

# 镜像配置
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("huggingface_hub[hf_transfer]==0.34.4", "requests")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

app = modal.App("comfyui-add-model", image=image)

# 模型类型和目录映射
MODEL_DIRS = {
    "checkpoints": "/cache/models/checkpoints",
    "loras": "/cache/models/loras",
    "vae": "/cache/models/vae",
    "clip": "/cache/models/clip",
    "text_encoders": "/cache/models/text_encoders",
    "diffusion_models": "/cache/models/diffusion_models",
    "controlnet": "/cache/models/controlnet",
    "upscale_models": "/cache/models/upscale_models",
    "embeddings": "/cache/models/embeddings",
}


@app.function(
    volumes={"/cache": vol},
    secrets=[hf_secret] if hf_secret else [],
    timeout=1800  # 30分钟超时
)
def add_model():
    """
    从 HuggingFace 下载模型
    """
    from huggingface_hub import hf_hub_download
    
    repo_id = HF_REPO_ID
    filename = HF_FILENAME
    model_type = MODEL_TYPE
    
    hf_token = os.getenv("HF_TOKEN")
    local_name = filename.split("/")[-1]
    model_dir = MODEL_DIRS.get(model_type, MODEL_DIRS["checkpoints"])
    final_path = f"{model_dir}/{local_name}"
    
    print(f"{'='*60}")
    print(f"📥 从 HuggingFace 下载模型")
    print(f"{'='*60}")
    print(f"仓库: {repo_id}")
    print(f"文件: {filename}")
    print(f"类型: {model_type}")
    print(f"保存为: {local_name}")
    print(f"{'='*60}\\n")
    
    # 检查是否已存在
    if os.path.exists(final_path):
        print(f"⚠️ 模型已存在: {final_path}")
        return {"success": False, "error": "模型已存在", "path": final_path}
    
    try:
        # 确保目录存在
        os.makedirs(model_dir, exist_ok=True)
        
        # 下载模型
        print("⬇️ 开始下载...")
        cached_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            cache_dir="/cache/hf_cache",
            token=hf_token
        )
        
        # 创建软链接
        subprocess.run(f"ln -s {cached_path} {final_path}", shell=True, check=True)
        
        # 提交到 Volume
        vol.commit()
        
        print(f"\\n✅ 模型下载成功!")
        print(f"路径: {final_path}")
        print(f"\\n⚠️ 重启 ComfyUI 后生效")
        
        return {
            "success": True,
            "path": final_path,
            "model_type": model_type,
            "source": f"hf://{repo_id}/{filename}"
        }
        
    except Exception as e:
        print(f"\\n❌ 下载失败: {e}")
        return {"success": False, "error": str(e)}


@app.local_entrypoint()
def main():
    """
    本地入口
    """
    print(f"\\n{'='*60}")
    print("ComfyUI 添加模型 (HuggingFace)")
    print(f"{'='*60}")
    print(f"仓库: {HF_REPO_ID}")
    print(f"文件: {HF_FILENAME}")
    print(f"类型: {MODEL_TYPE}")
    print(f"{'='*60}\\n")
    
    result = add_model.remote()
    
    if result.get("success"):
        print(f"\\n✅ 下载完成: {result.get('path')}")
    else:
        print(f"\\n❌ 下载失败: {result.get('error')}")
`
  },

  {
    id: 'comfyui-add-model-url',
    name: 'ComfyUI 添加模型 (URL)',
    description: '从 URL 直接下载模型到已部署的 ComfyUI',
    category: '图像生成',
    tags: ['ComfyUI', 'URL', '模型下载', 'LoRA', 'Civitai'],
    variables: [
      { name: 'MODEL_URL', label: '模型下载 URL', defaultValue: '', required: true, scope: 'script' },
      { name: 'MODEL_FILENAME', label: '保存的文件名', defaultValue: 'model.safetensors', required: true, scope: 'script' },
      { name: 'MODEL_TYPE', label: '模型类型', defaultValue: 'loras', required: false, options: ['checkpoints', 'loras', 'vae', 'clip', 'text_encoders', 'diffusion_models', 'controlnet', 'upscale_models', 'embeddings'], scope: 'script' },
      { name: 'VOLUME_NAME', label: 'Volume 名称', defaultValue: 'comfyui-cache', required: false, scope: 'project' },
    ],
    content: `"""
=============================================================================
ComfyUI 添加模型 (URL)
=============================================================================
从 URL 直接下载模型到 ComfyUI 的模型目录

使用方法:
    modal run <脚本名>.py
=============================================================================
"""
import modal
import os
from pathlib import Path

# 配置参数（由模板变量填充）
MODEL_URL = "{{MODEL_URL:模型下载 URL:}}"
MODEL_FILENAME = "{{MODEL_FILENAME:保存的文件名:model.safetensors}}"
MODEL_TYPE = "{{MODEL_TYPE:模型类型 (checkpoints/loras/vae/clip):loras}}"
VOLUME_NAME = "{{VOLUME_NAME:Volume 名称:comfyui-cache}}"

# 复用 ComfyUI 的 Volume
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

# 镜像配置
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("requests")
)

app = modal.App("comfyui-add-model-url", image=image)

# 模型类型和目录映射
MODEL_DIRS = {
    "checkpoints": "/cache/models/checkpoints",
    "loras": "/cache/models/loras",
    "vae": "/cache/models/vae",
    "clip": "/cache/models/clip",
    "text_encoders": "/cache/models/text_encoders",
    "diffusion_models": "/cache/models/diffusion_models",
    "controlnet": "/cache/models/controlnet",
    "upscale_models": "/cache/models/upscale_models",
    "embeddings": "/cache/models/embeddings",
}


@app.function(
    volumes={"/cache": vol},
    timeout=1800
)
def add_model():
    """
    从 URL 下载模型
    """
    import requests
    
    url = MODEL_URL
    filename = MODEL_FILENAME
    model_type = MODEL_TYPE
    
    model_dir = MODEL_DIRS.get(model_type, MODEL_DIRS["checkpoints"])
    final_path = f"{model_dir}/{filename}"
    
    print(f"{'='*60}")
    print(f"📥 从 URL 下载模型")
    print(f"{'='*60}")
    print(f"URL: {url[:80]}...")
    print(f"文件名: {filename}")
    print(f"类型: {model_type}")
    print(f"{'='*60}\\n")
    
    if not url:
        print("❌ 错误: 未提供下载 URL")
        return {"success": False, "error": "未提供下载 URL"}
    
    # 检查是否已存在
    if os.path.exists(final_path):
        print(f"⚠️ 模型已存在: {final_path}")
        return {"success": False, "error": "模型已存在", "path": final_path}
    
    try:
        os.makedirs(model_dir, exist_ok=True)
        
        print("⬇️ 开始下载...")
        with requests.get(url, stream=True, allow_redirects=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0
            
            with open(final_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\\r   进度: {progress:.1f}%", end="")
        
        print(f"\\n\\n✅ 模型下载成功!")
        print(f"路径: {final_path}")
        
        # 提交到 Volume
        vol.commit()
        
        print(f"\\n⚠️ 重启 ComfyUI 后生效")
        
        return {
            "success": True,
            "path": final_path,
            "model_type": model_type,
            "source": url
        }
        
    except Exception as e:
        print(f"\\n❌ 下载失败: {e}")
        # 清理不完整的文件
        if os.path.exists(final_path):
            os.remove(final_path)
        return {"success": False, "error": str(e)}


@app.local_entrypoint()
def main():
    """
    本地入口
    """
    print(f"\\n{'='*60}")
    print("ComfyUI 添加模型 (URL)")
    print(f"{'='*60}")
    print(f"URL: {MODEL_URL[:50]}..." if MODEL_URL else "URL: 未设置")
    print(f"文件名: {MODEL_FILENAME}")
    print(f"类型: {MODEL_TYPE}")
    print(f"{'='*60}\\n")
    
    result = add_model.remote()
    
    if result.get("success"):
        print(f"\\n✅ 下载完成: {result.get('path')}")
    else:
        print(f"\\n❌ 下载失败: {result.get('error')}")
`
  },

  {
    id: 'comfyui-add-model-local',
    name: 'ComfyUI 上传本地模型',
    description: '将本地模型文件上传到 ComfyUI Volume',
    category: '图像生成',
    tags: ['ComfyUI', '本地上传', '模型', 'Volume'],
    variables: [
      { name: 'LOCAL_MODEL_PATH', label: '选择本地模型文件', defaultValue: '', required: true, scope: 'script', inputType: 'file' },
      { name: 'MODEL_FILENAME', label: '保存的文件名 (可选，留空使用原文件名)', defaultValue: '', required: false, scope: 'script' },
      { name: 'MODEL_TYPE', label: '模型类型', defaultValue: 'checkpoints', required: true, options: ['checkpoints', 'loras', 'vae', 'clip', 'text_encoders', 'diffusion_models', 'controlnet', 'upscale_models', 'embeddings'], scope: 'script', inputType: 'select' },
      { name: 'VOLUME_NAME', label: 'Volume 名称', defaultValue: 'comfyui-cache', required: false, scope: 'project' },
    ],
    content: `"""
=============================================================================
ComfyUI 上传本地模型
=============================================================================
将本地模型文件上传到 ComfyUI 的模型目录

此脚本会显示上传命令，请在项目操作面板中使用"上传模型"功能执行
或手动执行生成的 modal volume put 命令
=============================================================================
"""
import os
from pathlib import Path

# =============================================
# 配置参数
# =============================================
LOCAL_MODEL_PATH = "{{LOCAL_MODEL_PATH:本地模型路径:D:/models/model.safetensors}}"
MODEL_FILENAME = "{{MODEL_FILENAME:保存的文件名 (可选):}}"
MODEL_TYPE = "{{MODEL_TYPE:模型类型:checkpoints}}"
VOLUME_NAME = "{{VOLUME_NAME:Volume 名称:comfyui-cache}}"

# =============================================
# 模型类型和目录映射
# =============================================
MODEL_DIRS = {
    "checkpoints": "/models/checkpoints",
    "loras": "/models/loras",
    "vae": "/models/vae",
    "clip": "/models/clip",
    "text_encoders": "/models/text_encoders",
    "diffusion_models": "/models/diffusion_models",
    "controlnet": "/models/controlnet",
    "upscale_models": "/models/upscale_models",
    "embeddings": "/models/embeddings",
}

# =============================================
# 生成上传命令
# =============================================
local_path = LOCAL_MODEL_PATH
filename = MODEL_FILENAME if MODEL_FILENAME else Path(local_path).name
model_type = MODEL_TYPE
remote_dir = MODEL_DIRS.get(model_type, MODEL_DIRS["checkpoints"])
remote_path = f"{remote_dir}/{filename}"

print("=" * 60)
print("📤 ComfyUI 本地模型上传")
print("=" * 60)
print(f"本地文件: {local_path}")
print(f"目标路径: {VOLUME_NAME}:{remote_path}")
print(f"模型类型: {model_type}")
print("=" * 60)
print()

# 检查本地文件是否存在
if os.path.exists(local_path):
    size_mb = os.path.getsize(local_path) / (1024 * 1024)
    print(f"✅ 本地文件存在，大小: {size_mb:.1f} MB")
else:
    print(f"❌ 本地文件不存在: {local_path}")
    exit(1)

print()
print("请执行以下命令上传文件:")
print()
print(f'  modal volume put {VOLUME_NAME} "{local_path}" {remote_path}')
print()
print("=" * 60)
`
  },

  {
    id: 'comfyui-diagnose',
    name: 'ComfyUI 诊断工具',
    description: '检查 ComfyUI Volume 中的模型和节点状态',
    category: '图像生成',
    tags: ['ComfyUI', '诊断', 'Volume', '调试'],
    variables: [
      { name: 'VOLUME_NAME', label: 'Volume 名称', defaultValue: 'comfyui-cache', required: false, scope: 'project' },
    ],
    content: `"""
=============================================================================
ComfyUI 诊断工具
=============================================================================
检查 Volume 中存储的模型和节点状态

使用方法:
    modal run <脚本名>.py
=============================================================================
"""
import modal
import os
import json
from pathlib import Path

# 配置参数
VOLUME_NAME = "{{VOLUME_NAME:Volume 名称:comfyui-cache}}"

vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = modal.Image.debian_slim(python_version="3.11")

app = modal.App("comfyui-diagnose", image=image)


@app.function(volumes={"/cache": vol})
def diagnose():
    """诊断 Volume 内容"""
    print("=" * 60)
    print("🔍 ComfyUI Volume 诊断报告")
    print("=" * 60)
    
    result = {"models": {}, "custom_nodes": [], "summary": {}}
    
    # 检查模型
    print("\\n📦 模型检查:")
    cache_models = Path("/cache/models")
    if cache_models.exists():
        for model_type_dir in cache_models.iterdir():
            if model_type_dir.is_dir():
                files = list(model_type_dir.iterdir())
                result["models"][model_type_dir.name] = [f.name for f in files]
                print(f"   {model_type_dir.name}: {len(files)} 个")
                for f in files:
                    size_mb = f.stat().st_size / (1024 * 1024) if f.exists() else 0
                    print(f"      - {f.name} ({size_mb:.1f} MB)")
    else:
        print("   ℹ️ 无持久化模型目录")
    
    # 检查节点
    print("\\n🧩 节点检查:")
    cache_nodes = Path("/cache/custom_nodes")
    if cache_nodes.exists():
        for node_dir in cache_nodes.iterdir():
            if node_dir.is_dir():
                has_req = (node_dir / "requirements.txt").exists()
                has_init = (node_dir / "__init__.py").exists()
                info = {
                    "name": node_dir.name,
                    "has_requirements": has_req,
                    "has_init": has_init
                }
                result["custom_nodes"].append(info)
                status = "✅" if has_init else "⚠️"
                print(f"   {status} {node_dir.name}")
                print(f"      requirements.txt: {'有' if has_req else '无'}")
    else:
        print("   ℹ️ 无持久化节点目录")
    
    # 汇总
    result["summary"] = {
        "total_models": sum(len(v) for v in result["models"].values()),
        "total_nodes": len(result["custom_nodes"])
    }
    
    print("\\n" + "=" * 60)
    print(f"📊 汇总: {result['summary']['total_models']} 个模型, {result['summary']['total_nodes']} 个节点")
    print("=" * 60)
    
    return result


@app.local_entrypoint()
def main():
    print("\\n🔍 开始诊断 ComfyUI Volume...")
    result = diagnose.remote()
    print("\\n✅ 诊断完成")
`
  },

  {
    id: 'comfyui-stop-app',
    name: 'ComfyUI 重启服务',
    description: '停止 ComfyUI 主服务，下次访问时自动重启并加载新节点',
    category: '图像生成',
    tags: ['ComfyUI', '重启', '节点', '服务'],
    variables: [
      { name: 'APP_NAME', label: 'Modal App 名称', defaultValue: 'comfyui-app', required: false, scope: 'project' },
    ],
    content: `"""
=============================================================================
ComfyUI 重启服务
=============================================================================
停止 ComfyUI 主服务，下次访问 URL 时会自动重启并加载新节点

使用方法:
    modal run <脚本名>.py

注意:
    - 添加节点后运行此脚本
    - 服务停止后访问 URL 会自动重启
    - 重启时会自动链接 Volume 中的节点并安装依赖
=============================================================================
"""
import modal
import subprocess

# 配置参数
APP_NAME = "{{APP_NAME:Modal App 名称:comfyui-app}}"

app = modal.App("comfyui-restart-helper")


@app.local_entrypoint()
def main():
    """停止 ComfyUI 主服务"""
    print(f"\\n{'='*60}")
    print(f"🔄 重启 ComfyUI 服务")
    print(f"{'='*60}")
    print(f"应用名称: {APP_NAME}")
    print(f"{'='*60}\\n")
    
    print("⏹️ 正在停止服务...")
    result = subprocess.run(
        ["modal", "app", "stop", APP_NAME],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ 服务已停止")
        print("\\n📌 后续步骤:")
        print("   1. 访问 ComfyUI URL，服务会自动重启")
        print("   2. 重启时会自动加载 Volume 中的新节点")
        print("   3. 节点依赖会自动安装")
    else:
        print(f"⚠️ 停止服务时出现问题: {result.stderr}")
    
    print(f"\\n{'='*60}")
`
  },

  // --------------------------------------------------------------------------
  // Z-Image-Turbo 相关
  // --------------------------------------------------------------------------
  
  // Z-Image 主服务 - 仅用于变量定义，实际脚本在 data/projects/z-image-turbo/
  {
    id: 'z-image-main-service',
    name: 'Z-Image 主服务',
    description: 'Z-Image-Turbo ComfyUI 应用服务',
    category: '图像生成',
    tags: ['Z-Image', 'ComfyUI', '部署'],
    variables: [
      { name: 'VOLUME_NAME', label: '模型存储 Volume', defaultValue: 'z-image-models', required: false, scope: 'project' },
      { name: 'APP_NAME', label: 'Modal 应用名称', defaultValue: 'z-image-turbo', required: false, scope: 'project' },
      { name: 'GPU_TYPE', label: 'GPU 类型', defaultValue: 'L40S', required: false, scope: 'project' },
    ],
    content: `# Z-Image 主服务脚本 - 请从项目模板创建`
  },

  // Z-Image 模型管理 - 仅用于变量定义
  {
    id: 'z-image-manage-models',
    name: 'Z-Image 模型管理',
    description: '管理 Z-Image-Turbo 共享 Volume 中的模型',
    category: '图像生成',
    tags: ['Z-Image', '模型管理'],
    variables: [
      { name: 'VOLUME_NAME', label: '模型存储 Volume', defaultValue: 'z-image-models', required: false, scope: 'project' },
      { name: 'APP_NAME', label: 'Modal 应用名称', defaultValue: 'z-image-turbo', required: false, scope: 'project' },
    ],
    content: `# Z-Image 模型管理脚本 - 请从项目模板创建`
  },

  {
    id: 'z-image-add-model-hf',
    name: 'Z-Image 添加模型 (HuggingFace)',
    description: '从 HuggingFace 下载模型到 Z-Image-Turbo 共享 Volume',
    category: '图像生成',
    tags: ['Z-Image', 'HuggingFace', '模型下载', '热加载'],
    variables: [
      { name: 'VOLUME_NAME', label: '模型存储 Volume', defaultValue: 'z-image-models', required: false, scope: 'project' },
      { name: 'APP_NAME', label: 'Modal 应用名称', defaultValue: 'z-image-turbo', required: false, scope: 'project' },
      { name: 'HF_REPO_ID', label: 'HuggingFace 仓库 ID', defaultValue: 'Comfy-Org/z_image_turbo', required: true, scope: 'script' },
      { name: 'HF_FILENAME', label: '文件名', defaultValue: 'z_image_turbo.safetensors', required: true, scope: 'script' },
      { name: 'MODEL_TYPE', label: '模型类型', defaultValue: 'diffusion_models', required: false, options: ['checkpoints', 'loras', 'vae', 'clip', 'text_encoders', 'diffusion_models', 'controlnet', 'upscale_models', 'embeddings'], scope: 'script' },
    ],
    content: `"""
=============================================================================
Z-Image-Turbo 添加模型 (HuggingFace)
=============================================================================
从 HuggingFace 下载模型到项目共享 Volume

使用方法:
    modal run <脚本名>.py
=============================================================================
"""
import modal
import os
from pathlib import Path

# 项目变量 - 与主服务共享
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:z-image-models}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:z-image-turbo}}"

# 脚本变量 - 每次执行时填写
HF_REPO_ID = "{{HF_REPO_ID:HuggingFace 仓库 ID:Comfy-Org/z_image_turbo}}"
HF_FILENAME = "{{HF_FILENAME:文件名:z_image_turbo.safetensors}}"
MODEL_TYPE = "{{MODEL_TYPE:模型类型:diffusion_models}}"

vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

MODEL_TYPES = ["checkpoints", "loras", "vae", "clip", "text_encoders",
               "diffusion_models", "controlnet", "upscale_models", "embeddings"]

try:
    hf_secret = modal.Secret.from_name("huggingface-secret")
except modal.exception.NotFoundError:
    hf_secret = None

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("huggingface_hub[hf_transfer]", "requests")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

app = modal.App(f"{APP_NAME}-downloader", image=image)


@app.function(
    volumes={"/models": vol},
    timeout=3600,
    secrets=[hf_secret] if hf_secret else []
)
def download_model():
    from huggingface_hub import hf_hub_download
    
    print(f"{'='*60}")
    print(f"📥 从 HuggingFace 下载模型")
    print(f"{'='*60}")
    print(f"仓库: {HF_REPO_ID}")
    print(f"文件: {HF_FILENAME}")
    print(f"类型: {MODEL_TYPE}")
    print(f"Volume: {VOLUME_NAME}")
    
    if MODEL_TYPE not in MODEL_TYPES:
        return {"success": False, "error": f"不支持的类型: {MODEL_TYPE}"}
    
    # 只取文件名，忽略 HuggingFace 仓库中的子目录路径
    local_name = Path(HF_FILENAME).name
    
    target_dir = Path(f"/models/{MODEL_TYPE}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / local_name
    
    if target_file.exists():
        print(f"\\n⚠️ 模型已存在: {local_name}")
        return {"success": True, "action": "exists"}
    
    try:
        print(f"\\n⏳ 下载中...")
        hf_token = os.getenv("HF_TOKEN")
        
        cached_path = hf_hub_download(
            repo_id=HF_REPO_ID,
            filename=HF_FILENAME,
            cache_dir="/tmp/hf_cache",
            token=hf_token
        )
        
        import shutil
        shutil.copy2(cached_path, str(target_file))
        vol.commit()
        
        size_mb = target_file.stat().st_size / (1024*1024)
        print(f"\\n✅ 下载成功! {local_name} ({size_mb:.1f} MB)")
        print(f"\\n💡 访问 /reload API 触发热加载:")
        print(f"   curl -X POST https://[workspace]--{APP_NAME}-zimageapi-reload.modal.run")
        
        return {"success": True, "action": "downloaded", "size_mb": size_mb}
        
    except Exception as e:
        print(f"\\n❌ 下载失败: {e}")
        return {"success": False, "error": str(e)}


@app.local_entrypoint()
def main():
    result = download_model.remote()
    print(f"\\n{'✅' if result.get('success') else '❌'} 操作完成")
`
  },

  {
    id: 'z-image-add-model-url',
    name: 'Z-Image 添加模型 (URL)',
    description: '从 URL 直接下载模型到 Z-Image-Turbo 共享 Volume',
    category: '图像生成',
    tags: ['Z-Image', 'URL', '模型下载'],
    variables: [
      { name: 'VOLUME_NAME', label: '模型存储 Volume', defaultValue: 'z-image-models', required: false, scope: 'project' },
      { name: 'APP_NAME', label: 'Modal 应用名称', defaultValue: 'z-image-turbo', required: false, scope: 'project' },
      { name: 'MODEL_URL', label: '模型下载 URL', defaultValue: '', required: true, scope: 'script' },
      { name: 'MODEL_FILENAME', label: '保存的文件名', defaultValue: 'model.safetensors', required: true, scope: 'script' },
      { name: 'MODEL_TYPE', label: '模型类型', defaultValue: 'loras', required: false, options: ['checkpoints', 'loras', 'vae', 'clip', 'text_encoders', 'diffusion_models', 'controlnet', 'upscale_models', 'embeddings'], scope: 'script' },
    ],
    content: `"""
=============================================================================
Z-Image-Turbo 添加模型 (URL)
=============================================================================
从 URL 直接下载模型到项目共享 Volume

使用方法:
    modal run <脚本名>.py
=============================================================================
"""
import modal
from pathlib import Path

# 项目变量 - 与主服务共享
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:z-image-models}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:z-image-turbo}}"

# 脚本变量 - 每次执行时填写
MODEL_URL = "{{MODEL_URL:模型下载 URL:}}"
MODEL_FILENAME = "{{MODEL_FILENAME:保存的文件名:model.safetensors}}"
MODEL_TYPE = "{{MODEL_TYPE:模型类型:loras}}"

vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

MODEL_TYPES = ["checkpoints", "loras", "vae", "clip", "text_encoders",
               "diffusion_models", "controlnet", "upscale_models", "embeddings"]

image = modal.Image.debian_slim(python_version="3.11").pip_install("requests", "tqdm")

app = modal.App(f"{APP_NAME}-url-downloader", image=image)


@app.function(volumes={"/models": vol}, timeout=3600)
def download_model():
    import requests
    from tqdm import tqdm
    
    print(f"{'='*60}")
    print(f"📥 从 URL 下载模型")
    print(f"{'='*60}")
    print(f"URL: {MODEL_URL}")
    print(f"文件: {MODEL_FILENAME}")
    print(f"类型: {MODEL_TYPE}")
    print(f"Volume: {VOLUME_NAME}")
    
    if not MODEL_URL:
        return {"success": False, "error": "未提供下载 URL"}
    
    if MODEL_TYPE not in MODEL_TYPES:
        return {"success": False, "error": f"不支持的类型: {MODEL_TYPE}"}
    
    target_dir = Path(f"/models/{MODEL_TYPE}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / MODEL_FILENAME
    
    if target_file.exists():
        print(f"\\n⚠️ 模型已存在: {MODEL_FILENAME}")
        return {"success": True, "action": "exists"}
    
    try:
        print(f"\\n⏳ 下载中...")
        
        response = requests.get(MODEL_URL, stream=True, timeout=60)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(target_file, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
                for chunk in response.iter_content(chunk_size=8192*1024):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        vol.commit()
        
        size_mb = target_file.stat().st_size / (1024*1024)
        print(f"\\n✅ 下载成功! ({size_mb:.1f} MB)")
        print(f"\\n💡 访问 /reload API 触发热加载:")
        print(f"   curl -X POST https://[workspace]--{APP_NAME}-zimageapi-reload.modal.run")
        
        return {"success": True, "action": "downloaded", "size_mb": size_mb}
        
    except Exception as e:
        if target_file.exists():
            target_file.unlink()
        print(f"\\n❌ 下载失败: {e}")
        return {"success": False, "error": str(e)}


@app.local_entrypoint()
def main():
    result = download_model.remote()
    print(f"\\n{'✅' if result.get('success') else '❌'} 操作完成")
`
  },

  {
    id: 'z-image-diagnose',
    name: 'Z-Image 诊断工具',
    description: '检查 Z-Image-Turbo 共享 Volume 和服务状态',
    category: '图像生成',
    tags: ['Z-Image', '诊断', 'Volume'],
    variables: [
      { name: 'VOLUME_NAME', label: '模型存储 Volume', defaultValue: 'z-image-models', required: false, scope: 'project' },
      { name: 'APP_NAME', label: 'Modal 应用名称', defaultValue: 'z-image-turbo', required: false, scope: 'project' },
    ],
    content: `"""
=============================================================================
Z-Image-Turbo 诊断工具
=============================================================================
检查项目共享 Volume 和服务状态

使用方法:
    modal run <脚本名>.py
=============================================================================
"""
import modal
from pathlib import Path

# 项目变量 - 与主服务共享
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:z-image-models}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:z-image-turbo}}"

vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = modal.Image.debian_slim(python_version="3.11")

app = modal.App(f"{APP_NAME}-diagnose", image=image)


@app.function(volumes={"/models": vol})
def diagnose():
    print("=" * 60)
    print("🔍 Z-Image-Turbo 诊断报告")
    print("=" * 60)
    
    print(f"\\n📦 项目配置:")
    print(f"   APP_NAME: {APP_NAME}")
    print(f"   VOLUME_NAME: {VOLUME_NAME}")
    
    print(f"\\n📦 Volume 检查:")
    volume_models = Path("/models")
    if volume_models.exists():
        total_size = 0
        total_files = 0
        for f in volume_models.rglob("*"):
            if f.is_file():
                total_size += f.stat().st_size
                total_files += 1
        print(f"   文件数: {total_files}")
        print(f"   总大小: {total_size / (1024*1024*1024):.2f} GB")
    else:
        print("   ℹ️ Volume 为空")
    
    print("\\n📊 模型统计:")
    model_types = ["checkpoints", "loras", "vae", "clip", "text_encoders",
                   "diffusion_models", "controlnet", "upscale_models", "embeddings"]
    
    has_models = False
    for model_type in model_types:
        type_dir = volume_models / model_type
        if type_dir.exists():
            count = len([f for f in type_dir.iterdir() if not f.name.startswith('.')])
            if count > 0:
                print(f"   {model_type}: {count} 个")
                has_models = True
    
    if not has_models:
        print("   ℹ️ 暂无模型")
    
    print(f"\\n🌐 服务访问地址:")
    print(f"   UI: https://[workspace]--{APP_NAME}-ui.modal.run")
    print(f"   API: https://[workspace]--{APP_NAME}-zimageapi-*.modal.run")
    
    print("\\n" + "=" * 60)
    return {"success": True}


@app.local_entrypoint()
def main():
    diagnose.remote()
    print("\\n✅ 诊断完成")
`
  },

  // --------------------------------------------------------------------------
  // 通用模板
  // --------------------------------------------------------------------------
  {
    id: 'modal-web-api',
    name: 'Web API 服务',
    description: '创建一个简单的 FastAPI Web 服务',
    category: '通用',
    tags: ['Web', 'API', 'FastAPI', 'HTTP'],
    variables: [
      { name: 'APP_NAME', label: '应用名称', defaultValue: 'my-web-api', required: true },
      { name: 'ENDPOINT_PATH', label: 'API 路径', defaultValue: '/api/hello', required: false },
    ],
    content: `"""
=============================================================================
Web API 服务
=============================================================================
创建一个简单的 FastAPI Web 服务

使用方法:
    modal deploy <脚本名>.py
=============================================================================
"""
import modal

# 配置参数
APP_NAME = "{{APP_NAME:应用名称:my-web-api}}"
ENDPOINT_PATH = "{{ENDPOINT_PATH:API 路径:/api/hello}}"

image = modal.Image.debian_slim().pip_install("fastapi[standard]")

app = modal.App(name=APP_NAME, image=image)


@app.function()
@modal.fastapi_endpoint(method="GET")
def hello(name: str = "World"):
    """
    简单的 Hello API
    """
    return {"message": f"Hello, {name}!", "app": APP_NAME}


@app.function()
@modal.fastapi_endpoint(method="POST")
def process(data: dict):
    """
    处理 POST 请求
    """
    return {
        "received": data,
        "status": "processed",
        "app": APP_NAME
    }


@app.local_entrypoint()
def main():
    print(f"\\n{'='*60}")
    print(f"Web API 服务: {APP_NAME}")
    print(f"{'='*60}")
    print(f"\\n使用 'modal deploy <脚本名>.py' 部署服务")
    print(f"\\n部署后访问:")
    print(f"  - GET  /hello?name=xxx")
    print(f"  - POST /process")
`
  },

  {
    id: 'modal-scheduled-task',
    name: '定时任务',
    description: '创建一个按 cron 表达式运行的定时任务',
    category: '通用',
    tags: ['定时任务', 'Cron', '调度', '自动化'],
    variables: [
      { name: 'APP_NAME', label: '应用名称', defaultValue: 'my-scheduler', required: true },
      { name: 'CRON_EXPRESSION', label: 'Cron 表达式', defaultValue: '0 9 * * *', required: true },
      { name: 'TASK_DESCRIPTION', label: '任务描述', defaultValue: '每天早上9点执行', required: false },
    ],
    content: `"""
=============================================================================
定时任务
=============================================================================
{{TASK_DESCRIPTION:任务描述:每天早上9点执行}}

Cron 表达式: {{CRON_EXPRESSION:Cron 表达式:0 9 * * *}}

使用方法:
    modal deploy <脚本名>.py
=============================================================================
"""
import modal
from datetime import datetime

# 配置参数
APP_NAME = "{{APP_NAME:应用名称:my-scheduler}}"
CRON_EXPRESSION = "{{CRON_EXPRESSION:Cron 表达式:0 9 * * *}}"

app = modal.App(name=APP_NAME)


@app.function(schedule=modal.Cron(CRON_EXPRESSION))
def scheduled_task():
    """
    定时执行的任务
    """
    now = datetime.now().isoformat()
    print(f"{'='*60}")
    print(f"⏰ 定时任务执行")
    print(f"{'='*60}")
    print(f"时间: {now}")
    print(f"应用: {APP_NAME}")
    print(f"{'='*60}")
    
    # TODO: 在这里添加你的任务逻辑
    
    return {"status": "completed", "timestamp": now}


@app.local_entrypoint()
def main():
    print(f"\\n{'='*60}")
    print(f"定时任务: {APP_NAME}")
    print(f"{'='*60}")
    print(f"Cron: {CRON_EXPRESSION}")
    print(f"\\n使用 'modal deploy <脚本名>.py' 部署定时任务")
    
    # 手动测试运行
    print("\\n正在测试运行...")
    result = scheduled_task.remote()
    print(f"结果: {result}")
`
  },
];

// 获取所有分类
export function getScriptTemplateCategories(): string[] {
  const categories = new Set(scriptTemplates.map(t => t.category));
  return ['全部', ...Array.from(categories)];
}

// 按分类过滤模板
export function filterScriptTemplates(category: string): ScriptTemplate[] {
  if (category === '全部') {
    return scriptTemplates;
  }
  return scriptTemplates.filter(t => t.category === category);
}


