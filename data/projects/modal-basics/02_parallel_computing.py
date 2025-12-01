"""
02 - 并行计算
学习目标：理解 Modal 的并行处理能力

这个例子展示：
- 如何并行执行多个任务
- map() 方法的使用
- 云端计算的性能优势
"""
import modal
import time

app = modal.App("parallel-computing")


@app.function()
def process_number(n: int) -> dict:
    """
    处理单个数字（模拟耗时任务）
    在云端并行执行
    """
    # 模拟计算密集型任务
    time.sleep(2)
    result = n ** 2
    return {
        "input": n,
        "output": result,
        "message": f"计算 {n}² = {result}"
    }


@app.local_entrypoint()
def main():
    """
    并行处理多个数字
    """
    numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    print(f"🔢 准备处理 {len(numbers)} 个数字...")
    print("⏱️  如果串行执行需要 20 秒，但并行只需要 2 秒！\n")
    
    start_time = time.time()
    
    # 使用 map 并行处理
    results = list(process_number.map(numbers))
    
    elapsed = time.time() - start_time
    
    print("📊 处理结果:")
    for result in results:
        print(f"  {result['message']}")
    
    print(f"\n⚡ 总耗时: {elapsed:.2f} 秒")
    print("💡 提示: Modal 自动在多个容器中并行执行，大大提升效率")
