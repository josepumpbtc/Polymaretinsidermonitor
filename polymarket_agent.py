import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import time

# --- 配置区 ---
# 建议在 GitHub Secrets 中设置 TELEGRAM_TOKEN
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8289795345:AAGwY_sVtvsZBC2VEazZG3Wl1hh9ltAEqo4")
CHAT_ID = "@polyinsidermonitor"
MIN_BET_USD = 3000  

# API 节点
DATA_API_URL = "https://data-api.polymarket.com/trades"
GAMMA_API_URL = "https://gamma-api.polymarket.com"

def get_user_profile(address):
    """获取用户详细画像：显示名称、创建时间"""
    if not address:
        return None
    try:
        res = requests.get(f"{GAMMA_API_URL}/users?address={address}", timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data and len(data) > 0:
                user_info = data[0]
                name = user_info.get('displayName') or user_info.get('username') or address
                created_at_str = user_info.get('createdAt')
                
                created_at = None
                if created_at_str:
                    # 转换 ISO 格式时间
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                
                return {"name": name, "created_at": created_at}
    except:
        pass
    return {"name": address, "created_at": None}

def get_user_trade_count(address):
    """查询用户历史交易总笔数"""
    try:
        # 使用 Data API 查询该用户的活动记录
        res = requests.get(f"https://data-api.polymarket.com/activity?user={address}&limit=20", timeout=5)
        if res.status_code == 200:
            data = res.json()
            return len(data) if data else 0
    except:
        return 999  # 出错时默认为老用户，避免误报
    return 0

def send_instant_alert(trade, profile, bet_count):
    """发送即时内幕预警消息（带调试输出版）"""
    created_days = "未知"
    if profile['created_at']:
        delta = datetime.now(profile['created_at'].tzinfo) - profile['created_at']
        created_days = f"{delta.days} 天"

    # 构建消息文本
    msg = (
        f"🚨 *疑似内幕交易警报* 🚨\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 投注金额: `${trade['bet_size']}` USDC\n"
        f"👤 用户: `{profile['name']}`\n"
        f"📅 账号年龄: `{created_days}`\n"
        f"📊 历史笔数: `{bet_count}` 次\n"
        f"🎯 预测结果: *{trade['outcome']}*\n"
        f"🏟️ 市场题目: {trade['market']}\n"
        f"⏰ 时间 (UTC): {trade['timestamp']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔍 *特征*: 新账号 / 低频交易者大额下单"
    )
    
    # Telegram API 请求
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": msg, 
        "parse_mode": "Markdown"
    }

    try:
        print(f"正在尝试发送消息到频道 {CHAT_ID}...")
        r = requests.post(url, json=payload, timeout=10)
        
        if r.status_code == 200:
            print("✅ Telegram 消息发送成功")
        else:
            # 关键：如果失败，这里会打印出 Telegram 返回的具体错误信息
            print(f"❌ Telegram API 报错: {r.status_code} - {r.text}")
            print(f"提示：请检查 Bot 是否为频道管理员，且 CHAT_ID '{CHAT_ID}' 是否正确。")
            
    except Exception as e:
        print(f"❌ 网络请求异常，无法连接到 Telegram: {e}")

def run_task():
    print(f"[{datetime.now()}] 正在扫描大额交易...")
    
    params = {
        "limit": 50,
        "filterType": "CASH",
        "filterAmount": MIN_BET_USD,
        "takerOnly": "true"
    }

    try:
        response = requests.get(DATA_API_URL, params=params, timeout=15)
        trades = response.json()

        if not trades:
            print("未发现大额交易。")
            return

        for t in trades:
            # 1. 提取金额（优先使用 usdcSize 确保准确）
            amt = float(t.get('usdcSize') or t.get('amount') or 0)
            if amt < MIN_BET_USD:
                continue

            user_addr = t.get('proxyWallet')
            if not user_addr: continue

            # 2. 获取用户信息和交易频次
            profile = get_user_profile(user_addr)
            bet_count = get_user_trade_count(user_addr)

            # 3. 判定逻辑：(金额 > 3000) AND (账号年龄 <= 10天 OR 交易次数 < 10)
            is_new_account = False
            if profile['created_at']:
                days_old = (datetime.now(profile['created_at'].tzinfo) - profile['created_at']).days
                if days_old <= 10:
                    is_new_account = True

            if is_new_account or bet_count < 10:
                print(f"🚩 命中目标: {profile['name']}，笔数: {bet_count}")
                
                trade_info = {
                    "bet_size": round(amt, 2),
                    "outcome": t.get('outcome'),
                    "market": t.get('title') or "Unknown Market",
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                send_instant_alert(trade_info, profile, bet_count)
                time.sleep(1) # 频率限制

    except Exception as e:
        print(f"❌ 执行错误: {e}")

if __name__ == "__main__":
    run_task()
