# SVD 1.1 (Stable Video Diffusion) 部署项目

## 项目简介

基于 ComfyUI 的 Stable Video Diffusion 1.1 图生视频服务，可以从单张图片生成高质量短视频。

## 模型信息

### SVD (Stable Video Diffusion)
- **开发者**: Stability AI
- **类型**: 图生视频 (Image-to-Video)
- **版本**: 1.1
- **许可**: Stability AI 社区许可

### 两个版本

#### 1. SVD 标准版
- **模型**: `svd.safetensors`
- **帧数**: 14 帧
- **时长**: ~2.3 秒 (6fps)
- **显存**: ~16GB
- **速度**: 较快

#### 2. SVD-XT 扩展版
- **模型**: `svd_xt.safetensors`
- **帧数**: 25 帧
- **时长**: ~4.2 秒 (6fps)
- **显存**: ~20GB
- **速度**: 较慢，质量更好

## 技术规格

| 参数 | 值 |
|------|-----|
| 输入分辨率 | 任意 (会自动调整) |
| 输出分辨率 | 576x1024 (竖屏) 或 1024x576 (横屏) |
| 帧率 | 6 fps |
| 采样步数 | 20-30 步 |
| CFG Scale | 2.0-3.0 |
| 推荐 GPU | A100 (40GB+) |

## 快速开始

### 1. 部署服务

```bash
cd "data/projects/SVD 1.1"
modal deploy svd_deploy.py
```

### 2. 访问 Web 界面

部署成功后，访问 Modal 提供的 URL：
```
https://[your-workspace]--svd-video-ui.modal.run
```

### 3. 生成视频

1. 上传一张图片（建议 1024x576 或 576x1024）
2. 选择模型：
   - `svd.safetensors` - 14 帧快速版
   - `svd_xt.safetensors` - 25 帧高质量版
3. 调整参数：
   - **Motion Bucket ID**: 控制运动幅度 (1-255，推荐 127)
   - **FPS**: 帧率 (推荐 6)
   - **Steps**: 采样步数 (推荐 20-30)
4. 点击生成

## 参数说明

### Motion Bucket ID
控制视频中的运动幅度：
- **低值 (1-50)**: 微小运动，适合静态场景
- **中值 (50-150)**: 适度运动，推荐值 127
- **高值 (150-255)**: 大幅运动，可能不稳定

### Augmentation Level
数据增强级别：
- **0**: 无增强（推荐）
- **0.1-0.3**: 轻微增强
- **> 0.5**: 强增强，可能影响质量

### CFG Scale
提示词引导强度：
- **1.5-2.0**: 弱引导，更自然
- **2.0-3.0**: 推荐范围
- **> 3.0**: 强引导，可能过度

## 使用场景

### 1. 产品展示视频
- 上传产品图片
- 生成 360° 旋转效果
- 适合电商展示

### 2. 人物动画
- 上传人物肖像
- 生成微表情、眨眼等动作
- 适合虚拟主播、数字人

### 3. 场景动画
- 上传风景照片
- 生成云朵飘动、水波荡漾
- 适合背景视频

### 4. 艺术创作
- 上传艺术作品
- 生成动态效果
- 适合数字艺术

## 最佳实践

### 输入图片建议

1. **分辨率**: 1024x576 (横屏) 或 576x1024 (竖屏)
2. **内容**: 清晰、主体明确
3. **避免**: 过于复杂的场景、多个主体
4. **格式**: PNG, JPG, WebP

### 参数调优

#### 快速预览
```
模型: svd.safetensors
Steps: 15
Motion Bucket ID: 100
CFG: 2.0
```

#### 高质量输出
```
模型: svd_xt.safetensors
Steps: 25
Motion Bucket ID: 127
CFG: 2.5
```

#### 静态场景
```
Motion Bucket ID: 30-50
Steps: 20
CFG: 2.0
```

#### 动态场景
```
Motion Bucket ID: 150-200
Steps: 25
CFG: 2.5
```

## 工作流示例

### 基础图生视频工作流

```json
{
  "1": "加载 SVD-XT 模型",
  "2": "加载输入图片",
  "3": "SVD 条件编码 (设置帧数、运动参数)",
  "4": "KSampler 采样",
  "5": "VAE 解码",
  "6": "视频合成输出"
}
```

### 高级工作流（带预处理）

```
输入图片 → 图片缩放 → 图片裁剪 → SVD 生成 → 帧插值 → 视频输出
```

## 性能优化

### 显存优化

1. **使用 SVD 标准版**: 14 帧比 25 帧省显存
2. **降低分辨率**: 512x512 可以在 16GB 显存运行
3. **减少采样步数**: 15-20 步通常足够

### 速度优化

1. **使用 A100**: 比 A10G 快 2-3 倍
2. **批量生成**: 一次生成多个视频
3. **预加载模型**: 保持容器活跃

## 常见问题

### Q1: 生成的视频抖动严重？
**A**: 降低 Motion Bucket ID 到 50-100，增加采样步数到 25-30。

### Q2: 视频内容与输入图片差异大？
**A**: 提高 CFG Scale 到 3.0-4.0，确保输入图片清晰。

### Q3: 显存不足？
**A**: 使用 SVD 标准版，或降低分辨率到 512x512。

### Q4: 生成速度慢？
**A**: 使用 A100 GPU，减少采样步数到 15-20。

### Q5: 如何生成更长的视频？
**A**: SVD 最多 25 帧，可以使用帧插值技术扩展到 50-100 帧。

## 技术限制

1. **固定帧数**: 14 或 25 帧，无法自定义
2. **固定分辨率**: 576x1024，其他分辨率需要缩放
3. **无文本提示**: 仅支持图片输入，不支持文本描述
4. **运动控制有限**: 只能通过 Motion Bucket ID 粗略控制

## 扩展功能

### 1. 帧插值
使用 RIFE 或 FILM 模型将 25 帧插值到 50-100 帧：
```python
# 安装 ComfyUI-Frame-Interpolation 节点
comfy node install ComfyUI-Frame-Interpolation
```

### 2. 超分辨率
使用 Real-ESRGAN 提升视频分辨率：
```python
# 安装 ComfyUI-VideoHelperSuite 节点
comfy node install ComfyUI-VideoHelperSuite
```

### 3. 音频添加
使用 FFmpeg 为视频添加背景音乐：
```bash
ffmpeg -i video.mp4 -i audio.mp3 -c:v copy -c:a aac output.mp4
```

## 相关资源

- [SVD 官方论文](https://stability.ai/research/stable-video-diffusion-scaling-latent-video-diffusion-models-to-large-datasets)
- [HuggingFace 模型页](https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt)
- [ComfyUI 官方文档](https://github.com/comfyanonymous/ComfyUI)
- [Modal 使用教程](../../docs/Modal使用教程.md)

## 许可证

本项目使用 Stability AI 社区许可证。商业使用请参考：
https://stability.ai/license

## 更新日志

- **2025-01-03**: 初始版本，支持 SVD 和 SVD-XT 模型

---

**需要帮助？** 查看 [常见问题](#常见问题) 或提交 Issue。
