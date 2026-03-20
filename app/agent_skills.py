import json
from sqlalchemy.orm import Session
from sqlalchemy import func
# 导入你现有的模型 (注意这里的相对路径，确保 app.models 能正确引入)
from app.models import Sku, Inventory, InventoryTransaction 
from app.api.inventory import increase_inventory
from app.schemas import InventoryUpdateRequest
import random

def get_real_inventory(db: Session, sku_code: str):
    """
    【真实 Skill】通过 sku_code 联合查询 Sku 和 Inventory 表获取可用库存
    """
    print(f"[Agent Skill] 正在去 MySQL 查询真实库存 -> SKU: {sku_code}")
    
    # 1. 先查 SKU 表找到 sku_id
    sku = db.query(Sku).filter(Sku.sku_code == sku_code).first()
    if not sku:
        return json.dumps({"error": f"数据库中未找到编码为 {sku_code} 的商品"})

    # 2. 查 Inventory 表汇总该 SKU 的总可用库存
    # (考虑到一个商品可能在多个 warehouse_id 里有库存，这里做一个 SUM 聚合)
    total_available = db.query(func.sum(Inventory.available_quantity))\
                        .filter(Inventory.sku_id == sku.sku_id).scalar() or 0
   
    total_available = int(total_available)
    # 注意：你的模型目前没有 safe_stock（安全库存线）这个字段
    # 为了 Agent 的业务逻辑能跑通，我们这里暂时模拟一个安全库存为 20。
    # 实际开发中，你可以在 Sku 表里加上 safe_stock 字段。
    simulated_safe_stock = 20 

    # 返回真实数据给大模型
    return json.dumps({
        "sku_code": sku.sku_code,
        "sku_name": sku.sku_name,
        "available_stock": total_available, # 返回真实的可用库存
        "safe_stock": simulated_safe_stock
    })

def create_real_replenishment(db: Session, sku_code: str, quantity: int, reason: str):
    """
    【终极完全体 Skill】Agent 直接调用重构项目中的核心入库逻辑！
    """
    print(f"[Agent Skill] 正在联动重构核心接口生成补单 -> SKU:{sku_code}, 数量:{quantity}")
    
    sku = db.query(Sku).filter(Sku.sku_code == sku_code).first()
    if not sku:
        return json.dumps({"error": "找不到该SKU，无法生成补单"})

    try:
        # 1. 严格按照你重构接口的要求，组装 Pydantic 请求体
        req_data = InventoryUpdateRequest(
            sku_id=sku.sku_id,
            warehouse_id=1,  # 默认入库到 1 号仓
            quantity=quantity,
            reason=f"AI自动触发补货: {reason}"
        )
        
        # 2. 核心大招：直接调用你 inventory.py 里的 increase_inventory！
        # 这样它就会走你写的全套逻辑：查库存 -> 累加可用库存 -> 记真实流水 -> 提交事务
        result = increase_inventory(request=req_data, db=db)
        
        return json.dumps({
            "status": "success", 
            "message": f"联动重构接口成功！{result['message']}"
        })
    except Exception as e:
        return json.dumps({"error": f"调用库存中台接口失败: {str(e)}"})