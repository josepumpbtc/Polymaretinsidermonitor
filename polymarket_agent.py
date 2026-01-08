import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import time

# --- 配置区 ---
# 建议在 GitHub Actions 中设置 Secrets：TELEGRAM_TOKEN
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8289795345:AAGwY_sVtvsZBC2VEazZG3Wl1hh9ltAEqo4")
CHAT_ID = "@polyinsidermonitor"
MIN_BET_USD = 3000  # 筛选金额（美元）

# API 节点
DATA_API_URL = "https://data-api.polymarket.com/trades"
GAMMA_API_URL = "https://gamma-api.polymarket.com"

# 全局缓存，减少重复请求，提高运行速度
market_cache = {}
user_cache = {}

def get_market_question(condition_id):
    """根据 condition_id 获取市场题目"""
    if not condition_id:
        return "Unknown Market"
    if condition_id in market_cache:
        return market_cache[condition_id]
    
    try:
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
    """根据钱包地址获取 Polymarket 用户名"""
    if not address:
        return "Unknown"
    if address in user_cache:
        return user_cache[address]
    
    try:
        res = requests.get(f"{GAMMA_API_URL}/users?address={address}", timeout=5)
        data = res.json()
        if data:
            name = data[0].get('displayName') or data[0].get('username') or address
            user_cache[address] = name
            return name
    except:
        pass
    return address

def send_to_telegram(file_path, count):
    """发送文件到 Telegram 频道"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    caption = (
        f"🐳 *Polymarket 鲸鱼交易日报*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 筛选标准: > ${MIN_BET_USD}\n"
        f"📊 今日单数: {count}\n"
        f"📅 时间: {datetime.now().strftime('%Y-%m-%d')}\n"
    )
    
    try:
        with open(file_path, 'rb') as f:
            payload = {
                "chat_id": CHAT_ID,
                "caption": caption,
                "parse_mode": "Markdown"
            }
            files = {"document": f}
            r = requests.post(url, data=payload, files=files)
        
        if r.status_code == 200:
            print("✅ 报告已发送至 Telegram")
            os.remove(file_path)
        else:
            print(f"❌ Telegram 发送失败: {r.text}")
    except Exception as e:
        print(f"❌ Telegram 发送出错: {e}")

def run_task():
    print(f"[{datetime.now()}] 启动抓取任务...")
    
    # 构造请求：获取最近交易，并使用服务端金额过滤
    params = {
        "limit": 100,
        "filterType": "CASH",
        "filterAmount": MIN_BET_USD,
        "takerOnly": "true"
    }

    try:
        response = requests.get(DATA_API_URL, params=params, timeout=15)
        trades = response.json()

        if not trades:
            # 如果没数据，给频道发个简单通知（可选）
            # requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
            #               data={"chat_id": CHAT_ID, "text": "📢 过去 24 小时未发现符合条件的鲸鱼交易。"})
            print("没有发现符合条件的交易。")
            return

        results = []
        for t in trades:
            # --- 关键修正：确保使用正确的 API 字段 ---
            amount = t.get('amount') # 成交的 USDC 数额
            if amount is None:
                amount = float(t.get('price', 0)) * float(t.get('size', 0))
            
            taker_addr = t.get('taker')
            condition_id = t.get('market')
            asset_id = t.get('asset_id')
            outcome = t.get('outcome')
            
            # 时间戳解析
            ts = t.get('timestamp')
            try:
                if int(ts) > 10**11: ts = int(ts) / 1000
                time_str = datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M:%S')
            except:
                time_str = "N/A"

            results.append({
                "bet_size": round(float(amount), 2),
                "username": get_username(taker_addr),
                "token_id": asset_id,
                "token_outcome_name": outcome,
                "market": get_market_question(condition_id),
                "timestamp": time_str
            })

        # 转换为 DataFrame
        df = pd.DataFrame(results)
        
        # 按照用户要求的顺序整理列
        output_df = df[["bet_size", "username", "token_id", "token_outcome_name", "market", "timestamp"]]
        
        # 保存 CSV
        filename = f"Whale_Bets_{datetime.now().strftime('%Y%m%d')}.csv"
        output_df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        # 发送
        send_to_telegram(filename, len(results))

    except Exception as e:
        print(f"❌ 运行过程中发生错误: {e}")

if __name__ == "__main__":
    run_task()
