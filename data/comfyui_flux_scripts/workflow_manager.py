"""
工作流模板管理器
提供工作流的创建、验证、测试和管理功能
"""

import modal
import json
from pathlib import Path
from typing import Optional, Dict, Any
from config import get_volume

# 简单镜像，用于管理工作流文件
workflow_image = modal.Image.debian_slim().pip_install("jsonschema")

vol = get_volume()
app = modal.App("comfyui-workflow-manager", image=workflow_image)


@app.function(volumes={"/cache": vol})
def save_workflow(workflow_name: str, workflow_data: dict) -> dict:
    """
    保存工作流模板到 Volume
    
    Args:
        workflow_name: 工作流名称
        workflow_data: 工作流数据（JSON格式）
    
    Returns:
        dict: 保存结果
    """
    workflows_dir = "/cache/workflows"
    Path(workflows_dir).mkdir(parents=True, exist_ok=True)
    
    workflow_path = f"{workflows_dir}/{workflow_name}.json"
    
    try:
        # 验证工作流格式
        if not isinstance(workflow_data, dict):
            raise ValueError("工作流数据必须是字典类型")
        
        # 保存工作流
        with open(workflow_path, 'w', encoding='utf-8') as f:
            json.dump(workflow_data, f, indent=2, ensure_ascii=False)
        
        # 提交到 Volume
        vol.commit()
        
        return {
            "success": True,
            "message": f"工作流 '{workflow_name}' 已保存",
            "path": workflow_path,
            "nodes_count": len(workflow_data)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.function(volumes={"/cache": vol})
def load_workflow(workflow_name: str) -> dict:
    """
    从 Volume 加载工作流模板
    
    Args:
        workflow_name: 工作流名称
    
    Returns:
        dict: 工作流数据
    """
    workflow_path = f"/cache/workflows/{workflow_name}.json"
    
    try:
        if not Path(workflow_path).exists():
            return {
                "success": False,
                "error": f"工作流 '{workflow_name}' 不存在"
            }
        
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
        
        return {
            "success": True,
            "workflow_name": workflow_name,
            "workflow_data": workflow_data,
            "nodes_count": len(workflow_data)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.function(volumes={"/cache": vol})
def list_workflows() -> dict:
    """列出所有保存的工作流模板"""
    workflows_dir = "/cache/workflows"
    
    if not Path(workflows_dir).exists():
        return {"workflows": [], "count": 0}
    
    workflows = []
    for workflow_file in Path(workflows_dir).glob("*.json"):
        try:
            with open(workflow_file, 'r') as f:
                data = json.load(f)
            
            workflows.append({
                "name": workflow_file.stem,
                "path": str(workflow_file),
                "nodes_count": len(data),
                "size_kb": workflow_file.stat().st_size / 1024
            })
        except Exception as e:
            workflows.append({
                "name": workflow_file.stem,
                "path": str(workflow_file),
                "error": f"读取失败: {str(e)}"
            })
    
    return {
        "workflows": workflows,
        "count": len(workflows)
    }


@app.function(volumes={"/cache": vol})
def delete_workflow(workflow_name: str) -> dict:
    """删除工作流模板"""
    workflow_path = f"/cache/workflows/{workflow_name}.json"
    
    try:
        if not Path(workflow_path).exists():
            return {
                "success": False,
                "error": f"工作流 '{workflow_name}' 不存在"
            }
        
        Path(workflow_path).unlink()
        vol.commit()
        
        return {
            "success": True,
            "message": f"工作流 '{workflow_name}' 已删除"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.function(volumes={"/cache": vol})
def validate_workflow(workflow_data: dict) -> dict:
    """
    验证工作流的有效性
    
    Args:
        workflow_data: 工作流数据
    
    Returns:
        dict: 验证结果
    """
    issues = []
    warnings = []
    
    # 检查基本结构
    if not isinstance(workflow_data, dict):
        issues.append("工作流必须是字典类型")
        return {"valid": False, "issues": issues, "warnings": warnings}
    
    if len(workflow_data) == 0:
        issues.append("工作流为空")
    
    # 检查每个节点
    node_ids = set()
    class_types = {}
    
    for node_id, node_data in workflow_data.items():
        node_ids.add(node_id)
        
        # 检查节点结构
        if not isinstance(node_data, dict):
            issues.append(f"节点 {node_id}: 必须是字典类型")
            continue
        
        # 检查必需字段
        if "class_type" not in node_data:
            issues.append(f"节点 {node_id}: 缺少 class_type")
        else:
            class_type = node_data["class_type"]
            class_types[class_type] = class_types.get(class_type, 0) + 1
        
        if "inputs" not in node_data:
            warnings.append(f"节点 {node_id}: 缺少 inputs")
        
        # 检查输入连接
        if "inputs" in node_data:
            inputs = node_data["inputs"]
            if isinstance(inputs, dict):
                for input_name, input_value in inputs.items():
                    # 检查节点引用
                    if isinstance(input_value, list) and len(input_value) == 2:
                        ref_node = str(input_value[0])
                        if ref_node not in workflow_data:
                            issues.append(
                                f"节点 {node_id}: 引用了不存在的节点 {ref_node}"
                            )
    
    # 检查是否有保存节点
    has_save_node = "SaveImage" in class_types
    if not has_save_node:
        warnings.append("工作流中没有 SaveImage 节点，可能无法输出图片")
    
    # 检查是否有采样器
    has_sampler = "KSampler" in class_types or "KSamplerAdvanced" in class_types
    if not has_sampler:
        warnings.append("工作流中没有采样器节点")
    
    # 统计信息
    stats = {
        "total_nodes": len(workflow_data),
        "node_types": class_types,
        "has_save_node": has_save_node,
        "has_sampler": has_sampler
    }
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "stats": stats
    }


@app.function(volumes={"/cache": vol})
def modify_workflow(
    workflow_name: str,
    modifications: dict
) -> dict:
    """
    修改工作流参数
    
    Args:
        workflow_name: 工作流名称
        modifications: 修改内容，格式: {"node_id.input_name": value}
        
    Example:
        modifications = {
            "27.width": 1024,
            "27.height": 1024,
            "31.steps": 30
        }
    
    Returns:
        dict: 修改结果
    """
    # 加载工作流
    result = load_workflow.local(workflow_name)
    if not result["success"]:
        return result
    
    workflow_data = result["workflow_data"]
    changes_made = []
    
    try:
        for key, value in modifications.items():
            parts = key.split(".")
            if len(parts) != 2:
                continue
            
            node_id, input_name = parts
            
            if node_id not in workflow_data:
                warnings.append(f"节点 {node_id} 不存在")
                continue
            
            if "inputs" not in workflow_data[node_id]:
                workflow_data[node_id]["inputs"] = {}
            
            old_value = workflow_data[node_id]["inputs"].get(input_name)
            workflow_data[node_id]["inputs"][input_name] = value
            
            changes_made.append({
                "node": node_id,
                "input": input_name,
                "old_value": old_value,
                "new_value": value
            })
        
        # 保存修改后的工作流
        modified_name = f"{workflow_name}_modified"
        save_result = save_workflow.local(modified_name, workflow_data)
        
        if save_result["success"]:
            return {
                "success": True,
                "message": f"已创建修改后的工作流: {modified_name}",
                "changes": changes_made,
                "new_workflow": modified_name
            }
        else:
            return save_result
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.local_entrypoint()
def main(
    action: str = "list",
    workflow_name: str = "",
    workflow_file: str = ""
):
    """
    工作流管理命令行入口
    
    使用示例:
    modal run workflow_manager.py --action=list
    modal run workflow_manager.py --action=save --workflow-name=my_workflow --workflow-file=workflow.json
    modal run workflow_manager.py --action=load --workflow-name=my_workflow
    modal run workflow_manager.py --action=validate --workflow-file=workflow.json
    modal run workflow_manager.py --action=delete --workflow-name=my_workflow
    """
    
    if action == "list":
        result = list_workflows.remote()
        print(f"\n{'='*60}")
        print(f"已保存的工作流: {result['count']} 个")
        print(f"{'='*60}\n")
        
        for wf in result['workflows']:
            print(f"📄 {wf['name']}")
            print(f"   节点数: {wf.get('nodes_count', 'N/A')}")
            print(f"   大小: {wf.get('size_kb', 0):.2f} KB")
            if 'error' in wf:
                print(f"   ⚠️  {wf['error']}")
            print()
    
    elif action == "save":
        if not workflow_name or not workflow_file:
            print("❌ 错误: 需要提供 --workflow-name 和 --workflow-file 参数")
            return
        
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            result = save_workflow.remote(workflow_name, workflow_data)
            
            if result['success']:
                print(f"\n✅ {result['message']}")
                print(f"节点数: {result['nodes_count']}")
                print(f"路径: {result['path']}")
            else:
                print(f"\n❌ 保存失败: {result['error']}")
        except Exception as e:
            print(f"\n❌ 读取文件失败: {e}")
    
    elif action == "load":
        if not workflow_name:
            print("❌ 错误: 需要提供 --workflow-name 参数")
            return
        
        result = load_workflow.remote(workflow_name)
        
        if result['success']:
            print(f"\n✅ 工作流 '{workflow_name}' 加载成功")
            print(f"节点数: {result['nodes_count']}")
            
            # 保存到本地文件
            output_file = f"{workflow_name}_loaded.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result['workflow_data'], f, indent=2, ensure_ascii=False)
            print(f"已保存到: {output_file}")
        else:
            print(f"\n❌ 加载失败: {result['error']}")
    
    elif action == "validate":
        if not workflow_file:
            print("❌ 错误: 需要提供 --workflow-file 参数")
            return
        
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            result = validate_workflow.remote(workflow_data)
            
            print(f"\n{'='*60}")
            print(f"工作流验证结果")
            print(f"{'='*60}\n")
            
            if result['valid']:
                print("✅ 工作流有效\n")
            else:
                print("❌ 工作流存在问题\n")
            
            if result['issues']:
                print("🔴 错误:")
                for issue in result['issues']:
                    print(f"  - {issue}")
                print()
            
            if result['warnings']:
                print("⚠️  警告:")
                for warning in result['warnings']:
                    print(f"  - {warning}")
                print()
            
            print("📊 统计信息:")
            stats = result['stats']
            print(f"  总节点数: {stats['total_nodes']}")
            print(f"  节点类型:")
            for node_type, count in stats['node_types'].items():
                print(f"    - {node_type}: {count}")
            
        except Exception as e:
            print(f"\n❌ 验证失败: {e}")
    
    elif action == "delete":
        if not workflow_name:
            print("❌ 错误: 需要提供 --workflow-name 参数")
            return
        
        result = delete_workflow.remote(workflow_name)
        
        if result['success']:
            print(f"\n✅ {result['message']}")
        else:
            print(f"\n❌ 删除失败: {result['error']}")
    
    else:
        print(f"❌ 未知操作: {action}")
        print("支持的操作: list, save, load, validate, delete")
