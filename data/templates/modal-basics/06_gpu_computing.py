"""
06 - GPU 计算
学习目标：理解如何在 Modal 中使用 GPU

这个例子展示：
- 如何请求 GPU 资源
- 如何使用 PyTorch 进行 GPU 计算
- GPU 和 CPU 的性能对比
"""
import modal

app = modal.App("gpu-computing-demo")

# 构建包含 PyTorch 的镜像
image = modal.Image.debian_slim().pip_install("torch", "numpy")


@app.function(image=image, gpu="T4")
def gpu_matrix_multiply(size: int = 1000):
    """
    使用 GPU 进行矩阵乘法
    T4 是入门级 GPU，适合学习和小规模计算
    """
    import torch
    import time
    
    print(f"🎮 使用 GPU 计算 {size}x{size} 矩阵乘法...")
    
    # 检查 GPU 是否可用
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"设备: {device}")
    
    if device == "cuda":
        print(f"GPU 型号: {torch.cuda.get_device_name(0)}")
    
    # 创建随机矩阵
    a = torch.randn(size, size, device=device)
    b = torch.randn(size, size, device=device)
    
    # 计时
    start = time.time()
    c = torch.matmul(a, b)
    torch.cuda.synchronize() if device == "cuda" else None
    elapsed = time.time() - start
    
    return {
        "device": device,
        "size": size,
        "time": f"{elapsed:.4f} 秒",
        "performance": f"{(size**3 * 2) / elapsed / 1e9:.2f} GFLOPS"
    }


@app.function(image=image)
def cpu_matrix_multiply(size: int = 1000):
    """
    使用 CPU 进行相同的计算（对比）
    """
    import torch
    import time
    
    print(f"💻 使用 CPU 计算 {size}x{size} 矩阵乘法...")
    
    a = torch.randn(size, size)
    b = torch.randn(size, size)
    
    start = time.time()
    c = torch.matmul(a, b)
    elapsed = time.time() - start
    
    return {
        "device": "cpu",
        "size": size,
        "time": f"{elapsed:.4f} 秒",
        "performance": f"{(size**3 * 2) / elapsed / 1e9:.2f} GFLOPS"
    }


@app.local_entrypoint()
def main():
    """
    对比 GPU 和 CPU 的性能
    """
    print("🎮 GPU vs CPU 性能对比")
    print("=" * 50)
    
    size = 2000
    
    print(f"\n测试: {size}x{size} 矩阵乘法\n")
    
    # GPU 计算
    print("1️⃣ GPU 计算:")
    gpu_result = gpu_matrix_multiply.remote(size)
    print(f"   设备: {gpu_result['device']}")
    print(f"   耗时: {gpu_result['time']}")
    print(f"   性能: {gpu_result['performance']}")
    
    # CPU 计算
    print("\n2️⃣ CPU 计算:")
    cpu_result = cpu_matrix_multiply.remote(size)
    print(f"   设备: {cpu_result['device']}")
    print(f"   耗时: {cpu_result['time']}")
    print(f"   性能: {cpu_result['performance']}")
    
    print("\n💡 提示:")
    print("- T4: 入门级 GPU，适合学习和开发")
    print("- A10G: 中端 GPU，适合生产环境")
    print("- A100: 高端 GPU，适合大规模训练")
    print("- H100: 最新最强 GPU，适合前沿研究")
