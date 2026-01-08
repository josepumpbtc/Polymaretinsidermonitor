import requests
import pandas as pd
from datetime import datetime
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 配置区 ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8289795345:AAGwY_sVtvsZBC2VEazZG3Wl1hh9ltAEqo4")
CHAT_ID = "@polyinsidermonitor"
MIN_BET_USD = 3000

# Google Sheet 配置
SHEET_ID = "1s6ZSKEjWqlu9GaW2DgAGDaH3ntTG1pUZ0sM8k2UY0MM"
# 建议在 GitHub Secrets 中存储 JSON 字符串，变量名为 GOOGLE_SERVICE_ACCOUNT
GOOGLE_SERVICE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT") 

# API 节点
DATA_API_URL = "https://data-api.polymarket.com/trades"
GAMMA_API_URL = "https://gamma-api.polymarket.com"

user_cache = {}

def get_username(address):
    if not address: return "Unknown User"
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

def update_google_sheet(df):
    """将数据追加到 Google Sheet"""
    print("正在同步到 Google Sheet...")
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # 加载凭据
        if GOOGLE_SERVICE_JSON:
            creds_dict = json.loads(GOOGLE_SERVICE_JSON)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            # 本地运行则寻找 service_account.json 文件
            creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
            
        client = gspread.authorize(creds)
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.get_worksheet(0) # 写入第一个工作表

        # 准备数据：转换为列表，并处理空值
        df_filled = df.fillna("")
        data_to_append = df_filled.values.tolist()
        
        # 追加数据
        worksheet.append_rows(data_to_append)
        print(f"✅ 成功追加 {len(data_to_append)} 行数据到 Google Sheet")
    except Exception as e:
        print(f"❌ Google Sheet 同步失败: {e}")

def send_to_telegram(file_path, count):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    caption = (
        f"🐳 *Polymarket 大额交易监控*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 门槛: > ${MIN_BET_USD}\n"
        f"📊 笔数: {count}\n"
        f"📅 日期: {datetime.now().strftime('%Y-%m-%d')}\n"
        f"🔗 [查看 Google Sheet](https://docs.google.com/spreadsheets/d/{SHEET_ID})"
    )
    try:
        with open(file_path, 'rb') as f:
            payload = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "Markdown", "disable_web_page_preview": "true"}
            requests.post(url, data=payload, files={"document": f})
        os.remove(file_path)
    except Exception as e:
        print(f"❌ Telegram 发送错误: {e}")

def run_task():
    print(f"[{datetime.now()}] 启动任务...")
    params = {"limit": 100, "filterType": "CASH", "filterAmount": MIN_BET_USD, "takerOnly": "true"}

    try:
        response = requests.get(DATA_API_URL, params=params, timeout=15)
        trades = response.json()
        if not trades: return

        results = []
        for t in trades:
            amt = t.get('amount') or (float(t.get('price', 0)) * float(t.get('size', 0)))
            raw_ts = t.get('timestamp')
            try:
                ts_val = int(raw_ts)
                if ts_val > 10**11: ts_val /= 1000
                time_str = datetime.fromtimestamp(ts_val).strftime('%Y-%m-%d %H:%M:%S')
            except: time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            results.append({
                "bet_size": round(float(amt), 2),
                "username": get_username(t.get('proxyWallet')),
                "token_id": t.get('asset'),
                "token_outcome_name": t.get('outcome'),
                "market": t.get('title') or "Unknown Market",
                "timestamp": time_str
            })

        df = pd.DataFrame(results)
        df = df[["bet_size", "username", "token_id", "token_outcome_name", "market", "timestamp"]]

        # 1. 写入 Google Sheet
        update_google_sheet(df)

        # 2. 生成 CSV 并发送 Telegram
        filename = f"Whales_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        send_to_telegram(filename, len(results))

    except Exception as e:
        print(f"❌ 执行错误: {e}")

if __name__ == "__main__":
    run_task()
