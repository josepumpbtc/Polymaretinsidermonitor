import requests
import pandas as pd
from datetime import datetime
import os

# --- 配置区 ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8289795345:AAGwY_sVtvsZBC2VEazZG3Wl1hh9ltAEqo4")
CHAT_ID = "@polyinsidermonitor"
MIN_BET_USD = 135  # 你设置的门槛

DATA_API_URL = "https://data-api.polymarket.com/trades"
GAMMA_API_URL = "https://gamma-api.polymarket.com"

# 缓存市场信息，避免重复请求
market_cache = {}

def get_market_question(condition_id):
    """解析 Condition ID 为市场题目"""
    if not condition_id or condition_id == "None":
        return "Unknown Market"
    if condition_id in market_cache:
        return market_cache[condition_id]
    
    try:
        # 查询 Gamma API 获取市场详情
        res = requests.get(f"{GAMMA_API_URL}/markets?condition_id={condition_id}", timeout=5)
        data = res.json()
        if data and len(data) > 0:
            question = data[0].get('question', "Unknown Market")
            market_cache[condition_id] = question
            return question
    except:
        pass
    return "Unknown Market"

def get_username(address):
    """查询用户昵称"""
    if not address: return "Unknown"
    try:
        res = requests.get(f"{GAMMA_API_URL}/users?address={address}", timeout=5)
        data = res.json()
        if data:
            return data[0].get('displayName') or data[0].get('username') or address
    except:
        pass
    return address

def run_task():
    print(f"[{datetime.now()}] 正在抓取大额交易 (>${MIN_BET_USD})...")
    
    params = {
        "limit": 100,
        "filterType": "CASH",     # 按美金金额过滤
        "filterAmount": MIN_BET_USD,
        "takerOnly": "true"
    }

    try:
        response = requests.get(DATA_API_URL, params=params, timeout=10)
        trades = response.json()

        if not trades:
            print("未发现符合条件的交易。")
            return

        results = []
        for t in trades:
            # --- 关键修正：使用正确的字段名 ---
            # 1. bet_size: 使用 'amount' (USDC 金额)
            raw_amount = t.get('amount')
            if raw_amount is None:
                # 备用计算：价格 * 数量
                raw_amount = float(t.get('price', 0)) * float(t.get('size', 0))
            
            # 2. 地址: 使用 'taker'
            addr = t.get('taker')
            
            # 3. 市场 ID: 使用 'market'
            cond_id = t.get('market')
            
            # 4. 资产 ID: 使用 'asset_id'
            token_id = t.get('asset_id')
            
            # 5. 时间戳处理
            ts = t.get('timestamp')
            try:
                # 检查是否为毫秒级时间戳
                if int(ts) > 10**11: ts = int(ts) / 1000
                time_str = datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M:%S')
            except:
                time_str = t.get('matchTime', "N/A")

            results.append({
                "bet_size": round(float(raw_amount), 2),
                "username": get_username(addr),
                "token_id": token_id,
                "token_outcome_name": t.get('outcome'),
                "market": get_market_question(cond_id),
                "timestamp": time_str
            })

        # 整理成 DataFrame 并按金额排序
        df = pd.DataFrame(results)
        df = df.sort_values(by="bet_size", ascending=False)

        # 生成并发送文件
        filename = f"Polymarket_Whales_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        # 此处调用你的 Telegram 发送逻辑...
        print(f"成功导出 {len(results)} 笔交易。")

    except Exception as e:
        print(f"执行出错: {e}")

if __name__ == "__main__":
    run_task()
