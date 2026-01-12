import requests
import pandas as pd
from datetime import datetime, timezone
import os
import time

# --- 配置区 ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "@polyinsidermonitor" # 确保这是公开频道，或者使用数字 ID
MIN_BET_USD = 3000  

DATA_API_URL = "https://data-api.polymarket.com"
GAMMA_API_URL = "https://gamma-api.polymarket.com"

def get_user_profile(address):
    """获取显示名称和创建时间"""
    try:
        res = requests.get(f"{GAMMA_API_URL}/users?address={address}", timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data:
                user = data[0]
                created_at = user.get('createdAt')
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00')) if created_at else None
                return {"name": user.get('displayName') or address, "created_at": dt}
    except Exception as e:
        print(f"获取 Profile 失败 ({address}): {e}")
    return {"name": address, "created_at": None}

def get_user_trade_count(address):
    """获取用户历史交易总数"""
    try:
        # 查询用户活动接口
        res = requests.get(f"{DATA_API_URL}/activity?user={address}&limit=1", timeout=10)
        if res.status_code == 200:
            # 这里的逻辑根据 API 返回值调整，通常返回一个列表
            data = res.json()
            return len(data) if data else 0
    except:
        return 99 # 报错则跳过，防止误报
    return 0

def send_instant_alert(trade_info, profile, bet_count):
    """发送即时报警"""
    if not TELEGRAM_TOKEN:
        print("❌ 错误: 未设置 TELEGRAM_TOKEN 环境变量")
        return

    age_str = "未知"
    if profile['created_at']:
        days = (datetime.now(timezone.utc) - profile['created_at']).days
        age_str = f"{days} 天"

    msg = (
        f"🚨 *疑似内幕交易警报* 🚨\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 投注金额: `${trade_info['bet_size']}` USDC\n"
        f"👤 用户: `{profile['name']}`\n"
        f"📅 账号年龄: `{age_str}`\n"
        f"📊 历史笔数: `{bet_count}` 次\n"
        f"🎯 预测结果: *{trade_info['outcome']}*\n"
        f"🏟️ 市场: {trade_info['market']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔍 *特征*: 疑似新账号/低频账号大额交易"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    if r.status_code != 200:
        print(f"❌ Telegram 发送失败: {r.text}")
    else:
        print(f"✅ 成功推送交易: {profile['name']}")

def run_task():
    print(f"开始扫描 (阈值: ${MIN_BET_USD})...")
    params = {"limit": 100, "filterType": "CASH", "filterAmount": MIN_BET_USD, "takerOnly": "true"}
    
    try:
        # 获取最新交易
        response = requests.get(f"{DATA_API_URL}/trades", params=params, timeout=15)
        trades = response.json()
        
        if not trades:
            print("当前无符合条件的交易。")
            return

        for t in trades:
            # 关键修复：同时检查 usdcSize 和 amount
            raw_amt = t.get('usdcSize') or t.get('amount')
            amt = float(raw_amt) if raw_amt else 0
            
            if amt < MIN_BET_USD:
                continue
                
            address = t.get('proxyWallet')
            if not address: continue
            
            profile = get_user_profile(address)
            bet_count = get_user_trade_count(address)
            
            # 判定逻辑：年龄 <= 10天 OR 交易笔数 < 10
            is_suspicious = False
            if profile['created_at']:
                days_old = (datetime.now(timezone.utc) - profile['created_at']).days
                if days_old <= 10: is_suspicious = True
            
            if bet_count < 10: is_suspicious = True
            
            if is_suspicious:
                trade_data = {
                    "bet_size": round(amt, 2),
                    "outcome": t.get('outcome'),
                    "market": t.get('title') or "未知市场"
                }
                send_instant_alert(trade_data, profile, bet_count)
                time.sleep(1) # 避免触发频率限制

    except Exception as e:
        print(f"运行时错误: {e}")

if __name__ == "__main__":
    run_task()
