# Comfy-视频生成

基于 ComfyUI + Wan 2.2 的视频生成项目。

## 脚本说明

| 脚本 | 功能 |
|------|------|
| `wan22_i2v_deploy.py` | Wan 2.2 图生视频 (I2V) 一键部署 |

## 使用方法

### 部署 Wan 2.2 I2V

```bash
cd data/projects/comfy-video-gen
modal deploy wan22_i2v_deploy.py
```

## 配置

- **GPU**: L40S (48GB) - FP8 量化
- **端口**: 24781
- **Volume**: `wan22-i2v-model-cache`

## 功能

- 图片 + 文字 → 视频
- 720P 分辨率
- 14B 模型 FP8 量化 (显存需求 ~30GB)
