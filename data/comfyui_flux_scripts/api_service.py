"""
API 服务模块
提供图像生成的 RESTful API 接口
"""

import json
import subprocess
import uuid
import socket
import urllib.request
import urllib.error
from pathlib import Path
import modal
import modal.experimental


def link_custom_nodes():
    """链接持久化的自定义节点"""
    print("🔗 链接持久化的自定义节点...")
    cache_custom_nodes = Path("/cache/custom_nodes")
    comfy_custom_nodes = Path("/root/comfy/ComfyUI/custom_nodes")
    
    if cache_custom_nodes.exists():
        for node_dir in cache_custom_nodes.iterdir():
            if node_dir.is_dir():
                link_path = comfy_custom_nodes / node_dir.name
                if not link_path.exists() and not link_path.is_symlink():
                    subprocess.run(
                        f"ln -s {node_dir} {link_path}",
                        shell=True,
                        check=False
                    )
                    print(f"   ✅ 已链接: {node_dir.name}")


def start_comfy_background(port=8000):
    """启动 ComfyUI 后台服务"""
    print(f"🚀 启动ComfyUI后台服务，端口: {port}")
    
    # 链接自定义节点
    link_custom_nodes()
    
    # 启动后台服务
    cmd = f"comfy launch --background -- --port {port}"
    subprocess.run(cmd, shell=True, check=True)


def poll_server_health(port=8000):
    """健康检查 - 确保 ComfyUI 服务正常运行"""
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/system_stats")
        urllib.request.urlopen(req, timeout=5)
        print("✅ ComfyUI服务健康检查通过")
        return True
    except (socket.timeout, urllib.error.URLError) as e:
        print("❌ ComfyUI服务健康检查失败")
        modal.experimental.stop_fetching_inputs()
        raise Exception("ComfyUI server is not healthy, stopping container")


def run_inference(workflow_path="/root/workflow_api.json"):
    """执行图像生成推理"""
    print("🎨 开始执行图像生成推理...")
    
    # 检查服务健康状态
    poll_server_health()
    
    # 执行工作流
    cmd = f"comfy run --workflow {workflow_path} --wait --timeout 1200 --verbose"
    subprocess.run(cmd, shell=True, check=True)
    
    # 获取生成的图像文件
    output_dir = "/root/comfy/ComfyUI/output"
    workflow = json.loads(Path(workflow_path).read_text())
    file_prefix = [
        node.get("inputs")
        for node in workflow.values()
        if node.get("class_type") == "SaveImage"
    ][0]["filename_prefix"]
    
    # 返回图像字节数据
    for f in Path(output_dir).iterdir():
        if f.name.startswith(file_prefix):
            return f.read_bytes()


def handle_api_request(prompt, workflow_template_path):
    """处理 API 请求"""
    print("📡 处理API请求...")
    
    # 加载工作流模板
    workflow_data = json.loads(Path(workflow_template_path).read_text())
    
    # 设置用户提示词
    workflow_data["6"]["inputs"]["text"] = prompt
    
    # 生成唯一的客户端ID和文件名
    client_id = uuid.uuid4().hex
    workflow_data["9"]["inputs"]["filename_prefix"] = client_id
    
    # 保存自定义工作流文件
    new_workflow_file = f"{client_id}.json"
    json.dump(workflow_data, Path(new_workflow_file).open("w"))
    
    # 执行推理并返回图像
    img_bytes = run_inference(new_workflow_file)
    return img_bytes
