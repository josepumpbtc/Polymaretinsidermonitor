import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import time

# --- 配置区 ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "@polyinsidermonitor"
MIN_BET_USD = 3000  
DATA_API_URL = "https://data-api.polymarket.com/trades"
GAMMA_API_URL = "https://gamma-api.polymarket.com"

def get_user_profile(address):
    """
    获取用户详细画像：创建时间、交易频次、显示名称
    """
    if not address:
        return None
    
    try:
        # 获取基础资料
        res = requests.get(f"{GAMMA_API_URL}/users?address={address}", timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data:
                user_info = data[0]
                display_name = user_info.get('displayName') or user_info.get('username') or address
                created_at_str = user_info.get('createdAt') # 格式通常为 2023-10-01T...
                
                # 解析创建时间
                created_at = None
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                
                return {
                    "name": display_name,
                    "created_at": created_at,
                    "address": address
                }
    except Exception as e:
        print(f"获取用户信息失败: {e}")
    return {"name": address, "created_at": None, "address": address}

def send_instant_alert(trade_info, user_profile):
    """发送即时报警到 Telegram"""
    created_days = "未知"
    if user_profile['created_at']:
        delta = datetime.now(user_profile['created_at'].tzinfo) - user_profile['created_at']
        created_days = f"{delta.days} 天"

    msg = (
        f"🚨 *疑似内幕交易警报* 🚨\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 投注金额: `${trade_info['bet_size']}`\n"
        f"👤 用户: `{user_profile['name']}`\n"
        f"📅 账号年龄: `{created_days}`\n"
        f"📊 预测目标: *{trade_info['token_outcome_name']}*\n"
        f"🏟️ 市场: {trade_info['market']}\n"
        f"⏰ 时间: {trade_info['timestamp']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔍 *特征*: 新账号大额首投"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def run_task():
    print(f"[{datetime.now()}] 启动扫描...")
    params = {"limit": 50, "filterType": "CASH", "filterAmount": MIN_BET_USD, "takerOnly": "true"}

    try:
        response = requests.get(DATA_API_URL, params=params, timeout=15)
        trades = response.json()
        if not trades: return

        for t in trades:
            amt = float(t.get('amount') or (float(t.get('price', 0)) * float(t.get('size', 0))))
            user_addr = t.get('proxyWallet')
            
            # 1. 基础金额过滤
            if amt < MIN_BET_USD: continue

            # 2. 获取深度用户数据
            profile = get_user_profile(user_addr)
            
            # 3. 判定“内幕交易”逻辑
            # 规则：创建时间 < 10天 (由于API限制，我们通过创建日期判定)
            is_new_account = False
            if profile['created_at']:
                days_old = (datetime.now(profile['created_at'].tzinfo) - profile['created_at']).days
                if days_old <= 10:
                    is_new_account = True

            # 封装交易信息
            trade_data = {
                "bet_size": round(amt, 2),
                "token_outcome_name": t.get('outcome'),
                "market": t.get('title') or "Unknown",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # 触发即时报警
            if is_new_account:
                print(f"🚩 发现可疑交易: {profile['name']} (新账号)")
                send_instant_alert(trade_data, profile)
                # 防止触发频率过快被 Telegram 封禁
                time.sleep(1)

    except Exception as e:
        print(f"执行错误: {e}")

if __name__ == "__main__":
    run_task()
