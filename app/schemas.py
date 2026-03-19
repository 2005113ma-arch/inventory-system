# pydantic.py (建议重命名为 schemas.py)
from enum import Enum
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

class ChangeType(int, Enum):
    """库存变动类型枚举 (对应数据库 TINYINT)"""
    INCREASE = 1      # 入库
    DECREASE = 2      # 出库
    LOCK = 3          # 锁定
    UNLOCK = 4        # 解锁

# ==================== 请求模型 ====================

class InventoryUpdateRequest(BaseModel):
    """库存更新请求"""
    # 允许通过别名(驼峰)传参，但代码里用下划线变量名接
    model_config = ConfigDict(populate_by_name=True)
    
    sku_id: int = Field(..., alias="skuId", description="商品 SKU 编号")
    warehouse_id: int = Field(..., alias="warehouseId", description="仓库编号")
    quantity: int = Field(..., description="变动数量（必须为正整数）", ge=1)
    reason: Optional[str] = Field(None, description="变动原因")

class InventoryLockRequest(BaseModel):
    """库存锁定请求"""
    model_config = ConfigDict(populate_by_name=True)
    
    sku_id: int = Field(..., alias="skuId")
    warehouse_id: int = Field(..., alias="warehouseId")
    quantity: int = Field(..., ge=1)
    order_id: str = Field(..., alias="orderId")

class InventoryUnlockRequest(BaseModel):
    """库存解锁请求"""
    model_config = ConfigDict(populate_by_name=True)
    
    order_id: str = Field(..., alias="orderId")
    sku_id: int = Field(..., alias="skuId")
    warehouse_id: int = Field(..., alias="warehouseId")
    quantity: int = Field(..., ge=1)

class BatchInventoryUpdateRequest(BaseModel):
    """批量库存更新请求"""
    items: List[InventoryUpdateRequest] = Field(..., min_length=1)

# ==================== 响应模型 ====================

class InventoryResponse(BaseModel):
    """库存查询响应"""
    # 开启 ORM 模式，允许直接读取 SQLAlchemy 对象
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    sku_id: int = Field(..., alias="skuId")
    warehouse_id: int = Field(..., alias="warehouseId")
    total_quantity: int = Field(..., alias="totalStock")
    locked_quantity: int = Field(..., alias="lockedStock")
    available_quantity: int = Field(..., alias="availableStock")

class InventoryLog(BaseModel):
    """库存流水记录响应"""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    transaction_id: int = Field(..., alias="id")
    sku_id: int = Field(..., alias="skuId")
    change_type: int = Field(..., alias="changeType")
    change_quantity: int = Field(..., alias="quantity")
    created_at: datetime = Field(..., alias="createTime")

class InventoryLogsResponse(BaseModel):
    """库存流水查询响应列表"""
    list: List[InventoryLog]
    total: int

class ErrorResponse(BaseModel):
    """错误响应"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None