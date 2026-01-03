"""
01 - Hello Modal
学习目标：理解 Modal 的基本概念和最简单的函数调用

这个例子展示：
- 如何创建 Modal 应用
- 如何定义远程函数
- 如何在本地调用云端函数
"""
import modal

# 创建 Modal 应用
app = modal.App("hello-modal")


@app.function()
def say_hello(name: str = "World") -> str:
    """
    一个简单的问候函数
    这个函数会在 Modal 的云端容器中运行
    """
    return f"Hello, {name}! 这条消息来自 Modal 云端 ☁️"


@app.local_entrypoint()
def main():
    """
    本地入口点
    这部分代码在你的本地机器上运行
    """
    print("🚀 开始调用 Modal 云端函数...")
    
    # 调用云端函数
    result = say_hello.remote("Modal 新手")
    
    print(f"📨 收到回复: {result}")
    print("\n✅ 成功！你已经完成了第一个 Modal 程序")
    print("💡 提示: 这个函数实际上是在云端运行的，不占用你的本地资源")
