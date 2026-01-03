"""
05 - 定时任务
学习目标：理解如何在 Modal 中设置定时任务

这个例子展示：
- 如何使用 Schedule 装饰器
- Cron 表达式的使用
- Period 周期性任务
"""
import modal
from datetime import datetime

app = modal.App("scheduled-tasks-demo")


@app.function(schedule=modal.Period(minutes=5))
def every_5_minutes():
    """
    每 5 分钟执行一次
    适合：健康检查、数据同步
    """
    print(f"⏰ 每5分钟任务执行: {datetime.now()}")
    return {"status": "completed", "time": datetime.now().isoformat()}


@app.function(schedule=modal.Cron("0 9 * * *"))
def daily_morning():
    """
    每天早上 9 点执行
    Cron 格式: 分 时 日 月 周
    适合：每日报告、数据备份
    """
    print(f"🌅 每日早晨任务: {datetime.now()}")
    return {"status": "daily_task_completed"}


@app.function(schedule=modal.Cron("0 0 * * 0"))
def weekly_sunday():
    """
    每周日午夜执行
    适合：周报生成、数据清理
    """
    print(f"📅 每周任务: {datetime.now()}")
    return {"status": "weekly_task_completed"}


@app.function()
def manual_task():
    """
    手动触发的任务
    可以通过 API 或命令行调用
    """
    print(f"🔧 手动任务执行: {datetime.now()}")
    return {"status": "manual_task_completed"}


@app.local_entrypoint()
def main():
    """
    定时任务说明
    
    部署方法:
    modal deploy 05_scheduled_tasks.py
    
    部署后，定时任务会自动运行，无需手动触发
    """
    print("⏰ 定时任务演示")
    print("=" * 50)
    print("\n已配置的定时任务:")
    print("1. 每 5 分钟执行一次 - 健康检查")
    print("2. 每天 9:00 执行 - 每日报告")
    print("3. 每周日 0:00 执行 - 周报生成")
    print("\n部署命令: modal deploy 05_scheduled_tasks.py")
    print("\n💡 提示: 部署后任务会自动运行，你可以在 Modal 控制台查看执行日志")
    
    # 手动执行一次
    print("\n🔧 手动执行一次任务...")
    result = manual_task.remote()
    print(f"结果: {result}")
