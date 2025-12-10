export interface TutorialSection {
  id: string;
  title: string;
  icon?: string;
  children: Tutorial[];
}

export interface Tutorial {
  id: string;
  title: string;
  content: string;
}

export const tutorialSections: TutorialSection[] = [
  {
    id: 'getting-started',
    title: '快速开始',
    children: [
      {
        id: 'installation',
        title: '安装与配置',
        content: `# 安装与配置

## 安装 Modal

\`\`\`bash
# 使用 pip 安装
pip install modal

# 或使用 conda
conda install -c conda-forge modal
\`\`\`

## 初始化配置

\`\`\`bash
# 初始化，会打开浏览器进行认证
modal setup

# 查看当前配置
modal config show
\`\`\`

## 验证安装

创建一个简单的测试文件 \`test.py\`：

\`\`\`python
import modal

app = modal.App("test-app")

@app.function()
def hello(name: str = "World"):
    return f"Hello, {name}!"

@app.local_entrypoint()
def main():
    result = hello.remote("Modal")
    print(result)
\`\`\`

运行测试：

\`\`\`bash
modal run test.py
\`\`\``
      },
      {
        id: 'first-app',
        title: '第一个应用',
        content: `# 第一个 Modal 应用

## 创建基础应用

\`\`\`python
import modal

# 创建应用
app = modal.App("my-first-app")

# 定义函数
@app.function()
def square(x: int) -> int:
    """计算平方"""
    return x * x

# 本地入口点
@app.local_entrypoint()
def main():
    result = square.remote(10)
    print(f"10 的平方是: {result}")
\`\`\`

## 运行方式

### 开发模式
\`\`\`bash
modal run my_first_app.py
\`\`\`

### 部署模式
\`\`\`bash
modal deploy my_first_app.py
\`\`\``
      }
    ]
  },
  {
    id: 'core-concepts',
    title: '核心概念',
    children: [
      {
        id: 'images',
        title: '镜像管理',
        content: `# 镜像管理

## 什么是镜像？

镜像定义了函数运行的环境，包括操作系统、Python版本和依赖包。

## 创建镜像

### 基础镜像

\`\`\`python
import modal

# Debian Slim (推荐，体积小)
image = modal.Image.debian_slim()

# Debian Slim with Python 3.11
image = modal.Image.debian_slim(python_version="3.11")

# 从 Docker Hub
image = modal.Image.from_registry("ubuntu:22.04")
\`\`\`

### 安装 Python 包

\`\`\`python
# 单个包
image = modal.Image.debian_slim().pip_install("numpy")

# 多个包
image = modal.Image.debian_slim().pip_install(
    "numpy",
    "pandas",
    "scikit-learn"
)

# 指定版本
image = modal.Image.debian_slim().pip_install(
    "torch==2.0.0",
    "transformers>=4.30.0"
)

# 从 requirements.txt
image = modal.Image.debian_slim().pip_install_from_requirements(
    "requirements.txt"
)
\`\`\`

### 安装系统包

\`\`\`python
# apt 安装
image = modal.Image.debian_slim().apt_install(
    "git",
    "wget",
    "curl",
    "ffmpeg"
)
\`\`\`

### 链式调用

\`\`\`python
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "wget")
    .pip_install("torch", "transformers")
    .run_commands(
        "git clone https://github.com/user/repo.git /repo",
        "cd /repo && pip install -e ."
    )
)
\`\`\`

### 添加本地文件

\`\`\`python
from pathlib import Path

image = (
    modal.Image.debian_slim()
    .copy_local_file("config.json", "/app/config.json")
    .copy_local_dir("models/", "/app/models/")
)
\`\`\`

## 使用镜像

\`\`\`python
# 应用级别
app = modal.App("my-app", image=image)

# 函数级别
@app.function(image=custom_image)
def my_function():
    import numpy as np
    return np.array([1, 2, 3])
\`\`\``
      },
      {
        id: 'gpu-basics',
        title: 'GPU 计算',
        content: `# GPU 计算

## GPU 类型和选择

| GPU | 显存 | 性能 | 价格 | 适用场景 |
|-----|------|------|------|---------|
| T4 | 16GB | ⭐⭐ | $ | 开发测试、小模型推理 |
| L4 | 24GB | ⭐⭐⭐ | $$ | 生产环境、性价比首选 |
| A10G | 24GB | ⭐⭐⭐ | $$ | 训练和推理平衡 |
| A100 | 40GB/80GB | ⭐⭐⭐⭐ | $$$ | 大模型训练 |
| H100 | 80GB | ⭐⭐⭐⭐⭐ | $$$$ | 最高性能需求 |

## 基础用法

\`\`\`python
import modal

app = modal.App("gpu-app")

image = modal.Image.debian_slim().pip_install("torch", "torchvision")

@app.function(
    gpu="T4",  # 指定 GPU 类型
    image=image
)
def gpu_function():
    import torch
    
    # 检查 GPU
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    else:
        device = torch.device("cpu")
    
    # 在 GPU 上创建张量
    x = torch.randn(1000, 1000).to(device)
    y = torch.matmul(x, x)
    
    return y.cpu().numpy()

@app.local_entrypoint()
def main():
    result = gpu_function.remote()
    print(f"Result shape: {result.shape}")
\`\`\`

## 多 GPU

\`\`\`python
# 使用多个 GPU
@app.function(gpu="A100:2")  # 2个 A100
def multi_gpu_training():
    import torch
    
    if torch.cuda.device_count() > 1:
        print(f"Using {torch.cuda.device_count()} GPUs")
        # 使用 DataParallel 或 DistributedDataParallel
\`\`\`

## GPU 内存管理

\`\`\`python
@app.function(gpu="A10G")
def gpu_memory_demo():
    import torch
    
    # 清空缓存
    torch.cuda.empty_cache()
    
    # 查看内存使用
    print(f"Allocated: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print(f"Cached: {torch.cuda.memory_reserved() / 1e9:.2f} GB")
    
    # 设置内存增长策略
    torch.cuda.set_per_process_memory_fraction(0.8)  # 限制使用 80% 显存
\`\`\``
      },
      {
        id: 'class-methods',
        title: '类和方法',
        content: `# 类和方法

使用类可以在多次调用间共享状态，特别适合需要加载大型模型的场景。

## 基础用法

\`\`\`python
import modal

app = modal.App("class-demo")

image = modal.Image.debian_slim().pip_install("torch", "transformers")

@app.cls(
    gpu="T4",
    image=image,
    container_idle_timeout=300  # 5分钟不用才关闭
)
class ModelInference:
    @modal.enter()
    def load_model(self):
        """容器启动时执行一次"""
        from transformers import AutoModel, AutoTokenizer
        
        print("Loading model...")
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        self.model = AutoModel.from_pretrained("bert-base-uncased")
        print("Model loaded!")
    
    @modal.method()
    def predict(self, text: str):
        """每次调用都执行"""
        inputs = self.tokenizer(text, return_tensors="pt")
        outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean().item()
    
    @modal.method()
    def batch_predict(self, texts: list):
        """批量预测"""
        results = []
        for text in texts:
            results.append(self.predict(text))
        return results

@app.local_entrypoint()
def main():
    # 实例化类
    model = ModelInference()
    
    # 多次调用，模型只加载一次
    result1 = model.predict.remote("Hello Modal")
    result2 = model.predict.remote("Another text")
    
    # 批量调用
    texts = ["text1", "text2", "text3"]
    results = model.batch_predict.remote(texts)
    
    print(results)
\`\`\`

## 类的生命周期

\`\`\`python
@app.cls()
class LifecycleDemo:
    @modal.enter()
    def setup(self):
        """容器启动时执行"""
        print("Setting up...")
        self.data = load_data()
    
    @modal.method()
    def process(self, item):
        """处理数据"""
        return self.data.process(item)
    
    @modal.exit()
    def cleanup(self):
        """容器关闭时执行"""
        print("Cleaning up...")
        self.data.close()
\`\`\`

## Web 方法

\`\`\`python
@app.cls()
class WebModel:
    @modal.enter()
    def load(self):
        from transformers import pipeline
        self.classifier = pipeline("sentiment-analysis")
    
    @modal.web_endpoint(method="POST")
    def classify(self, item: dict):
        text = item.get("text", "")
        result = self.classifier(text)[0]
        return {
            "label": result["label"],
            "score": result["score"]
        }
\`\`\`

访问: \`https://username--class-demo-webmodel-classify.modal.run\``
      }
    ]
  },
  {
    id: 'storage',
    title: '存储管理',
    children: [
      {
        id: 'volumes',
        title: 'Volume 持久化',
        content: `# Volume 持久化存储

## 创建和使用

\`\`\`python
import modal

app = modal.App("volume-demo")
volume = modal.Volume.from_name("my-data", create_if_missing=True)

@app.function(volumes={"/data": volume})
def save_file(filename: str, content: str):
    with open(f"/data/{filename}", 'w') as f:
        f.write(content)
    volume.commit()  # 重要！
    return "Saved"

@app.function(volumes={"/data": volume})
def read_file(filename: str):
    with open(f"/data/{filename}", 'r') as f:
        return f.read()
\`\`\`

## Volume 命令

\`\`\`bash
modal volume list
modal volume get my-data
modal volume delete my-data
\`\`\``
      },
      {
        id: 'secrets',
        title: 'Secret 管理',
        content: `# Secret 密钥管理

## 创建 Secret

\`\`\`bash
modal secret create my-keys \\
    API_KEY=sk-xxx \\
    DB_URL=postgresql://...
\`\`\`

## 使用 Secret

\`\`\`python
import modal

app = modal.App("secret-demo")
secret = modal.Secret.from_name("my-keys")

@app.function(secrets=[secret])
def use_secret():
    import os
    api_key = os.environ["API_KEY"]
    return f"Using key: {api_key[:10]}..."
\`\`\``
      }
    ]
  },
  {
    id: 'web-services',
    title: 'Web 服务',
    children: [
      {
        id: 'web-endpoints',
        title: 'Web Endpoint',
        content: `# Web Endpoint

## GET 请求

\`\`\`python
import modal

app = modal.App("web-api")

@app.function()
@modal.web_endpoint(method="GET")
def hello(name: str = "World"):
    return {"message": f"Hello, {name}!"}
\`\`\`

## POST 请求

\`\`\`python
@app.function()
@modal.web_endpoint(method="POST")
def process(item: dict):
    return {"result": item.get("value", 0) * 2}
\`\`\``
      },
      {
        id: 'fastapi',
        title: 'FastAPI 集成',
        content: `# FastAPI 集成

\`\`\`python
import modal

app = modal.App("fastapi-app")
image = modal.Image.debian_slim().pip_install("fastapi[standard]")

@app.function(image=image)
@modal.asgi_app()
def create_app():
    from fastapi import FastAPI
    
    web_app = FastAPI()
    
    @web_app.get("/")
    def root():
        return {"message": "Hello FastAPI!"}
    
    @web_app.get("/items/{item_id}")
    def read_item(item_id: int):
        return {"item_id": item_id}
    
    return web_app
\`\`\`

启动服务：

\`\`\`bash
modal serve fastapi_app.py
\`\`\``
      }
    ]
  },
  {
    id: 'parallel',
    title: '并行处理',
    children: [
      {
        id: 'map-starmap',
        title: 'Map 并行',
        content: `# 并行处理

## map() - 单参数并行

\`\`\`python
import modal

app = modal.App("parallel")

@app.function()
def process(item: str):
    import time
    time.sleep(1)  # 模拟耗时操作
    return item.upper()

@app.local_entrypoint()
def main():
    items = ["apple", "banana", "cherry", "date", "elderberry"]
    
    # 串行执行需要 5 秒
    # 并行执行只需约 1 秒
    results = list(process.map(items))
    print(results)
    # ['APPLE', 'BANANA', 'CHERRY', 'DATE', 'ELDERBERRY']
\`\`\`

## starmap() - 多参数并行

\`\`\`python
@app.function()
def add(a: int, b: int, c: int = 0):
    return a + b + c

@app.local_entrypoint()
def main():
    # 参数以元组形式传递
    tasks = [(1, 2), (3, 4), (5, 6)]
    results = list(add.starmap(tasks))
    print(results)  # [3, 7, 11]
    
    # 带可选参数
    tasks_with_c = [(1, 2, 10), (3, 4, 20)]
    results = list(add.starmap(tasks_with_c))
    print(results)  # [13, 27]
\`\`\`

## for_each() - 不关心返回值

\`\`\`python
@app.function()
def send_email(email: str):
    print(f"Sending email to {email}")
    # 发送邮件逻辑
    
@app.local_entrypoint()
def main():
    emails = ["user1@example.com", "user2@example.com"]
    
    # 并行发送，不等待返回
    for _ in send_email.for_each(emails):
        pass
\`\`\`

## 实战：批量图像处理

\`\`\`python
import modal

app = modal.App("image-processing")

image = modal.Image.debian_slim().pip_install("Pillow", "requests")

@app.function(image=image, cpu=2)
def process_image(url: str):
    from PIL import Image
    import requests
    from io import BytesIO
    
    # 下载图片
    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    
    # 调整大小
    img = img.resize((512, 512))
    
    # 转换格式
    img = img.convert("RGB")
    
    return {
        "url": url,
        "size": img.size,
        "mode": img.mode
    }

@app.local_entrypoint()
def main():
    urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        # ... 100 张图片
    ]
    
    # 并行处理所有图片
    results = list(process_image.map(urls))
    print(f"Processed {len(results)} images")
\`\`\``
      },
      {
        id: 'scheduled-jobs',
        title: '定时任务',
        content: `# 定时任务

## Cron 定时

\`\`\`python
import modal

app = modal.App("scheduled-jobs")

# 每天早上 9 点运行
@app.function(schedule=modal.Cron("0 9 * * *"))
def daily_report():
    print("Generating daily report...")
    # 生成报告逻辑
    return "Report generated"

# 每周一早上 8 点
@app.function(schedule=modal.Cron("0 8 * * 1"))
def weekly_cleanup():
    print("Running weekly cleanup...")
    # 清理逻辑

# 每小时的第 30 分钟
@app.function(schedule=modal.Cron("30 * * * *"))
def hourly_sync():
    print("Syncing data...")
    # 同步数据
\`\`\`

## Period 定时

\`\`\`python
# 每小时运行
@app.function(schedule=modal.Period(hours=1))
def hourly_task():
    print("Running hourly task")

# 每 30 分钟运行
@app.function(schedule=modal.Period(minutes=30))
def frequent_task():
    print("Running every 30 minutes")

# 每 6 小时运行
@app.function(schedule=modal.Period(hours=6))
def periodic_backup():
    print("Creating backup...")
\`\`\`

## Cron 表达式说明

\`\`\`
格式: 分 时 日 月 周

示例:
0 9 * * *       # 每天 9:00
30 8 * * 1-5    # 工作日 8:30
0 0 1 * *       # 每月 1 号 0:00
0 */6 * * *     # 每 6 小时
15 2 * * 0      # 每周日 2:15
\`\`\`

## 部署定时任务

\`\`\`bash
# 部署后自动按计划运行
modal deploy scheduled_jobs.py

# 查看定时任务状态
modal app list

# 手动触发定时任务
modal run scheduled_jobs.py::daily_report
\`\`\`

## 实战：自动备份数据库

\`\`\`python
import modal

app = modal.App("database-backup")

volume = modal.Volume.from_name("backups", create_if_missing=True)
secret = modal.Secret.from_name("db-credentials")

@app.function(
    schedule=modal.Cron("0 2 * * *"),  # 每天凌晨 2 点
    volumes={"/backups": volume},
    secrets=[secret],
    timeout=3600  # 1 小时超时
)
def backup_database():
    import os
    import subprocess
    from datetime import datetime
    
    # 获取数据库凭据
    db_url = os.environ["DATABASE_URL"]
    
    # 生成备份文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"/backups/db_backup_{timestamp}.sql"
    
    # 执行备份
    subprocess.run([
        "pg_dump",
        db_url,
        "-f", backup_file
    ], check=True)
    
    # 提交到 Volume
    volume.commit()
    
    print(f"Backup created: {backup_file}")
    
    # 清理旧备份（保留最近 7 天）
    # cleanup_old_backups()
\`\`\``
      }
    ]
  },
  {
    id: 'real-world-examples',
    title: '实战案例',
    children: [
      {
        id: 'image-generation',
        title: '图像生成 API',
        content: `# 图像生成 API (Stable Diffusion)

完整的图像生成服务示例。

\`\`\`python
import modal

app = modal.App("stable-diffusion-api")

# 创建包含所需依赖的镜像
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "diffusers==0.21.0",
        "transformers==4.30.0",
        "torch==2.0.1",
        "accelerate",
    )
)

# Volume 用于缓存模型
volume = modal.Volume.from_name("sd-models", create_if_missing=True)

@app.cls(
    gpu="A10G",
    image=image,
    volumes={"/models": volume},
    container_idle_timeout=300,
)
class StableDiffusion:
    @modal.enter()
    def load_model(self):
        """加载模型（只在容器启动时执行一次）"""
        from diffusers import StableDiffusionPipeline
        import torch
        
        print("Loading Stable Diffusion model...")
        
        self.pipe = StableDiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-2-1",
            torch_dtype=torch.float16,
            cache_dir="/models"
        ).to("cuda")
        
        # 可选：启用内存优化
        self.pipe.enable_attention_slicing()
        
        # 提交模型到 Volume
        volume.commit()
        
        print("Model loaded!")
    
    @modal.method()
    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        num_images: int = 1,
        steps: int = 25,
        guidance_scale: float = 7.5
    ):
        """生成图像"""
        images = self.pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_images_per_prompt=num_images,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
        ).images
        
        # 转换为 base64
        import io
        import base64
        
        results = []
        for img in images:
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode()
            results.append(img_str)
        
        return results
    
    @modal.web_endpoint(method="POST")
    def api(self, item: dict):
        """Web API 端点"""
        prompt = item.get("prompt", "")
        images = self.generate(prompt)
        
        return {
            "prompt": prompt,
            "images": images,
            "count": len(images)
        }

@app.local_entrypoint()
def main(prompt: str = "a cat in space"):
    model = StableDiffusion()
    images = model.generate.remote(prompt)
    print(f"Generated {len(images)} images")
\`\`\`

使用 API：

\`\`\`bash
curl -X POST https://username--stable-diffusion-api-stablediffusion-api.modal.run \\
  -H "Content-Type: application/json" \\
  -d '{"prompt": "a beautiful sunset"}'
\`\`\``
      },
      {
        id: 'data-pipeline',
        title: '数据处理流水线',
        content: `# 数据处理流水线

完整的数据ETL流水线示例。

\`\`\`python
import modal

app = modal.App("data-pipeline")

image = modal.Image.debian_slim().pip_install(
    "pandas",
    "requests",
    "sqlalchemy",
    "psycopg2-binary"
)

volume = modal.Volume.from_name("data-cache", create_if_missing=True)
secret = modal.Secret.from_name("database-credentials")

@app.function(image=image)
def extract_data(source_url: str):
    """提取数据"""
    import requests
    import pandas as pd
    
    print(f"Extracting data from {source_url}")
    response = requests.get(source_url)
    data = response.json()
    
    df = pd.DataFrame(data)
    print(f"Extracted {len(df)} records")
    
    return df.to_dict('records')

@app.function(image=image, cpu=2)
def transform_data(records: list):
    """转换数据"""
    import pandas as pd
    
    print(f"Transforming {len(records)} records")
    df = pd.DataFrame(records)
    
    # 数据清洗
    df = df.dropna()
    df = df.drop_duplicates()
    
    # 数据转换
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['amount'] = df['amount'].astype(float)
    
    # 数据聚合
    df['month'] = df['created_at'].dt.to_period('M')
    summary = df.groupby('month').agg({
        'amount': ['sum', 'mean', 'count']
    }).reset_index()
    
    print(f"Transformed to {len(summary)} summary records")
    
    return summary.to_dict('records')

@app.function(
    image=image,
    secrets=[secret],
    volumes={"/cache": volume}
)
def load_data(records: list, table_name: str):
    """加载数据到数据库"""
    import os
    import pandas as pd
    from sqlalchemy import create_engine
    
    print(f"Loading {len(records)} records to {table_name}")
    
    # 连接数据库
    db_url = os.environ["DATABASE_URL"]
    engine = create_engine(db_url)
    
    # 保存到数据库
    df = pd.DataFrame(records)
    df.to_sql(table_name, engine, if_exists='replace', index=False)
    
    # 同时缓存到 Volume
    df.to_parquet(f"/cache/{table_name}.parquet")
    volume.commit()
    
    print(f"Loaded {len(records)} records successfully")
    
    return {"status": "success", "rows": len(records)}

@app.function(
    image=image,
    schedule=modal.Cron("0 */6 * * *")  # 每 6 小时运行
)
def run_pipeline():
    """运行完整的ETL流水线"""
    print("Starting ETL pipeline...")
    
    # Extract
    raw_data = extract_data.remote(
        "https://api.example.com/data"
    )
    
    # Transform
    transformed_data = transform_data.remote(raw_data)
    
    # Load
    result = load_data.remote(transformed_data, "monthly_summary")
    
    print(f"Pipeline completed: {result}")
    
    return result

@app.local_entrypoint()
def main():
    # 手动触发流水线
    result = run_pipeline.remote()
    print(result)
\`\`\``
      },
      {
        id: 'webscraper',
        title: 'Web 爬虫',
        content: `# 分布式 Web 爬虫

使用 Modal 进行大规模网页抓取。

\`\`\`python
import modal

app = modal.App("web-scraper")

image = modal.Image.debian_slim().pip_install(
    "beautifulsoup4",
    "requests",
    "selenium",
    "webdriver-manager"
)

volume = modal.Volume.from_name("scraper-data", create_if_missing=True)

@app.function(image=image, cpu=1)
def scrape_page(url: str):
    """抓取单个页面"""
    import requests
    from bs4 import BeautifulSoup
    
    try:
        print(f"Scraping {url}")
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 提取数据
        title = soup.find('h1').text if soup.find('h1') else ""
        paragraphs = [p.text for p in soup.find_all('p')]
        links = [a['href'] for a in soup.find_all('a', href=True)]
        
        return {
            "url": url,
            "title": title,
            "content": " ".join(paragraphs[:5]),  # 前5段
            "links": links[:10],  # 前10个链接
            "success": True
        }
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return {
            "url": url,
            "success": False,
            "error": str(e)
        }

@app.function(
    image=image,
    volumes={"/data": volume}
)
def save_results(results: list, filename: str):
    """保存结果"""
    import json
    
    output_path = f"/data/{filename}"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    volume.commit()
    
    print(f"Saved {len(results)} results to {output_path}")
    
    return output_path

@app.local_entrypoint()
def main():
    # 要抓取的 URL 列表
    urls = [
        "https://example.com/page1",
        "https://example.com/page2",
        # ... 可以有成百上千个 URL
    ]
    
    # 并行抓取所有页面
    print(f"Scraping {len(urls)} pages...")
    results = list(scrape_page.map(urls))
    
    # 统计成功率
    successful = sum(1 for r in results if r['success'])
    print(f"Success rate: {successful}/{len(results)}")
    
    # 保存结果
    save_results.remote(results, "scrape_results.json")
    
    print("Scraping completed!")
\`\`\``
      }
    ]
  },
  {
    id: 'best-practices',
    title: '最佳实践',
    children: [
      {
        id: 'cost-optimization',
        title: '成本优化',
        content: `# 成本优化

## 选择合适的 GPU

| GPU | 成本 | 适用场景 |
|-----|------|---------|
| T4 | $ | 开发测试 |
| A10G | $$ | 生产环境 |
| A100 | $$$ | 高性能需求 |

## 设置超时

\`\`\`python
@app.function(
    timeout=300,  # 5分钟超时
    container_idle_timeout=60  # 空闲1分钟后回收
)
def my_function():
    pass
\`\`\`

## 使用 Volume 缓存

避免重复下载模型：

\`\`\`python
volume = modal.Volume.from_name("models")

@app.function(volumes={"/models": volume})
def load_model():
    # 模型会缓存，下次不用重新下载
    model = AutoModel.from_pretrained(
        "bert-base-uncased",
        cache_dir="/models"
    )
    volume.commit()
\`\`\``
      },
      {
        id: 'debugging',
        title: '调试技巧',
        content: `# 调试技巧

## 查看日志

\`\`\`bash
# 实时查看日志
modal app logs my-app --follow

# 查看最近日志
modal app logs my-app --lines 100

# 查看特定函数的日志
modal app logs my-app --function my_function

# 导出日志到文件
modal app logs my-app > logs.txt
\`\`\`

## 交互式 Shell

\`\`\`bash
# 进入应用的交互式环境
modal shell app.py

# 在 shell 中测试代码
>>> import numpy as np
>>> np.array([1, 2, 3])
\`\`\`

## 本地调试

\`\`\`python
import modal

app = modal.App("debug-app")

@app.function()
def my_function(x: int):
    # 添加详细的调试信息
    print(f"Input: {x}")
    print(f"Type: {type(x)}")
    
    try:
        result = x * 2
        print(f"Result: {result}")
        return result
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        raise

# 本地测试（不在 Modal 上运行）
if __name__ == "__main__":
    # 直接调用函数进行测试
    result = my_function.local(10)
    print(result)
\`\`\`

## 性能分析

\`\`\`python
import time

@app.function()
def profiled_function():
    start = time.time()
    
    # 操作 1
    t1 = time.time()
    operation1()
    print(f"Operation 1: {time.time() - t1:.2f}s")
    
    # 操作 2
    t2 = time.time()
    operation2()
    print(f"Operation 2: {time.time() - t2:.2f}s")
    
    print(f"Total time: {time.time() - start:.2f}s")
\`\`\`

## 错误处理

\`\`\`python
from modal import App

app = App("error-handling")

@app.function(retries=3)  # 自动重试 3 次
def robust_function(url: str):
    import requests
    from requests.exceptions import RequestException
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        print(f"Request failed: {e}")
        # 记录错误但不抛出，返回默认值
        return {"error": str(e)}
    except Exception as e:
        print(f"Unexpected error: {e}")
        # 重新抛出异常，触发重试
        raise
\`\`\``
      },
      {
        id: 'common-issues',
        title: '常见问题',
        content: `# 常见问题和解决方案

## 问题 1: 镜像构建失败

**症状**: pip install 失败或依赖冲突

**解决方案**:
\`\`\`python
# 指定确切的版本
image = modal.Image.debian_slim().pip_install(
    "torch==2.0.1",
    "transformers==4.30.0"
)

# 分步安装
image = (
    modal.Image.debian_slim()
    .pip_install("torch==2.0.1")  # 先安装基础包
    .pip_install("transformers")   # 再安装依赖包
)

# 使用 conda
image = (
    modal.Image.from_registry("continuumio/miniconda3:latest")
    .run_commands(
        "conda install -y pytorch torchvision -c pytorch"
    )
)
\`\`\`

## 问题 2: GPU 内存不足

**症状**: CUDA out of memory

**解决方案**:
\`\`\`python
# 1. 使用更大的 GPU
@app.function(gpu="A100")  # 从 T4 升级到 A100

# 2. 减小批次大小
batch_size = 8  # 改为 4 或 2

# 3. 清理 GPU 缓存
import torch
torch.cuda.empty_cache()

# 4. 使用梯度累积
# 5. 启用混合精度训练
\`\`\`

## 问题 3: 函数超时

**症状**: Function timed out after 300s

**解决方案**:
\`\`\`python
# 增加超时时间
@app.function(timeout=1800)  # 30 分钟
def long_running_task():
    pass

# 或者拆分成多个小任务
@app.function()
def process_batch(batch):
    return [process_item(item) for item in batch]

@app.local_entrypoint()
def main():
    # 分批处理
    batches = split_into_batches(all_items, batch_size=100)
    results = list(process_batch.map(batches))
\`\`\`

## 问题 4: Volume 数据丢失

**症状**: 写入的文件下次找不到

**解决方案**:
\`\`\`python
# 必须调用 commit()!
@app.function(volumes={"/data": volume})
def save_data():
    with open("/data/file.txt", "w") as f:
        f.write("content")
    
    volume.commit()  # ⭐ 重要！
    
    return "Saved"
\`\`\`

## 问题 5: 依赖导入失败

**症状**: ModuleNotFoundError

**解决方案**:
\`\`\`python
# 确保在镜像中安装了依赖
image = modal.Image.debian_slim().pip_install("missing-package")

@app.function(image=image)
def my_function():
    import missing_package  # 现在可以导入了
\`\`\`

## 问题 6: Secret 环境变量获取不到

**症状**: KeyError: 'API_KEY'

**解决方案**:
\`\`\`python
# 1. 确保 secret 已创建
# modal secret create my-secret API_KEY=xxx

# 2. 在函数中引用 secret
secret = modal.Secret.from_name("my-secret")

@app.function(secrets=[secret])  # ⭐ 必须传入
def use_secret():
    import os
    api_key = os.environ.get("API_KEY")  # 使用 get() 更安全
    if not api_key:
        raise ValueError("API_KEY not found")
\`\`\`

## 问题 7: 并发限制

**症状**: 任务排队时间过长

**解决方案**:
\`\`\`python
# 增加并发数
@app.function(
    concurrency_limit=10  # 允许 10 个并发执行
)
def concurrent_task():
    pass
\`\`\`

## 获取帮助

- 📖 官方文档: https://modal.com/docs
- 💬 Discord 社区: https://modal.com/discord
- 🐛 GitHub Issues: https://github.com/modal-labs/modal-client
- 📧 支持邮箱: support@modal.com`
      }
    ]
  }
];
