"""
11 - 日志分析与异常检测
业务场景：服务器产生海量日志，人工排查问题如大海捞针

解决的问题：
- 每天产生 GB 级别的日志文件，无法人工检查
- 服务出问题时需要快速定位错误日志
- 需要统计分析日志中的异常模式

这个例子展示：
- 并行处理大量日志文件
- 使用正则表达式匹配异常模式
- 统计汇总分析结果
- Volume 存储分析报告
"""
import modal
import re
from datetime import datetime
from collections import Counter
import json

app = modal.App("log-analyzer")

# 存储分析报告
volume = modal.Volume.from_name("log-reports", create_if_missing=True)

# 异常模式定义
ERROR_PATTERNS = [
    {"name": "ERROR 级别", "pattern": r"\bERROR\b", "severity": "high"},
    {"name": "异常堆栈", "pattern": r"Exception|Traceback", "severity": "high"},
    {"name": "超时错误", "pattern": r"timeout|timed?\s*out", "severity": "medium"},
    {"name": "连接失败", "pattern": r"connection\s*(refused|reset|failed)", "severity": "medium"},
    {"name": "内存问题", "pattern": r"out\s*of\s*memory|OOM|memory\s*error", "severity": "critical"},
    {"name": "磁盘问题", "pattern": r"disk\s*(full|space)|no\s*space\s*left", "severity": "critical"},
    {"name": "认证失败", "pattern": r"authentication\s*failed|unauthorized|403|401", "severity": "medium"},
    {"name": "数据库错误", "pattern": r"database\s*error|sql\s*error|deadlock", "severity": "high"},
]


@app.function()
def analyze_log_chunk(log_lines: list[str], chunk_id: int) -> dict:
    """
    分析一块日志数据
    在云端并行处理，每个块独立分析
    """
    result = {
        "chunk_id": chunk_id,
        "total_lines": len(log_lines),
        "error_counts": Counter(),
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "error_samples": [],  # 保存一些错误样本
        "hourly_distribution": Counter(),
    }
    
    # 时间戳正则（常见日志格式）
    timestamp_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}\s+\d{2}):\d{2}:\d{2}')
    
    for line in log_lines:
        # 提取小时分布
        ts_match = timestamp_pattern.search(line)
        if ts_match:
            hour = ts_match.group(1)
            result["hourly_distribution"][hour] += 1
        
        # 检查各种错误模式
        for pattern_info in ERROR_PATTERNS:
            if re.search(pattern_info["pattern"], line, re.IGNORECASE):
                result["error_counts"][pattern_info["name"]] += 1
                result["severity_counts"][pattern_info["severity"]] += 1
                
                # 保存前 5 个错误样本
                if len(result["error_samples"]) < 5:
                    result["error_samples"].append({
                        "type": pattern_info["name"],
                        "severity": pattern_info["severity"],
                        "line": line[:200]  # 截断过长的行
                    })
    
    return result


@app.function()
def merge_analysis_results(results: list[dict]) -> dict:
    """
    合并所有块的分析结果
    """
    merged = {
        "total_lines": 0,
        "total_chunks": len(results),
        "error_counts": Counter(),
        "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "error_samples": [],
        "hourly_distribution": Counter(),
    }
    
    for result in results:
        merged["total_lines"] += result["total_lines"]
        
        for error_type, count in result["error_counts"].items():
            merged["error_counts"][error_type] += count
        
        for severity, count in result["severity_counts"].items():
            merged["severity_counts"][severity] += count
        
        merged["error_samples"].extend(result["error_samples"])
        
        for hour, count in result["hourly_distribution"].items():
            merged["hourly_distribution"][hour] += count
    
    # 只保留前 10 个错误样本
    merged["error_samples"] = merged["error_samples"][:10]
    
    # 转换 Counter 为普通 dict 以便 JSON 序列化
    merged["error_counts"] = dict(merged["error_counts"])
    merged["hourly_distribution"] = dict(merged["hourly_distribution"])
    
    return merged


@app.function(volumes={"/reports": volume})
def save_analysis_report(analysis: dict, report_name: str) -> str:
    """
    保存分析报告
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"/reports/{report_name}_{timestamp}.json"
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_lines_analyzed": analysis["total_lines"],
            "total_errors_found": sum(analysis["error_counts"].values()),
            "critical_issues": analysis["severity_counts"]["critical"],
            "high_issues": analysis["severity_counts"]["high"],
        },
        "details": analysis
    }
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    volume.commit()
    return report_path


def generate_mock_logs(num_lines: int = 10000) -> list[str]:
    """
    生成模拟日志数据（用于演示）
    实际场景中，日志会从文件或日志服务读取
    """
    import random
    
    log_templates = [
        "{ts} INFO  [main] Application started successfully",
        "{ts} DEBUG [worker-{n}] Processing request {n}",
        "{ts} INFO  [api] Request completed in {n}ms",
        "{ts} WARN  [db] Query took {n}ms, consider optimization",
        "{ts} ERROR [api] Request failed: Connection timeout",
        "{ts} ERROR [worker-{n}] Exception in thread: NullPointerException",
        "{ts} ERROR [db] Database connection failed: Connection refused",
        "{ts} ERROR [auth] Authentication failed for user_{n}",
        "{ts} CRITICAL [system] Out of memory error detected",
        "{ts} ERROR [api] Traceback (most recent call last):",
    ]
    
    logs = []
    base_time = datetime(2024, 1, 15, 0, 0, 0)
    
    for i in range(num_lines):
        # 生成时间戳
        ts = base_time.replace(
            hour=i % 24,
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        
        # 大部分是正常日志，少部分是错误
        if random.random() < 0.05:  # 5% 错误率
            template = random.choice(log_templates[4:])  # 错误模板
        else:
            template = random.choice(log_templates[:4])  # 正常模板
        
        log_line = template.format(ts=ts_str, n=random.randint(1, 100))
        logs.append(log_line)
    
    return logs


@app.local_entrypoint()
def main():
    """
    运行日志分析
    
    使用方法：
    - 运行分析：modal run 11_log_analyzer.py
    
    实际使用：
    - 从 S3/Volume 读取日志文件
    - 或从日志服务 API 获取日志
    """
    print("📋 日志分析与异常检测系统")
    print("=" * 50)
    
    # 生成模拟日志
    print("📝 生成模拟日志数据...")
    logs = generate_mock_logs(50000)  # 5 万行日志
    print(f"📊 共 {len(logs)} 行日志待分析")
    
    # 分块处理
    chunk_size = 5000
    chunks = [logs[i:i+chunk_size] for i in range(0, len(logs), chunk_size)]
    print(f"📦 分成 {len(chunks)} 块并行处理\n")
    
    # 并行分析所有块
    print("🔍 开始并行分析...")
    chunk_results = list(analyze_log_chunk.starmap(
        [(chunk, i) for i, chunk in enumerate(chunks)]
    ))
    
    # 合并结果
    print("📊 合并分析结果...")
    final_analysis = merge_analysis_results.remote(chunk_results)
    
    # 打印分析结果
    print("\n" + "=" * 50)
    print("📈 分析结果汇总")
    print("=" * 50)
    print(f"总行数: {final_analysis['total_lines']:,}")
    print(f"总错误: {sum(final_analysis['error_counts'].values()):,}")
    print(f"\n🚨 严重程度分布:")
    print(f"  - 严重 (Critical): {final_analysis['severity_counts']['critical']}")
    print(f"  - 高危 (High): {final_analysis['severity_counts']['high']}")
    print(f"  - 中等 (Medium): {final_analysis['severity_counts']['medium']}")
    
    print(f"\n📊 错误类型统计:")
    for error_type, count in sorted(final_analysis['error_counts'].items(), 
                                     key=lambda x: x[1], reverse=True):
        print(f"  - {error_type}: {count}")
    
    if final_analysis['error_samples']:
        print(f"\n📝 错误样本:")
        for i, sample in enumerate(final_analysis['error_samples'][:3], 1):
            print(f"  {i}. [{sample['severity']}] {sample['type']}")
            print(f"     {sample['line'][:80]}...")
    
    # 保存报告
    report_path = save_analysis_report.remote(final_analysis, "daily_log_analysis")
    print(f"\n💾 报告已保存: {report_path}")
    
    print("\n💡 提示:")
    print("1. 修改 ERROR_PATTERNS 添加自定义错误模式")
    print("2. 实际使用时从日志文件或日志服务读取数据")
    print("3. 可以配合定时任务实现每日自动分析")

