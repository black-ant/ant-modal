# Modal 使用教程

本教程将帮助你快速掌握 Modal 平台的核心功能，并通过实战案例学习如何为应用添加模型和插件。

---

## 目录

1. [Modal 基础概念](#modal-基础概念)
2. [环境准备](#环境准备)
3. [基础操作](#基础操作)
4. [实战案例：为应用添加模型和插件](#实战案例为应用添加模型和插件)
5. [常见问题](#常见问题)

---

## Modal 基础概念

### 核心组件

- **App (应用)**: Modal 上运行的服务单元，可以包含多个函数
- **Function (函数)**: 在云端执行的代码单元，支持 GPU 加速
- **Volume (存储卷)**: 持久化存储，用于保存模型、数据等文件
- **Secret (密钥)**: 安全存储 API Token、密码等敏感信息
- **Image (镜像)**: 定义运行环境，包含依赖库和系统配置

### 工作流程

```
本地脚本 → modal deploy → 云端容器 → 持久化存储 (Volume)
```

---

## 环境准备

### 1. 安装 Modal CLI

```bash
pip install modal
```

### 2. 配置 Token

在 Modal Manager 中配置你的 Modal Token：

1. 访问 [Modal Dashboard](https://modal.com/settings/tokens)
2. 创建新的 Token
3. 在 Modal Manager 的"应用管理"中添加 Token

### 3. 创建 HuggingFace Secret (可选)

如果需要下载 HuggingFace 上的模型：

```bash
modal secret create huggingface-secret HF_TOKEN=hf_your_token_here
```

---

## 基础操作

### 部署应用

```bash
modal deploy your_script.py
```

### 运行函数

```bash
modal run your_script.py
```

### 查看应用状态

```bash
modal app list
```

### 停止应用

```bash
modal app stop your-app-name
```

---

## 实战案例：为应用添加模型和插件

本案例以 **ComfyUI 节点管理器** 为例，演示如何为已部署的应用动态添加模型和自定义节点。

### 场景说明

你已经部署了一个 ComfyUI 应用，现在想要：
1. 添加新的 AI 模型（从 HuggingFace 或 URL）
2. 安装自定义节点扩展
3. 让新资源在应用中生效

### 核心原理

**关键：使用共享 Volume 实现资源持久化和热加载**

```
主应用 (comfyui-app)
    ↓ 挂载
Volume (comfyui-cache)
    ↑ 挂载
辅助脚本 (add_model_hf.py)
```

所有脚本共享同一个 Volume，辅助脚本下载的模型会保存到 Volume，主应用重启后自动加载。

---

### 步骤 1: 部署主应用

首先部署 ComfyUI 主服务：

```bash
modal deploy comfyui_app.py
```

**关键配置点：**

```python
# comfyui_app.py

# 1. 创建共享 Volume
vol = modal.Volume.from_name("comfyui-cache", create_if_missing=True)

# 2. 创建应用
app = modal.App(name="comfyui-app", image=image)

# 3. 在容器启动时链接 Volume 中的资源
def _link_resources_from_volume():
    """链接 Volume 中所有持久化资源"""
    # 链接模型
    cache_models = Path("/cache/models")
    comfy_models = Path("/root/comfy/ComfyUI/models")
    
    for model_type_dir in cache_models.iterdir():
        for model_file in model_type_dir.iterdir():
            link_path = comfy_models / model_type_dir.name / model_file.name
            subprocess.run(f"ln -s {model_file} {link_path}", shell=True)
    
    # 链接自定义节点
    cache_nodes = Path("/cache/custom_nodes")
    comfy_nodes = Path("/root/comfy/ComfyUI/custom_nodes")
    
    for node_dir in cache_nodes.iterdir():
        link_path = comfy_nodes / node_dir.name
        subprocess.run(f"ln -s {node_dir} {link_path}", shell=True)
```

---

### 步骤 2: 添加 HuggingFace 模型

使用 `add_model_hf.py` 从 HuggingFace 下载模型：

**脚本配置：**

```python
# add_model_hf.py

# 项目变量 - 与主服务共享同一个 Volume
VOLUME_NAME = "comfyui-cache"  # 必须与主应用一致
APP_NAME = "comfyui-app"

# 脚本变量 - 每次执行时填写
HF_REPO_ID = "Comfy-Org/flux1-dev"
HF_FILENAME = "flux1-dev-fp8.safetensors"
MODEL_TYPE = "checkpoints"  # 可选: checkpoints, loras, vae, clip 等

# 使用与主服务相同的 Volume
vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

@app.function(volumes={"/cache": vol}, timeout=3600)
def download_model():
    """从 HuggingFace 下载模型"""
    from huggingface_hub import hf_hub_download
    
    # 下载到 Volume
    target_dir = Path(f"/cache/models/{MODEL_TYPE}")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    cached_path = hf_hub_download(
        repo_id=HF_REPO_ID,
        filename=HF_FILENAME,
        cache_dir="/cache/hf_cache"
    )
    
    # 创建符号链接
    target_file = target_dir / Path(HF_FILENAME).name
    os.symlink(cached_path, str(target_file))
    
    # 提交到 Volume（关键步骤！）
    vol.commit()
```

**执行下载：**

```bash
modal run add_model_hf.py
```

**输出示例：**

```
============================================================
📥 从 HuggingFace 下载模型
============================================================
仓库: Comfy-Org/flux1-dev
文件: flux1-dev-fp8.safetensors
类型: checkpoints
Volume: comfyui-cache

⏳ 下载中...

✅ 下载成功!
   文件: checkpoints/flux1-dev-fp8.safetensors
   大小: 23456.7 MB
```

---

### 步骤 3: 添加 URL 模型

使用 `add_model_url.py` 从任意 URL 下载模型（如 Civitai）：

**脚本配置：**

```python
# add_model_url.py

VOLUME_NAME = "comfyui-cache"
APP_NAME = "comfyui-app"

# 脚本变量
MODEL_URL = "https://civitai.com/api/download/models/123456"
MODEL_FILENAME = "style_lora.safetensors"
MODEL_TYPE = "loras"

vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

@app.function(volumes={"/cache": vol}, timeout=3600)
def download_model():
    """从 URL 下载模型"""
    import requests
    from tqdm import tqdm
    
    target_dir = Path(f"/cache/models/{MODEL_TYPE}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / MODEL_FILENAME
    
    # 流式下载
    response = requests.get(MODEL_URL, stream=True, timeout=60)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(target_file, 'wb') as f:
        with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
            for chunk in response.iter_content(chunk_size=8192*1024):
                f.write(chunk)
                pbar.update(len(chunk))
    
    # 提交到 Volume
    vol.commit()
```

**执行下载：**

```bash
modal run add_model_url.py
```

---

### 步骤 4: 添加自定义节点

使用 `add_custom_nodes.py` 安装自定义节点：

**脚本配置：**

```python
# add_custom_nodes.py

VOLUME_NAME = "comfyui-cache"
APP_NAME = "comfyui-app"

# 节点配置
NODE_REPO_URL = "https://github.com/ltdrdata/ComfyUI-Manager.git"
NODE_NAME = "ComfyUI-Manager"

vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

@app.function(volumes={"/cache": vol}, timeout=1800)
def install_node():
    """安装自定义节点到 Volume"""
    import subprocess
    
    cache_nodes_dir = Path("/cache/custom_nodes")
    cache_nodes_dir.mkdir(parents=True, exist_ok=True)
    
    target_dir = cache_nodes_dir / NODE_NAME
    
    if target_dir.exists():
        print(f"⚠️ 节点已存在: {NODE_NAME}")
        return {"success": True, "action": "exists"}
    
    # 克隆仓库
    subprocess.run(
        f"git clone {NODE_REPO_URL} {target_dir}",
        shell=True,
        check=True
    )
    
    # 安装依赖
    req_file = target_dir / "requirements.txt"
    if req_file.exists():
        subprocess.run(
            f"pip install -r {req_file}",
            shell=True,
            check=True
        )
    
    # 保存安装信息
    install_info = {
        "node_name": NODE_NAME,
        "repo_url": NODE_REPO_URL,
        "installed_at": datetime.now().isoformat()
    }
    (target_dir / ".install_info.json").write_text(json.dumps(install_info))
    
    # 提交到 Volume
    vol.commit()
```

**执行安装：**

```bash
modal run add_custom_nodes.py
```

---

### 步骤 5: 验证资源

使用 `diagnose.py` 检查 Volume 中的资源：

```bash
modal run comfyui_app.py::diagnose
```

**输出示例：**

```
============================================================
🔍 ComfyUI Volume 诊断报告
============================================================

📦 模型检查:
   checkpoints: 2 个
      - flux1-dev-fp8.safetensors (23456.7 MB)
      - 一青十色.safetensors (6789.2 MB)
   loras: 5 个
      - style_lora.safetensors (234.5 MB)
      - ume_sky_v2.safetensors (145.8 MB)
      ...

🧩 节点检查:
   ✅ ComfyUI-Manager
      requirements.txt: 有
      __init__.py: 有
   ✅ was-node-suite-comfyui
      requirements.txt: 有
      __init__.py: 有

============================================================
📊 汇总: 7 个模型, 2 个节点
============================================================
```

---

### 步骤 6: 重启应用使资源生效

**关键步骤：停止应用，让 Modal 自动重启并加载新资源**

```bash
modal app stop comfyui-app
```

**发生了什么：**

1. Modal 停止当前运行的容器
2. 下次访问 ComfyUI URL 时，Modal 自动启动新容器
3. 新容器启动时执行 `_link_resources_from_volume()`
4. 自动链接 Volume 中所有模型和节点
5. ComfyUI 加载新资源，可以使用了！

**验证：**

访问 ComfyUI Web 界面，检查：
- 模型列表中是否出现新模型
- 节点菜单中是否出现新节点

---

### 完整工作流程图

```
┌─────────────────────────────────────────────────────────┐
│  步骤 1: 部署主应用                                      │
│  modal deploy comfyui_app.py                            │
│  → 创建 Volume: comfyui-cache                           │
│  → 部署应用: comfyui-app                                │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  步骤 2-4: 添加资源（可多次执行）                        │
│  modal run add_model_hf.py    # 添加 HF 模型            │
│  modal run add_model_url.py   # 添加 URL 模型           │
│  modal run add_custom_nodes.py # 添加节点               │
│  → 所有资源保存到 Volume: /cache/models/                │
│  → 所有资源保存到 Volume: /cache/custom_nodes/          │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  步骤 5: 验证资源                                        │
│  modal run comfyui_app.py::diagnose                     │
│  → 检查 Volume 中的模型和节点                            │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  步骤 6: 重启应用                                        │
│  modal app stop comfyui-app                             │
│  → Modal 自动重启容器                                    │
│  → 容器启动时链接 Volume 资源                            │
│  → 新模型和节点生效！                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 核心技术要点

### 1. Volume 共享机制

**为什么需要共享 Volume？**

```python
# 主应用
vol = modal.Volume.from_name("comfyui-cache", create_if_missing=True)
app = modal.App(name="comfyui-app", image=image)

# 辅助脚本
vol = modal.Volume.from_name("comfyui-cache", create_if_missing=True)
app = modal.App(name="comfyui-app-hf-downloader", image=image)
```

两个应用使用相同的 Volume 名称，实现数据共享。

### 2. 符号链接技术

**为什么使用符号链接？**

```python
# HuggingFace 缓存在 /cache/hf_cache/
cached_path = hf_hub_download(..., cache_dir="/cache/hf_cache")

# 创建符号链接到 ComfyUI 模型目录
target_file = Path("/cache/models/checkpoints/model.safetensors")
os.symlink(cached_path, str(target_file))
```

优点：
- 避免重复存储，节省空间
- HuggingFace 缓存可复用
- 支持多个应用共享同一模型

### 3. Volume 提交

**为什么需要 `vol.commit()`？**

```python
# 下载模型
download_file(url, target_path)

# 提交到 Volume（关键！）
vol.commit()
```

Modal 的 Volume 是写时复制（Copy-on-Write），必须显式提交才能持久化。

### 4. 热加载机制

**容器启动时自动加载资源：**

```python
@modal.enter()
def launch_comfy_background(self):
    """容器启动时执行"""
    # 1. 链接模型
    _link_models_from_volume()
    
    # 2. 链接节点
    _link_custom_nodes_from_volume()
    
    # 3. 启动 ComfyUI
    subprocess.run("comfy launch --background", shell=True)
```

---

## 常见问题

### Q1: 添加模型后看不到？

**原因：** 没有重启应用

**解决：**
```bash
modal app stop comfyui-app
```

### Q2: 模型下载失败？

**原因：** HuggingFace Token 未配置或网络问题

**解决：**
```bash
# 配置 Token
modal secret create huggingface-secret HF_TOKEN=hf_xxx

# 检查 Secret
modal secret list
```

### Q3: 节点安装后不生效？

**原因：** 节点依赖未安装

**检查：**
```python
# 在 _link_custom_nodes_from_volume() 中添加依赖安装
req_file = node_dir / "requirements.txt"
if req_file.exists():
    subprocess.run(f"pip install -r {req_file}", shell=True)
```

### Q4: Volume 空间不足？

**查看 Volume 使用情况：**
```bash
modal volume list
```

**清理不需要的模型：**
```bash
modal run comfyui_app.py::cleanup_models
```

### Q5: 如何删除模型？

**方法 1：使用管理脚本**
```python
@app.function(volumes={"/cache": vol})
def delete_model(model_type: str, filename: str):
    target = Path(f"/cache/models/{model_type}/{filename}")
    if target.exists():
        target.unlink()
    vol.commit()
```

**方法 2：手动删除**
```bash
modal volume get comfyui-cache models/checkpoints/old_model.safetensors
# 删除文件后
modal volume put comfyui-cache models/checkpoints/
```

---

## 最佳实践

### 1. 模型命名规范

```
checkpoints/
  ├── flux1-dev-fp8.safetensors
  ├── 一青十色.safetensors
  └── sdxl-base-1.0.safetensors

loras/
  ├── style_anime.safetensors
  ├── style_realistic.safetensors
  └── ume_sky_v2.safetensors
```

使用有意义的文件名，方便管理。

### 2. 批量下载模型

```python
# batch_download.py
MODELS = [
    {"repo": "Comfy-Org/flux1-dev", "file": "flux1-dev-fp8.safetensors", "type": "checkpoints"},
    {"repo": "stabilityai/sd-vae-ft-mse", "file": "diffusion_pytorch_model.safetensors", "type": "vae"},
]

for model in MODELS:
    download_model(model["repo"], model["file"], model["type"])
```

### 3. 版本管理

```python
# 在文件名中包含版本号
"flux1-dev-fp8-v1.0.safetensors"
"style_lora-v2.1.safetensors"

# 或使用子目录
"/cache/models/checkpoints/v1.0/flux1-dev-fp8.safetensors"
"/cache/models/checkpoints/v1.1/flux1-dev-fp8.safetensors"
```

### 4. 监控 Volume 使用

```python
@app.function(volumes={"/cache": vol})
def monitor_volume():
    """监控 Volume 使用情况"""
    import shutil
    
    total, used, free = shutil.disk_usage("/cache")
    
    print(f"总空间: {total / (1024**3):.1f} GB")
    print(f"已使用: {used / (1024**3):.1f} GB")
    print(f"剩余: {free / (1024**3):.1f} GB")
    
    # 列出大文件
    for root, dirs, files in os.walk("/cache"):
        for file in files:
            path = Path(root) / file
            size_gb = path.stat().st_size / (1024**3)
            if size_gb > 1:  # 大于 1GB
                print(f"{size_gb:.1f} GB - {path}")
```

---

## 总结

通过本教程，你学会了：

1. ✅ **理解 Volume 共享机制** - 多个应用共享同一存储
2. ✅ **添加 HuggingFace 模型** - 使用 `add_model_hf.py`
3. ✅ **添加 URL 模型** - 使用 `add_model_url.py`
4. ✅ **安装自定义节点** - 使用 `add_custom_nodes.py`
5. ✅ **验证和诊断** - 使用 `diagnose.py`
6. ✅ **热加载机制** - 重启应用使资源生效

**核心原则：**
- 所有资源保存到共享 Volume
- 使用符号链接避免重复存储
- 容器启动时自动链接资源
- 添加资源后重启应用

现在你可以灵活地为任何 Modal 应用添加模型和插件了！

---

## 相关资源

- [Modal 官方文档](https://modal.com/docs)
- [ComfyUI 官方文档](https://github.com/comfyanonymous/ComfyUI)
- [HuggingFace Hub](https://huggingface.co/models)
- [Civitai 模型库](https://civitai.com/)

---

**有问题？** 查看 [常见问题](#常见问题) 或提交 Issue。
