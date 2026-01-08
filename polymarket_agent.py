import requests
import pandas as pd
from datetime import datetime
import os

# --- 配置区 ---
# 请在 GitHub Secrets 中设置 TELEGRAM_TOKEN
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8289795345:AAGwY_sVtvsZBC2VEazZG3Wl1hh9ltAEqo4")
CHAT_ID = "@polyinsidermonitor"
MIN_BET_USD = 3000  # 建议根据需求调整，如测试时可改为 135

# API 节点
DATA_API_URL = "https://data-api.polymarket.com/trades"
GAMMA_API_URL = "https://gamma-api.polymarket.com"

# 缓存用户名，减少 API 请求
user_cache = {}

def get_username(address):
    """获取 Polymarket 用户名，如果未设置则返回地址"""
    if not address:
        return "Unknown User"
    if address in user_cache:
        return user_cache[address]
    
    try:
        res = requests.get(f"{GAMMA_API_URL}/users?address={address}", timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data and len(data) > 0:
                name = data[0].get('displayName') or data[0].get('username') or address
                user_cache[address] = name
                return name
    except:
        pass
    return address

def send_to_telegram(file_path, count):
    """发送 CSV 文件到 Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    caption = (
        f"🐳 *Polymarket 大额交易监控*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 门槛: > ${MIN_BET_USD}\n"
        f"📊 笔数: {count}\n"
        f"📅 日期: {datetime.now().strftime('%Y-%m-%d')}\n"
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
            print("✅ 报告已成功发送")
            os.remove(file_path)
        else:
            print(f"❌ 发送失败: {r.text}")
    except Exception as e:
        print(f"❌ Telegram 发送错误: {e}")

def run_task():
    print(f"[{datetime.now()}] 正在抓取数据...")
    
    # 构造请求参数
    params = {
        "limit": 1000,
        "filterType": "CASH",
        "filterAmount": MIN_BET_USD,
        "takerOnly": "true"
    }

    try:
        response = requests.get(DATA_API_URL, params=params, timeout=15)
        trades = response.json()

        if not trades:
            print("未发现符合条件的交易。")
            return

        results = []
        for t in trades:
            # --- 关键修正：使用 Data API 的正确字段 ---
            
            # 1. 金额：优先取 amount，否则用 price * size
            amt = t.get('amount')
            if amt is None:
                amt = float(t.get('price', 0)) * float(t.get('size', 0))
            
            # 2. 用户：最新字段是 proxyWallet
            user_addr = t.get('proxyWallet')
            
            # 3. 市场题目：API 直接返回了 title
            market_title = t.get('title') or "Unknown Market"
            
            # 4. Token/Asset ID：字段名是 asset
            token_id = t.get('asset')
            
            # 5. 结果名称：outcome
            outcome_name = t.get('outcome')
            
            # 6. 时间戳处理
            raw_ts = t.get('timestamp')
            try:
                # 兼容毫秒和秒
                ts_val = int(raw_ts)
                if ts_val > 10**11: ts_val /= 1000
                time_str = datetime.fromtimestamp(ts_val).strftime('%Y-%m-%d %H:%M:%S')
            except:
                time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            results.append({
                "bet_size": round(float(amt), 2),
                "username": get_username(user_addr),
                "token_id": token_id,
                "token_outcome_name": outcome_name,
                "market": market_title,
                "timestamp": time_str
            })

        # 转换为 DataFrame
        df = pd.DataFrame(results)
        
        # 按照你的要求排列列顺序
        df = df[["bet_size", "username", "token_id", "token_outcome_name", "market", "timestamp"]]
        
        # 导出并发送
        filename = f"Polymarket_Whales_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        send_to_telegram(filename, len(results))

    except Exception as e:
        print(f"❌ 执行错误: {e}")

if __name__ == "__main__":
    run_task()
