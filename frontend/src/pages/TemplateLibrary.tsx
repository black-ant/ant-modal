import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookTemplate, Plus, Code, Sparkles, Zap, Box, Check, FileCode, Folder, Variable, X } from 'lucide-react';
import clsx from 'clsx';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import Card from '../components/Card';
import Button from '../components/Button';
import VariableFormDialog from '../components/VariableFormDialog';
import { main } from '../../wailsjs/go/models';
import { GetModalAppList, CreateProjectFromTemplate, GetProjects, CreateScript } from '../../wailsjs/go/main/App';
import {
  scriptTemplates,
  ScriptTemplate,
  getScriptTemplateCategories,
  filterScriptTemplates,
  replaceTemplateVariables
} from '../data/scriptTemplates';

// ============================================================================
// 项目模板定义
// ============================================================================

interface ProjectTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  scripts: Array<{
    name: string;
    fileName: string;
    description: string;
    content: string;
  }>;
  tags: string[];
}

const projectTemplates: ProjectTemplate[] = [
  {
    id: 'stable-diffusion',
    name: 'Stable Diffusion 图像生成',
    description: '使用 SDXL 模型生成高质量图像，支持电商产品图、社媒营销图等业务场景',
    category: '图像生成',
    icon: 'sparkles',
    tags: ['SDXL', '图像生成', 'AI', 'GPU', '电商', '营销'],
    scripts: [
      { name: 'SD 图像生成服务', fileName: 'sd_service.py', description: 'Stable Diffusion XL 基础图像生成服务', content: `# SD 服务脚本` },
      { name: '电商产品图批量生成', fileName: 'sd_ecommerce_product.py', description: '解决：为每个产品生成多种风格展示图，提升上新效率', content: `# 电商产品图脚本` },
      { name: '社媒营销图生成', fileName: 'sd_social_media.py', description: '解决：运营每天需要大量配图，一键生成多平台尺寸', content: `# 社媒营销图脚本` }
    ]
  },
  {
    id: 'ai-llm',
    name: 'AI 大模型服务',
    description: '一站式大模型部署，支持 Llama/Qwen/ChatGLM/Mistral/Yi/DeepSeek 等主流模型',
    category: 'AI服务',
    icon: 'sparkles',
    tags: ['LLM', 'Llama', 'Qwen', 'ChatGLM', 'Mistral', 'Yi', 'DeepSeek'],
    scripts: [
      { name: 'Llama 3 对话服务', fileName: 'llama_service.py', description: 'Meta Llama 3 模型，通用对话和问答', content: `# Llama 服务脚本` },
      { name: 'Qwen 通义千问', fileName: 'qwen_service.py', description: '阿里通义千问，中文能力强', content: `# Qwen 服务脚本` },
      { name: 'ChatGLM 智谱', fileName: 'chatglm_service.py', description: '智谱 GLM-4，优秀中文理解', content: `# ChatGLM 服务脚本` },
      { name: 'Mistral/Mixtral', fileName: 'mistral_service.py', description: 'Mistral 高性能推理，MoE 架构', content: `# Mistral 服务脚本` },
      { name: 'Yi 零一万物', fileName: 'yi_service.py', description: '零一万物 Yi，支持超长上下文', content: `# Yi 服务脚本` },
      { name: 'DeepSeek 翻译', fileName: 'deepseek_service.py', description: 'DeepSeek V3 翻译服务', content: `# DeepSeek 服务脚本` }
    ]
  },
  {
    id: 'whisper-stt',
    name: 'Whisper 语音识别',
    description: '使用 OpenAI Whisper 进行语音转文字，支持会议纪要、字幕生成等场景',
    category: 'AI服务',
    icon: 'sparkles',
    tags: ['Whisper', 'STT', '语音识别', '会议', '字幕'],
    scripts: [
      { name: 'Whisper 语音识别', fileName: 'whisper_service.py', description: '基础语音转文字服务', content: `# Whisper 服务脚本` },
      { name: '会议纪要自动生成', fileName: 'whisper_meeting_minutes.py', description: '解决：每次会议后整理纪要耗时 2 小时且容易遗漏', content: `# 会议纪要脚本` },
      { name: '视频字幕自动生成', fileName: 'whisper_subtitle.py', description: '解决：手动添加字幕每小时视频需要 4-6 小时', content: `# 字幕生成脚本` }
    ]
  },
  {
    id: 'embedding-service',
    name: '文本嵌入服务',
    description: '生成文本向量，支持企业知识库检索、商品推荐等业务场景',
    category: 'AI服务',
    icon: 'sparkles',
    tags: ['Embedding', '向量', '语义搜索', '知识库', '推荐'],
    scripts: [
      { name: '文本嵌入服务', fileName: 'embedding_service.py', description: '基础文本向量化和语义搜索', content: `# Embedding 服务脚本` },
      { name: '企业知识库检索', fileName: 'embedding_knowledge_base.py', description: '解决：传统关键词搜索找不到语义相关的文档内容', content: `# 知识库检索脚本` },
      { name: '相似商品推荐', fileName: 'embedding_similar_product.py', description: '解决：用户描述需求后无法匹配到相似商品', content: `# 商品推荐脚本` }
    ]
  },
  {
    id: 'lora-training',
    name: 'LoRA 微调训练',
    description: '使用 LoRA 技术微调 Stable Diffusion 模型',
    category: '模型训练',
    icon: 'sparkles',
    tags: ['LoRA', '微调', 'Training', 'SD'],
    scripts: [
      { name: 'LoRA 训练服务', fileName: 'lora_training.py', description: 'LoRA 模型训练和推理', content: `# LoRA 训练脚本` }
    ]
  },
  {
    id: 'comfyui-node-manager',
    name: 'Comfy-Flux 图像生成',
    description: '完整的 ComfyUI 部署和管理方案：安装应用、添加模型、管理节点',
    category: '图像生成',
    icon: 'sparkles',
    tags: ['ComfyUI', 'Flux', '图像生成', 'Volume', '模型管理'],
    scripts: [
      {
        name: 'ComfyUI 主应用',
        fileName: 'comfyui_app.py',
        description: '完整服务：环境配置 + 模型下载 + UI/API 服务',
        content: `"""
=============================================================================
ComfyUI 完整应用服务
=============================================================================
⚠️ 首次使用请先配置项目变量（点击项目标题旁的齿轮图标）:
  - VOLUME_NAME: 模型存储 Volume 名称
  - APP_NAME: Modal 应用名称（所有脚本共用）
  - GPU_TYPE: GPU 类型

部署命令: modal deploy comfyui_app.py
=============================================================================
"""
# 完整的主应用脚本内容请参考 data/projects/comfyui-node-manager/comfyui_app.py
# 这里提供简化版本用于快速入门

import modal
import subprocess
from pathlib import Path

VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:comfyui-cache}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:comfyui-app}}"
GPU_TYPE = "{{GPU_TYPE:GPU 类型:L40S}}"

# 构建镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "wget", "curl")
    .pip_install("fastapi[standard]==0.115.4", "comfy-cli==1.5.1")
    .run_commands("comfy --skip-prompt install --fast-deps --nvidia")
)

vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
app = modal.App(name=APP_NAME, image=image)

@app.function(
    max_containers=1,
    gpu=GPU_TYPE,
    volumes={"/cache": vol},
    timeout=86400
)
@modal.web_server(8000, startup_timeout=60)
def ui():
    """ComfyUI Web 界面"""
    subprocess.Popen("comfy launch -- --listen 0.0.0.0 --port 8000", shell=True)
`
      },
      {
        name: '添加模型 (HuggingFace)',
        fileName: 'add_model_hf.py',
        description: '从 HuggingFace 下载模型到共享 Volume',
        content: `"""
=============================================================================
ComfyUI 添加模型 (HuggingFace)
=============================================================================
从 HuggingFace 下载模型到共享 Volume

使用方法:
    modal run add_model_hf.py
=============================================================================
"""
import modal
import os
from pathlib import Path

# =============================================================================
# 项目变量 - 与主服务共享同一个 Volume
# =============================================================================
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:comfyui-cache}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:comfyui-app}}"

# 脚本变量 - 每次执行时填写
HF_REPO_ID = "{{HF_REPO_ID:HuggingFace 仓库 ID:Comfy-Org/flux1-dev}}"
HF_FILENAME = "{{HF_FILENAME:文件名:flux1-dev-fp8.safetensors}}"
MODEL_TYPE = "{{MODEL_TYPE:模型类型:checkpoints}}"

# =============================================================================
# 使用与主服务相同的 Volume
# =============================================================================
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

app = modal.App(f"{APP_NAME}-hf-downloader", image=image)


@app.function(
    volumes={"/cache": vol},
    timeout=3600,
    secrets=[hf_secret] if hf_secret else []
)
def download_model():
    """从 HuggingFace 下载模型"""
    from huggingface_hub import hf_hub_download
    
    repo_id = HF_REPO_ID
    filename = HF_FILENAME
    model_type = MODEL_TYPE
    
    print(f"{'='*60}")
    print(f"📥 从 HuggingFace 下载模型")
    print(f"{'='*60}")
    print(f"仓库: {repo_id}")
    print(f"文件: {filename}")
    print(f"类型: {model_type}")
    print(f"Volume: {VOLUME_NAME}")
    
    if model_type not in MODEL_TYPES:
        return {"success": False, "error": f"不支持的类型: {model_type}"}
    
    # 只取文件名，忽略 HuggingFace 仓库中的子目录路径
    local_name = Path(filename).name
    
    target_dir = Path(f"/cache/models/{model_type}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / local_name
    
    if target_file.exists() or target_file.is_symlink():
        print(f"\\n⚠️ 模型已存在: {local_name}")
        return {"success": True, "action": "exists"}
    
    try:
        print(f"\\n⏳ 下载中...")
        hf_token = os.getenv("HF_TOKEN")
        
        cached_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            cache_dir="/cache/hf_cache",
            token=hf_token
        )
        
        # 创建符号链接
        os.symlink(cached_path, str(target_file))
        vol.commit()
        
        size_mb = Path(cached_path).stat().st_size / (1024*1024)
        print(f"\\n✅ 下载成功!")
        print(f"   文件: {model_type}/{local_name}")
        print(f"   大小: {size_mb:.1f} MB")
        
        return {"success": True, "action": "downloaded", "size_mb": size_mb, "local_name": local_name}
        
    except Exception as e:
        print(f"\\n❌ 下载失败: {e}")
        return {"success": False, "error": str(e)}


@app.local_entrypoint()
def main():
    print(f"\\n{'='*60}")
    print(f"ComfyUI 添加模型 ({APP_NAME})")
    print(f"{'='*60}")
    
    result = download_model.remote()
    
    if result.get("success"):
        if result.get("action") == "downloaded":
            print(f"\\n✅ 模型下载完成: {result.get('local_name')}")
            print(f"\\n📌 下一步: 重启 ComfyUI 服务使模型生效")
            print(f"   运行: modal app stop {APP_NAME}")
        else:
            print(f"\\n✅ 模型已存在，无需下载")
    else:
        print(f"\\n❌ 失败: {result.get('error')}")
`
      },
      {
        name: '添加模型 (URL)',
        fileName: 'add_model_url.py',
        description: '从 URL 直接下载模型到共享 Volume',
        content: `"""
=============================================================================
ComfyUI 添加模型 (URL)
=============================================================================
从 URL 直接下载模型到共享 Volume

使用方法:
    modal run add_model_url.py
=============================================================================
"""
import modal
from pathlib import Path

# =============================================================================
# 项目变量 - 与主服务共享同一个 Volume
# =============================================================================
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:comfyui-cache}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:comfyui-app}}"

# 脚本变量 - 每次执行时填写
MODEL_URL = "{{MODEL_URL:模型下载 URL:}}"
MODEL_FILENAME = "{{MODEL_FILENAME:保存的文件名:model.safetensors}}"
MODEL_TYPE = "{{MODEL_TYPE:模型类型:loras}}"

# =============================================================================
# 使用与主服务相同的 Volume
# =============================================================================
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

MODEL_TYPES = ["checkpoints", "loras", "vae", "clip", "text_encoders",
               "diffusion_models", "controlnet", "upscale_models", "embeddings"]

image = modal.Image.debian_slim(python_version="3.11").pip_install("requests", "tqdm")

app = modal.App(f"{APP_NAME}-url-downloader", image=image)


@app.function(volumes={"/cache": vol}, timeout=3600)
def download_model():
    """从 URL 下载模型"""
    import requests
    from tqdm import tqdm
    
    url = MODEL_URL
    filename = MODEL_FILENAME
    model_type = MODEL_TYPE
    
    print(f"{'='*60}")
    print(f"📥 从 URL 下载模型")
    print(f"{'='*60}")
    print(f"URL: {url}")
    print(f"文件: {filename}")
    print(f"类型: {model_type}")
    print(f"Volume: {VOLUME_NAME}")
    
    if not url:
        return {"success": False, "error": "未提供下载 URL"}
    
    if model_type not in MODEL_TYPES:
        return {"success": False, "error": f"不支持的类型: {model_type}"}
    
    target_dir = Path(f"/cache/models/{model_type}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename
    
    if target_file.exists():
        print(f"\\n⚠️ 模型已存在: {filename}")
        return {"success": True, "action": "exists"}
    
    try:
        print(f"\\n⏳ 下载中...")
        
        response = requests.get(url, stream=True, timeout=60)
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
        print(f"\\n✅ 下载成功!")
        print(f"   文件: {model_type}/{filename}")
        print(f"   大小: {size_mb:.1f} MB")
        
        return {"success": True, "action": "downloaded", "size_mb": size_mb, "filename": filename}
        
    except Exception as e:
        if target_file.exists():
            target_file.unlink()
        print(f"\\n❌ 下载失败: {e}")
        return {"success": False, "error": str(e)}


@app.local_entrypoint()
def main():
    print(f"\\n{'='*60}")
    print(f"ComfyUI 添加模型 ({APP_NAME})")
    print(f"{'='*60}")
    
    result = download_model.remote()
    
    if result.get("success"):
        if result.get("action") == "downloaded":
            print(f"\\n✅ 模型下载完成: {result.get('filename')}")
            print(f"\\n📌 下一步: 重启 ComfyUI 服务使模型生效")
            print(f"   运行: modal app stop {APP_NAME}")
        else:
            print(f"\\n✅ 模型已存在，无需下载")
    else:
        print(f"\\n❌ 失败: {result.get('error')}")
`
      },
      {
        name: '添加自定义节点',
        fileName: 'add_node.py',
        description: '从 Git 仓库安装自定义节点到 ComfyUI',
        content: `"""
=============================================================================
ComfyUI 添加自定义节点
=============================================================================
从 Git 仓库安装自定义节点到 ComfyUI

使用方法:
    modal run add_node.py
=============================================================================
"""
import modal
import subprocess
import json
from pathlib import Path
from datetime import datetime

# =============================================================================
# 项目变量 - 与主服务共享同一个 Volume
# =============================================================================
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:comfyui-cache}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:comfyui-app}}"

# 脚本变量 - 每次执行时填写
NODE_REPO_URL = "{{NODE_REPO_URL:节点 Git 仓库 URL:https://github.com/ltdrdata/ComfyUI-Manager.git}}"
NODE_BRANCH = "{{NODE_BRANCH:分支:main}}"

# =============================================================================
# 使用与主服务相同的 Volume
# =============================================================================
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install("requests")
)

app = modal.App(f"{APP_NAME}-node-installer", image=image)


@app.function(
    volumes={"/cache": vol},
    timeout=600
)
def install_node():
    """安装自定义节点到共享 Volume"""
    repo_url = NODE_REPO_URL
    branch = NODE_BRANCH
    
    node_name = repo_url.split("/")[-1].replace(".git", "")
    node_path = f"/cache/custom_nodes/{node_name}"
    
    print(f"{'='*60}")
    print(f"📦 安装 Custom Node: {node_name}")
    print(f"{'='*60}")
    print(f"仓库: {repo_url}")
    print(f"分支: {branch}")
    print(f"Volume: {VOLUME_NAME}")
    
    # 确保目录存在
    Path("/cache/custom_nodes").mkdir(parents=True, exist_ok=True)
    
    # 检查是否已存在
    if Path(node_path).exists():
        print(f"\\n⚠️ 节点已存在: {node_name}")
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
                vol.commit()
                print(f"✅ 节点更新成功")
                return {
                    "success": True,
                    "action": "updated",
                    "node_name": node_name,
                    "message": "节点已更新，请重启 ComfyUI 服务"
                }
            else:
                print(f"⚠️ 更新失败: {result.stderr}")
        except Exception as e:
            print(f"❌ 更新出错: {e}")
    
    try:
        # 步骤 1: 克隆仓库
        print("\\n[1/3] 克隆仓库...")
        clone_cmd = ["git", "clone", "-b", branch, "--depth", "1", repo_url, node_path]
        result = subprocess.run(clone_cmd, capture_output=True, text=True, timeout=180)
        
        if result.returncode != 0:
            raise Exception(f"克隆失败: {result.stderr}")
        print("✓ 克隆成功")
        
        # 步骤 2: 检查依赖文件
        requirements_file = f"{node_path}/requirements.txt"
        has_req = Path(requirements_file).exists()
        
        if has_req:
            print("\\n[2/3] 检测到依赖文件...")
            print("   ℹ️ 依赖将在 ComfyUI 启动时自动安装")
            with open(requirements_file, 'r') as f:
                deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                if deps:
                    print(f"   📦 依赖项: {', '.join(deps[:5])}" + ("..." if len(deps) > 5 else ""))
        else:
            print("\\n[2/3] 无依赖文件")
        
        # 步骤 3: 记录安装信息
        print("\\n[3/3] 记录安装信息...")
        install_info = {
            "node_name": node_name,
            "repo_url": repo_url,
            "branch": branch,
            "installed_at": datetime.now().isoformat(),
            "has_requirements": has_req
        }
        
        info_file = f"{node_path}/.install_info.json"
        with open(info_file, 'w') as f:
            json.dump(install_info, f, indent=2)
        
        vol.commit()
        print("✓ 已保存到 Volume")
        
        print(f"\\n{'='*60}")
        print(f"✅ Custom Node {node_name} 安装成功!")
        print(f"{'='*60}")
        
        return {
            "success": True,
            "action": "installed",
            "node_name": node_name,
            "message": "节点安装成功，请重启 ComfyUI 服务"
        }
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "操作超时", "node_name": node_name}
    except Exception as e:
        # 清理失败的安装
        if Path(node_path).exists():
            import shutil
            shutil.rmtree(node_path)
        return {"success": False, "error": str(e), "node_name": node_name}


@app.local_entrypoint()
def main():
    print(f"\\n{'='*60}")
    print(f"ComfyUI 添加自定义节点 ({APP_NAME})")
    print(f"{'='*60}")
    
    result = install_node.remote()
    
    if result.get("success"):
        print(f"\\n✅ 操作完成")
        print(f"\\n📌 下一步: 重启 ComfyUI 服务使节点生效")
        print(f"   运行: modal app stop {APP_NAME}")
        print(f"   然后访问 ComfyUI URL，服务会自动重启并加载节点")
    else:
        print(f"\\n❌ 失败: {result.get('error')}")
`
      },
      {
        name: '诊断工具',
        fileName: 'diagnose.py',
        description: '检查共享 Volume 中的模型和节点状态',
        content: `"""
=============================================================================
ComfyUI 诊断工具
=============================================================================
检查 Volume 中存储的模型和节点状态

使用方法:
    modal run diagnose.py
=============================================================================
"""
import modal
import os
import json
from pathlib import Path

# 配置参数
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:comfyui-cache}}"

vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = modal.Image.debian_slim(python_version="3.11")

app = modal.App("comfyui-diagnose", image=image)

# 模型类型映射
MODEL_TYPES = ["checkpoints", "loras", "vae", "clip", "controlnet", "upscale_models", "embeddings"]


@app.function(volumes={"/cache": vol})
def diagnose():
    """诊断 Volume 内容"""
    print("=" * 60)
    print("🔍 ComfyUI Volume 诊断报告")
    print("=" * 60)
    
    result = {"models": {}, "custom_nodes": [], "summary": {}}
    
    # 1. 检查模型
    print("\\n📦 模型检查:")
    cache_models = Path("/cache/models")
    total_models = 0
    
    if cache_models.exists():
        for model_type in MODEL_TYPES:
            model_dir = cache_models / model_type
            if model_dir.exists():
                files = list(model_dir.iterdir())
                if files:
                    result["models"][model_type] = []
                    print(f"\\n   📁 {model_type} ({len(files)} 个):")
                    for f in files:
                        size_mb = f.stat().st_size / (1024 * 1024) if f.exists() else 0
                        is_link = f.is_symlink()
                        result["models"][model_type].append({
                            "name": f.name,
                            "size_mb": round(size_mb, 2),
                            "is_link": is_link
                        })
                        link_mark = " 🔗" if is_link else ""
                        print(f"      • {f.name} ({size_mb:.1f} MB){link_mark}")
                        total_models += 1
    else:
        print("   ℹ️ 无持久化模型目录")
    
    # 2. 检查节点
    print("\\n" + "=" * 60)
    print("🧩 节点检查:")
    cache_nodes = Path("/cache/custom_nodes")
    
    if cache_nodes.exists():
        nodes = list(cache_nodes.iterdir())
        valid_nodes = 0
        
        for node_dir in nodes:
            if node_dir.is_dir():
                has_req = (node_dir / "requirements.txt").exists()
                has_init = (node_dir / "__init__.py").exists()
                
                # 尝试读取安装信息
                info_file = node_dir / ".install_info.json"
                install_info = {}
                if info_file.exists():
                    try:
                        install_info = json.loads(info_file.read_text())
                    except:
                        pass
                
                info = {
                    "name": node_dir.name,
                    "has_requirements": has_req,
                    "has_init": has_init,
                    "valid": has_init,
                    "repo_url": install_info.get("repo_url", ""),
                    "installed_at": install_info.get("installed_at", "")
                }
                result["custom_nodes"].append(info)
                
                status = "✅" if has_init else "⚠️"
                if has_init:
                    valid_nodes += 1
                
                print(f"\\n   {status} {node_dir.name}")
                if info["repo_url"]:
                    print(f"      仓库: {info['repo_url']}")
                print(f"      requirements.txt: {'有' if has_req else '无'}")
                print(f"      __init__.py: {'有' if has_init else '无'}")
        
        print(f"\\n   📊 节点统计: {valid_nodes}/{len(nodes)} 个有效")
    else:
        print("   ℹ️ 无持久化节点目录")
    
    # 3. 汇总
    result["summary"] = {
        "total_models": total_models,
        "total_nodes": len(result["custom_nodes"]),
        "valid_nodes": sum(1 for n in result["custom_nodes"] if n["valid"])
    }
    
    print("\\n" + "=" * 60)
    print("📊 汇总")
    print("=" * 60)
    print(f"   模型: {result['summary']['total_models']} 个")
    print(f"   节点: {result['summary']['valid_nodes']}/{result['summary']['total_nodes']} 个有效")
    
    if result["summary"]["total_nodes"] > 0 or result["summary"]["total_models"] > 0:
        print("\\n📌 提示:")
        print("   如果添加了新资源，需要重启 ComfyUI 服务才能生效")
        print("   运行: modal app stop comfyui-app")
    
    print("=" * 60)
    
    return result


@app.local_entrypoint()
def main():
    print("\\n🔍 开始诊断 ComfyUI Volume...")
    result = diagnose.remote()
    print("\\n✅ 诊断完成")
`
      }
    ]
  },
  {
    id: 'z-image-turbo',
    name: 'Comfy-Z-Image-Turbo 图像生成',
    description: '阿里巴巴 Z-Image-Turbo 高效图像生成，6B 参数媲美 20B+ 模型，支持热加载模型',
    category: '图像生成',
    icon: 'sparkles',
    tags: ['Z-Image', 'ComfyUI', '图像生成', '热加载', 'L40S', '真实人像'],
    scripts: [
      {
        name: 'Z-Image 主服务',
        fileName: 'z_image_app.py',
        description: 'ComfyUI + 热加载 API 完整服务',
        content: `"""
=============================================================================
Z-Image-Turbo ComfyUI 应用服务
=============================================================================
⚠️ 首次使用请先配置项目变量（点击项目标题旁的齿轮图标）:
  - VOLUME_NAME: 模型存储 Volume 名称
  - APP_NAME: Modal 应用名称（所有脚本共用）
  - GPU_TYPE: GPU 类型

特点：
- 启动后可随时添加模型，无需重启
- 内置热加载 API，下载模型后自动生效
- 支持中英文双语输入

使用方法:
    1. 配置项目变量
    2. 部署应用: modal deploy z_image_app.py
    3. 添加模型: 使用"添加模型"脚本
=============================================================================
"""
import os
import subprocess
from pathlib import Path

import modal

# =============================================================================
# 项目变量 - 在项目变量管理中配置
# =============================================================================
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:z-image-models}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:z-image-turbo}}"
GPU_TYPE = "{{GPU_TYPE:GPU 类型:L40S}}"

# =============================================================================
# Volume 和镜像配置
# =============================================================================
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "wget", "curl")
    .pip_install(
        "fastapi[standard]==0.115.4",
        "comfy-cli==1.5.3",
        "requests==2.32.3",
        "huggingface_hub[hf_transfer]==0.34.4"
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_commands("comfy --skip-prompt install --fast-deps --nvidia")
)

try:
    hf_secret = modal.Secret.from_name("huggingface-secret")
except modal.exception.NotFoundError:
    hf_secret = None

# 使用项目变量中的 APP_NAME
app = modal.App(name=APP_NAME, image=image)


def link_models_from_volume():
    """从 Volume 链接模型到 ComfyUI"""
    print("🔗 链接 Volume 中的模型...")
    
    volume_models = Path("/models")
    comfy_models = Path("/root/comfy/ComfyUI/models")
    
    if not volume_models.exists():
        print("   ℹ️ Volume 中暂无模型")
        return 0
    
    linked = 0
    model_types = ["checkpoints", "loras", "vae", "clip", "text_encoders", 
                   "diffusion_models", "controlnet", "upscale_models", "embeddings"]
    
    for model_type in model_types:
        src_dir = volume_models / model_type
        if not src_dir.exists():
            continue
        
        dst_dir = comfy_models / model_type
        dst_dir.mkdir(parents=True, exist_ok=True)
        
        for model_file in src_dir.iterdir():
            if model_file.name.startswith('.'):
                continue
            dst_path = dst_dir / model_file.name
            if not dst_path.exists() and not dst_path.is_symlink():
                os.symlink(str(model_file), str(dst_path))
                linked += 1
                print(f"   ✅ {model_type}/{model_file.name}")
    
    print(f"   📊 共链接 {linked} 个模型")
    return linked


@app.function(
    max_containers=1,
    gpu=GPU_TYPE,
    volumes={"/models": vol},
    timeout=86400
)
@modal.concurrent(max_inputs=10)
@modal.web_server(8000, startup_timeout=60)
def ui():
    """ComfyUI Web 界面"""
    print("🌐 启动 Z-Image-Turbo Web 界面...")
    link_models_from_volume()
    subprocess.Popen("comfy launch -- --listen 0.0.0.0 --port 8000", shell=True)


@app.cls(
    scaledown_window=300,
    gpu=GPU_TYPE,
    volumes={"/models": vol}
)
@modal.concurrent(max_inputs=5)
class ZImageAPI:
    """Z-Image-Turbo API 服务"""
    
    @modal.enter()
    def startup(self):
        print("🚀 启动 Z-Image-Turbo API 服务...")
        link_models_from_volume()
        subprocess.run("comfy launch --background -- --port 8000", shell=True, check=True)
    
    @modal.fastapi_endpoint(method="POST")
    def reload(self):
        """热加载模型 - 下载新模型后调用"""
        print("🔄 热加载请求...")
        try:
            vol.reload()
            count = link_models_from_volume()
            return {"success": True, "message": f"热加载完成，链接了 {count} 个新模型"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @modal.fastapi_endpoint(method="GET")
    def models(self):
        """列出所有可用模型"""
        vol.reload()
        models = {}
        volume_models = Path("/models")
        if volume_models.exists():
            for type_dir in volume_models.iterdir():
                if type_dir.is_dir():
                    files = [f.name for f in type_dir.iterdir() if not f.name.startswith('.')]
                    if files:
                        models[type_dir.name] = files
        return {"models": models, "total": sum(len(v) for v in models.values())}


@app.local_entrypoint()
def main():
    print("=" * 60)
    print(f"Z-Image-Turbo ComfyUI ({APP_NAME})")
    print("=" * 60)
    print(f"\\n📦 Volume: {VOLUME_NAME}")
    print(f"🖥️ GPU: {GPU_TYPE}")
    print("\\n📌 使用方法:")
    print("   1. 部署: modal deploy z_image_app.py")
    print("   2. 添加模型: 使用'添加模型'脚本")
    print(f"   3. 访问 UI: https://[workspace]--{APP_NAME}-ui.modal.run")
`
      },
      {
        name: '添加模型 (HuggingFace)',
        fileName: 'add_model_hf.py',
        description: '从 HuggingFace 下载模型到共享 Volume，支持自动热加载',
        content: `"""
=============================================================================
Z-Image-Turbo 添加模型 (HuggingFace)
=============================================================================
从 HuggingFace 下载模型到项目共享的 Volume

使用方法:
    modal run add_model_hf.py
=============================================================================
"""
import modal
import os
from pathlib import Path

# =============================================================================
# 项目变量 - 与主服务共享同一个 Volume
# =============================================================================
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:z-image-models}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:z-image-turbo}}"

# 脚本变量 - 每次执行时填写
HF_REPO_ID = "{{HF_REPO_ID:HuggingFace 仓库 ID:Comfy-Org/z_image_turbo}}"
HF_FILENAME = "{{HF_FILENAME:文件名:z_image_turbo.safetensors}}"
MODEL_TYPE = "{{MODEL_TYPE:模型类型:diffusion_models}}"

# =============================================================================
# 使用与主服务相同的 Volume
# =============================================================================
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

# 使用项目的 APP_NAME 作为前缀
app = modal.App(f"{APP_NAME}-downloader", image=image)


@app.function(
    volumes={"/models": vol},
    timeout=3600,
    secrets=[hf_secret] if hf_secret else []
)
def download_model():
    """从 HuggingFace 下载模型"""
    from huggingface_hub import hf_hub_download
    
    repo_id = HF_REPO_ID
    filename = HF_FILENAME
    model_type = MODEL_TYPE
    
    print(f"{'='*60}")
    print(f"📥 从 HuggingFace 下载模型")
    print(f"{'='*60}")
    print(f"仓库: {repo_id}")
    print(f"文件: {filename}")
    print(f"类型: {model_type}")
    print(f"Volume: {VOLUME_NAME}")
    
    if model_type not in MODEL_TYPES:
        return {"success": False, "error": f"不支持的类型: {model_type}"}
    
    # 只取文件名，忽略 HuggingFace 仓库中的子目录路径
    local_name = Path(filename).name
    
    target_dir = Path(f"/models/{model_type}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / local_name
    
    if target_file.exists():
        print(f"\\n⚠️ 模型已存在: {local_name}")
        return {"success": True, "action": "exists"}
    
    try:
        print(f"\\n⏳ 下载中...")
        hf_token = os.getenv("HF_TOKEN")
        
        cached_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            cache_dir="/tmp/hf_cache",
            token=hf_token
        )
        
        import shutil
        shutil.copy2(cached_path, str(target_file))
        vol.commit()
        
        size_mb = target_file.stat().st_size / (1024*1024)
        print(f"\\n✅ 下载成功!")
        print(f"   文件: {model_type}/{local_name}")
        print(f"   大小: {size_mb:.1f} MB")
        
        return {"success": True, "action": "downloaded", "size_mb": size_mb, "local_name": local_name}
        
    except Exception as e:
        print(f"\\n❌ 下载失败: {e}")
        return {"success": False, "error": str(e)}


def trigger_hot_reload():
    """触发主服务热加载"""
    print(f"\\n🔄 触发热加载...")
    
    try:
        # 尝试查找并调用已部署的 ZImageAPI.reload 方法
        ZImageAPI = modal.Cls.lookup(APP_NAME, "ZImageAPI")
        result = ZImageAPI().reload.remote()
        
        if result.get("success"):
            print(f"   ✅ 热加载成功!")
            return True
        else:
            print(f"   ⚠️ 热加载响应: {result}")
            return False
            
    except modal.exception.NotFoundError:
        print(f"   ⚠️ 主服务 ({APP_NAME}) 尚未部署")
        print(f"   💡 请先部署主服务: modal deploy z_image_app.py")
        return False
    except Exception as e:
        print(f"   ⚠️ 热加载失败: {e}")
        print(f"   💡 如果主服务未运行，模型将在下次启动时自动加载")
        return False


@app.local_entrypoint()
def main():
    print(f"\\n{'='*60}")
    print(f"Z-Image-Turbo 添加模型 ({APP_NAME})")
    print(f"{'='*60}")
    
    result = download_model.remote()
    
    if result.get("success"):
        if result.get("action") == "downloaded":
            print(f"\\n✅ 模型下载完成: {result.get('local_name')}")
            # 自动触发热加载
            trigger_hot_reload()
        else:
            print(f"\\n✅ 模型已存在，无需下载")
    else:
        print(f"\\n❌ 失败: {result.get('error')}")
`
      },
      {
        name: '添加模型 (URL)',
        fileName: 'add_model_url.py',
        description: '从 URL 直接下载模型到共享 Volume，支持自动热加载',
        content: `"""
=============================================================================
Z-Image-Turbo 添加模型 (URL)
=============================================================================
从 URL 直接下载模型到项目共享的 Volume

使用方法:
    modal run add_model_url.py
=============================================================================
"""
import modal
from pathlib import Path

# =============================================================================
# 项目变量 - 与主服务共享同一个 Volume
# =============================================================================
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:z-image-models}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:z-image-turbo}}"

# 脚本变量 - 每次执行时填写
MODEL_URL = "{{MODEL_URL:模型下载 URL:}}"
MODEL_FILENAME = "{{MODEL_FILENAME:保存的文件名:model.safetensors}}"
MODEL_TYPE = "{{MODEL_TYPE:模型类型:loras}}"

# =============================================================================
# 使用与主服务相同的 Volume
# =============================================================================
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

MODEL_TYPES = ["checkpoints", "loras", "vae", "clip", "text_encoders",
               "diffusion_models", "controlnet", "upscale_models", "embeddings"]

image = modal.Image.debian_slim(python_version="3.11").pip_install("requests", "tqdm")

app = modal.App(f"{APP_NAME}-url-downloader", image=image)


@app.function(volumes={"/models": vol}, timeout=3600)
def download_model():
    """从 URL 下载模型"""
    import requests
    from tqdm import tqdm
    
    url = MODEL_URL
    filename = MODEL_FILENAME
    model_type = MODEL_TYPE
    
    print(f"{'='*60}")
    print(f"📥 从 URL 下载模型")
    print(f"{'='*60}")
    print(f"URL: {url}")
    print(f"文件: {filename}")
    print(f"类型: {model_type}")
    print(f"Volume: {VOLUME_NAME}")
    
    if not url:
        return {"success": False, "error": "未提供下载 URL"}
    
    if model_type not in MODEL_TYPES:
        return {"success": False, "error": f"不支持的类型: {model_type}"}
    
    target_dir = Path(f"/models/{model_type}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename
    
    if target_file.exists():
        print(f"\\n⚠️ 模型已存在: {filename}")
        return {"success": True, "action": "exists"}
    
    try:
        print(f"\\n⏳ 下载中...")
        
        response = requests.get(url, stream=True, timeout=60)
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
        print(f"\\n✅ 下载成功!")
        print(f"   文件: {model_type}/{filename}")
        print(f"   大小: {size_mb:.1f} MB")
        
        return {"success": True, "action": "downloaded", "size_mb": size_mb, "filename": filename}
        
    except Exception as e:
        if target_file.exists():
            target_file.unlink()
        print(f"\\n❌ 下载失败: {e}")
        return {"success": False, "error": str(e)}


def trigger_hot_reload():
    """触发主服务热加载"""
    print(f"\\n🔄 触发热加载...")
    
    try:
        # 尝试查找并调用已部署的 ZImageAPI.reload 方法
        ZImageAPI = modal.Cls.lookup(APP_NAME, "ZImageAPI")
        result = ZImageAPI().reload.remote()
        
        if result.get("success"):
            print(f"   ✅ 热加载成功!")
            return True
        else:
            print(f"   ⚠️ 热加载响应: {result}")
            return False
            
    except modal.exception.NotFoundError:
        print(f"   ⚠️ 主服务 ({APP_NAME}) 尚未部署")
        print(f"   💡 请先部署主服务: modal deploy z_image_app.py")
        return False
    except Exception as e:
        print(f"   ⚠️ 热加载失败: {e}")
        print(f"   💡 如果主服务未运行，模型将在下次启动时自动加载")
        return False


@app.local_entrypoint()
def main():
    print(f"\\n{'='*60}")
    print(f"Z-Image-Turbo 添加模型 ({APP_NAME})")
    print(f"{'='*60}")
    
    result = download_model.remote()
    
    if result.get("success"):
        if result.get("action") == "downloaded":
            print(f"\\n✅ 模型下载完成: {result.get('filename')}")
            # 自动触发热加载
            trigger_hot_reload()
        else:
            print(f"\\n✅ 模型已存在，无需下载")
    else:
        print(f"\\n❌ 失败: {result.get('error')}")
`
      },
      {
        name: '添加模型 (本地上传)',
        fileName: 'add_model_local.py',
        description: '从本地上传模型文件到共享 Volume，支持自动热加载',
        content: `"""
=============================================================================
Z-Image-Turbo 添加模型 (本地上传)
=============================================================================
从本地上传模型文件到共享 Volume

使用方法:
    modal run add_model_local.py --local-path=./model.safetensors --type=loras
=============================================================================
"""
import modal
from pathlib import Path
import shutil

# =============================================================================
# 项目变量 - 与主服务共享同一个 Volume
# =============================================================================
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:z-image-models}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:z-image-turbo}}"

# 脚本变量 - 每次执行时填写
LOCAL_FILE_PATH = "{{LOCAL_FILE_PATH:本地文件路径:./model.safetensors}}"
MODEL_TYPE = "{{MODEL_TYPE:模型类型:loras}}"

# =============================================================================
# 使用与主服务相同的 Volume
# =============================================================================
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

MODEL_TYPES = ["checkpoints", "loras", "vae", "clip", "text_encoders",
               "diffusion_models", "controlnet", "upscale_models", "embeddings"]

image = modal.Image.debian_slim(python_version="3.11")

app = modal.App(f"{APP_NAME}-local-uploader", image=image)


@app.function(volumes={"/models": vol}, timeout=3600)
def upload_model(local_path: str, model_type: str):
    """将本地模型上传到 Volume"""
    
    print(f"{'='*60}")
    print(f"📤 上传本地模型到 Volume")
    print(f"{'='*60}")
    print(f"本地文件: {local_path}")
    print(f"类型: {model_type}")
    print(f"Volume: {VOLUME_NAME}")
    
    if model_type not in MODEL_TYPES:
        return {"success": False, "error": f"不支持的类型: {model_type}"}
    
    # 获取文件名
    filename = Path(local_path).name
    
    # 目标路径
    target_dir = Path(f"/models/{model_type}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename
    
    if target_file.exists():
        print(f"\\n⚠️ 模型已存在: {filename}")
        return {"success": True, "action": "exists"}
    
    try:
        print(f"\\n⏳ 上传中...")
        
        # 从挂载点复制文件到 Volume
        source_file = Path(local_path)
        if not source_file.exists():
            raise Exception(f"本地文件不存在: {local_path}")
        
        shutil.copy2(str(source_file), str(target_file))
        vol.commit()
        
        size_mb = target_file.stat().st_size / (1024*1024)
        print(f"\\n✅ 上传成功!")
        print(f"   文件: {model_type}/{filename}")
        print(f"   大小: {size_mb:.1f} MB")
        
        return {"success": True, "action": "uploaded", "size_mb": size_mb, "filename": filename}
        
    except Exception as e:
        # 清理失败的上传
        if target_file.exists():
            target_file.unlink()
        print(f"\\n❌ 上传失败: {e}")
        return {"success": False, "error": str(e)}


def trigger_hot_reload():
    """触发主服务热加载"""
    print(f"\\n🔄 触发热加载...")
    
    try:
        # 尝试查找并调用已部署的 ZImageAPI.reload 方法
        ZImageAPI = modal.Cls.lookup(APP_NAME, "ZImageAPI")
        result = ZImageAPI().reload.remote()
        
        if result.get("success"):
            print(f"   ✅ 热加载成功!")
            return True
        else:
            print(f"   ⚠️ 热加载响应: {result}")
            return False
            
    except modal.exception.NotFoundError:
        print(f"   ⚠️ 主服务 ({APP_NAME}) 尚未部署")
        print(f"   💡 请先部署主服务: modal deploy z_image_app.py")
        return False
    except Exception as e:
        print(f"   ⚠️ 热加载失败: {e}")
        print(f"   💡 如果主服务未运行，模型将在下次启动时自动加载")
        return False


@app.local_entrypoint()
def main(local_path: str = LOCAL_FILE_PATH, type: str = MODEL_TYPE):
    """
    本地入口
    
    使用方法:
        modal run add_model_local.py --local-path=./model.safetensors --type=loras
    """
    print(f"\\n{'='*60}")
    print(f"Z-Image-Turbo 上传本地模型 ({APP_NAME})")
    print(f"{'='*60}")
    
    # 验证本地文件存在
    if not Path(local_path).exists():
        print(f"\\n❌ 错误: 本地文件不存在: {local_path}")
        return
    
    # 创建文件挂载
    print(f"准备挂载本地文件...")
    local_file = Path(local_path).resolve()
    
    # 使用 Mount 将本地文件挂载到容器
    mount = modal.Mount.from_local_file(
        local_path=str(local_file),
        remote_path=f"/tmp/{local_file.name}"
    )
    
    # 运行上传函数，传入挂载后的路径
    with mount:
        result = upload_model.remote(f"/tmp/{local_file.name}", type)
    
    if result.get("success"):
        if result.get("action") == "uploaded":
            print(f"\\n✅ 模型上传完成: {result.get('filename')}")
            # 自动触发热加载
            trigger_hot_reload()
        else:
            print(f"\\n✅ 模型已存在，无需上传")
    else:
        print(f"\\n❌ 失败: {result.get('error')}")
`
      },
      {
        name: '模型管理',
        fileName: 'manage_models.py',
        description: '列出共享 Volume 中的所有模型',
        content: `"""
=============================================================================
Z-Image-Turbo 模型管理
=============================================================================
管理项目共享 Volume 中的模型：列出、删除

使用方法:
    modal run manage_models.py
=============================================================================
"""
import modal
from pathlib import Path

# =============================================================================
# 项目变量 - 与主服务共享同一个 Volume
# =============================================================================
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:z-image-models}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:z-image-turbo}}"

vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

MODEL_TYPES = ["checkpoints", "loras", "vae", "clip", "text_encoders",
               "diffusion_models", "controlnet", "upscale_models", "embeddings"]

image = modal.Image.debian_slim(python_version="3.11")

app = modal.App(f"{APP_NAME}-manager", image=image)


@app.function(volumes={"/models": vol})
def list_models():
    """列出所有模型"""
    print("=" * 60)
    print(f"📋 模型列表 (Volume: {VOLUME_NAME})")
    print("=" * 60)
    
    models = {}
    total = 0
    
    for model_type in MODEL_TYPES:
        type_dir = Path(f"/models/{model_type}")
        if type_dir.exists():
            files = []
            for f in type_dir.iterdir():
                if not f.name.startswith('.'):
                    try:
                        size = f.stat().st_size / (1024*1024)
                        files.append({"name": f.name, "size_mb": size})
                    except:
                        files.append({"name": f.name, "size_mb": 0})
            
            if files:
                models[model_type] = files
                total += len(files)
                print(f"\\n📁 {model_type}:")
                for f in files:
                    print(f"   - {f['name']} ({f['size_mb']:.1f} MB)")
    
    if not models:
        print("\\nℹ️ 暂无模型")
        print("\\n💡 使用'添加模型'脚本下载模型")
    
    print(f"\\n{'='*60}")
    print(f"📊 共 {total} 个模型")
    
    return {"models": models, "total": total}


@app.local_entrypoint()
def main():
    print(f"\\n{'='*60}")
    print(f"Z-Image-Turbo 模型管理 ({APP_NAME})")
    print(f"{'='*60}")
    list_models.remote()
`
      },
      {
        name: '诊断工具',
        fileName: 'diagnose.py',
        description: '检查共享 Volume 和服务状态',
        content: `"""
=============================================================================
Z-Image-Turbo 诊断工具
=============================================================================
检查项目共享 Volume 和服务状态

使用方法:
    modal run diagnose.py
=============================================================================
"""
import modal
from pathlib import Path

# =============================================================================
# 项目变量 - 与主服务共享
# =============================================================================
VOLUME_NAME = "{{VOLUME_NAME:模型存储 Volume:z-image-models}}"
APP_NAME = "{{APP_NAME:Modal 应用名称:z-image-turbo}}"

vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = modal.Image.debian_slim(python_version="3.11")

app = modal.App(f"{APP_NAME}-diagnose", image=image)


@app.function(volumes={"/models": vol})
def diagnose():
    """诊断系统状态"""
    print("=" * 60)
    print(f"🔍 Z-Image-Turbo 诊断报告")
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
    print("✅ 诊断完成")
    
    return {"success": True}


@app.local_entrypoint()
def main():
    print("\\n🔍 开始诊断 Z-Image-Turbo...")
    diagnose.remote()
`
      }
    ]
  },
  {
    id: 'wan21-t2v',
    name: 'Wan 2.1 文生视频',
    description: 'Wan 2.1 Text-to-Video，阿里巴巴开源视频生成模型，支持 14B/1.3B 参数',
    category: '视频生成',
    icon: 'sparkles',
    tags: ['Wan2.1', 'T2V', '文生视频', 'ComfyUI', 'L40S'],
    scripts: [
      {
        name: 'Wan 2.1 T2V 部署',
        fileName: 'wan21_t2v_deploy.py',
        description: '【一键部署】Wan 2.1 文生视频服务，自动下载模型并启动 ComfyUI',
        content: `# Wan 2.1 T2V 部署脚本
# 请使用 Modal Manager 创建项目后，脚本会自动从模板复制
# 部署命令: modal deploy wan21_t2v_deploy.py
`
      }
    ]
  },
  {
    id: 'postgresql-server',
    name: 'PostgreSQL 数据库',
    description: '部署持久化 PostgreSQL 数据库，支持复杂查询和事务',
    category: '数据存储',
    icon: 'box',
    tags: ['PostgreSQL', 'SQL', '数据库', '持久化'],
    scripts: [
      { name: 'PostgreSQL 服务', fileName: 'postgres_service.py', description: '部署 PostgreSQL 数据库服务', content: `# PostgreSQL 服务脚本` }
    ]
  },
  {
    id: 'mongodb-server',
    name: 'MongoDB 数据库',
    description: '部署 MongoDB 文档数据库，灵活的 JSON 存储',
    category: '数据存储',
    icon: 'box',
    tags: ['MongoDB', 'NoSQL', '文档数据库'],
    scripts: [
      { name: 'MongoDB 服务', fileName: 'mongodb_service.py', description: '部署 MongoDB 数据库服务', content: `# MongoDB 服务脚本` }
    ]
  },
  {
    id: 'minio-storage',
    name: 'MinIO 对象存储',
    description: '部署 S3 兼容的对象存储服务，适合文件存储',
    category: '数据存储',
    icon: 'box',
    tags: ['MinIO', 'S3', '对象存储', '文件'],
    scripts: [
      { name: 'MinIO 存储服务', fileName: 'minio_service.py', description: '部署 MinIO 对象存储', content: `# MinIO 服务脚本` }
    ]
  },
  {
    id: 'image-classification',
    name: '图像识别分类',
    description: '使用 ViT/ResNet 进行图像分类，商品分类和内容审核',
    category: 'AI服务',
    icon: 'sparkles',
    tags: ['图像分类', 'ViT', 'ResNet', 'CV'],
    scripts: [
      { name: '图像分类服务', fileName: 'image_classifier.py', description: '使用 ViT 进行图像分类', content: `# 图像分类脚本` }
    ]
  },
  {
    id: 'ocr-service',
    name: 'OCR 文字识别',
    description: '使用 EasyOCR 识别图片中的文字，支持中英文',
    category: 'AI服务',
    icon: 'sparkles',
    tags: ['OCR', '文字识别', 'EasyOCR', '中英文'],
    scripts: [
      { name: 'OCR 识别服务', fileName: 'ocr_service.py', description: '图片文字识别', content: `# OCR 服务脚本` }
    ]
  },
  {
    id: 'sentiment-analysis',
    name: '情感分析',
    description: '分析文本情感倾向，适合评论分析和舆情监控',
    category: 'AI服务',
    icon: 'sparkles',
    tags: ['情感分析', 'NLP', '评论', '舆情'],
    scripts: [
      { name: '情感分析服务', fileName: 'sentiment_service.py', description: '分析文本情感（正面/负面）', content: `# 情感分析脚本` }
    ]
  },
  {
    id: 'rabbitmq-server',
    name: 'RabbitMQ 消息队列',
    description: '部署消息队列服务，支持异步任务和服务解耦',
    category: '基础设施',
    icon: 'box',
    tags: ['RabbitMQ', '消息队列', 'AMQP', '异步'],
    scripts: [
      { name: 'RabbitMQ 服务', fileName: 'rabbitmq_service.py', description: '部署 RabbitMQ 消息队列', content: `# RabbitMQ 服务脚本` }
    ]
  },
  {
    id: 'celery-tasks',
    name: 'Celery 任务队列',
    description: '分布式任务队列，支持异步任务和定时任务',
    category: '基础设施',
    icon: 'box',
    tags: ['Celery', '任务队列', '分布式', '定时任务'],
    scripts: [
      { name: 'Celery 任务服务', fileName: 'celery_service.py', description: '分布式任务处理', content: `# Celery 服务脚本` }
    ]
  },
  {
    id: 'api-gateway',
    name: 'API 网关',
    description: '统一 API 入口，支持限流、认证、路由转发',
    category: '基础设施',
    icon: 'box',
    tags: ['API网关', '限流', '认证', '路由'],
    scripts: [
      { name: 'API 网关服务', fileName: 'gateway_service.py', description: '统一 API 入口和流量控制', content: `# API 网关脚本` }
    ]
  },
  {
    id: 'modal-basics',
    name: 'Modal 完整入门教程',
    description: '从零开始学习 Modal，包含 14 个循序渐进的实战案例：基础功能 + 真实业务场景',
    category: '入门教程',
    icon: 'zap',
    tags: ['入门', '教程', '完整体系', '实战', '业务场景'],
    scripts: [
      { name: '01 - Hello Modal', fileName: '01_hello_modal.py', description: '最简单的云函数调用，理解 Modal 基本概念', content: `# Hello Modal 脚本` },
      { name: '02 - 并行计算', fileName: '02_parallel_computing.py', description: '学习如何并行处理任务，体验云计算的性能优势', content: `# 并行计算脚本` },
      { name: '03 - Web API', fileName: '03_web_api.py', description: '将函数暴露为 HTTP API，构建 Web 服务', content: `# Web API 脚本` },
      { name: '04 - 数据持久化', fileName: '04_volume_storage.py', description: '使用 Volume 持久化存储数据，实现文件读写', content: `# Volume 存储脚本` },
      { name: '05 - 定时任务', fileName: '05_scheduled_tasks.py', description: '设置定时任务，自动化执行周期性工作', content: `# 定时任务脚本` },
      { name: '06 - GPU 计算', fileName: '06_gpu_computing.py', description: '使用 GPU 加速计算，对比 CPU 和 GPU 性能', content: `# GPU 计算脚本` },
      { name: '07 - 电商销售报表', fileName: '07_ecommerce_report.py', description: '解决：每天手动统计销售数据耗时易错，自动化生成日报', content: `# 电商报表脚本` },
      { name: '08 - 网站可用性监控', fileName: '08_website_monitor.py', description: '解决：网站宕机无法及时发现，24/7 自动监控告警', content: `# 网站监控脚本` },
      { name: '09 - 批量图片水印', fileName: '09_image_watermark.py', description: '解决：大量图片需要添加版权水印，本地处理太慢', content: `# 图片水印脚本` },
      { name: '10 - 竞品价格监控', fileName: '10_price_tracker.py', description: '解决：竞争对手调价后不能及时发现，错失反应时机', content: `# 价格监控脚本` },
      { name: '11 - 日志分析异常检测', fileName: '11_log_analyzer.py', description: '解决：海量服务器日志中发现问题如大海捞针', content: `# 日志分析脚本` },
      { name: '12 - 短链接追踪服务', fileName: '12_url_shortener.py', description: '解决：营销链接太长且无法追踪点击效果', content: `# 短链接脚本` },
      { name: '13 - PDF 批量处理', fileName: '13_pdf_processor.py', description: '解决：HR/财务需要批量合并、拆分、加水印 PDF', content: `# PDF处理脚本` },
      { name: '14 - 多渠道通知服务', fileName: '14_notification_service.py', description: '解决：活动期间需要快速发送大量用户通知', content: `# 通知服务脚本` }
    ]
  }
];

// ============================================================================
// 主组件
// ============================================================================

export default function TemplateLibrary() {
  const navigate = useNavigate();

  // Tab 状态
  const [activeTab, setActiveTab] = useState<'project' | 'script'>('project');

  // 项目模板状态
  const [apps, setApps] = useState<main.ModalApp[]>([]);
  const [projects, setProjects] = useState<main.Project[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<ProjectTemplate | null>(null);
  const [selectedAppId, setSelectedAppId] = useState('');
  const [projectName, setProjectName] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [projectFilter, setProjectFilter] = useState<string>('all');

  // 脚本模板状态
  const [scriptFilter, setScriptFilter] = useState<string>('全部');
  const [selectedScriptTemplate, setSelectedScriptTemplate] = useState<ScriptTemplate | null>(null);
  const [showVariableDialog, setShowVariableDialog] = useState(false);
  const [showUseTemplateDialog, setShowUseTemplateDialog] = useState(false);
  const [targetProjectId, setTargetProjectId] = useState('');
  const [scriptFileName, setScriptFileName] = useState('');
  const [createMode, setCreateMode] = useState<'configure' | 'template'>('configure');

  useEffect(() => {
    loadApps();
    loadProjects();
  }, []);

  const loadApps = async () => {
    const data = await GetModalAppList();
    setApps(data || []);
  };

  const loadProjects = async () => {
    const data = await GetProjects();
    setProjects(data || []);
  };

  // 项目模板分类
  const projectCategories = ['all', ...Array.from(new Set(projectTemplates.map(t => t.category)))];
  const filteredProjectTemplates = projectFilter === 'all'
    ? projectTemplates
    : projectTemplates.filter(t => t.category === projectFilter);

  // 脚本模板分类
  const scriptCategories = getScriptTemplateCategories();
  const filteredScriptTemplates = filterScriptTemplates(scriptFilter);

  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'box': return Box;
      case 'sparkles': return Sparkles;
      case 'zap': return Zap;
      default: return Code;
    }
  };

  // 项目模板处理
  const handleSelectProjectTemplate = (template: ProjectTemplate) => {
    console.log('[TemplateLibrary] 选择项目模板:', { id: template.id, name: template.name, scriptsCount: template.scripts.length });
    setSelectedTemplate(template);
    setProjectName(template.name);
    if (apps.length === 1) {
      setSelectedAppId(apps[0].id);
    }
  };

  const handleCreateProject = async () => {
    if (!selectedTemplate || !projectName || !selectedAppId) {
      console.warn('[TemplateLibrary] 创建项目校验失败: 信息不完整');
      alert('请填写完整信息');
      return;
    }

    setIsCreating(true);
    console.log('[TemplateLibrary] 开始从模板创建项目:', {
      templateId: selectedTemplate.id,
      templateName: selectedTemplate.name,
      projectName,
      appId: selectedAppId
    });

    try {
      await CreateProjectFromTemplate(selectedTemplate.id, projectName, selectedAppId);
      console.log('[TemplateLibrary] 项目创建成功:', projectName);
      alert('项目创建成功！');
      setSelectedTemplate(null);
      setProjectName('');
      navigate('/');
    } catch (err: any) {
      console.error('[TemplateLibrary] 项目创建失败:', err);
      // 提取详细错误信息
      const errorMessage = typeof err === 'string' ? err : (err.message || err.toString() || '未知错误');
      alert(`创建失败: ${errorMessage}`);
    } finally {
      setIsCreating(false);
    }
  };

  // 脚本模板处理
  const handleSelectScriptTemplate = (template: ScriptTemplate) => {
    console.log('[TemplateLibrary] 选择脚本模板:', { id: template.id, name: template.name, variableCount: template.variables.length });
    setSelectedScriptTemplate(template);
    // 默认文件名
    const defaultFileName = template.id.replace(/-/g, '_') + '.py';
    setScriptFileName(defaultFileName);
  };

  const handleUseScriptTemplate = async () => {
    if (!targetProjectId) {
      console.warn('[TemplateLibrary] 脚本创建校验失败: 未选择目标项目');
      alert('请选择目标项目');
      return;
    }
    if (!scriptFileName.trim()) {
      console.warn('[TemplateLibrary] 脚本创建校验失败: 未输入文件名');
      alert('请输入脚本文件名');
      return;
    }
    if (!selectedScriptTemplate) return;

    const hasVariables = selectedScriptTemplate.variables.length > 0;

    console.log('[TemplateLibrary] 使用脚本模板:', {
      templateId: selectedScriptTemplate.id,
      templateName: selectedScriptTemplate.name,
      targetProjectId,
      scriptFileName,
      createMode,
      hasVariables,
      variableCount: selectedScriptTemplate.variables.length
    });

    if (createMode === 'configure' && hasVariables) {
      // 模式 A + 有变量: 弹出变量表单，填写后创建独立脚本
      console.log('[TemplateLibrary] 打开变量配置对话框');
      setShowVariableDialog(true);
    } else {
      // 模式 A 无变量 或 模式 B: 直接保存内容
      setIsCreating(true);
      try {
        const fileName = scriptFileName.endsWith('.py') ? scriptFileName : `${scriptFileName}.py`;
        const isTemplate = createMode === 'template' && hasVariables;

        console.log('[TemplateLibrary] 调用后端创建脚本:', {
          fileName,
          isTemplate,
          contentLength: selectedScriptTemplate.content.length
        });

        await CreateScript(
          targetProjectId,
          selectedScriptTemplate.name,
          fileName,
          isTemplate ? selectedScriptTemplate.description + ' [模板脚本]' : selectedScriptTemplate.description,
          selectedScriptTemplate.content  // 原始内容
        );

        console.log('[TemplateLibrary] 脚本创建成功:', fileName);
        alert(isTemplate ? '模板脚本创建成功！部署时将提示填写参数。' : '脚本创建成功！');
        setShowUseTemplateDialog(false);
        setSelectedScriptTemplate(null);
        setTargetProjectId('');
        setCreateMode('configure');

        navigate(`/project/${targetProjectId}`);
      } catch (err: any) {
        console.error('[TemplateLibrary] 脚本创建失败:', err);
        // 提取详细错误信息
        const errorMessage = typeof err === 'string' ? err : (err.message || err.toString() || '未知错误');
        alert(`创建失败: ${errorMessage}`);
      } finally {
        setIsCreating(false);
      }
    }
  };

  const handleVariableConfirm = async (finalContent: string, values: Record<string, string>) => {
    if (!selectedScriptTemplate || !targetProjectId) return;

    setIsCreating(true);
    console.log('[TemplateLibrary] 变量配置完成，开始创建脚本:', {
      templateName: selectedScriptTemplate.name,
      targetProjectId,
      values,
      contentLength: finalContent.length
    });

    try {
      // 确保文件名以 .py 结尾
      const fileName = scriptFileName.endsWith('.py') ? scriptFileName : `${scriptFileName}.py`;

      console.log('[TemplateLibrary] 调用后端创建脚本:', fileName);

      // 创建脚本
      await CreateScript(
        targetProjectId,
        selectedScriptTemplate.name,
        fileName,
        selectedScriptTemplate.description,
        finalContent
      );

      console.log('[TemplateLibrary] 脚本创建成功 (变量已替换):', fileName);
      alert('脚本创建成功！');
      setShowVariableDialog(false);
      setShowUseTemplateDialog(false);
      setSelectedScriptTemplate(null);
      setTargetProjectId('');

      // 跳转到项目页面
      navigate(`/project/${targetProjectId}`);
    } catch (err: any) {
      console.error('[TemplateLibrary] 脚本创建失败:', err);
      // 提取详细错误信息
      const errorMessage = typeof err === 'string' ? err : (err.message || err.toString() || '未知错误');
      alert(`创建失败: ${errorMessage}`);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h1 className="text-lg font-bold text-gray-800 flex items-center gap-2">
            <BookTemplate className="w-5 h-5 text-primary-500" />
            模板库
          </h1>
          <p className="text-gray-500 text-xs">选择模板快速创建项目或脚本</p>
        </div>
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-1 mb-4 bg-gray-100 p-1 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab('project')}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-all',
            activeTab === 'project'
              ? 'bg-white text-primary-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          )}
        >
          <Folder className="w-4 h-4" />
          项目模板
        </button>
        <button
          onClick={() => setActiveTab('script')}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-all',
            activeTab === 'script'
              ? 'bg-white text-primary-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-800'
          )}
        >
          <FileCode className="w-4 h-4" />
          脚本模板
          <span className="px-1.5 py-0.5 text-xs bg-primary-100 text-primary-600 rounded">
            {scriptTemplates.length}
          </span>
        </button>
      </div>

      {/* ========== 项目模板 Tab ========== */}
      {activeTab === 'project' && (
        <>
          {/* 分类过滤 */}
          <div className="flex gap-2 mb-4">
            {projectCategories.map(cat => (
              <button
                key={cat}
                onClick={() => setProjectFilter(cat)}
                className={clsx(
                  'px-3 py-1.5 text-sm rounded-lg transition-colors',
                  projectFilter === cat
                    ? 'bg-primary-500 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                )}
              >
                {cat === 'all' ? '全部' : cat}
              </button>
            ))}
          </div>

          {/* 项目模板网格 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredProjectTemplates.map((template) => {
              const Icon = getIcon(template.icon);
              return (
                <Card
                  key={template.id}
                  className="cursor-pointer hover:-translate-y-1 transition-all p-4"
                  onClick={() => handleSelectProjectTemplate(template)}
                >
                  <div className="flex items-start gap-3 mb-3">
                    <div className="p-2 bg-primary-100 rounded-lg shrink-0">
                      <Icon className="w-5 h-5 text-primary-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-semibold text-gray-800 mb-1">{template.name}</h3>
                      <p className="text-xs text-gray-500 line-clamp-2">{template.description}</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1 mb-3">
                    {template.tags.slice(0, 4).map(tag => (
                      <span key={tag} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                        {tag}
                      </span>
                    ))}
                  </div>
                  <div className="text-xs text-gray-500">
                    {template.scripts.length} 个脚本
                  </div>
                </Card>
              );
            })}
          </div>
        </>
      )}

      {/* ========== 脚本模板 Tab ========== */}
      {activeTab === 'script' && (
        <>
          {/* 分类过滤 */}
          <div className="flex gap-2 mb-4">
            {scriptCategories.map(cat => (
              <button
                key={cat}
                onClick={() => setScriptFilter(cat)}
                className={clsx(
                  'px-3 py-1.5 text-sm rounded-lg transition-colors',
                  scriptFilter === cat
                    ? 'bg-primary-500 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                )}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* 脚本模板网格 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredScriptTemplates.map((template) => (
              <Card
                key={template.id}
                className="cursor-pointer hover:-translate-y-1 transition-all p-4"
                onClick={() => handleSelectScriptTemplate(template)}
              >
                <div className="flex items-start gap-3 mb-3">
                  <div className="p-2 bg-amber-100 rounded-lg shrink-0">
                    <FileCode className="w-5 h-5 text-amber-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-gray-800 mb-1">{template.name}</h3>
                    <p className="text-xs text-gray-500 line-clamp-2">{template.description}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1 mb-3">
                  {template.tags.slice(0, 4).map(tag => (
                    <span key={tag} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <Variable className="w-3.5 h-3.5" />
                  {template.variables.length} 个参数
                </div>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* ========== 创建项目弹窗 ========== */}
      {selectedTemplate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setSelectedTemplate(null)}>
          <Card className="w-full max-w-md animate-slide-in" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-primary-100 rounded-lg">
                {(() => {
                  const Icon = getIcon(selectedTemplate.icon);
                  return <Icon className="w-5 h-5 text-primary-600" />;
                })()}
              </div>
              <div>
                <h2 className="text-base font-bold text-gray-800">创建项目</h2>
                <p className="text-xs text-gray-500">{selectedTemplate.name}</p>
              </div>
            </div>

            <div className="space-y-3 mb-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">项目名称 *</label>
                <input
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="输入项目名称"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">关联应用 *</label>
                <select
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={selectedAppId}
                  onChange={(e) => setSelectedAppId(e.target.value)}
                >
                  <option value="">请选择应用</option>
                  {apps.map((app) => (
                    <option key={app.id} value={app.id}>
                      {app.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs font-medium text-gray-700 mb-2">包含的脚本:</p>
                <div className="space-y-1">
                  {selectedTemplate.scripts.map((script, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-xs text-gray-600">
                      <Check className="w-3 h-3 text-green-500" />
                      <span>{script.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="secondary" size="sm" onClick={() => setSelectedTemplate(null)}>
                取消
              </Button>
              <Button size="sm" onClick={handleCreateProject} disabled={isCreating}>
                <Plus className="w-3 h-3 mr-1" />
                {isCreating ? '创建中...' : '创建项目'}
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* ========== 脚本模板详情弹窗 ========== */}
      {selectedScriptTemplate && !showVariableDialog && !showUseTemplateDialog && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => { setSelectedScriptTemplate(null); setShowUseTemplateDialog(false); }}>
          <Card className="w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col animate-slide-in" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gradient-to-r from-amber-50 to-white shrink-0">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-100 rounded-lg">
                  <FileCode className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-gray-800">{selectedScriptTemplate.name}</h2>
                  <p className="text-xs text-gray-500">{selectedScriptTemplate.category}</p>
                </div>
              </div>
              <button
                onClick={() => { setSelectedScriptTemplate(null); setShowUseTemplateDialog(false); }}
                className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
              {/* 描述 */}
              <p className="text-sm text-gray-600 mb-4">{selectedScriptTemplate.description}</p>

              {/* 标签 */}
              <div className="flex flex-wrap gap-1 mb-4">
                {selectedScriptTemplate.tags.map(tag => (
                  <span key={tag} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded">
                    {tag}
                  </span>
                ))}
              </div>

              {/* 变量列表 */}
              <div className="bg-amber-50 rounded-lg p-4 mb-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <Variable className="w-4 h-4 text-amber-600" />
                  模板参数 ({selectedScriptTemplate.variables.length})
                </h3>
                <div className="space-y-2">
                  {selectedScriptTemplate.variables.map((v, idx) => (
                    <div key={idx} className="bg-white rounded-lg p-3 border border-amber-200">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">{v.label}</span>
                        {v.required && (
                          <span className="text-xs text-red-500">必填</span>
                        )}
                      </div>
                      <code className="text-xs text-amber-600 bg-amber-100 px-1.5 py-0.5 rounded mt-1 inline-block">
                        {`{{${v.name}}}`}
                      </code>
                      {v.defaultValue && (
                        <p className="text-xs text-gray-400 mt-1">
                          默认值: {v.defaultValue}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* 代码预览 */}
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                  <Code className="w-4 h-4" />
                  脚本预览
                </h3>
                <div className="rounded-lg overflow-hidden max-h-80 overflow-y-auto">
                  <SyntaxHighlighter
                    language="python"
                    style={vscDarkPlus}
                    customStyle={{
                      margin: 0,
                      padding: '1rem',
                      fontSize: '0.75rem',
                      lineHeight: '1.5',
                      borderRadius: '0.5rem',
                    }}
                    showLineNumbers
                    lineNumberStyle={{
                      minWidth: '2.5em',
                      paddingRight: '1em',
                      color: '#6b7280',
                      userSelect: 'none',
                    }}
                  >
                    {selectedScriptTemplate.content.length > 3000
                      ? selectedScriptTemplate.content.slice(0, 3000) + '\n\n# ... (内容已截断)'
                      : selectedScriptTemplate.content}
                  </SyntaxHighlighter>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 bg-gray-50 shrink-0">
              <Button variant="secondary" size="sm" onClick={() => { setSelectedScriptTemplate(null); setShowUseTemplateDialog(false); }}>
                关闭
              </Button>
              <Button size="sm" onClick={() => setShowUseTemplateDialog(true)}>
                <Plus className="w-3 h-3 mr-1" />
                使用此模板
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* ========== 使用脚本模板弹窗 ========== */}
      {selectedScriptTemplate && showUseTemplateDialog && !showVariableDialog && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowUseTemplateDialog(false)}>
          <Card className="w-full max-w-md animate-slide-in" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-amber-100 rounded-lg">
                <FileCode className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <h2 className="text-base font-bold text-gray-800">使用脚本模板</h2>
                <p className="text-xs text-gray-500">{selectedScriptTemplate.name}</p>
              </div>
            </div>

            <div className="space-y-4 mb-4">
              {/* 选择目标项目 */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">目标项目 *</label>
                <select
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={targetProjectId}
                  onChange={(e) => setTargetProjectId(e.target.value)}
                >
                  <option value="">请选择项目</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* 脚本文件名 */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">脚本文件名 *</label>
                <input
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={scriptFileName}
                  onChange={(e) => setScriptFileName(e.target.value)}
                  placeholder="例如: add_node.py"
                />
              </div>

              {/* 创建模式选择 */}
              <div className="space-y-2">
                <label className="block text-xs font-medium text-gray-700">创建方式</label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="createMode"
                      checked={createMode === 'configure'}
                      onChange={() => setCreateMode('configure')}
                      className="text-primary-500 focus:ring-primary-500"
                    />
                    <span className="text-sm text-gray-700">立即配置参数</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="createMode"
                      checked={createMode === 'template'}
                      onChange={() => setCreateMode('template')}
                      className="text-primary-500 focus:ring-primary-500"
                    />
                    <span className="text-sm text-gray-700">保留为模板</span>
                  </label>
                </div>
                <div className={clsx(
                  "rounded-lg p-3 text-xs",
                  createMode === 'configure' ? "bg-blue-50 text-blue-700" : "bg-amber-50 text-amber-700"
                )}>
                  {selectedScriptTemplate.variables.length > 0 ? (
                    createMode === 'configure'
                      ? `现在填写 ${selectedScriptTemplate.variables.length} 个参数，创建独立脚本（变量将被替换）`
                      : `保留变量占位符，每次部署时弹窗填写参数`
                  ) : (
                    createMode === 'configure'
                      ? '此模板无需配置参数，将直接创建脚本'
                      : '保留原始模板内容'
                  )}
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="secondary" size="sm" onClick={() => setShowUseTemplateDialog(false)}>
                返回
              </Button>
              <Button size="sm" onClick={handleUseScriptTemplate} disabled={isCreating}>
                {createMode === 'configure' ? (
                  <>
                    <Variable className="w-3 h-3 mr-1" />
                    配置参数
                  </>
                ) : (
                  <>
                    <Check className="w-3 h-3 mr-1" />
                    {isCreating ? '创建中...' : '创建模板脚本'}
                  </>
                )}
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* ========== 变量表单弹窗 ========== */}
      {showVariableDialog && selectedScriptTemplate && (
        <VariableFormDialog
          templateName={selectedScriptTemplate.name}
          templateContent={selectedScriptTemplate.content}
          variables={selectedScriptTemplate.variables}
          onClose={() => setShowVariableDialog(false)}
          onConfirm={handleVariableConfirm}
        />
      )}
    </div>
  );
}
