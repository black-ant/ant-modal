# ComfyUI 节点管理器

基于 Modal 的 ComfyUI 完整部署和管理方案，支持动态添加模型和节点。

## 核心设计

**所有脚本共享同一个 Volume (`comfyui-cache`)**，实现：
- 模型持久化存储
- 自定义节点持久化
- 运行时动态添加资源

## 工作原理

```
┌─────────────────────────────────────────────────────────────────┐
│                    共享 Volume: comfyui-cache                    │
├─────────────────────────────────────────────────────────────────┤
│  /models/                    │  /custom_nodes/                  │
│    ├── checkpoints/          │    ├── ComfyUI-Easy-Use/         │
│    ├── loras/                │    ├── ComfyUI-Manager/          │
│    ├── vae/                  │    └── ...                       │
│    └── ...                   │                                  │
└─────────────────────────────────────────────────────────────────┘
         ↑                                    ↑
         │                                    │
    add_models.py                   comfyui_add_node_easy.py
    (添加模型)                         (添加节点)
         │                                    │
         └────────────────┬───────────────────┘
                          │
                          ▼
                   comfyui_app.py
                   (主服务启动时)
                          │
                          ▼
              ┌───────────────────────┐
              │  自动链接并加载资源    │
              │  • 链接模型文件        │
              │  • 链接节点目录        │
              │  • 安装节点依赖        │
              └───────────────────────┘
```

## 脚本说明

### 1. comfyui_app.py - 主服务（首次部署）

完整的 ComfyUI 服务，包含：
- 环境配置（Python 3.11 + ComfyUI）
- 基础 Custom Nodes
- 基础模型（可配置）
- Web UI 服务
- REST API 服务

```bash
# 部署应用（首次）
modal deploy comfyui_app.py

# 部署后会获得 URL:
# https://[workspace]--comfyui-app-ui.modal.run
```

### 2. add_models.py - 添加模型（随时添加）

支持从 HuggingFace 或 URL 下载模型：

```bash
# 查看已安装的模型
modal run add_models.py --action=list

# 从 HuggingFace 添加模型（需要填写变量）
modal run add_models.py

# 安装预设模型包
modal run add_models.py --action=preset --preset=flux-basic
```

### 3. comfyui_add_node_easy.py - 添加节点（随时添加）

通过 Git 克隆安装自定义节点：

```bash
# 执行脚本，填写节点仓库地址
modal run comfyui_add_node_easy.py
```

### 4. diagnose.py - 诊断工具

检查 Volume 中的资源状态：

```bash
modal run diagnose.py
```

### 5. restart_service.py - 重启服务

添加资源后重启服务以加载：

```bash
modal run restart_service.py
```

## 使用流程

### 首次部署

```bash
# 1. 部署主服务
modal deploy comfyui_app.py

# 2. 访问 URL 开始使用
```

### 添加新资源

```bash
# 1. 添加模型（可选）
modal run add_models.py

# 2. 添加节点（可选）
modal run comfyui_add_node_easy.py

# 3. 查看添加的资源
modal run diagnose.py

# 4. 重启服务以加载新资源
modal run restart_service.py

# 5. 访问 URL，服务自动重启并加载
```

## 注意事项

1. **Volume 共享**：所有脚本使用同一个 Volume (`comfyui-cache`)，数据互通
2. **持久化**：模型和节点存储在 Volume 中，不会因容器销毁而丢失
3. **自动加载**：ComfyUI 启动时会自动链接 Volume 中的模型和节点
4. **依赖安装**：节点依赖会在 ComfyUI 启动时自动安装
5. **重启生效**：添加资源后需要重启服务才能生效

## 常见问题

### Q: 添加节点后为什么看不到？

A: 需要重启服务。运行 `modal run restart_service.py`，然后访问 URL。

### Q: 可以同时添加多个节点吗？

A: 可以。多次运行添加节点脚本，每次填写不同的仓库地址。添加完成后统一重启服务即可。

### Q: 如何查看已添加的资源？

A: 运行 `modal run diagnose.py` 查看 Volume 中的所有模型和节点。
