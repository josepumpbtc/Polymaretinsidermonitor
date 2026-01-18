import requests
import pandas as pd
from datetime import datetime, timezone
import os
import time
import json

# --- 配置区 ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = "@polyinsidermonitor" # 确保这是公开频道，或者使用数字 ID
MIN_BET_USD = 3000  

DATA_API_URL = "https://data-api.polymarket.com"
GAMMA_API_URL = "https://gamma-api.polymarket.com"

def parse_timestamp(time_str):
    """解析时间戳，支持多种格式"""
    if not time_str:
        return None
    
    try:
        if isinstance(time_str, (int, float)):
            # 如果是时间戳（秒或毫秒）
            if time_str > 1e10:  # 毫秒时间戳
                return datetime.fromtimestamp(time_str / 1000, tz=timezone.utc)
            else:  # 秒时间戳
                return datetime.fromtimestamp(time_str, tz=timezone.utc)
        elif isinstance(time_str, str):
            # 处理 ISO 格式字符串
            if time_str.endswith('Z'):
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(time_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
    except Exception as e:
        print(f"⚠️ DEBUG - 时间解析失败: {e}, 原始值: {time_str}")
    return None

def get_user_profile(address):
    """获取显示名称和创建时间（通过第一笔交易时间估算）"""
    # 由于 Gamma API 需要认证，改用 data-api 获取用户的第一笔交易时间
    try:
        # 方法1: 尝试从用户活动数据中获取第一笔交易时间
        res = requests.get(f"{DATA_API_URL}/activity?user={address}&limit=1000", timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data and len(data) > 0:
                # 找出最早的一笔交易（按时间戳排序）
                earliest_trade = None
                earliest_time = None
                
                for trade in data:
                    # 尝试多种可能的时间字段
                    time_str = (trade.get('timestamp') or 
                               trade.get('time') or 
                               trade.get('createdAt') or
                               trade.get('created_at') or
                               trade.get('date') or
                               trade.get('blockTimestamp'))
                    
                    if time_str:
                        dt = parse_timestamp(time_str)
                        if dt:
                            if earliest_time is None or dt < earliest_time:
                                earliest_time = dt
                                earliest_trade = trade
                
                if earliest_trade and earliest_time:
                    print(f"✅ DEBUG - 找到最早交易时间: {earliest_time}")
                    
                    # 尝试从交易数据中获取用户名（如果有）
                    display_name = (earliest_trade.get('user') or 
                                   earliest_trade.get('username') or 
                                   earliest_trade.get('displayName') or 
                                   address)
                    
                    return {"name": display_name, "created_at": earliest_time}
        
        # 方法2: 如果 activity API 没有返回数据，尝试从 trades API 获取
        print(f"⚠️ DEBUG - activity API 无数据，尝试从 trades API 获取...")
        res2 = requests.get(f"{DATA_API_URL}/trades?user={address}&limit=1000", timeout=10)
        if res2.status_code == 200:
            trades = res2.json()
            if trades and len(trades) > 0:
                # 找出最早的一笔交易
                earliest_trade = None
                earliest_time = None
                
                for trade in trades:
                    time_str = (trade.get('timestamp') or 
                               trade.get('time') or 
                               trade.get('createdAt') or
                               trade.get('created_at') or
                               trade.get('blockTimestamp'))
                    
                    if time_str:
                        dt = parse_timestamp(time_str)
                        if dt:
                            if earliest_time is None or dt < earliest_time:
                                earliest_time = dt
                                earliest_trade = trade
                
                if earliest_time:
                    print(f"✅ DEBUG - 从第一笔交易获取创建时间: {earliest_time}")
                    return {"name": address, "created_at": earliest_time}
        
    except Exception as e:
        print(f"⚠️ 获取用户 Profile 失败 ({address}): {e}")
        import traceback
        traceback.print_exc()
    
    # 如果所有方法都失败，返回默认值
    print(f"⚠️ DEBUG - 无法获取账号创建时间，使用默认值")
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

def test_user_profile(address=None):
    """测试函数：验证用户 Profile API 响应"""
    print("=" * 60)
    print("🧪 开始测试用户 Profile API")
    print("=" * 60)
    
    # 如果没有提供地址，从实际交易中获取一个
    if not address:
        print("\n📥 从实际交易中获取测试地址...")
        try:
            params = {"limit": 1, "filterType": "CASH", "filterAmount": MIN_BET_USD, "takerOnly": "true"}
            response = requests.get(f"{DATA_API_URL}/trades", params=params, timeout=15)
            trades = response.json()
            if trades and len(trades) > 0:
                address = trades[0].get('proxyWallet')
                print(f"✅ 找到测试地址: {address}")
            else:
                # 使用一个示例地址（从图片中看到的地址）
                address = "0x075ed056bac4e1b9f123a98983268ab891a81521"
                print(f"⚠️ 未找到交易，使用示例地址: {address}")
        except Exception as e:
            print(f"❌ 获取交易失败: {e}")
            address = "0x075ed056bac4e1b9f123a98983268ab891a81521"
            print(f"使用示例地址: {address}")
    
    print(f"\n🔍 测试地址: {address}")
    print(f"🌐 测试 Data API: {DATA_API_URL}/activity?user={address}\n")
    
    # 测试 Data API 请求（因为 Gamma API 需要认证）
    try:
        print("=" * 60)
        print("📡 测试 Data API - Activity 端点")
        print("=" * 60)
        res = requests.get(f"{DATA_API_URL}/activity?user={address}&limit=10&sort=asc", timeout=10)
        
        print(f"📊 HTTP 状态码: {res.status_code}")
        print(f"📋 响应头: {dict(res.headers)}\n")
        
        if res.status_code == 200:
            data = res.json()
            print(f"📦 响应数据类型: {type(data)}")
            print(f"📏 响应数据长度: {len(data) if isinstance(data, (list, dict)) else 'N/A'}\n")
            
            if data and isinstance(data, list) and len(data) > 0:
                first_activity = data[0]
                print("=" * 60)
                print("📄 第一笔活动数据详情:")
                print("=" * 60)
                print(json.dumps(first_activity, indent=2, ensure_ascii=False, default=str))
                print("=" * 60)
                
                print("\n🔑 所有可用字段:")
                for key, value in first_activity.items():
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:100] + "..."
                    print(f"  - {key}: {value_str}")
                
                print("\n" + "=" * 60)
                print("🔍 查找时间相关字段:")
                print("=" * 60)
                
                # 查找所有可能包含时间的字段
                time_fields = []
                for key, value in first_activity.items():
                    key_lower = key.lower()
                    if any(keyword in key_lower for keyword in ['time', 'date', 'create', 'join', 'register']):
                        time_fields.append((key, value))
                
                if time_fields:
                    for field_name, field_value in time_fields:
                        print(f"\n  ✅ 找到时间相关字段: {field_name}")
                        print(f"     类型: {type(field_value)}")
                        print(f"     值: {field_value}")
                else:
                    print("  ⚠️ 未找到任何时间相关字段")
                
                # 测试解析
                print("\n" + "=" * 60)
                print("🧪 测试解析函数:")
                print("=" * 60)
                profile = get_user_profile(address)
                print(f"\n📊 解析结果:")
                print(f"  名称: {profile['name']}")
                print(f"  创建时间: {profile['created_at']}")
                if profile['created_at']:
                    days = (datetime.now(timezone.utc) - profile['created_at']).days
                    print(f"  账号年龄: {days} 天")
                else:
                    print(f"  账号年龄: 未知")
                    
            elif isinstance(data, dict):
                print("📄 响应是字典格式:")
                print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
            else:
                print("⚠️ API 返回空数据或无活动记录")
        else:
            print(f"❌ Activity API 请求失败")
            print(f"响应内容: {res.text[:500]}")
        
        # 如果 activity API 没有数据，尝试 trades API
        if res.status_code != 200 or not data or len(data) == 0:
            print("\n" + "=" * 60)
            print("📡 测试 Data API - Trades 端点")
            print("=" * 60)
            res2 = requests.get(f"{DATA_API_URL}/trades?user={address}&limit=10&sort=asc", timeout=10)
            print(f"📊 HTTP 状态码: {res2.status_code}")
            
            if res2.status_code == 200:
                trades = res2.json()
                if trades and len(trades) > 0:
                    first_trade = trades[0]
                    print(f"📏 找到 {len(trades)} 笔交易")
                    print("\n📄 第一笔交易数据:")
                    print(json.dumps(first_trade, indent=2, ensure_ascii=False, default=str))
                    
                    # 查找时间字段
                    print("\n🔍 查找时间相关字段:")
                    for key, value in first_trade.items():
                        key_lower = key.lower()
                        if any(keyword in key_lower for keyword in ['time', 'date', 'create']):
                            print(f"  ✅ {key}: {value} (类型: {type(value)})")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)

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

        # 建议修改 run_task 中的金额提取部分
        for t in trades:
            # 兼容性修复：依次尝试不同的金额字段
            raw_amt = t.get('usdcSize') or t.get('amount') or t.get('cash')
            if raw_amt is None:
                # 如果是订单簿撮合，尝试 price * size
                try:
                    raw_amt = float(t.get('price', 0)) * float(t.get('size', 0))
                except:
                    raw_amt = 0
                    
            amt = float(raw_amt)
            print(f"检查交易: 用户 {t.get('proxyWallet')[:10]}... 金额: ${amt}") # 调试日志
            
            if amt < MIN_BET_USD:
                continue
            # ... 后续逻辑 ...
            
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
    import sys
    # 如果命令行参数包含 "test"，则运行测试函数
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_address = sys.argv[2] if len(sys.argv) > 2 else None
        test_user_profile(test_address)
    else:
        run_task()
