# HunyuanVideo 1.5 Modal 部署

腾讯混元视频 1.5 - 基于 ComfyUI 的视频生成服务

## 📋 模型特点

- **8.3B 参数**: 轻量级设计，消费级 GPU 可运行
- **多分辨率**: 支持 480p / 720p / 1080p
- **双模式**: 文生视频 (T2V) + 图生视频 (I2V)
- **高质量**: 媲美更大参数模型的生成效果

## 🚀 快速开始

### 1. 配置项目变量

点击项目标题旁的齿轮图标，配置以下变量：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| VOLUME_NAME | 模型存储 Volume | hunyuan-video-cache |
| APP_NAME | Modal 应用名称 | hunyuan-video-app |
| GPU_TYPE | GPU 类型 | H100 |

### 2. 下载模型

```bash
# 下载 720p 基础模型 (推荐)
modal run download_models.py

# 下载 480p 模型 (更快，显存要求更低)
modal run download_models.py --resolution 480p

# 包含 I2V 和超分辨率模型
modal run download_models.py --include-i2v --include-sr
```

### 3. 部署应用

```bash
modal deploy hunyuan_video_deploy.py
```

### 4. 访问 ComfyUI

部署成功后，访问：
```
https://[your-workspace]--hunyuan-video-app-ui.modal.run
```

## 📁 模型文件

| 模型 | 大小 | 说明 |
|------|------|------|
| hunyuan_video_720p_bf16.safetensors | ~16GB | 720p 主模型 |
| clip_l.safetensors | ~246MB | CLIP 文本编码器 |
| llava_llama3_fp8_scaled.safetensors | ~9GB | LLaVA 视觉语言模型 |
| hunyuan_video_vae_bf16.safetensors | ~493MB | VAE 解码器 |

## 💻 硬件要求

| 分辨率 | 最低 VRAM | 推荐 VRAM |
|--------|-----------|-----------|
| 480p | 16GB | 24GB |
| 720p | 24GB | 40GB+ |
| 1080p | 40GB | 80GB |

## 🔧 ComfyUI 工作流

HunyuanVideo 1.5 在 ComfyUI 中使用以下节点：

1. **UNETLoader** - 加载主模型
2. **DualCLIPLoader** - 加载文本编码器
3. **VAELoader** - 加载 VAE
4. **EmptyHunyuanLatentVideo** - 创建视频潜空间
5. **KSampler** - 采样生成
6. **VAEDecodeTiled** - 解码视频 (推荐使用 Tiled 版本节省显存)

## 📚 参考资料

- [HunyuanVideo 1.5 官方仓库](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5)
- [HuggingFace 模型页面](https://huggingface.co/tencent/HunyuanVideo-1.5)
- [ComfyUI Wiki 教程](https://comfyui-wiki.com/en/tutorial/advanced/hunyuan-text-to-video-workflow-guide-and-example)
