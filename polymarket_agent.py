import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import time

# --- 配置区 ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8289795345:AAGwY_sVtvsZBC2VEazZG3Wl1hh9ltAEqo4")
CHAT_ID = "@polyinsidermonitor"
MIN_BET_USD = 3000

# Polymarket 官方数据接口 (覆盖 CLOB 订单簿交易)
DATA_API_URL = "https://data-api.polymarket.com/trades"
GAMMA_API_URL = "https://gamma-api.polymarket.com"

def get_market_info(condition_id):
    """通过 Gamma API 获取市场题目"""
    try:
        # 缓存市场信息可以进一步优化速度
        res = requests.get(f"{GAMMA_API_URL}/markets?condition_id={condition_id}", timeout=5)
        data = res.json()
        if data and len(data) > 0:
            return data[0].get('question', "未知市场")
    except:
        pass
    return "未知市场"

def get_username(address):
    """获取用户名"""
    try:
        res = requests.get(f"{GAMMA_API_URL}/users?address={address}", timeout=5)
        data = res.json()
        if data:
            return data[0].get('displayName') or data[0].get('username') or address
    except:
        pass
    return address

def fetch_whale_bets():
    print(f"[{datetime.now()}] 正在从 Data-API 抓取大额交易...")
    
    # 构造请求：筛选现金金额 > 3000 的交易
    params = {
        "limit": 100,
        "filterType": "CASH",
        "filterAmount": MIN_BET_USD,
        "takerOnly": "true"
    }

    try:
        response = requests.get(DATA_API_URL, params=params, timeout=10)
        trades = response.json()

        if not trades:
            print("最近未发现符合条件的交易。")
            return None

        results = []
        for t in trades:
            # 这里的 match_time 通常是 ISO 格式字符串
            trade_time = t.get('matchTime') or t.get('timestamp')
            
            results.append({
                "bet_size": round(float(t.get('usdAmount', 0)), 2),
                "username": get_username(t.get('taker')),
                "token_id": t.get('assetId'),
                "token_outcome_name": t.get('outcome'),
                "market": get_market_info(t.get('market')),
                "timestamp": trade_time
            })

        df = pd.DataFrame(results)
        filename = f"Whale_Bets_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        return filename

    except Exception as e:
        print(f"抓取失败: {e}")
        return None

def send_to_telegram(file_path):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    caption = f"🐳 Polymarket 鲸鱼追踪 (单笔 > ${MIN_BET_USD})\n时间: {datetime.now().strftime('%Y-%m-%d')}"
    with open(file_path, 'rb') as f:
        requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"document": f})
    os.remove(file_path)

if __name__ == "__main__":
    file = fetch_whale_bets()
    if file:
        send_to_telegram(file)
        print("报告已发送！")
