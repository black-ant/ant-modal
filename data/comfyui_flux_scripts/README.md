# ComfyUI Flux 工具箱

完整的 ComfyUI Modal 部署工具集，包含自定义节点管理、批量图像生成、工作流管理等功能。

## 📦 项目结构

```
comfyui_flux_scripts/
├── app.py                  # 主应用入口
├── config.py               # 配置管理（增强版）
├── model_download.py       # 模型下载模块
├── ui_service.py          # UI 服务模块
├── api_service.py         # API 服务模块
├── workflow_api.json      # 默认工作流模板
│
├── manage_nodes.py        # ✨ Custom Nodes 管理工具
├── batch_inference.py     # ✨ 批量图像生成工具
├── workflow_manager.py    # ✨ 工作流模板管理器
└── utils.py               # ✨ 实用工具函数集
```

## 🚀 快速开始

### 1. 部署主应用

```bash
# 部署 ComfyUI 主服务
modal deploy app.py

# 启动开发服务器（支持热重载）
modal serve app.py
```

### 2. 管理 Custom Nodes

```bash
# 列出已安装的节点
modal run manage_nodes.py --action=list

# 安装新节点
modal run manage_nodes.py \
  --action=install \
  --repo-url=https://github.com/ltdrdata/ComfyUI-Manager.git

# 更新节点
modal run manage_nodes.py --action=update --node-name=ComfyUI-Manager

# 卸载节点
modal run manage_nodes.py --action=uninstall --node-name=ComfyUI-Manager
```

**常用节点推荐：**

```bash
# ComfyUI Manager - 节点管理器
modal run manage_nodes.py \
  --action=install \
  --repo-url=https://github.com/ltdrdata/ComfyUI-Manager.git

# ControlNet Auxiliary - ControlNet 预处理器
modal run manage_nodes.py \
  --action=install \
  --repo-url=https://github.com/Fannovel16/comfyui_controlnet_aux.git

# IP-Adapter Plus - 图像提示适配器
modal run manage_nodes.py \
  --action=install \
  --repo-url=https://github.com/cubiq/ComfyUI_IPAdapter_plus.git

# AnimateDiff - 动画生成
modal run manage_nodes.py \
  --action=install \
  --repo-url=https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git
```

### 3. 批量生成图像

#### 单图生成

```bash
modal run batch_inference.py \
  --prompt "A beautiful sunset over the ocean"
```

#### 批量生成（串行模式）

```bash
# 创建提示词文件 prompts.txt
cat > prompts.txt << EOF
A beautiful landscape with mountains
A cute cat playing with yarn
A futuristic cityscape at night
EOF

# 批量生成
modal run batch_inference.py --prompts-file prompts.txt
```

#### 批量生成（并行模式）

```bash
# 使用并行模式，每个提示词独立容器，速度更快
modal run batch_inference.py \
  --prompts-file prompts.txt \
  --parallel
```

#### 自定义参数

```bash
modal run batch_inference.py \
  --prompt "A majestic dragon" \
  --width 1024 \
  --height 1024 \
  --steps 30 \
  --cfg 7.5
```

### 4. 管理工作流模板

```bash
# 列出所有工作流
modal run workflow_manager.py --action=list

# 保存工作流到 Volume
modal run workflow_manager.py \
  --action=save \
  --workflow-name=my_workflow \
  --workflow-file=workflow.json

# 加载工作流
modal run workflow_manager.py \
  --action=load \
  --workflow-name=my_workflow

# 验证工作流
modal run workflow_manager.py \
  --action=validate \
  --workflow-file=workflow.json

# 删除工作流
modal run workflow_manager.py \
  --action=delete \
  --workflow-name=my_workflow
```

### 5. 使用工具函数

```bash
# 查看图片信息
modal run utils.py \
  --action=info \
  --image-file=test.png

# 调整图片大小
modal run utils.py \
  --action=resize \
  --image-file=test.png \
  --width=512 \
  --height=512 \
  --output-file=resized.png

# 转换图片格式
modal run utils.py \
  --action=convert \
  --image-file=test.png \
  --output-format=JPEG \
  --quality=90 \
  --output-file=output.jpg

# 添加水印
modal run utils.py \
  --action=watermark \
  --image-file=test.png \
  --watermark-text="My Image" \
  --position=bottom-right \
  --output-file=watermarked.png
```

## ⚙️ 配置管理

### GPU 配置

编辑 `config.py` 中的 GPU 设置：

```python
# 可选: "T4", "A10G", "A100", "L4", "L40S", "H100"
GPU_TYPE = "L40S"
GPU_COUNT = 1  # 多 GPU 并行
```

### 预设配置

使用预设配置快速切换环境：

```python
from config import get_preset_config

# 开发环境配置（便宜）
dev_config = get_preset_config("dev")
# {"gpu": "T4", "max_containers": 1, "memory": 8192, ...}

# 生产环境配置（性能）
prod_config = get_preset_config("prod")
# {"gpu": "A100", "max_containers": 5, "memory": 32768, ...}

# 高性能配置（顶配）
high_perf_config = get_preset_config("high_perf")
# {"gpu": "H100", "max_containers": 3, "memory": 65536, ...}
```

### 容器配置

```python
MAX_CONTAINERS = 1              # 最大并发容器数
MAX_CONCURRENT_INPUTS = 10      # 每个容器的最大并发请求
CONTAINER_IDLE_TIMEOUT = 300    # 容器空闲超时（秒）
MEMORY_SIZE = 16384             # 内存大小（MB）
```

## 📚 Python SDK 使用

### 程序化调用

```python
import modal

# 1. 批量生成图像
app = modal.App.lookup("comfyui-batch-processor")
generator = app.BatchImageGenerator()

prompts = [
    "A beautiful sunset",
    "A cute cat",
    "A mountain landscape"
]

results = generator.generate_batch.remote(
    prompts,
    width=1024,
    height=1024,
    steps=25
)

# 2. 安装节点
node_manager = modal.App.lookup("comfyui-node-manager")
install_fn = modal.Function.lookup("comfyui-node-manager", "install_node")

result = install_fn.remote(
    "https://github.com/ltdrdata/ComfyUI-Manager.git"
)

# 3. 图像处理
utils_app = modal.App.lookup("comfyui-utils")
resize_fn = modal.Function.lookup("comfyui-utils", "resize_image")

with open("image.png", "rb") as f:
    img_bytes = f.read()

resized = resize_fn.remote(img_bytes, width=512, height=512)

with open("resized.png", "wb") as f:
    f.write(resized)
```

## 🔧 高级用法

### 1. 批量安装节点

创建 `install_nodes.py`:

```python
import modal

app = modal.App.lookup("comfyui-node-manager")
batch_install = modal.Function.lookup("comfyui-node-manager", "batch_install_nodes")

nodes = [
    "https://github.com/ltdrdata/ComfyUI-Manager.git",
    "https://github.com/Fannovel16/comfyui_controlnet_aux.git",
    "https://github.com/cubiq/ComfyUI_IPAdapter_plus.git",
]

result = batch_install.remote(nodes)
print(f"成功: {result['successful']}, 失败: {result['failed']}")
```

### 2. 自定义工作流生成

```python
import json

# 基于现有工作流修改
with open("workflow_api.json", "r") as f:
    workflow = json.load(f)

# 修改参数
workflow["27"]["inputs"]["width"] = 1024
workflow["27"]["inputs"]["height"] = 1024
workflow["31"]["inputs"]["steps"] = 30

# 保存新工作流
with open("custom_workflow.json", "w") as f:
    json.dump(workflow, f, indent=2)

# 上传到 Volume
from workflow_manager import save_workflow
result = save_workflow.remote("my_custom_workflow", workflow)
```

### 3. 监控和日志

```bash
# 查看应用日志
modal app logs example-comfyapp

# 实时跟踪日志
modal app logs example-comfyapp --follow

# 查看应用状态
modal app list

# 查看详细信息
modal app show example-comfyapp
```

## 📊 性能优化

### 并行处理策略

**串行模式**（单容器）：
- 适合：少量图片（< 10张）
- 优点：节省成本，容器复用
- 缺点：速度较慢

**并行模式**（多容器）：
- 适合：大量图片（> 10张）
- 优点：速度快，自动扩展
- 缺点：成本较高，冷启动时间

### GPU 选择建议

| GPU 类型 | 性能 | 成本 | 适用场景 |
|---------|------|------|---------|
| T4 | ⭐⭐ | $ | 开发测试 |
| L4 | ⭐⭐⭐ | $$ | 生产环境（经济） |
| A10G | ⭐⭐⭐⭐ | $$$ | 生产环境（均衡） |
| L40S | ⭐⭐⭐⭐ | $$$ | 生产环境（推荐） |
| A100 | ⭐⭐⭐⭐⭐ | $$$$ | 高性能需求 |
| H100 | ⭐⭐⭐⭐⭐ | $$$$$ | 顶级性能 |

## 🐛 故障排除

### 常见问题

**1. 节点安装失败**
```bash
# 检查节点是否已存在
modal run manage_nodes.py --action=list

# 手动删除后重试
modal run manage_nodes.py --action=uninstall --node-name=XXX
```

**2. 批量生成超时**
```bash
# 增加超时时间（修改 config.py）
REQUEST_TIMEOUT = 3600  # 1小时
```

**3. Volume 空间不足**
```bash
# 查看 Volume 使用情况
modal volume get hf-hub-cache

# 清理不需要的文件
modal shell manage_nodes.py
# 在 shell 中手动删除文件
```

## 📝 开发指南

### 添加新功能

1. 创建新的 Python 文件
2. 使用 Modal App 包装
3. 定义函数并添加 `@app.function()` 装饰器
4. 添加 `@app.local_entrypoint()` 用于命令行调用

### 示例：创建新工具

```python
import modal
from config import get_volume

vol = get_volume()
image = modal.Image.debian_slim().pip_install("your-package")
app = modal.App("my-new-tool", image=image)

@app.function(volumes={"/cache": vol})
def my_function(param: str):
    """你的功能描述"""
    # 实现逻辑
    return result

@app.local_entrypoint()
def main(param: str = "default"):
    result = my_function.remote(param)
    print(result)
```

## 📄 许可证

MIT License

## 🙏 致谢

- ComfyUI 项目
- Modal 云平台
- 所有 Custom Nodes 开发者

## 📮 联系方式

如有问题或建议，请提交 Issue。
