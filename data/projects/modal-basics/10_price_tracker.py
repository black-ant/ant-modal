"""
10 - 竞品价格监控
业务场景：电商运营需要及时了解竞争对手的价格变化

解决的问题：
- 竞争对手调价后不能及时发现，错失反应时机
- 手动检查数十个商品价格太耗时
- 需要记录历史价格趋势用于分析

这个例子展示：
- 定时任务持续监控
- 并行抓取多个页面
- Volume 存储历史价格数据
- 价格变化时发送通知
"""
import modal
import json
from datetime import datetime
import urllib.request
import urllib.error
import re

app = modal.App("price-tracker")

# 存储历史价格数据
volume = modal.Volume.from_name("price-history", create_if_missing=True)

# 要监控的商品列表（实际使用时替换为真实商品）
# 注意：实际爬虫需要遵守网站的 robots.txt 和使用条款
PRODUCTS_TO_TRACK = [
    {
        "name": "竞品A - 蓝牙耳机",
        "sku": "competitor_a_001",
        "url": "https://example.com/product/001",  # 替换为实际 URL
        "price_selector": "span.price"  # CSS 选择器
    },
    {
        "name": "竞品B - 无线鼠标",
        "sku": "competitor_b_002",
        "url": "https://example.com/product/002",
        "price_selector": "div.product-price"
    },
    {
        "name": "竞品C - 机械键盘",
        "sku": "competitor_c_003",
        "url": "https://example.com/product/003",
        "price_selector": ".price-value"
    },
]


@app.function()
def fetch_product_price(product: dict) -> dict:
    """
    抓取单个商品的价格
    
    注意：这是简化的示例，实际爬虫可能需要：
    - 使用 Selenium/Playwright 处理 JS 渲染
    - 处理反爬虫机制
    - 使用代理 IP
    """
    result = {
        "sku": product["sku"],
        "name": product["name"],
        "url": product["url"],
        "timestamp": datetime.now().isoformat(),
        "price": None,
        "status": "unknown",
        "error": None
    }
    
    try:
        # 发送请求获取页面
        req = urllib.request.Request(
            product["url"],
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        
        # 实际场景中需要解析 HTML 获取价格
        # 这里使用模拟数据演示
        # response = urllib.request.urlopen(req, timeout=10)
        # html = response.read().decode('utf-8')
        # 使用 BeautifulSoup 或正则表达式提取价格
        
        # 模拟获取到的价格（实际中从页面解析）
        import random
        mock_prices = {
            "competitor_a_001": 299.00 + random.randint(-20, 20),
            "competitor_b_002": 159.00 + random.randint(-10, 10),
            "competitor_c_003": 599.00 + random.randint(-50, 50),
        }
        
        result["price"] = mock_prices.get(product["sku"], 99.99)
        result["status"] = "success"
        
    except urllib.error.URLError as e:
        result["status"] = "error"
        result["error"] = f"网络错误: {str(e)}"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result


@app.function(volumes={"/data": volume})
def save_price_record(price_data: dict):
    """
    保存价格记录到历史文件
    """
    sku = price_data["sku"]
    history_file = f"/data/{sku}_history.json"
    
    # 读取现有历史
    try:
        with open(history_file, "r") as f:
            history = json.load(f)
    except FileNotFoundError:
        history = {"sku": sku, "name": price_data["name"], "records": []}
    
    # 添加新记录
    history["records"].append({
        "timestamp": price_data["timestamp"],
        "price": price_data["price"]
    })
    
    # 只保留最近 30 天的记录（每天约 288 条，按每 5 分钟一次）
    max_records = 30 * 288
    if len(history["records"]) > max_records:
        history["records"] = history["records"][-max_records:]
    
    # 保存
    with open(history_file, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    volume.commit()


@app.function(volumes={"/data": volume})
def check_price_change(price_data: dict) -> dict:
    """
    检查价格是否有变化
    返回变化信息
    """
    sku = price_data["sku"]
    history_file = f"/data/{sku}_history.json"
    
    change_info = {
        "sku": sku,
        "name": price_data["name"],
        "current_price": price_data["price"],
        "has_change": False,
        "change_type": None,
        "previous_price": None,
        "change_amount": None,
        "change_percent": None
    }
    
    try:
        with open(history_file, "r") as f:
            history = json.load(f)
        
        if history["records"]:
            # 获取上一条记录的价格
            previous_price = history["records"][-1]["price"]
            
            if previous_price != price_data["price"]:
                change_info["has_change"] = True
                change_info["previous_price"] = previous_price
                change_info["change_amount"] = price_data["price"] - previous_price
                change_info["change_percent"] = round(
                    (price_data["price"] - previous_price) / previous_price * 100, 2
                )
                change_info["change_type"] = "涨价" if change_info["change_amount"] > 0 else "降价"
    except FileNotFoundError:
        pass
    
    return change_info


@app.function()
def send_price_alert(change_info: dict):
    """
    发送价格变动通知
    """
    print(f"\n💰 价格变动通知")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"商品: {change_info['name']}")
    print(f"变动: {change_info['change_type']}")
    print(f"原价: ¥{change_info['previous_price']:.2f}")
    print(f"现价: ¥{change_info['current_price']:.2f}")
    print(f"变化: {change_info['change_amount']:+.2f} ({change_info['change_percent']:+.1f}%)")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # 实际场景中发送到通知渠道
    # 如：企业微信、钉钉、邮件等


@app.function(schedule=modal.Period(hours=1))  # 每小时检查一次
def track_all_prices():
    """
    定时追踪所有商品价格
    """
    print(f"🔍 开始价格监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📋 监控商品数量: {len(PRODUCTS_TO_TRACK)}")
    
    # 并行抓取所有商品价格
    price_results = list(fetch_product_price.map(PRODUCTS_TO_TRACK))
    
    print("\n📊 价格检查结果:")
    
    for price_data in price_results:
        if price_data["status"] == "success":
            # 检查价格变化
            change_info = check_price_change.remote(price_data)
            
            if change_info["has_change"]:
                # 有价格变化，发送通知
                send_price_alert.remote(change_info)
                icon = "📈" if change_info["change_type"] == "涨价" else "📉"
                print(f"{icon} {price_data['name']}: ¥{price_data['price']:.2f} ({change_info['change_type']})")
            else:
                print(f"✅ {price_data['name']}: ¥{price_data['price']:.2f} (无变化)")
            
            # 保存价格记录
            save_price_record.remote(price_data)
        else:
            print(f"❌ {price_data['name']}: 获取失败 - {price_data['error']}")
    
    return price_results


@app.local_entrypoint()
def main():
    """
    手动运行价格检查
    
    使用方法：
    - 测试运行：modal run 10_price_tracker.py
    - 部署定时监控：modal deploy 10_price_tracker.py
    """
    print("💹 竞品价格监控系统")
    print("=" * 50)
    print("💡 部署后会每小时自动检查价格变化")
    print("📌 现在手动执行一次作为测试...\n")
    
    results = track_all_prices.remote()
    
    print("\n💡 提示:")
    print("1. 修改 PRODUCTS_TO_TRACK 添加要监控的商品")
    print("2. 实际使用需要实现页面解析逻辑")
    print("3. 价格历史数据会保存到 Volume 中")
    print("4. 建议遵守目标网站的爬虫政策")

