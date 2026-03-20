import json
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from openai import AsyncOpenAI
from app.config import settings
# 引入你的数据库依赖 (根据你实际项目的路径调整，通常是 app.database)
from app.database import get_db
# 引入我们刚才写的真实 Skills
from app.agent_skills import get_real_inventory, create_real_replenishment
import traceback

router = APIRouter(prefix="/api/agent", tags=["智能 Agent"])

# 初始化大模型客户端 (记得确保 .env 里配置了 DEEPSEEK_API_KEY)
# 这里用 os.getenv 获取环境变量，比写死在代码里更安全
client = AsyncOpenAI(
    api_key=settings.DEEPSEEK_API_KEY, 
    base_url="https://api.deepseek.com"
)

# --- 定义大模型能看到的 Tools (说明书) ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_real_inventory",
            "description": "查询指定商品 sku_code 的当前真实库存数量和安全库存线",
            "parameters": {"type": "object", "properties": {"sku_code": {"type": "string"}}, "required": ["sku_code"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_real_replenishment",
            "description": "提交补货申请单。当判断需要补货时调用此工具。",
            "parameters": {
                "type": "object", 
                "properties": {
                    "sku_code": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "reason": {"type": "string"}
                }, 
                "required": ["sku_code", "quantity", "reason"]
            }
        }
    }
]

class ChatRequest(BaseModel):
    prompt: str

@router.post("/chat", summary="与库存 Agent 对话接口")
async def chat_with_agent(request: ChatRequest, db: Session = Depends(get_db)):
  try: 
    """
    接收前端指令，调度大模型，并传入 db session 执行真实数据库操作
    """
    messages = [{"role": "user", "content": request.prompt}]
    
    # 允许 Agent 最多连续思考 5 步
    for _ in range(5):
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        print("✅ 收到大模型回复！") # 看看能不能走到这里
        msg = response.choices[0].message
        messages.append(msg)
        
        # 如果大模型得出最终结论，直接返回
        if not msg.tool_calls:
            return {"status": "success", "reply": msg.content}
            
        # 如果需要调用工具，就在本地执行真实业务代码
        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            # 路由到咱们刚才写的真实的 agent_skills.py 中的函数，重点是把 db 传进去！
            if func_name == "get_real_inventory":
                result = get_real_inventory(db=db, sku_code=args.get("sku_code"))
            elif func_name == "create_real_replenishment":
                result = create_real_replenishment(db=db, sku_code=args.get("sku_code"), quantity=args.get("quantity"), reason=args.get("reason"))
            else:
                result = json.dumps({"error": "未知工具"})
                
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": func_name,
                "content": result
            })
            
    return {"status": "error", "reply": "对话轮次超限，系统未能完成任务。"}
  except Exception as e:
        # ⚠️ 这里是关键！我们要把隐藏的错误炸出来！
        print("\n" + "="*50)
        print("🚨 发生致命错误！详细堆栈信息如下：")
        traceback.print_exc() 
        print("="*50 + "\n")
        return {"status": "error", "reply": f"系统内部异常: {str(e)}"}