# ComfyUI 模块化安装脚本

## 📋 概述

本项目将 ComfyUI Flux 部署脚本拆分为 8 个独立的模块化脚本，每个脚本专注于特定功能，可单独运行或组合使用。

## 📦 脚本列表

### 1. 基础环境安装 (setup_base_environment.py)
**功能：** 构建基础 Docker 镜像和 ComfyUI 核心环境
- 安装 Python 3.11 + Git
- 安装 FastAPI、comfy-cli
- 安装 llama-cpp-python (CUDA 124)
- 安装 ComfyUI 0.3.59

**使用：**
```bash
modal run setup_base_environment.py
```

### 2. 节点安装 (install_custom_nodes.py)
**功能：** 安装 ComfyUI 自定义节点扩展
- was-node-suite-comfyui (1.0.2)
- ComfyUI-joycaption-beta-one-GGUF
- 持久化到 Volume `/cache/custom_nodes`

**使用：**
```bash
modal run install_custom_nodes.py
```

### 3. 基础模型下载 (download_base_models.py)
**功能：** 从 HuggingFace 下载核心模型
- Flux1-dev-fp8 主模型
- Clip 模型 (clip_g, clip_l, t5xxl_fp8)
- VAE 模型 (ae.safetensors)

**环境要求：** 需要配置 `huggingface-secret`

**使用：**
```bash
modal run download_base_models.py
```

### 4. LoRA 模型下载 (download_lora_models.py)
**功能：** 下载风格迁移 LoRA 模型
- Ume Sky (天空风格)
- Dark Fantasy (暗黑幻想)
- Ghibsky Illustration (吉卜力天空)

**使用：**
```bash
modal run download_lora_models.py
```

### 5. LLAVA 模型下载 (download_llava_models.py)
**功能：** 下载图像理解 LLAVA 模型
- Llama-Joycaption 主模型
- LLAVA 投影模型

**使用：**
```bash
modal run download_llava_models.py
```

### 6. URL 模型下载 (download_url_models.py)
**功能：** 从 Civitai 等 URL 下载额外模型
- 14 个风格模型（一青十色、中世纪风格、机械风格等）
- 智能缓存检测，避免重复下载
- 支持断点续传

**使用：**
```bash
modal run download_url_models.py
```

### 7. 服务配置 (configure_service.py)
**功能：** 生成服务配置文件
- 创建默认 workflow_api.json
- 配置 Modal Volume
- 设置环境变量

**使用：**
```bash
modal run configure_service.py
```

### 8. 完整部署 (deploy_complete.py)
**功能：** 一键部署完整的生产环境
- 整合所有模块
- 部署 UI 服务 (Web 界面，端口 8000)
- 部署 API 服务 (FastAPI 端点)
- 健康检查和并发控制

**使用：**
```bash
# 部署到生产环境
modal deploy deploy_complete.py

# 开发模式（支持热重载）
modal serve deploy_complete.py
```

## 🚀 快速开始

### 方案 A: 完整部署（推荐）
如果你想一次性部署整个系统：
```bash
modal deploy deploy_complete.py
```

### 方案 B: 模块化安装
如果你想分步安装或只需要部分功能：

1. **基础环境**
```bash
modal run setup_base_environment.py
```

2. **安装节点**（可选）
```bash
modal run install_custom_nodes.py
```

3. **下载必需模型**
```bash
modal run download_base_models.py
```

4. **下载可选模型**（根据需要选择）
```bash
# LoRA 风格模型
modal run download_lora_models.py

# 图像理解模型
modal run download_llava_models.py

# 额外风格模型
modal run download_url_models.py
```

5. **配置服务**
```bash
modal run configure_service.py
```

6. **部署**
```bash
modal deploy deploy_complete.py
```

## ⚙️ 环境要求

### 必需配置
1. **Modal Account**: 需要有效的 Modal 账户
2. **HuggingFace Secret**: 用于下载模型
   ```bash
   modal secret create huggingface-secret HF_TOKEN=your_token_here
   ```

### 可选配置
- **GPU**: 脚本默认使用 L40S GPU，可根据需要调整
- **Volume**: 自动创建 `hf-hub-cache` 用于缓存模型

## 📊 脚本特性

### ✅ 独立性
- 每个脚本可单独运行
- 包含完整的 import 和依赖

### 💾 缓存策略
- 所有模型使用 `/cache` 目录
- 避免重复下载
- 支持断点续传

### 🛡️ 错误处理
- 完善的异常捕获
- 部分失败不影响整体
- 详细的日志输出

### 🔄 并发控制
- UI 服务: 最多 10 个并发用户
- API 服务: 最多 5 个并发请求
- 自动扩缩容

## 📝 配置文件

### data/projects.json
项目配置文件，映射中文脚本名称到文件：

```json
{
  "scripts": [
    {"name": "基础环境安装", "path": "setup_base_environment.py"},
    {"name": "节点安装", "path": "install_custom_nodes.py"},
    {"name": "基础模型下载", "path": "download_base_models.py"},
    {"name": "LoRA模型下载", "path": "download_lora_models.py"},
    {"name": "LLAVA模型下载", "path": "download_llava_models.py"},
    {"name": "URL模型下载", "path": "download_url_models.py"},
    {"name": "服务配置", "path": "configure_service.py"},
    {"name": "完整部署", "path": "deploy_complete.py"}
  ]
}
```

## 🔍 常见问题

### Q: 下载模型失败怎么办？
A: 检查 HuggingFace Token 是否配置正确，网络是否稳定。由于使用了缓存机制，重新运行脚本会从断点继续。

### Q: 如何自定义 Workflow？
A: 编辑 `configure_service.py` 中的 `create_default_workflow()` 函数，或运行后修改生成的 `workflow_api.json`。

### Q: GPU 不够用怎么办？
A: 修改 `deploy_complete.py` 中的 `gpu="L40S"` 为其他型号，如 `gpu="T4"` 或 `gpu="A100"`。

### Q: 如何查看服务日志？
A: 使用 Modal CLI 命令：
```bash
modal app logs example-comfyapp
modal app logs example-comfyapp --follow  # 实时日志
```

## 🎯 API 使用示例

部署完成后，可通过 API 生成图像：

```python
import requests

# 获取 API 端点（从 Modal 控制台获取）
api_url = "https://your-app.modal.run/api"

# 发送请求
response = requests.post(api_url, json={
    "prompt": "A beautiful landscape with mountains and a lake at sunset"
})

# 保存图像
with open("output.jpg", "wb") as f:
    f.write(response.content)
```

## 📚 技术架构

```
基础环境 (Python 3.11 + ComfyUI)
    ↓
自定义节点 (was-node-suite + joycaption)
    ↓
模型层 (Flux + Clip + VAE + LoRA + LLAVA)
    ↓
服务层 (UI Service + API Service)
    ↓
部署层 (Modal Cloud + GPU + Volume)
```

## 🛠️ 维护与更新

### 更新模型
重新运行对应的下载脚本即可，缓存机制会跳过已下载的文件。

### 更新 ComfyUI 版本
修改各脚本中的版本号：
```python
.run_commands("comfy --skip-prompt install --fast-deps --nvidia --version X.X.X")
```

### 清理缓存
如需清理 Volume 缓存：
```bash
modal volume delete hf-hub-cache
```

## 📄 许可证

本项目基于原始 ComfyUI Flux 脚本改编，遵循相应的开源协议。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**最后更新:** 2025-11-26
**作者:** Modal Manager Project

