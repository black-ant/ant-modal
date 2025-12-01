"""
Modal 定时任务调度器
使用 Modal 的 Schedule 功能执行定时任务
"""
import modal
from datetime import datetime

app = modal.App("cron-scheduler")

image = modal.Image.debian_slim().pip_install("requests")


# 每小时执行一次
@app.function(
    image=image,
    schedule=modal.Period(hours=1)
)
def hourly_task():
    """每小时执行的任务"""
    print(f"⏰ 每小时任务执行: {datetime.now()}")
    # 在这里添加你的任务逻辑
    return {"status": "completed", "time": datetime.now().isoformat()}


# 每天凌晨2点执行
@app.function(
    image=image,
    schedule=modal.Cron("0 2 * * *")
)
def daily_backup():
    """每天凌晨2点执行数据备份"""
    print(f"💾 执行每日备份: {datetime.now()}")
    # 备份逻辑
    return {"status": "backup_completed"}


# 每周一上午9点执行
@app.function(
    image=image,
    schedule=modal.Cron("0 9 * * 1")
)
def weekly_report():
    """每周一生成周报"""
    print(f"📊 生成周报: {datetime.now()}")
    # 生成报告逻辑
    return {"status": "report_generated"}


# 每5分钟执行一次
@app.function(
    image=image,
    schedule=modal.Period(minutes=5)
)
def health_check():
    """健康检查任务"""
    print(f"🏥 健康检查: {datetime.now()}")
    # 检查服务状态
    return {"status": "healthy"}


# 每月1号执行
@app.function(
    image=image,
    schedule=modal.Cron("0 0 1 * *")
)
def monthly_cleanup():
    """每月清理任务"""
    print(f"🧹 执行月度清理: {datetime.now()}")
    # 清理旧数据
    return {"status": "cleanup_completed"}


@app.function(image=image)
def run_task_now(task_name: str):
    """手动触发任务"""
    tasks = {
        "hourly": hourly_task,
        "daily": daily_backup,
        "weekly": weekly_report,
        "health": health_check,
        "monthly": monthly_cleanup
    }
    
    if task_name in tasks:
        result = tasks[task_name].remote()
        return {"task": task_name, "result": result}
    else:
        return {"error": f"Unknown task: {task_name}"}


@app.local_entrypoint()
def main(task: str = ""):
    """
    本地入口
    
    使用方法:
    modal deploy scheduler.py  # 部署定时任务
    modal run scheduler.py --task=hourly  # 手动运行任务
    """
    if task:
        result = run_task_now.remote(task)
        print(result)
    else:
        print("定时任务已部署")
        print("可用任务: hourly, daily, weekly, health, monthly")
