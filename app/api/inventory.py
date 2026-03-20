from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import get_db
from app.models import Inventory, InventoryLock, InventoryTransaction
from app.schemas import (
    InventoryLockRequest, 
    InventoryUpdateRequest, 
    InventoryUnlockRequest, 
    InventoryResponse, 
    InventoryLogsResponse, 
    ChangeType
)

router = APIRouter(prefix="/inventory", tags=["库存管理"])

# 定义最大重试次数，应对高并发冲突
MAX_RETRIES = 3

@router.post("/lock")
def lock_inventory(request: InventoryLockRequest, db: Session = Depends(get_db)):
    """
    锁定库存接口：使用乐观锁防止超卖，带有重试机制
    """
    for attempt in range(MAX_RETRIES):
        # 1. 查询当前库存状态
        inventory = db.query(Inventory).filter(
            Inventory.sku_id == request.sku_id,
            Inventory.warehouse_id == request.warehouse_id
        ).first()

        # 校验商品和仓库是否存在
        if not inventory:
            raise HTTPException(status_code=404, detail="未找到该商品或仓库的库存记录")

        # 校验可用库存是否充足
        if inventory.available_quantity < request.quantity:
            raise HTTPException(status_code=400, detail="可用库存不足")

        # 2. 核心：带版本号的乐观锁更新
        # 这里的 filter 加上了 version == inventory.version，确保在此期间没有其他人修改过
        updated_rows = db.query(Inventory).filter(
            Inventory.inventory_id == inventory.inventory_id,
            Inventory.version == inventory.version
        ).update({
            Inventory.available_quantity: Inventory.available_quantity - request.quantity,
            Inventory.locked_quantity: Inventory.locked_quantity + request.quantity,
            Inventory.version: Inventory.version + 1
        }, synchronize_session=False)

        # 3. 检查更新结果
        if updated_rows == 0:
            # 说明有其他并发请求刚刚修改了这条记录，版本号变了，更新失败
            if attempt < MAX_RETRIES - 1:
                continue  # 触发重试，重新去查最新的版本号
            else:
                # 重试次数用完，告诉前端系统繁忙
                raise HTTPException(status_code=409, detail="系统繁忙，请稍后再试")

        # 4. 如果更新成功，记录锁定表和流水表
        try:
            # 记录库存锁定表 (假设默认锁定 30 分钟)
            expire_time = datetime.now() + timedelta(minutes=30)
            lock_record = InventoryLock(
                order_id=request.order_id,
                sku_id=request.sku_id,
                warehouse_id=request.warehouse_id,
                lock_quantity=request.quantity,
                lock_status=1, # 1-锁定中
                expire_time=expire_time
            )
            db.add(lock_record)

            # 记录流水表
            transaction_record = InventoryTransaction(
                sku_id=request.sku_id,
                warehouse_id=request.warehouse_id,
                change_type=ChangeType.LOCK.value,
                change_quantity=request.quantity,
                before_quantity=inventory.available_quantity,
                after_quantity=inventory.available_quantity - request.quantity,
                business_type="ORDER_LOCK",
                business_id=request.order_id,
                operator="system"
            )
            db.add(transaction_record)

            # 统一提交事务
            db.commit()
            
            return {
                "code": "SUCCESS",
                "message": "库存锁定成功",
                "data": {"orderId": request.order_id, "lockedQuantity": request.quantity}
            }
            
        except Exception as e:
            # 如果写记录失败，回滚刚才的库存更新
            db.rollback()
            raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")

    raise HTTPException(status_code=409, detail="系统繁忙，请稍后再试")

@router.get("/query", response_model=InventoryResponse)
def query_inventory(skuId: int, warehouseId: int, db: Session = Depends(get_db)):
    """
    1. 库存查询接口：根据 SKU ID 和 仓库 ID 查询实时库存量
    """
    inventory = db.query(Inventory).filter(
        Inventory.sku_id == skuId,
        Inventory.warehouse_id == warehouseId
    ).first()

    if not inventory:
        raise HTTPException(status_code=404, detail="未找到该商品或仓库的库存记录")

    # FastAPI 会自动把查出来的 ORM 对象，根据我们之前写的 ConfigDict(from_attributes=True) 转换成 JSON
    return inventory


@router.post("/increase")
def increase_inventory(request: InventoryUpdateRequest, db: Session = Depends(get_db)):
    """
    2. 库存增加接口：用于采购入库，批量增加库存
    """
    # 查找当前库存记录
    inventory = db.query(Inventory).filter(
        Inventory.sku_id == request.sku_id,
        Inventory.warehouse_id == request.warehouse_id
    ).first()

    before_qty = 0
    if inventory:
        # 如果库里有这个商品，直接累加
        before_qty = inventory.available_quantity
        inventory.total_quantity += request.quantity
        inventory.available_quantity += request.quantity
    else:
        # 如果是个全新的商品第一次入库，创建新记录
        inventory = Inventory(
            sku_id=request.sku_id,
            warehouse_id=request.warehouse_id,
            total_quantity=request.quantity,
            available_quantity=request.quantity,
            locked_quantity=0,
            version=0
        )
        db.add(inventory)
        db.flush()  # 刷新到数据库以获取状态，但不提交事务

    # 记录库存流水表
    transaction_record = InventoryTransaction(
        sku_id=request.sku_id,
        warehouse_id=request.warehouse_id,
        change_type=ChangeType.INCREASE.value,
        change_quantity=request.quantity,
        before_quantity=before_qty,
        after_quantity=before_qty + request.quantity,
        business_type="PROCUREMENT_IN",
        business_id=request.reason or "SYSTEM_ADD",
        operator="admin"
    )
    db.add(transaction_record)

    try:
        db.commit()
        return {"code": "SUCCESS", "message": f"成功入库 {request.quantity} 件"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"入库失败: {str(e)}")
    
@router.post("/unlock")
def unlock_inventory(request: InventoryUnlockRequest, db: Session = Depends(get_db)):
    """
    3. 库存解锁接口：订单取消或超时后，释放被锁定的库存
    """
    # 查找之前的锁定记录
    lock_record = db.query(InventoryLock).filter(
        InventoryLock.order_id == request.order_id,
        InventoryLock.sku_id == request.sku_id,
        InventoryLock.warehouse_id == request.warehouse_id,
        InventoryLock.lock_status == 1 # 1-锁定中
    ).first()

    if not lock_record:
        raise HTTPException(status_code=404, detail="未找到该订单的有效锁定记录")

    # 查出当前库存
    inventory = db.query(Inventory).filter(
        Inventory.sku_id == request.sku_id,
        Inventory.warehouse_id == request.warehouse_id
    ).first()

    # 乐观锁释放库存（把锁定的加回可用里）
    updated_rows = db.query(Inventory).filter(
        Inventory.inventory_id == inventory.inventory_id,
        Inventory.version == inventory.version
    ).update({
        Inventory.available_quantity: Inventory.available_quantity + request.quantity,
        Inventory.locked_quantity: Inventory.locked_quantity - request.quantity,
        Inventory.version: Inventory.version + 1
    }, synchronize_session=False)

    if updated_rows == 0:
        raise HTTPException(status_code=409, detail="系统繁忙，解锁冲突，请重试")

    # 更新锁定记录的状态为 3-已释放
    lock_record.lock_status = 3
    lock_record.updated_at = datetime.now()

    # 记录流水
    tx = InventoryTransaction(
        sku_id=request.sku_id,
        warehouse_id=request.warehouse_id,
        change_type=ChangeType.UNLOCK.value,
        change_quantity=request.quantity,
        before_quantity=inventory.available_quantity,
        after_quantity=inventory.available_quantity + request.quantity,
        business_type="ORDER_CANCEL",
        business_id=request.order_id,
        operator="system"
    )
    db.add(tx)
    
    db.commit()
    return {"code": "SUCCESS", "message": "库存解锁成功"}


@router.post("/decrease")
def decrease_inventory(request: InventoryUpdateRequest, db: Session = Depends(get_db)):
    """
    4. 库存扣减接口：用于非下单场景的直接扣减，或发货时的真实扣减
    """
    for attempt in range(MAX_RETRIES):
        inventory = db.query(Inventory).filter(
            Inventory.sku_id == request.sku_id,
            Inventory.warehouse_id == request.warehouse_id
        ).first()

        if not inventory or inventory.available_quantity < request.quantity:
            raise HTTPException(status_code=400, detail="可用库存不足，无法扣减")

        # 真实扣减：总库存和可用库存同时减少
        updated_rows = db.query(Inventory).filter(
            Inventory.inventory_id == inventory.inventory_id,
            Inventory.version == inventory.version
        ).update({
            Inventory.total_quantity: Inventory.total_quantity - request.quantity,
            Inventory.available_quantity: Inventory.available_quantity - request.quantity,
            Inventory.version: Inventory.version + 1
        }, synchronize_session=False)

        if updated_rows == 0:
            if attempt < MAX_RETRIES - 1:
                continue
            raise HTTPException(status_code=409, detail="系统繁忙，请重试")

        # 记录流水
        tx = InventoryTransaction(
            sku_id=request.sku_id,
            warehouse_id=request.warehouse_id,
            change_type=ChangeType.DECREASE.value,
            change_quantity=request.quantity,
            before_quantity=inventory.available_quantity,
            after_quantity=inventory.available_quantity - request.quantity,
            business_type="DIRECT_DECREASE",
            business_id=request.reason or "SYSTEM_DEC",
            operator="admin"
        )
        db.add(tx)
        db.commit()
        return {"code": "SUCCESS", "message": "库存直接扣减成功"}
    
    raise HTTPException(status_code=409, detail="系统繁忙，请重试")


@router.get("/logs", response_model=InventoryLogsResponse)
def query_inventory_logs(
    skuId: int, 
    warehouseId: int, 
    page: int = Query(1, ge=1, description="页码"), 
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    5. 库存流水查询：记录所有库存变动流水，便于对账
    """
    # 按时间倒序查询流水
    query = db.query(InventoryTransaction).filter(
        InventoryTransaction.sku_id == skuId,
        InventoryTransaction.warehouse_id == warehouseId
    ).order_by(InventoryTransaction.created_at.desc())

    total = query.count()
    # 实现简单分页
    logs = query.offset((page - 1) * size).limit(size).all()

    return {
        "list": logs,
        "total": total
    }