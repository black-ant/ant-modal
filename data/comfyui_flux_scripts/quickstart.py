"""
ComfyUI 工具箱快速入门脚本
演示所有主要功能的使用方法
"""

import modal
import json
from pathlib import Path


def demo_manage_nodes():
    """演示节点管理功能"""
    print("\n" + "="*60)
    print("1. Custom Nodes 管理演示")
    print("="*60)
    
    # 列出已安装的节点
    app = modal.App.lookup("comfyui-node-manager", create_if_missing=False)
    list_fn = modal.Function.lookup("comfyui-node-manager", "list_nodes")
    
    result = list_fn.remote()
    print(f"\n已安装的节点: {result['count']} 个")
    for node in result['nodes']:
        print(f"  • {node['name']}")
    
    # 演示如何安装新节点
    print("\n要安装新节点，运行:")
    print("  modal run manage_nodes.py \\")
    print("    --action=install \\")
    print("    --repo-url=https://github.com/ltdrdata/ComfyUI-Manager.git")


def demo_batch_inference():
    """演示批量图像生成"""
    print("\n" + "="*60)
    print("2. 批量图像生成演示")
    print("="*60)
    
    # 创建示例提示词文件
    prompts = [
        "A serene mountain landscape at sunset",
        "A futuristic cyberpunk cityscape",
        "A magical forest with glowing mushrooms"
    ]
    
    with open("demo_prompts.txt", "w", encoding="utf-8") as f:
        for prompt in prompts:
            f.write(prompt + "\n")
    
    print(f"\n创建了示例提示词文件: demo_prompts.txt")
    print(f"包含 {len(prompts)} 个提示词\n")
    
    print("要批量生成图像，运行:")
    print("\n  # 串行模式（单容器）")
    print("  modal run batch_inference.py --prompts-file demo_prompts.txt")
    print("\n  # 并行模式（多容器，更快）")
    print("  modal run batch_inference.py --prompts-file demo_prompts.txt --parallel")
    print("\n  # 自定义参数")
    print("  modal run batch_inference.py \\")
    print("    --prompts-file demo_prompts.txt \\")
    print("    --width 1024 --height 1024 --steps 30")


def demo_workflow_manager():
    """演示工作流管理"""
    print("\n" + "="*60)
    print("3. 工作流管理演示")
    print("="*60)
    
    # 创建示例工作流
    sample_workflow = {
        "27": {
            "inputs": {
                "width": 1024,
                "height": 1024,
                "batch_size": 1
            },
            "class_type": "EmptySD3LatentImage"
        },
        "31": {
            "inputs": {
                "steps": 25,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal"
            },
            "class_type": "KSampler"
        }
    }
    
    with open("demo_workflow.json", "w", encoding="utf-8") as f:
        json.dump(sample_workflow, f, indent=2)
    
    print("\n创建了示例工作流文件: demo_workflow.json")
    
    print("\n要管理工作流，运行:")
    print("\n  # 保存工作流到 Volume")
    print("  modal run workflow_manager.py \\")
    print("    --action=save \\")
    print("    --workflow-name=my_workflow \\")
    print("    --workflow-file=demo_workflow.json")
    print("\n  # 列出所有工作流")
    print("  modal run workflow_manager.py --action=list")
    print("\n  # 验证工作流")
    print("  modal run workflow_manager.py \\")
    print("    --action=validate \\")
    print("    --workflow-file=demo_workflow.json")


def demo_utils():
    """演示工具函数"""
    print("\n" + "="*60)
    print("4. 实用工具演示")
    print("="*60)
    
    print("\n图像处理工具:")
    print("\n  # 查看图片信息")
    print("  modal run utils.py --action=info --image-file=image.png")
    print("\n  # 调整大小")
    print("  modal run utils.py \\")
    print("    --action=resize \\")
    print("    --image-file=image.png \\")
    print("    --width=512 --height=512")
    print("\n  # 格式转换")
    print("  modal run utils.py \\")
    print("    --action=convert \\")
    print("    --image-file=image.png \\")
    print("    --output-format=JPEG --quality=90")
    print("\n  # 添加水印")
    print("  modal run utils.py \\")
    print("    --action=watermark \\")
    print("    --image-file=image.png \\")
    print("    --watermark-text='My Image'")


def demo_python_sdk():
    """演示 Python SDK 用法"""
    print("\n" + "="*60)
    print("5. Python SDK 编程示例")
    print("="*60)
    
    sdk_example = '''
# 示例 1: 批量生成图像
import modal

app = modal.App.lookup("comfyui-batch-processor")
generator = app.BatchImageGenerator()

prompts = ["A cat", "A dog", "A bird"]
results = generator.generate_batch.remote(
    prompts,
    width=1024,
    height=1024
)

# 示例 2: 安装节点
install_fn = modal.Function.lookup("comfyui-node-manager", "install_node")
result = install_fn.remote(
    "https://github.com/ltdrdata/ComfyUI-Manager.git"
)

# 示例 3: 图像处理
resize_fn = modal.Function.lookup("comfyui-utils", "resize_image")
with open("image.png", "rb") as f:
    img_bytes = f.read()
resized = resize_fn.remote(img_bytes, width=512, height=512)
'''
    
    # 保存示例代码
    with open("sdk_examples.py", "w", encoding="utf-8") as f:
        f.write(sdk_example)
    
    print("\n已创建 Python SDK 示例文件: sdk_examples.py")
    print("\n可以直接运行该文件来测试 SDK 功能:")
    print("  python sdk_examples.py")


def demo_config():
    """演示配置管理"""
    print("\n" + "="*60)
    print("6. 配置管理")
    print("="*60)
    
    config_example = '''
# 修改 config.py 中的设置

# GPU 配置
GPU_TYPE = "L40S"  # 可选: T4, A10G, A100, L4, L40S, H100
GPU_COUNT = 1      # 多 GPU 并行

# 容器配置
MAX_CONTAINERS = 1              # 最大并发容器数
MAX_CONCURRENT_INPUTS = 10      # 每个容器的并发请求
CONTAINER_IDLE_TIMEOUT = 300    # 空闲超时（秒）

# 内存和超时
MEMORY_SIZE = 16384             # 内存大小（MB）
REQUEST_TIMEOUT = 1200          # 请求超时（秒）

# 使用预设配置
from config import get_preset_config

# 开发环境（便宜）
dev_config = get_preset_config("dev")

# 生产环境（性能）
prod_config = get_preset_config("prod")

# 高性能（顶配）
high_perf = get_preset_config("high_perf")
'''
    
    print("\n配置示例:")
    print(config_example)


def show_deployment_guide():
    """显示部署指南"""
    print("\n" + "="*60)
    print("7. 部署指南")
    print("="*60)
    
    print("\n基本部署流程:")
    print("\n  1️⃣  部署主应用")
    print("     modal deploy app.py")
    print("\n  2️⃣  安装常用节点")
    print("     modal run manage_nodes.py --action=install --repo-url=...")
    print("\n  3️⃣  测试图像生成")
    print("     modal run batch_inference.py --prompt='Test image'")
    print("\n  4️⃣  查看日志和监控")
    print("     modal app logs example-comfyapp")
    print("\n  5️⃣  根据需要扩展功能")


def show_cost_optimization():
    """显示成本优化建议"""
    print("\n" + "="*60)
    print("8. 成本优化建议")
    print("="*60)
    
    print("\n💰 省钱技巧:")
    print("\n  • 开发时使用 T4 GPU（便宜）")
    print("  • 生产环境使用 L40S 或 A10G（性价比高）")
    print("  • 合理设置 CONTAINER_IDLE_TIMEOUT")
    print("  • 批量任务时考虑串行 vs 并行的成本")
    print("  • 使用 Volume 缓存模型，避免重复下载")
    print("  • 监控使用情况: modal app stats example-comfyapp")


def main():
    """主入口"""
    print("\n" + "="*60)
    print("🎨 ComfyUI 工具箱快速入门")
    print("="*60)
    
    print("\n本脚本将演示所有主要功能的使用方法")
    print("创建示例文件并显示相关命令\n")
    
    try:
        # 运行各个演示
        demo_manage_nodes()
        demo_batch_inference()
        demo_workflow_manager()
        demo_utils()
        demo_python_sdk()
        demo_config()
        show_deployment_guide()
        show_cost_optimization()
        
        print("\n" + "="*60)
        print("✅ 快速入门完成！")
        print("="*60)
        
        print("\n📚 生成的示例文件:")
        print("  • demo_prompts.txt - 批量生成提示词示例")
        print("  • demo_workflow.json - 工作流示例")
        print("  • sdk_examples.py - Python SDK 示例")
        
        print("\n📖 更多信息请查看:")
        print("  • README.md - 完整文档")
        print("  • config.py - 配置说明")
        
        print("\n🚀 开始使用:")
        print("  1. 部署主应用: modal deploy app.py")
        print("  2. 查看帮助: modal run <script>.py --help")
        print("  3. 运行示例: 按照上面显示的命令执行")
        
        print("\n💡 提示:")
        print("  • 所有工具都支持 --help 查看详细参数")
        print("  • 可以组合使用多个工具完成复杂任务")
        print("  • Volume 会自动保存所有数据，重启不丢失")
        
        print("\n" + "="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出错: {e}")
        print("请确保已正确安装 Modal 并配置认证")


if __name__ == "__main__":
    main()
