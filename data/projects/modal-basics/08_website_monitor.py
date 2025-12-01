"""
08 - 网站可用性监控告警
业务场景：网站宕机无法及时发现，影响业务和用户体验

解决的问题：
- 网站出问题时运维人员不能第一时间知道
- 手动检查效率低且不可能 24/7 持续
- 需要记录历史可用性数据用于 SLA 报告

这个例子展示：
- 定时任务持续监控
- 并行检查多个站点
- 异常时发送告警通知
- 使用 Dict 存储状态
"""
import modal
import urllib.request
import urllib.error
import time
from datetime import datetime

app = modal.App("website-monitor")

# 使用 Dict 存储监控状态（跨调用持久化）
monitor_state = modal.Dict.from_name("monitor-state", create_if_missing=True)


# 要监控的网站列表（实际使用时替换为你的网站）
WEBSITES = [
    {"name": "公司官网", "url": "https://www.example.com", "timeout": 10},
    {"name": "API 服务", "url": "https://api.example.com/health", "timeout": 5},
    {"name": "管理后台", "url": "https://admin.example.com", "timeout": 10},
    {"name": "用户文档", "url": "https://docs.example.com", "timeout": 10},
]


@app.function()
def check_website(site: dict) -> dict:
    """
    检查单个网站的可用性
    返回检查结果，包含响应时间和状态
    """
    result = {
        "name": site["name"],
        "url": site["url"],
        "timestamp": datetime.now().isoformat(),
        "status": "unknown",
        "response_time": None,
        "error": None
    }
    
    try:
        start_time = time.time()
        
        # 发送 HTTP 请求
        req = urllib.request.Request(
            site["url"],
            headers={"User-Agent": "Modal-Website-Monitor/1.0"}
        )
        response = urllib.request.urlopen(req, timeout=site["timeout"])
        
        response_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
        result["status"] = "up"
        result["response_time"] = round(response_time, 2)
        result["status_code"] = response.status
        
    except urllib.error.HTTPError as e:
        result["status"] = "error"
        result["error"] = f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        result["status"] = "down"
        result["error"] = str(e.reason)
    except Exception as e:
        result["status"] = "down"
        result["error"] = str(e)
    
    return result


@app.function()
def send_alert(site_name: str, status: str, error: str = None):
    """
    发送告警通知
    
    实际场景中可以集成：
    - 企业微信/钉钉/飞书机器人
    - Slack/Discord Webhook
    - 邮件通知
    - 短信告警
    """
    alert_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 这里打印告警信息，实际中替换为 Webhook 调用
    print(f"🚨 告警通知")
    print(f"━━━━━━━━━━━━━━━━━━━━")
    print(f"站点: {site_name}")
    print(f"状态: {status}")
    print(f"时间: {alert_time}")
    if error:
        print(f"错误: {error}")
    print(f"━━━━━━━━━━━━━━━━━━━━")
    
    # 示例：发送到企业微信（取消注释并填入你的 Webhook）
    # webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
    # data = json.dumps({"msgtype": "text", "text": {"content": f"告警: {site_name} {status}"}})
    # req = urllib.request.Request(webhook_url, data=data.encode(), headers={"Content-Type": "application/json"})
    # urllib.request.urlopen(req)


@app.function(schedule=modal.Period(minutes=5))  # 每 5 分钟检查一次
def monitor_all_websites():
    """
    定时监控所有网站
    每 5 分钟运行一次，检查所有站点状态
    """
    print(f"🔍 开始监控检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📋 监控站点数量: {len(WEBSITES)}")
    
    # 并行检查所有网站
    results = list(check_website.map(WEBSITES))
    
    # 统计结果
    up_count = sum(1 for r in results if r["status"] == "up")
    down_count = sum(1 for r in results if r["status"] in ["down", "error"])
    
    print(f"\n📊 检查结果: {up_count} 正常 / {down_count} 异常")
    
    for result in results:
        # 获取上次状态
        state_key = f"status_{result['name']}"
        last_status = monitor_state.get(state_key, "unknown")
        
        # 状态图标
        status_icon = "✅" if result["status"] == "up" else "❌"
        
        # 输出检查结果
        if result["status"] == "up":
            print(f"{status_icon} {result['name']}: {result['response_time']}ms")
        else:
            print(f"{status_icon} {result['name']}: {result['status']} - {result['error']}")
        
        # 状态变化时发送告警
        if last_status == "up" and result["status"] != "up":
            # 网站刚刚宕机，发送告警
            send_alert.remote(result["name"], "宕机", result["error"])
        elif last_status != "up" and last_status != "unknown" and result["status"] == "up":
            # 网站恢复，发送恢复通知
            send_alert.remote(result["name"], "已恢复")
        
        # 更新状态
        monitor_state[state_key] = result["status"]
    
    return results


@app.local_entrypoint()
def main():
    """
    手动运行监控检查（用于测试）
    
    使用方法：
    - 测试运行：modal run 08_website_monitor.py
    - 部署持续监控：modal deploy 08_website_monitor.py
    """
    print("🖥️  网站可用性监控系统")
    print("=" * 50)
    print("💡 部署后会每 5 分钟自动检查所有站点")
    print("📌 现在手动执行一次作为测试...\n")
    
    results = monitor_all_websites.remote()
    
    print("\n💡 提示:")
    print("1. 修改 WEBSITES 列表添加你要监控的网站")
    print("2. 在 send_alert 函数中配置你的通知渠道")
    print("3. 使用 modal deploy 部署后会 24/7 持续监控")

