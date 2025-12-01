"""
07 - 电商销售报表自动生成
业务场景：每天手动统计销售数据耗时且容易出错

解决的问题：
- 运营每天需要花 2 小时整理昨日销售数据
- 手动计算容易出错，影响决策
- 老板需要每天早上 9 点前看到报表

这个例子展示：
- 定时任务自动执行
- 并行处理订单数据
- 生成汇总报表并存储
"""
import modal
from datetime import datetime, timedelta
import json

app = modal.App("ecommerce-report")

# 创建持久化存储用于保存报表
volume = modal.Volume.from_name("ecommerce-reports", create_if_missing=True)


@app.function()
def process_orders_batch(orders: list[dict]) -> dict:
    """
    处理一批订单数据
    在云端并行执行，每个批次独立计算
    """
    total_amount = sum(order["amount"] for order in orders)
    total_count = len(orders)
    
    # 按商品分类统计
    category_stats = {}
    for order in orders:
        category = order.get("category", "其他")
        if category not in category_stats:
            category_stats[category] = {"count": 0, "amount": 0}
        category_stats[category]["count"] += 1
        category_stats[category]["amount"] += order["amount"]
    
    return {
        "total_amount": total_amount,
        "total_count": total_count,
        "category_stats": category_stats
    }


@app.function()
def merge_batch_results(batch_results: list[dict]) -> dict:
    """
    合并所有批次的统计结果
    """
    merged = {
        "total_amount": 0,
        "total_count": 0,
        "category_stats": {}
    }
    
    for result in batch_results:
        merged["total_amount"] += result["total_amount"]
        merged["total_count"] += result["total_count"]
        
        for category, stats in result["category_stats"].items():
            if category not in merged["category_stats"]:
                merged["category_stats"][category] = {"count": 0, "amount": 0}
            merged["category_stats"][category]["count"] += stats["count"]
            merged["category_stats"][category]["amount"] += stats["amount"]
    
    return merged


@app.function(volumes={"/reports": volume})
def save_report(report: dict, report_date: str):
    """
    保存报表到持久化存储
    """
    report_path = f"/reports/{report_date}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    volume.commit()
    return report_path


@app.function(schedule=modal.Cron("0 8 * * *"))  # 每天早上 8 点执行
def generate_daily_report():
    """
    定时生成每日销售报表
    
    实际场景中，这里会从数据库获取订单数据
    这里用模拟数据演示
    """
    # 模拟从数据库获取昨日订单
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 模拟订单数据（实际中从 MySQL/PostgreSQL 获取）
    mock_orders = [
        {"id": i, "amount": 100 + i * 10, "category": ["电子产品", "服装", "食品", "家居"][i % 4]}
        for i in range(1000)
    ]
    
    # 将订单分成多个批次，并行处理
    batch_size = 100
    batches = [mock_orders[i:i+batch_size] for i in range(0, len(mock_orders), batch_size)]
    
    print(f"📊 开始生成 {yesterday} 的销售报表...")
    print(f"📦 共 {len(mock_orders)} 条订单，分 {len(batches)} 批并行处理")
    
    # 并行处理所有批次
    batch_results = list(process_orders_batch.map(batches))
    
    # 合并结果
    final_report = merge_batch_results.remote(batch_results)
    final_report["report_date"] = yesterday
    final_report["generated_at"] = datetime.now().isoformat()
    
    # 保存报表
    report_path = save_report.remote(final_report, yesterday)
    
    print(f"✅ 报表生成完成！")
    print(f"📈 总销售额: ¥{final_report['total_amount']:,.2f}")
    print(f"📦 总订单数: {final_report['total_count']}")
    print(f"💾 报表已保存: {report_path}")
    
    return final_report


@app.local_entrypoint()
def main():
    """
    手动运行生成报表（用于测试）
    
    使用方法：
    - 测试运行：modal run 07_ecommerce_report.py
    - 部署定时任务：modal deploy 07_ecommerce_report.py
    """
    print("🏪 电商销售报表生成系统")
    print("=" * 50)
    print("💡 此脚本会每天早上 8:00 自动运行")
    print("📌 现在手动执行一次作为测试...\n")
    
    report = generate_daily_report.remote()
    
    print("\n📊 报表详情:")
    for category, stats in report["category_stats"].items():
        print(f"  {category}: {stats['count']} 单, ¥{stats['amount']:,.2f}")

