import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import time

# --- 配置区 ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8289795345:AAGwY_sVtvsZBC2VEazZG3Wl1hh9ltAEqo4")
CHAT_ID = "@polyinsidermonitor"
MIN_BET_USD = 3000

DATA_API_URL = "https://data-api.polymarket.com/trades"
GAMMA_API_URL = "https://gamma-api.polymarket.com"

user_cache = {}

def get_username(address):
    if not address: return "Unknown"
    if address in user_cache: return user_cache[address]
    try:
        res = requests.get(f"{GAMMA_API_URL}/users?address={address}", timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data:
                name = data[0].get('displayName') or data[0].get('username') or address
                user_cache[address] = name
                return name
    except: pass
    return address

def run_task():
    print(f"[{datetime.now()}] 开始抓取过去 24 小时的所有大额交易...")
    
    # 1. 设置 24 小时的时间截止线
    cutoff_time = datetime.now() - timedelta(hours=24)
    cutoff_ts = int(cutoff_time.timestamp())
    
    all_results = []
    last_timestamp = None # 用于分页
    
    while True:
        # 2. 构造请求参数
        params = {
            "limit": 100,
            "filterType": "CASH",
            "filterAmount": MIN_BET_USD,
            "takerOnly": "true"
        }
        # 如果有上一次抓取的最后时间，则从那个时间点继续往前查
        if last_timestamp:
            params["timestamp"] = last_timestamp

        try:
            response = requests.get(DATA_API_URL, params=params, timeout=15)
            trades = response.json()

            if not trades or len(trades) == 0:
                break

            finished = False
            for t in trades:
                # 获取该交易的时间戳
                raw_ts = int(t.get('timestamp'))
                # API 有时返回毫秒，需要转换
                ts_seconds = raw_ts / 1000 if raw_ts > 10**11 else raw_ts
                
                # 如果这笔交易已经超过 24 小时，停止抓取
                if ts_seconds < cutoff_ts:
                    finished = True
                    break

                # 提取数据
                amt = t.get('amount') or (float(t.get('price', 0)) * float(t.get('size', 0)))
                time_str = datetime.fromtimestamp(ts_seconds).strftime('%Y-%m-%d %H:%M:%S')

                all_results.append({
                    "bet_size": round(float(amt), 2),
                    "username": get_username(t.get('proxyWallet')),
                    "token_id": t.get('asset'),
                    "token_outcome_name": t.get('outcome'),
                    "market": t.get('title') or "Unknown Market",
                    "timestamp": time_str
                })
                
                # 更新最后一次看到的时间戳，供下一页使用
                last_timestamp = raw_ts

            print(f"目前已抓取 {len(all_results)} 笔符合条件的交易...")
            
            if finished:
                break
            
            # 稍微停顿，避免请求过快被封 IP
            time.sleep(0.5)

        except Exception as e:
            print(f"抓取分页时出错: {e}")
            break

    # 3. 生成 CSV 并发送
    if all_results:
        df = pd.DataFrame(all_results)
        # 去重（防止分页重叠）
        df = df.drop_duplicates()
        df = df[["bet_size", "username", "token_id", "token_outcome_name", "market", "timestamp"]]
        
        filename = f"Whale_Bets_24H_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        # 发送至 Telegram
        send_to_telegram(filename, len(df))
    else:
        print("过去 24 小时内未发现符合条件的交易。")

def send_to_telegram(file_path, count):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    caption = (
        f"🐳 *Polymarket 24小时全量报告*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 门槛: > ${MIN_BET_USD}\n"
        f"📊 总计: {count} 笔交易\n"
        f"📅 周期: 过去 24 小时\n"
    )
    with open(file_path, 'rb') as f:
        requests.post(url, data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "Markdown"}, files={"document": f})
    os.remove(file_path)

if __name__ == "__main__":
    run_task()
