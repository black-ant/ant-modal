#!/usr/bin/env python3
"""
=============================================================================
ComfyUI 服务配置脚本
=============================================================================
功能说明：
- 生成默认的 workflow_api.json 配置文件
- 配置 Modal Volume 持久化存储
- 设置环境变量和 HuggingFace Secrets
- 准备服务运行所需的基础配置

使用方法：
    modal run configure_service.py

独立运行：
    此脚本可独立运行，创建服务所需的配置文件
=============================================================================
"""

import json
from pathlib import Path
import modal

# =============================================================================
# S1: 默认 Workflow 配置
# =============================================================================

def create_default_workflow():
    """创建默认的 Flux 文本生成图像 Workflow"""
    
    # 基础的 Flux 工作流配置
    # 这是一个简化的 ComfyUI workflow，用于文本生成图像
    workflow = {
        "3": {
            "inputs": {
                "seed": 156680208700286,
                "steps": 20,
                "cfg": 3.5,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler",
            "_meta": {"title": "KSampler"}
        },
        "4": {
            "inputs": {
                "ckpt_name": "flux1-dev-fp8.safetensors"
            },
            "class_type": "CheckpointLoaderSimple",
            "_meta": {"title": "Load Checkpoint"}
        },
        "5": {
            "inputs": {
                "width": 1024,
                "height": 1024,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage",
            "_meta": {"title": "Empty Latent Image"}
        },
        "6": {
            "inputs": {
                "text": "A beautiful landscape with mountains and a lake at sunset",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "CLIP Text Encode (Prompt)"}
        },
        "7": {
            "inputs": {
                "text": "",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {"title": "CLIP Text Encode (Negative)"}
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode",
            "_meta": {"title": "VAE Decode"}
        },
        "9": {
            "inputs": {
                "filename_prefix": "ComfyUI",
                "images": ["8", 0]
            },
            "class_type": "SaveImage",
            "_meta": {"title": "Save Image"}
        }
    }
    
    return workflow

# =============================================================================
# S2: 配置生成函数
# =============================================================================

def generate_config():
    """生成服务配置文件"""
    
    print("🔧 生成 ComfyUI 服务配置...")
    
    # S2.1: 创建 workflow_api.json
    print("📄 创建 workflow_api.json...")
    workflow = create_default_workflow()
    
    workflow_path = Path("/root/workflow_api.json")
    workflow_path.write_text(json.dumps(workflow, indent=2))
    print(f"   ✅ Workflow 配置已保存到: {workflow_path}")
    
    # S2.2: 验证配置
    print("🔍 验证配置文件...")
    if workflow_path.exists():
        size = workflow_path.stat().st_size
        print(f"   ✅ 文件大小: {size} bytes")
        print(f"   ✅ 节点数量: {len(workflow)} 个")
    
    # S2.3: 显示配置摘要
    print("\n📊 配置摘要:")
    print(f"   - 主模型: flux1-dev-fp8.safetensors")
    print(f"   - 默认尺寸: 1024x1024")
    print(f"   - 采样步数: 20")
    print(f"   - CFG Scale: 3.5")
    print(f"   - 采样器: euler")
    
    print("\n✅ 服务配置生成完成！")
    return {"status": "success", "workflow_path": str(workflow_path)}

# =============================================================================
# S3: 构建配置镜像
# =============================================================================

# 基础镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install("comfy-cli==1.5.1")
    .run_commands("comfy --skip-prompt install --fast-deps --nvidia --version 0.3.59")
)

# 生成配置文件
image = image.run_function(generate_config)

# HuggingFace Secret 配置
try:
    hf_secret = modal.Secret.from_name("huggingface-secret")
    print("✅ HuggingFace Secret 已配置")
except:
    print("⚠️  HuggingFace Secret 未配置，部分功能可能受限")
    hf_secret = None

# Volume 持久化存储
vol = modal.Volume.from_name("hf-hub-cache", create_if_missing=True)
print("✅ Volume 持久化存储已配置")

# =============================================================================
# S4: 创建 Modal 应用
# =============================================================================

app = modal.App(name="comfyui-service-config", image=image)

print("\n✅ 服务配置镜像构建完成！")
print("💡 提示：配置文件可用于后续的服务部署")


@app.function()
def show_config():
    """显示当前配置"""
    import json
    
    workflow_path = Path("/root/workflow_api.json")
    
    if workflow_path.exists():
        workflow = json.loads(workflow_path.read_text())
        
        print("📋 当前 Workflow 配置:")
        print(f"   - 文件路径: {workflow_path}")
        print(f"   - 节点数量: {len(workflow)}")
        print(f"   - 主模型: {workflow['4']['inputs']['ckpt_name']}")
        print(f"   - 图像尺寸: {workflow['5']['inputs']['width']}x{workflow['5']['inputs']['height']}")
        
        return {"status": "success", "nodes": len(workflow)}
    else:
        print("❌ 配置文件不存在")
        return {"status": "error", "message": "Config file not found"}


@app.local_entrypoint()
def main():
    """本地入口点"""
    print("🚀 显示服务配置...")
    result = show_config.remote()
    print(f"\n📊 结果: {result}")

