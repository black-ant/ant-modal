import { CodeSnippetCategory } from '../types';

export const codeSnippetCategories: CodeSnippetCategory[] = [
  {
    id: 'modal-basics',
    name: 'Modal 基础',
    icon: '🔧',
    description: 'Modal 平台的基础配置和组件',
    snippets: [
      {
        id: 'basic-app',
        title: '基础应用模板',
        description: '创建一个基本的 Modal 应用',
        category: 'modal-basics',
        tags: ['app', 'basic'],
        code: `import modal

app = modal.App(name="my-app")

@app.function()
def hello():
    print("Hello from Modal!")
    return "Hello, World!"`,
      },
      {
        id: 'debian-image',
        title: 'Debian 镜像',
        description: '使用 Debian Slim 作为基础镜像',
        category: 'modal-basics',
        tags: ['image', 'debian'],
        code: `image = modal.Image.debian_slim(python_version="3.11")`,
      },
      {
        id: 'conda-image',
        title: 'Conda 镜像',
        description: '使用 Conda 环境',
        category: 'modal-basics',
        tags: ['image', 'conda'],
        code: `image = modal.Image.conda().conda_install(
    "pytorch",
    "torchvision",
    channels=["pytorch", "nvidia"]
)`,
      },
      {
        id: 'pip-install',
        title: '安装 Python 包',
        description: '在镜像中安装 pip 包',
        category: 'modal-basics',
        tags: ['image', 'pip'],
        code: `image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "fastapi",
    "uvicorn",
    "pydantic"
)`,
      },
      {
        id: 'volume-create',
        title: '创建 Volume',
        description: '创建持久化存储卷',
        category: 'modal-basics',
        tags: ['volume', 'storage'],
        code: `volume = modal.Volume.from_name("my-volume", create_if_missing=True)`,
      },
      {
        id: 'volume-mount',
        title: '挂载 Volume',
        description: '将 Volume 挂载到函数',
        category: 'modal-basics',
        tags: ['volume', 'mount'],
        code: `@app.function(volumes={"/data": volume})
def process_data():
    # 访问 /data 目录
    with open("/data/file.txt", "r") as f:
        content = f.read()
    return content`,
      },
      {
        id: 'secret-usage',
        title: '使用 Secret',
        description: '在函数中使用密钥',
        category: 'modal-basics',
        tags: ['secret', 'security'],
        code: `@app.function(secrets=[modal.Secret.from_name("my-secret")])
def use_secret():
    import os
    api_key = os.environ["API_KEY"]
    return api_key`,
      },
      {
        id: 'schedule-cron',
        title: '定时任务 (Cron)',
        description: '使用 Cron 表达式设置定时任务',
        category: 'modal-basics',
        tags: ['schedule', 'cron'],
        code: `@app.function(schedule=modal.Cron("0 9 * * *"))  # 每天上午9点
def daily_task():
    print("执行每日任务")
    return "Task completed"`,
      },
      {
        id: 'schedule-period',
        title: '定时任务 (周期)',
        description: '使用时间周期设置定时任务',
        category: 'modal-basics',
        tags: ['schedule', 'period'],
        code: `@app.function(schedule=modal.Period(hours=6))  # 每6小时执行一次
def periodic_task():
    print("执行周期任务")
    return "Task completed"`,
      },
      {
        id: 'gpu-config',
        title: 'GPU 配置',
        description: '配置 GPU 资源',
        category: 'modal-basics',
        tags: ['gpu', 'resource'],
        code: `@app.function(gpu="A100")  # 使用 A100 GPU
def gpu_task():
    import torch
    print(f"GPU 可用: {torch.cuda.is_available()}")
    return torch.cuda.get_device_name(0)`,
      },
      {
        id: 'timeout-config',
        title: '超时配置',
        description: '设置函数超时时间',
        category: 'modal-basics',
        tags: ['timeout', 'config'],
        code: `@app.function(timeout=3600)  # 1小时超时
def long_running_task():
    # 长时间运行的任务
    pass`,
      },
    ],
  },
  {
    id: 'model-download',
    name: '模型下载',
    icon: '📦',
    description: '各种模型下载方法',
    snippets: [
      {
        id: 'huggingface-download',
        title: 'HuggingFace 模型下载',
        description: '从 HuggingFace 下载模型',
        category: 'model-download',
        tags: ['huggingface', 'model'],
        code: `from huggingface_hub import snapshot_download

@app.function()
def download_hf_model():
    model_name = "stabilityai/stable-diffusion-xl-base-1.0"
    cache_dir = "/models"
    
    snapshot_download(
        repo_id=model_name,
        cache_dir=cache_dir,
        local_dir=cache_dir,
        local_dir_use_symlinks=False
    )
    print(f"模型已下载到: {cache_dir}")`,
      },
      {
        id: 'huggingface-with-token',
        title: 'HuggingFace 带 Token 下载',
        description: '使用 Token 下载私有模型',
        category: 'model-download',
        tags: ['huggingface', 'token'],
        code: `from huggingface_hub import snapshot_download

@app.function(secrets=[modal.Secret.from_name("huggingface-secret")])
def download_hf_private_model():
    import os
    
    model_name = "your-private-model"
    token = os.environ["HF_TOKEN"]
    
    snapshot_download(
        repo_id=model_name,
        token=token,
        cache_dir="/models",
        local_dir="/models",
        local_dir_use_symlinks=False
    )`,
      },
      {
        id: 'civitai-download',
        title: 'Civitai 模型下载',
        description: '从 Civitai 下载模型',
        category: 'model-download',
        tags: ['civitai', 'model'],
        code: `import requests
from pathlib import Path

def download_civitai_model(model_id: str, output_path: str):
    """从 Civitai 下载模型"""
    url = f"https://civitai.com/api/download/models/{model_id}"
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"模型已下载到: {output_path}")`,
      },
      {
        id: 'url-download-progress',
        title: 'URL 下载带进度条',
        description: '从 URL 下载文件并显示进度',
        category: 'model-download',
        tags: ['url', 'progress'],
        code: `import requests
from pathlib import Path
from tqdm import tqdm

def download_file_with_progress(url: str, output_path: str):
    """带进度条的文件下载"""
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'wb') as f:
        with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                pbar.update(len(chunk))
    
    print(f"下载完成: {output_path}")`,
      },
      {
        id: 'batch-download',
        title: '批量下载模型',
        description: '批量下载多个模型文件',
        category: 'model-download',
        tags: ['batch', 'download'],
        code: `import requests
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

def download_file(url: str, output_path: str):
    response = requests.get(url, stream=True)
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return output_path

@app.function()
def batch_download_models():
    models = [
        ("https://example.com/model1.safetensors", "/models/model1.safetensors"),
        ("https://example.com/model2.safetensors", "/models/model2.safetensors"),
    ]
    
    Path("/models").mkdir(parents=True, exist_ok=True)
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(download_file, url, path) for url, path in models]
        for future in futures:
            print(f"已下载: {future.result()}")`,
      },
    ],
  },
  {
    id: 'environment',
    name: '环境配置',
    icon: '⚙️',
    description: '环境和依赖配置',
    snippets: [
      {
        id: 'pip-requirements',
        title: '从 requirements.txt 安装',
        description: '使用 requirements.txt 安装依赖',
        category: 'environment',
        tags: ['pip', 'requirements'],
        code: `image = modal.Image.debian_slim(python_version="3.11").pip_install_from_requirements("requirements.txt")`,
      },
      {
        id: 'apt-packages',
        title: '安装系统包',
        description: '使用 apt 安装系统包',
        category: 'environment',
        tags: ['apt', 'system'],
        code: `image = modal.Image.debian_slim().apt_install(
    "ffmpeg",
    "libsm6",
    "libxext6"
)`,
      },
      {
        id: 'env-variables',
        title: '设置环境变量',
        description: '在镜像中设置环境变量',
        category: 'environment',
        tags: ['env', 'variables'],
        code: `image = modal.Image.debian_slim().env({
    "CUDA_VISIBLE_DEVICES": "0",
    "TRANSFORMERS_CACHE": "/cache",
})`,
      },
      {
        id: 'run-commands',
        title: '运行自定义命令',
        description: '在镜像构建时运行命令',
        category: 'environment',
        tags: ['run', 'commands'],
        code: `image = modal.Image.debian_slim().run_commands(
    "mkdir -p /workspace",
    "chmod 777 /workspace",
    "echo 'Setup complete' > /workspace/setup.txt"
)`,
      },
      {
        id: 'dockerfile-commands',
        title: 'Dockerfile 风格命令',
        description: '使用 Dockerfile 风格的命令',
        category: 'environment',
        tags: ['dockerfile'],
        code: `image = (
    modal.Image.debian_slim(python_version="3.11")
    .run_commands("apt-get update")
    .apt_install("git", "wget")
    .pip_install("torch", "transformers")
    .env({"HF_HOME": "/cache"})
)`,
      },
    ],
  },
  {
    id: 'service-deployment',
    name: '服务部署',
    icon: '🚀',
    description: 'Web 服务和应用部署',
    snippets: [
      {
        id: 'fastapi-service',
        title: 'FastAPI Web 服务',
        description: '部署 FastAPI Web 应用',
        category: 'service-deployment',
        tags: ['fastapi', 'web'],
        code: `from fastapi import FastAPI
from modal import asgi_app

web_app = FastAPI()

@web_app.get("/")
def read_root():
    return {"message": "Hello from Modal!"}

@web_app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.function()
@asgi_app()
def fastapi_app():
    return web_app`,
      },
      {
        id: 'gradio-webui',
        title: 'Gradio WebUI',
        description: '部署 Gradio 界面',
        category: 'service-deployment',
        tags: ['gradio', 'ui'],
        code: `import gradio as gr

def greet(name):
    return f"Hello {name}!"

@app.function()
@modal.web_endpoint(method="GET")
def gradio_app():
    demo = gr.Interface(fn=greet, inputs="text", outputs="text")
    return demo.launch(share=False, server_name="0.0.0.0")`,
      },
      {
        id: 'async-function',
        title: '异步任务函数',
        description: '创建异步任务处理函数',
        category: 'service-deployment',
        tags: ['async', 'task'],
        code: `@app.function()
async def async_task(data: dict):
    """异步处理任务"""
    import asyncio
    
    # 模拟异步处理
    await asyncio.sleep(1)
    
    result = {
        "status": "completed",
        "data": data,
        "processed": True
    }
    
    return result`,
      },
      {
        id: 'webhook-endpoint',
        title: 'Webhook 端点',
        description: '创建 Webhook 接收端点',
        category: 'service-deployment',
        tags: ['webhook', 'api'],
        code: `from fastapi import Request

@app.function()
@modal.web_endpoint(method="POST")
async def webhook_handler(request: Request):
    """处理 Webhook 请求"""
    data = await request.json()
    
    # 处理 webhook 数据
    print(f"收到 webhook 数据: {data}")
    
    return {"status": "received", "message": "Webhook processed"}`,
      },
      {
        id: 'comfyui-deployment',
        title: 'ComfyUI 部署',
        description: '部署 ComfyUI 服务',
        category: 'service-deployment',
        tags: ['comfyui', 'ui'],
        code: `@app.function(
    gpu="A100",
    volumes={"/models": volume},
    timeout=3600
)
@modal.web_endpoint(method="GET")
def comfyui_app():
    """部署 ComfyUI"""
    import subprocess
    
    # 启动 ComfyUI
    subprocess.Popen([
        "python", "main.py",
        "--listen", "0.0.0.0",
        "--port", "8188"
    ])
    
    return {"status": "ComfyUI started", "port": 8188}`,
      },
      {
        id: 'local-entrypoint',
        title: '本地入口点',
        description: '定义本地执行入口',
        category: 'service-deployment',
        tags: ['entrypoint', 'local'],
        code: `@app.local_entrypoint()
def main():
    """本地执行入口"""
    print("开始执行任务...")
    
    # 调用远程函数
    result = my_function.remote()
    
    print(f"任务完成: {result}")`,
      },
    ],
  },
  {
    id: 'advanced',
    name: '高级功能',
    icon: '⚡',
    description: '高级功能和优化技巧',
    snippets: [
      {
        id: 'class-method',
        title: '类方法部署',
        description: '将类方法部署为 Modal 函数',
        category: 'advanced',
        tags: ['class', 'method'],
        code: `@app.cls(gpu="A100")
class ModelInference:
    @modal.enter()
    def load_model(self):
        """容器启动时加载模型"""
        print("加载模型...")
        self.model = None  # 加载你的模型
    
    @modal.method()
    def predict(self, input_data):
        """推理方法"""
        result = self.model(input_data)
        return result`,
      },
      {
        id: 'map-parallel',
        title: '并行映射执行',
        description: '并行处理多个任务',
        category: 'advanced',
        tags: ['parallel', 'map'],
        code: `@app.function()
def process_item(item):
    # 处理单个项目
    return f"Processed: {item}"

@app.local_entrypoint()
def main():
    items = range(100)
    
    # 并行处理所有项目
    for result in process_item.map(items):
        print(result)`,
      },
      {
        id: 'retry-policy',
        title: '重试策略',
        description: '配置函数重试策略',
        category: 'advanced',
        tags: ['retry', 'error-handling'],
        code: `@app.function(
    retries=3,
    timeout=300
)
def unreliable_task():
    """可能失败的任务，最多重试3次"""
    import random
    
    if random.random() < 0.3:
        raise Exception("随机失败")
    
    return "成功"`,
      },
      {
        id: 'shared-volume',
        title: '共享 Volume 数据',
        description: '在多个函数间共享数据',
        category: 'advanced',
        tags: ['volume', 'share'],
        code: `shared_volume = modal.Volume.from_name("shared-data", create_if_missing=True)

@app.function(volumes={"/shared": shared_volume})
def write_data(data: str):
    """写入数据到共享卷"""
    with open("/shared/data.txt", "w") as f:
        f.write(data)
    shared_volume.commit()

@app.function(volumes={"/shared": shared_volume})
def read_data():
    """从共享卷读取数据"""
    shared_volume.reload()
    with open("/shared/data.txt", "r") as f:
        return f.read()`,
      },
    ],
  },
];

