# models.py
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, UniqueConstraint, SmallInteger, Index
from datetime import datetime
from app.database import Base

class Warehouse(Base):
    """仓库表"""
    __tablename__ = 'warehouse'

    warehouse_id = Column(BigInteger, primary_key=True, autoincrement=True)
    warehouse_name = Column(String(100), nullable=False)
    warehouse_code = Column(String(50), nullable=False, unique=True)
    address = Column(String(255))
    status = Column(SmallInteger, default=1)  # 1-启用 0-禁用
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Sku(Base):
    """商品表"""
    __tablename__ = 'sku'

    sku_id = Column(BigInteger, primary_key=True, autoincrement=True)
    sku_code = Column(String(50), nullable=False, unique=True)
    sku_name = Column(String(200), nullable=False)
    category_id = Column(BigInteger)
    status = Column(SmallInteger, default=1)  # 1-启用 0-禁用
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Inventory(Base):
    """库存核心表"""
    __tablename__ = 'inventory'
    
    inventory_id = Column(BigInteger, primary_key=True, autoincrement=True)
    sku_id = Column(BigInteger, nullable=False, index=True)
    warehouse_id = Column(BigInteger, nullable=False, index=True)
    total_quantity = Column(Integer, default=0)
    available_quantity = Column(Integer, default=0)
    locked_quantity = Column(Integer, default=0)
    version = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    __table_args__ = (UniqueConstraint('sku_id', 'warehouse_id', name='uk_sku_warehouse'),)


class InventoryLock(Base):
    """库存锁定表"""
    __tablename__ = 'inventory_lock'

    lock_id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id = Column(String(64), nullable=False, index=True) 
    sku_id = Column(BigInteger, nullable=False)
    warehouse_id = Column(BigInteger, nullable=False)
    lock_quantity = Column(Integer, nullable=False) 
    lock_status = Column(SmallInteger, default=1)  # 1-锁定中 2-已扣减 3-已释放
    expire_time = Column(DateTime, nullable=False) 
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index('idx_sku_warehouse', 'sku_id', 'warehouse_id'),
        Index('idx_expire_time', 'expire_time'),
    )


class InventoryTransaction(Base):
    """库存流水表"""
    __tablename__ = 'inventory_transaction'
    
    transaction_id = Column(BigInteger, primary_key=True, autoincrement=True)
    sku_id = Column(BigInteger, nullable=False, index=True)
    warehouse_id = Column(BigInteger, nullable=False, index=True)
    change_type = Column(SmallInteger, nullable=False)
    change_quantity = Column(Integer, nullable=False)
    before_quantity = Column(Integer, nullable=False)
    after_quantity = Column(Integer, nullable=False)
    business_type = Column(String(50))
    business_id = Column(String(64), index=True)
    operator = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)