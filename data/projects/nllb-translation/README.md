# NLLB 多语言翻译服务

使用 Meta 的 NLLB (No Language Left Behind) 模型部署高性能、低成本的翻译服务。

## 特点

- ✅ **支持 200+ 种语言**：覆盖全球主要语言
- 💰 **成本低**：T4 显卡即可运行，比大语言模型便宜 5-10 倍
- ⚡ **速度快**：专门的翻译模型，推理速度快
- 🎯 **质量高**：翻译质量优于通用 LLM
- 🔄 **批量处理**：支持批量翻译，提高效率

## 硬件要求

- **GPU**: T4（推荐）或更高
- **显存**: 4-6GB
- **成本**: 约 $0.20/小时（T4）

## 支持的语言

常用语言代码：

| 语言 | 代码 | NLLB 代码 |
|------|------|-----------|
| 简体中文 | zh | zho_Hans |
| 繁体中文 | zh-tw | zho_Hant |
| 英语 | en | eng_Latn |
| 日语 | ja | jpn_Jpan |
| 韩语 | ko | kor_Hang |
| 法语 | fr | fra_Latn |
| 德语 | de | deu_Latn |
| 西班牙语 | es | spa_Latn |
| 俄语 | ru | rus_Cyrl |
| 阿拉伯语 | ar | arb_Arab |

完整语言列表：https://github.com/facebookresearch/flores/blob/main/flores200/README.md

## 快速开始

### 1. 部署服务

```bash
modal deploy nllb_translator.py
```

### 2. 测试翻译

```bash
modal run nllb_translator.py
```

### 3. 使用 API

部署后会获得一个 HTTPS 端点，可以通过 HTTP 请求使用：

```bash
# 单条翻译
curl -X POST https://your-app.modal.run/translate_api \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好，世界！",
    "source_lang": "zh",
    "target_lang": "en"
  }'

# 批量翻译
curl -X POST https://your-app.modal.run/translate_api \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["你好", "谢谢", "再见"],
    "source_lang": "zh",
    "target_lang": "en"
  }'
```

## Python 客户端示例

```python
import requests

# 翻译 API 端点
API_URL = "https://your-app.modal.run/translate_api"

# 单条翻译
response = requests.post(API_URL, json={
    "text": "人工智能正在改变世界",
    "source_lang": "zh",
    "target_lang": "en"
})
print(response.json()["translation"])
# 输出: Artificial intelligence is changing the world

# 批量翻译
response = requests.post(API_URL, json={
    "texts": [
        "机器学习",
        "深度学习",
        "神经网络"
    ],
    "source_lang": "zh",
    "target_lang": "en"
})
for translation in response.json()["translations"]:
    print(translation)
```

## 模型版本

项目默认使用 `facebook/nllb-200-distilled-600M`（600M 参数），适合大多数场景。

如需更高质量，可以修改代码使用更大的模型：

- `facebook/nllb-200-1.3B` - 1.3B 参数，需要 A10G
- `facebook/nllb-200-3.3B` - 3.3B 参数，需要 A100

修改方法：在 `nllb_translator.py` 中更改 `model_name` 变量。

## 性能优化

### 1. 批量处理

批量翻译可以显著提高吞吐量：

```python
translator = NLLBTranslator()
results = translator.batch_translate.remote(
    texts=["文本1", "文本2", "文本3"],
    source_lang="zh",
    target_lang="en"
)
```

### 2. 调整 Beam Search

在代码中修改 `num_beams` 参数：
- `num_beams=1`: 最快，质量稍低
- `num_beams=5`: 默认，平衡速度和质量
- `num_beams=10`: 最高质量，速度较慢

### 3. 容器配置

根据负载调整容器参数：

```python
@app.cls(
    gpu="T4",
    container_idle_timeout=300,  # 5分钟无请求后休眠
    timeout=600,                  # 单次请求超时
)
```

## 成本估算

基于 Modal 的 T4 定价（约 $0.20/小时）：

| 场景 | 每小时翻译量 | 成本 |
|------|-------------|------|
| 轻度使用 | 1000 条 | $0.20 |
| 中度使用 | 5000 条 | $0.20 |
| 重度使用 | 10000+ 条 | $0.20 |

由于按使用时间计费，实际成本取决于容器运行时间。

## 常见问题

### Q: 如何添加新语言？

A: 在 `lang_codes` 字典中添加语言代码映射，参考 NLLB 语言列表。

### Q: 翻译质量不理想怎么办？

A: 可以尝试：
1. 使用更大的模型（1.3B 或 3.3B）
2. 增加 `num_beams` 参数
3. 调整 `max_length` 参数

### Q: 可以翻译长文本吗？

A: 默认最大长度 512 tokens。如需翻译长文本，建议先分段，然后批量翻译。

### Q: 支持自动语言检测吗？

A: NLLB 不支持自动检测。可以集成 `langdetect` 或 `fasttext` 库实现。

## 相关资源

- [NLLB 论文](https://arxiv.org/abs/2207.04672)
- [Hugging Face 模型](https://huggingface.co/facebook/nllb-200-distilled-600M)
- [Modal 文档](https://modal.com/docs)

## 许可证

NLLB 模型使用 CC-BY-NC 4.0 许可证。
