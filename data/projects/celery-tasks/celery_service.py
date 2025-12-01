"""
Celery 分布式任务队列
配合 Redis 后端实现分布式任务处理

适用场景：
- 后台异步任务
- 定时任务调度
- 分布式计算
"""
import modal

app = modal.App("celery-tasks")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "celery[redis]",
        "redis",
    )
)


# 使用 Modal 原生方式实现类似 Celery 的功能
@app.function(image=image, timeout=3600)
def process_task(task_type: str, payload: dict) -> dict:
    """
    通用任务处理器
    
    Args:
        task_type: 任务类型
        payload: 任务数据
    """
    import time
    
    print(f"🔄 处理任务: {task_type}")
    
    if task_type == "send_email":
        # 模拟发送邮件
        time.sleep(1)
        return {
            "status": "success",
            "task": task_type,
            "to": payload.get("to"),
            "subject": payload.get("subject")
        }
    
    elif task_type == "generate_report":
        # 模拟生成报表
        time.sleep(3)
        return {
            "status": "success",
            "task": task_type,
            "report_id": f"report_{int(time.time())}"
        }
    
    elif task_type == "process_image":
        # 模拟图像处理
        time.sleep(2)
        return {
            "status": "success",
            "task": task_type,
            "processed": True
        }
    
    else:
        return {
            "status": "error",
            "message": f"Unknown task type: {task_type}"
        }


@app.function(image=image, timeout=7200)
def batch_process_tasks(tasks: list[dict]) -> list[dict]:
    """
    批量处理任务（并行）
    
    Args:
        tasks: 任务列表 [{"type": "...", "payload": {...}}, ...]
    """
    results = list(process_task.starmap([
        (task["type"], task.get("payload", {}))
        for task in tasks
    ]))
    
    return results


@app.function(image=image)
def schedule_task(
    task_type: str,
    payload: dict,
    delay_seconds: int = 0
) -> dict:
    """
    调度任务（支持延迟执行）
    """
    import time
    
    if delay_seconds > 0:
        print(f"⏰ 任务将在 {delay_seconds} 秒后执行")
        time.sleep(delay_seconds)
    
    result = process_task.remote(task_type, payload)
    return result


@app.function(image=image)
@modal.web_endpoint(method="POST")
def task_api(data: dict):
    """
    任务队列 API
    
    POST /task_api
    {
        "action": "submit",  // submit, batch, schedule
        "task_type": "send_email",
        "payload": {"to": "user@example.com", "subject": "Hello"},
        "delay": 0  // for schedule
    }
    """
    action = data.get("action", "submit")
    
    try:
        if action == "submit":
            result = process_task.spawn(
                data.get("task_type", ""),
                data.get("payload", {})
            )
            return {
                "status": "submitted",
                "task_id": str(result.object_id)
            }
        
        elif action == "batch":
            results = batch_process_tasks.remote(data.get("tasks", []))
            return {"status": "success", "results": results}
        
        elif action == "schedule":
            result = schedule_task.remote(
                data.get("task_type", ""),
                data.get("payload", {}),
                data.get("delay", 0)
            )
            return {"status": "success", "result": result}
        
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.local_entrypoint()
def main():
    """演示任务队列"""
    print("⚙️ Celery 风格任务队列")
    print("=" * 50)
    
    # 提交单个任务
    print("\n1. 提交单个任务:")
    result = process_task.remote("send_email", {
        "to": "test@example.com",
        "subject": "Test Email"
    })
    print(f"   结果: {result}")
    
    # 批量并行处理
    print("\n2. 批量并行处理:")
    tasks = [
        {"type": "send_email", "payload": {"to": f"user{i}@example.com"}}
        for i in range(5)
    ]
    results = batch_process_tasks.remote(tasks)
    print(f"   处理了 {len(results)} 个任务")
    
    print("\n💡 提示:")
    print("   - 使用 spawn 提交异步任务")
    print("   - 使用 starmap 并行处理")
    print("   - Modal 原生支持分布式任务")

