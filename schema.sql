-- 仓库表
CREATE TABLE warehouse (
    warehouse_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    warehouse_name VARCHAR(100) NOT NULL,
    warehouse_code VARCHAR(50) UNIQUE NOT NULL,
    address VARCHAR(255),
    status TINYINT DEFAULT 1 COMMENT '1-启用 0-禁用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_warehouse_code (warehouse_code)
);

-- 商品表
CREATE TABLE sku (
    sku_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sku_code VARCHAR(50) UNIQUE NOT NULL,
    sku_name VARCHAR(200) NOT NULL,
    category_id BIGINT,
    status TINYINT DEFAULT 1 COMMENT '1-启用 0-禁用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_sku_code (sku_code)
);

-- 库存表（核心）
CREATE TABLE inventory (
    inventory_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sku_id BIGINT NOT NULL,
    warehouse_id BIGINT NOT NULL,
    total_quantity INT UNSIGNED DEFAULT 0 COMMENT '总库存',
    available_quantity INT UNSIGNED DEFAULT 0 COMMENT '可用库存',
    locked_quantity INT UNSIGNED DEFAULT 0 COMMENT '锁定库存',
    version INT DEFAULT 0 COMMENT '乐观锁版本号',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_sku_warehouse (sku_id, warehouse_id),
    INDEX idx_sku_id (sku_id),
    INDEX idx_warehouse_id (warehouse_id)
);

-- 库存锁定表
CREATE TABLE inventory_lock (
    lock_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id VARCHAR(64) NOT NULL,
    sku_id BIGINT NOT NULL,
    warehouse_id BIGINT NOT NULL,
    lock_quantity INT UNSIGNED NOT NULL,
    lock_status TINYINT DEFAULT 1 COMMENT '1-锁定中 2-已扣减 3-已释放',
    expire_time TIMESTAMP NOT NULL COMMENT '锁定期限',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_order_id (order_id),
    INDEX idx_sku_warehouse (sku_id, warehouse_id),
    INDEX idx_expire_time (expire_time)
);

-- 库存流水表
CREATE TABLE inventory_transaction (
    transaction_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    sku_id BIGINT NOT NULL,
    warehouse_id BIGINT NOT NULL,
    change_type TINYINT NOT NULL COMMENT '1-入库 2-出库 3-锁定 4-解锁',
    change_quantity INT NOT NULL,
    before_quantity INT UNSIGNED NOT NULL,
    after_quantity INT UNSIGNED NOT NULL,
    business_type VARCHAR(50) COMMENT '业务类型：采购/销售/退货等',
    business_id VARCHAR(64) COMMENT '业务单号',
    operator VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sku_warehouse (sku_id, warehouse_id),
    INDEX idx_business_id (business_id),
    INDEX idx_created_at (created_at)
);