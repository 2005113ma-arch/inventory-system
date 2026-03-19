# stress_test.py
import asyncio
import httpx
import time

# 测试配置
API_URL = "http://127.0.0.1:8000/inventory/lock"
CONCURRENT_USERS = 50  # 模拟 50 个人同时抢
SKU_ID = 10001
WAREHOUSE_ID = 1
LOCK_QUANTITY = 1

async def buy_item(client: httpx.AsyncClient, user_id: int):
    """模拟单个用户发起抢购请求"""
    payload = {
        "skuId": SKU_ID,
        "warehouseId": WAREHOUSE_ID,
        "quantity": LOCK_QUANTITY,
        "orderId": f"ORDER_TEST_{user_id}"
    }
    try:
        response = await client.post(API_URL, json=payload)
        return user_id, response.status_code, response.json()
    except Exception as e:
        return user_id, 500, str(e)

async def main():
    print(f"🚀 开始模拟 {CONCURRENT_USERS} 个用户同时抢购...")
    start_time = time.time()
    
    # 创建一个异步的 HTTP 客户端
    async with httpx.AsyncClient() as client:
        # 组装 50 个并发任务
        tasks = [buy_item(client, i) for i in range(CONCURRENT_USERS)]
        
        # asyncio.gather 会让这 50 个任务在同一瞬间并发发出去！
        results = await asyncio.gather(*tasks)

    end_time = time.time()
    
    # 统计结果
    success_count = 0
    conflict_count = 0
    
    for user_id, status, data in results:
        if status == 200:
            success_count += 1
            print(f"✅ 用户 {user_id:02d} 抢购成功!")
        elif status == 409:
            conflict_count += 1
            print(f"⚠️ 用户 {user_id:02d} 没抢到 (系统繁忙/并发冲突)")
        elif status == 400:
            print(f"❌ 用户 {user_id:02d} 没抢到 (库存已经不足)")
        else:
            print(f"❓ 用户 {user_id:02d} 遇到其他错误: {data}")

    print("\n" + "="*30)
    print("📊 压测结果统计：")
    print(f"⏱️  总耗时: {end_time - start_time:.2f} 秒")
    print(f"✅  成功抢到: {success_count} 人")
    print(f"⚠️  并发冲突: {conflict_count} 人")
    print("="*30)

if __name__ == "__main__":
    asyncio.run(main())