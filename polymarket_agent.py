import requests
import pandas as pd
from datetime import datetime, timedelta
import os

# --- 配置区 ---
# 建议在本地终端运行: export TELEGRAM_TOKEN="你的TOKEN"
# 或者直接在这里填入你的 Token (注意不要泄露给他人)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8289795345:AAGwY_sVtvsZBC2VEazZG3Wl1hh9ltAEqo4")
CHAT_ID = "@polyinsidermonitor" 
MIN_BET_SIZE = 1000

# API 节点
SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets-v2"
GAMMA_API_URL = "https://gamma-api.polymarket.com/users?address="

def get_username(address):
    """查询 Polymarket 用户名"""
    try:
        response = requests.get(f"{GAMMA_API_URL}{address}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data:
                return data[0].get('displayName') or data[0].get('username') or address
    except:
        pass
    return address

def run_task():
    print(f"开始抓取数据 - 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 获取过去 24 小时的时间戳
    yesterday = datetime.now() - timedelta(days=1)
    timestamp_cutoff = int(yesterday.timestamp())

    # GraphQL 查询
    query = """
    {
      fpmmTrades(
        where: {
          timestamp_gt: "%s",
          fpmm_In: true, 
          tradeAmount_gt: "3000000000"
        }
        orderBy: timestamp
        orderDirection: desc
      ) {
        timestamp
        creator { id }
        tradeAmount
        outcomeIndex
        fpmm {
          id
          outcomes
          market { question }
        }
      }
    }
    """ % timestamp_cutoff

    try:
        response = requests.post(SUBGRAPH_URL, json={'query': query})
        data = response.json().get('data', {}).get('fpmmTrades', [])
        
        if not data:
            msg = "📢 过去 24 小时未发现超过 $3000 的交易。"
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          data={"chat_id": CHAT_ID, "text": msg})
            print(msg)
            return

        results = []
        for trade in data:
            addr = trade['creator']['id']
            outcomes = trade['fpmm']['outcomes']
            idx = int(trade['outcomeIndex'])
            results.append({
                "bet_size": round(float(trade['tradeAmount']) / 1e6, 2),
                "username": get_username(addr),
                "token_id": f"{trade['fpmm']['id']}-{idx}",
                "token_outcome_name": outcomes[idx] if outcomes else f"Index {idx}",
                "market": trade['fpmm']['market']['question'],
                "time_utc": datetime.fromtimestamp(int(trade['timestamp'])).strftime('%Y-%m-%d %H:%M')
            })

        # 生成 CSV
        df = pd.DataFrame(results)
        filename = f"Polymarket_Whales_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')

        # 发送到 Telegram
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
        caption = f"📊 Polymarket 每日大额交易报告 (>{MIN_BET_SIZE} USD)\n共计: {len(results)} 笔"
        
        with open(filename, 'rb') as f:
            r = requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"document": f})
        
        if r.status_code == 200:
            print(f"成功！文件 {filename} 已发送至频道。")
        else:
            print(f"发送失败: {r.text}")

    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    run_task()
