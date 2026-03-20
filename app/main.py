# app/main.py
import time
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.agent_router import router as agent_router
from app.api import inventory
from app.database import engine
from app.models import Base

# ==================== 1. 配置日志 ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# 自动建表（后续我们会用 Alembic 替代它）


app = FastAPI(title="电商库存中台 API", description="支持高并发的库存管理系统", version="1.0.0")

# 注册路由
app.include_router(agent_router)

app.include_router(inventory.router)
# ==================== 2. 全局日志中间件 (耗时统计) ====================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # 放行请求，去执行具体的路由代码
    response = await call_next(request)
    
    # 计算耗时 (毫秒)
    process_time = (time.time() - start_time) * 1000 
    
    # 打印日志：路径 | 方法 | 状态码 | 耗时
    logger.info(
        f"Path: {request.url.path} | Method: {request.method} | "
        f"Status: {response.status_code} | Time: {process_time:.2f}ms"
    )
    return response

# ==================== 3. 全局业务异常处理 ====================
# 拦截我们在代码里主动 raise 的 HTTPException (如库存不足、未找到记录等)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"业务异常拦截: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": "BUSINESS_ERROR", 
            "message": exc.detail, 
            "data": None
        }
    )

# ==================== 4. 全局参数校验异常处理 ====================
# 拦截 FastAPI 自动触发的参数类型错误 (422 Unprocessable Entity)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"参数校验失败: {exc.errors()}")
    return JSONResponse(
        status_code=400,  # 统一转为 400 错误
        content={
            "code": "VALIDATION_ERROR", 
            "message": "请求参数格式错误", 
            "details": str(exc.errors())
        }
    )

@app.get("/")
def root():
    return {"message": "库存中台服务已成功启动！请访问 /docs 查看接口文档"}