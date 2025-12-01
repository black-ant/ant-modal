#!/usr/bin/env python3
"""
=============================================================================
ComfyUI 完整部署脚本
=============================================================================
功能说明：
- 整合所有模块，构建完整的生产环境镜像
- 部署 UI 服务（Web界面，端口 8000，L40S GPU）
- 部署 API 服务（FastAPI 端点，支持 HTTP 请求）
- 实现健康检查和并发控制
- 支持图像生成的完整工作流

环境要求：
    - HuggingFace Secret: huggingface-secret
    - Modal Volume: hf-hub-cache

使用方法：
    # 部署到生产环境
    modal deploy deploy_complete.py
    
    # 开发模式（热重载）
    modal serve deploy_complete.py

独立运行：
    此脚本包含完整的 ComfyUI 部署，可一键部署生产环境
=============================================================================
"""

import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Dict

import modal
import modal.experimental

# =============================================================================
# S1: 构建完整镜像
# =============================================================================

print("🔧 开始构建 ComfyUI 完整部署镜像...")

# S1.1: 基础环境
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install("fastapi[standard]==0.115.4")
    .pip_install("comfy-cli==1.5.1")
    .run_commands(
        "python -m pip uninstall llama-cpp-python -y || true",
        "pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124"
    )
    .pip_install("requests==2.32.3")
    .run_commands("comfy --skip-prompt install --fast-deps --nvidia --version 0.3.59")
)

# S1.2: 安装自定义节点
print("📦 安装自定义节点...")
image = image.run_commands(
    "comfy node install --fast-deps was-node-suite-comfyui@1.0.2",
    "git clone https://github.com/judian17/ComfyUI-joycaption-beta-one-GGUF.git /root/comfy/ComfyUI/custom_nodes/ComfyUI-joycaption-beta-one-GGUF"
)

# S1.3: 配置 HuggingFace
hf_secret = modal.Secret.from_name("huggingface-secret")
vol = modal.Volume.from_name("hf-hub-cache", create_if_missing=True)

# =============================================================================
# S2: 模型下载（整合所有模型）
# =============================================================================

def download_all_models():
    """下载所有必需的模型文件"""
    from huggingface_hub import hf_hub_download
    import requests
    
    hf_token = os.getenv("HF_TOKEN")
    print(f"🔑 HuggingFace Token: {'已配置 ✅' if hf_token else '未配置 ❌'}")
    
    # S2.1: 基础模型
    print("\n📥 [1/5] 下载基础模型...")
    try:
        flux_model = hf_hub_download(
            repo_id="Comfy-Org/flux1-dev",
            filename="flux1-dev-fp8.safetensors",
            cache_dir="/cache",
        )
        subprocess.run(
            f"ln -sf {flux_model} /root/comfy/ComfyUI/models/checkpoints/flux1-dev-fp8.safetensors",
            shell=True, check=True
        )
        print("   ✅ Flux1-dev 主模型")
    except Exception as e:
        print(f"   ❌ Flux1-dev 失败: {e}")
    
    # S2.2: Clip 模型
    print("\n📥 [2/5] 下载 Clip 模型...")
    clip_models = [
        ("stabilityai/stable-diffusion-3-medium", "text_encoders/clip_g.safetensors", "clip_g.safetensors"),
        ("stabilityai/stable-diffusion-3-medium", "text_encoders/clip_l.safetensors", "clip_l.safetensors"),
        ("stabilityai/stable-diffusion-3-medium", "text_encoders/t5xxl_fp8_e4m3fn.safetensors", "t5xxl_fp8_e4m3fn.safetensors"),
    ]
    
    clip_dir = "/root/comfy/ComfyUI/models/clip"
    os.makedirs(clip_dir, exist_ok=True)
    
    for repo_id, filename, local_name in clip_models:
        try:
            clip_path = hf_hub_download(repo_id=repo_id, filename=filename, cache_dir="/cache", token=hf_token)
            subprocess.run(f"ln -sf {clip_path} {clip_dir}/{local_name}", shell=True, check=True)
            print(f"   ✅ {local_name}")
        except Exception as e:
            print(f"   ❌ {local_name}: {e}")
    
    # S2.3: VAE 模型
    print("\n📥 [3/5] 下载 VAE 模型...")
    try:
        vae_model = hf_hub_download(
            repo_id="black-forest-labs/FLUX.1-dev",
            filename="ae.safetensors",
            cache_dir="/cache",
            token=hf_token
        )
        subprocess.run(
            f"ln -sf {vae_model} /root/comfy/ComfyUI/models/vae/ae.safetensors",
            shell=True, check=True
        )
        print("   ✅ VAE 模型")
    except Exception as e:
        print(f"   ❌ VAE 失败: {e}")
    
    # S2.4: LoRA 模型
    print("\n📥 [4/5] 下载 LoRA 模型...")
    lora_models = [
        ("UmeAiRT/FLUX.1-dev-LoRA-Ume_Sky", "ume_sky_v2.safetensors"),
        ("Shakker-Labs/FLUX.1-dev-LoRA-Dark-Fantasy", "FLUX.1-dev-lora-Dark-Fantasy.safetensors"),
        ("aleksa-codes/flux-ghibsky-illustration", "lora_v2.safetensors"),
    ]
    
    lora_dir = "/root/comfy/ComfyUI/models/loras"
    os.makedirs(lora_dir, exist_ok=True)
    
    for repo_id, filename in lora_models:
        try:
            lora_path = hf_hub_download(repo_id=repo_id, filename=filename, cache_dir="/cache")
            subprocess.run(f"ln -sf {lora_path} {lora_dir}/{filename}", shell=True, check=True)
            print(f"   ✅ {filename}")
        except Exception as e:
            print(f"   ❌ {filename}: {e}")
    
    # S2.5: LLAVA 模型
    print("\n📥 [5/5] 下载 LLAVA 模型...")
    llava_models = [
        ("concedo/llama-joycaption-beta-one-hf-llava-mmproj-gguf", "Llama-Joycaption-Beta-One-Hf-Llava-F16.gguf"),
        ("concedo/llama-joycaption-beta-one-hf-llava-mmproj-gguf", "llama-joycaption-beta-one-llava-mmproj-model-f16.gguf"),
    ]
    
    llava_dir = "/root/comfy/ComfyUI/models/llava_gguf"
    os.makedirs(llava_dir, exist_ok=True)
    
    for repo_id, filename in llava_models:
        try:
            llava_path = hf_hub_download(repo_id=repo_id, filename=filename, cache_dir="/cache")
            subprocess.run(f"ln -sf {llava_path} {llava_dir}/{filename}", shell=True, check=True)
            print(f"   ✅ {filename}")
        except Exception as e:
            print(f"   ❌ {filename}: {e}")
    
    print("\n✅ 所有模型下载完成！")


# S2.6: 生成默认 Workflow
def create_workflow():
    """创建默认 Workflow 配置"""
    workflow = {
        "3": {
            "inputs": {"seed": 156680208700286, "steps": 20, "cfg": 3.5, "sampler_name": "euler",
                      "scheduler": "simple", "denoise": 1, "model": ["4", 0], "positive": ["6", 0],
                      "negative": ["7", 0], "latent_image": ["5", 0]},
            "class_type": "KSampler"
        },
        "4": {"inputs": {"ckpt_name": "flux1-dev-fp8.safetensors"}, "class_type": "CheckpointLoaderSimple"},
        "5": {"inputs": {"width": 1024, "height": 1024, "batch_size": 1}, "class_type": "EmptyLatentImage"},
        "6": {"inputs": {"text": "A beautiful landscape", "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
        "7": {"inputs": {"text": "", "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
        "8": {"inputs": {"samples": ["3", 0], "vae": ["4", 2]}, "class_type": "VAEDecode"},
        "9": {"inputs": {"filename_prefix": "ComfyUI", "images": ["8", 0]}, "class_type": "SaveImage"}
    }
    Path("/root/workflow_api.json").write_text(json.dumps(workflow, indent=2))
    print("✅ Workflow 配置已生成")


# S2.7: 添加到镜像
image = (
    image.pip_install("huggingface_hub[hf_transfer]==0.34.4")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_function(download_all_models, volumes={"/cache": vol}, secrets=[hf_secret])
    .run_function(create_workflow)
)

# =============================================================================
# S3: 创建 Modal 应用
# =============================================================================

app = modal.App(name="example-comfyapp", image=image)

print("\n✅ ComfyUI 完整镜像构建完成！")

# =============================================================================
# S4: UI 服务
# =============================================================================

@app.function(max_containers=1, gpu="L40S", volumes={"/cache": vol})
@modal.concurrent(max_inputs=10)
@modal.web_server(8000, startup_timeout=60)
def ui():
    """
    ComfyUI Web 界面服务
    - 端口: 8000
    - GPU: L40S
    - 最大并发: 10 个用户
    """
    print("🌐 启动 ComfyUI Web 界面...")
    
    # 链接 Volume 中的自定义节点
    cache_custom_nodes = Path("/cache/custom_nodes")
    comfy_custom_nodes = Path("/root/comfy/ComfyUI/custom_nodes")
    
    if cache_custom_nodes.exists():
        for node_dir in cache_custom_nodes.iterdir():
            if node_dir.is_dir():
                link_path = comfy_custom_nodes / node_dir.name
                if not link_path.exists() and not link_path.is_symlink():
                    subprocess.run(f"ln -s {node_dir} {link_path}", shell=True, check=False)
    
    subprocess.Popen("comfy launch -- --listen 0.0.0.0 --port 8000", shell=True)

# =============================================================================
# S5: API 服务
# =============================================================================

@app.cls(scaledown_window=300, gpu="L40S", volumes={"/cache": vol})
@modal.concurrent(max_inputs=5)
class ComfyUI:
    """
    ComfyUI API 服务类
    - 支持 RESTful API
    - 最大并发: 5 个请求
    - 自动缩放
    """
    port: int = 8000
    
    @modal.enter()
    def launch_comfy_background(self):
        """容器启动时初始化 ComfyUI"""
        print(f"🚀 启动 ComfyUI 后台服务（端口 {self.port}）...")
        
        # 链接自定义节点
        cache_custom_nodes = Path("/cache/custom_nodes")
        comfy_custom_nodes = Path("/root/comfy/ComfyUI/custom_nodes")
        
        if cache_custom_nodes.exists():
            for node_dir in cache_custom_nodes.iterdir():
                if node_dir.is_dir():
                    link_path = comfy_custom_nodes / node_dir.name
                    if not link_path.exists() and not link_path.is_symlink():
                        subprocess.run(f"ln -s {node_dir} {link_path}", shell=True, check=False)
        
        cmd = f"comfy launch --background -- --port {self.port}"
        subprocess.run(cmd, shell=True, check=True)
    
    @modal.method()
    def infer(self, workflow_path: str = "/root/workflow_api.json"):
        """执行图像生成推理"""
        print("🎨 执行图像生成...")
        
        # 健康检查
        self.poll_server_health()
        
        # 运行工作流
        cmd = f"comfy run --workflow {workflow_path} --wait --timeout 1200 --verbose"
        subprocess.run(cmd, shell=True, check=True)
        
        # 获取生成的图像
        output_dir = "/root/comfy/ComfyUI/output"
        workflow = json.loads(Path(workflow_path).read_text())
        file_prefix = [
            node.get("inputs")
            for node in workflow.values()
            if node.get("class_type") == "SaveImage"
        ][0]["filename_prefix"]
        
        for f in Path(output_dir).iterdir():
            if f.name.startswith(file_prefix):
                return f.read_bytes()
    
    @modal.fastapi_endpoint(method="POST")
    def api(self, item: Dict):
        """FastAPI 端点 - 处理 HTTP POST 请求"""
        from fastapi import Response
        
        print("📡 处理 API 请求...")
        
        # 加载工作流模板
        workflow_data = json.loads(Path("/root/workflow_api.json").read_text())
        
        # 设置用户提示词
        workflow_data["6"]["inputs"]["text"] = item.get("prompt", "A beautiful landscape")
        
        # 生成唯一文件名
        client_id = uuid.uuid4().hex
        workflow_data["9"]["inputs"]["filename_prefix"] = client_id
        
        # 保存自定义工作流
        new_workflow_file = f"{client_id}.json"
        json.dump(workflow_data, Path(new_workflow_file).open("w"))
        
        # 执行推理
        img_bytes = self.infer.local(new_workflow_file)
        return Response(img_bytes, media_type="image/jpeg")
    
    def poll_server_health(self) -> Dict:
        """健康检查 - 确保 ComfyUI 服务正常"""
        import socket
        import urllib
        
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}/system_stats")
            urllib.request.urlopen(req, timeout=5)
            print("✅ ComfyUI 服务健康")
        except (socket.timeout, urllib.error.URLError):
            print("❌ ComfyUI 服务不健康，停止容器")
            modal.experimental.stop_fetching_inputs()
            raise Exception("ComfyUI server is not healthy")

print("\n🎉 ComfyUI 完整部署脚本准备就绪！")
print("💡 使用方法:")
print("   - 部署: modal deploy deploy_complete.py")
print("   - 开发: modal serve deploy_complete.py")

