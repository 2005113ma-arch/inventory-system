#  智能电商库存自动化中台 (AI-Driven Inventory System)

基于 `FastAPI` + `Vue3` 构建的现代化电商库存管理系统。不仅包含应对高并发场景的坚实底层业务逻辑（乐观锁防超卖、完整流水溯源），更创新性地引入了基于大模型 **Function Calling** 的 AI Agent 智能大脑，实现了从“被动查库存”到“主动智能补货”的自动化升级。

[项目全栈架构预览](https://via.placeholder.com/800x400?text=Insert+Your+Chat+Console+Screenshot+Here) *()*

##  核心亮点 (Core Features)

### 1.  AI Agent 智能自动化工作流
* **Function Calling 深度整合**：剥离传统的 CRUD 面板，将底层库存查询、补单业务封装为标准化 Skills。
* **业务闭环思考**：Agent 能够理解自然语言指令（如：“查一下SKU-1003库存，不够自动补单”），自主完成 `多表数据检索 -> 规则比对(安全库存线) -> 调用核心业务 API` 的复杂工作流。
* **异步非阻塞**：基于 `AsyncOpenAI` 与 FastAPI 异步特性，保障大模型调度时不阻塞主业务线程。

### 2.  高并发防超卖架构 (核心业务底座)
* **乐观锁机制**：库存表设计 `version` 字段，扣减/锁定操作严格校验版本号，从数据库层面杜绝超卖。
* **自旋重试**：内置高并发冲突下的安全重试机制（`MAX_RETRIES`），兼顾数据强一致性与系统吞吐量。
* **精细化库存状态**：拆分 `总库存(total)`、`可用库存(available)` 与 `锁定库存(locked)`，支持订单锁定与超时释放。

### 3. 规范的全栈工程化
* **后端**：`FastAPI` + `SQLAlchemy` + `Pydantic`，严谨的请求校验与依赖注入。配置与敏感信息统一由 `.env` 和 `pydantic_settings` 安全管理。
* **前端**：`Vue3` + `Vite` + `Element Plus` 构建响应式交互控制台。
* **数据持久化**：MySQL 强约束表结构设计，包含完整的流水账本（`InventoryTransaction`）便于资金与物资对账。

## 技术栈 (Tech Stack)

* **后端框架**: Python 3, FastAPI, Uvicorn
* **数据库/ORM**: MySQL 8.0, SQLAlchemy, PyMySQL
* **AI 大模型**: DeepSeek API (兼容 OpenAI SDK 格式)
* **前端框架**: Vue.js 3, Vite, Element Plus, Axios

## 快速启动 (Quick Start)

### 1. 数据库准备
1. 创建 MySQL 数据库 `inventory_center`。
2. 运行项目根目录或 `app/` 下的建表脚本（或依赖 SQLAlchemy 自动建表）。
3. 插入测试数据（确保存在 `SKU-1003` 等商品）。

### 2. 后端服务启动
```bash
# 进入项目根目录
cd inventory-system

# 安装依赖
pip install -r requirements.txt

# 配置环境变量 (新建 .env 文件)
# DB_URL=mysql+pymysql://root:123456@localhost/inventory_center
# DEEPSEEK_API_KEY=sk-xxxxxxx

# 启动 FastAPI 服务
uvicorn app.main:app --reload
