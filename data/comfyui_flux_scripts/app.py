"""
ComfyUI Flux 主应用入口
整合所有模块，提供完整的图像生成服务
"""

from pathlib import Path
import modal
from config import *
from model_download import download_all_models
from ui_service import start_ui_server
from api_service import start_comfy_background, handle_api_request

# ============================================
# 构建完整镜像
# ============================================

# 基础镜像
image = build_base_image()

# 安装自定义节点
image = install_custom_nodes(image)

# 获取配置
hf_secret = get_hf_secret()
vol = get_volume()

# 添加模型下载和 HuggingFace 支持
image = (
    image.pip_install("huggingface_hub[hf_transfer]==0.34.4")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_function(
        download_all_models,
        volumes={"/cache": vol},
        secrets=[hf_secret]
    )
    .add_local_file(
        Path(__file__).parent / "workflow_api.json",
        "/root/workflow_api.json"
    )
)

# 创建 Modal 应用
app = modal.App(name=APP_NAME, image=image)


# ============================================
# UI 服务
# ============================================

@app.function(
    max_containers=MAX_CONTAINERS,
    gpu=GPU_TYPE,
    volumes={"/cache": vol}
)
@modal.concurrent(max_inputs=MAX_CONCURRENT_INPUTS)
@modal.web_server(API_PORT, startup_timeout=60)
def ui():
    """ComfyUI 交互式 Web 界面"""
    start_ui_server(API_PORT)


# ============================================
# API 服务
# ============================================

@app.cls(
    scaledown_window=SCALEDOWN_WINDOW,
    gpu=GPU_TYPE,
    volumes={"/cache": vol}
)
@modal.concurrent(max_inputs=5)
class ComfyUI:
    """ComfyUI API 服务类"""
    port: int = API_PORT
    
    @modal.enter()
    def launch_comfy_background(self):
        """容器启动时初始化 ComfyUI 后台服务"""
        start_comfy_background(self.port)
    
    @modal.method()
    def infer(self, workflow_path: str = "/root/workflow_api.json"):
        """执行图像生成推理"""
        from api_service import run_inference
        return run_inference(workflow_path)
    
    @modal.fastapi_endpoint(method="POST")
    def api(self, item: dict):
        """FastAPI 端点 - 处理 HTTP POST 请求"""
        from fastapi import Response
        
        img_bytes = handle_api_request(
            prompt=item["prompt"],
            workflow_template_path=Path(__file__).parent / "workflow_api.json"
        )
        return Response(img_bytes, media_type="image/jpeg")
