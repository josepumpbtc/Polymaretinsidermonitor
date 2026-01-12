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

def get_user_profile(address):
    """获取显示名称和创建时间"""
    try:
        res = requests.get(f"{GAMMA_API_URL}/users?address={address}", timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data:
                user = data[0]
                # 调试：打印 API 返回的原始数据
                print(f"🔍 DEBUG - API 返回的用户数据: {user}")
                
                # 尝试多种可能的字段名
                created_at = user.get('createdAt') or user.get('created_at') or user.get('created')
                
                if created_at:
                    try:
                        # 处理不同的日期格式
                        if isinstance(created_at, (int, float)):
                            # 如果是时间戳
                            dt = datetime.fromtimestamp(created_at, tz=timezone.utc)
                        elif isinstance(created_at, str):
                            # 处理 ISO 格式字符串
                            if created_at.endswith('Z'):
                                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            else:
                                dt = datetime.fromisoformat(created_at)
                            # 如果没有时区信息，假设是 UTC
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                        else:
                            dt = None
                        print(f"✅ DEBUG - 解析的创建时间: {dt}")
                    except Exception as parse_error:
                        print(f"⚠️ DEBUG - 日期解析失败: {parse_error}, 原始值: {created_at}")
                        dt = None
                else:
                    print(f"⚠️ DEBUG - 未找到创建时间字段，可用字段: {list(user.keys())}")
                    dt = None
                
                return {"name": user.get('displayName') or address, "created_at": dt}
            else:
                print(f"⚠️ DEBUG - API 返回空数据")
        else:
            print(f"⚠️ DEBUG - API 请求失败，状态码: {res.status_code}, 响应: {res.text[:200]}")
    except Exception as e:
        print(f"❌ 获取 Profile 失败 ({address}): {e}")
        import traceback
        traceback.print_exc()
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
    print(f"🌐 API URL: {GAMMA_API_URL}/users?address={address}\n")
    
    # 测试 API 请求
    try:
        res = requests.get(f"{GAMMA_API_URL}/users?address={address}", timeout=10)
        
        print(f"📊 HTTP 状态码: {res.status_code}")
        print(f"📋 响应头: {dict(res.headers)}\n")
        
        if res.status_code == 200:
            data = res.json()
            print(f"📦 响应数据类型: {type(data)}")
            print(f"📏 响应数据长度: {len(data) if isinstance(data, (list, dict)) else 'N/A'}\n")
            
            if data:
                if isinstance(data, list) and len(data) > 0:
                    user = data[0]
                    print("=" * 60)
                    print("📄 用户数据详情:")
                    print("=" * 60)
                    print(json.dumps(user, indent=2, ensure_ascii=False, default=str))
                    print("=" * 60)
                    
                    print("\n🔑 所有可用字段:")
                    for key, value in user.items():
                        value_str = str(value)
                        if len(value_str) > 100:
                            value_str = value_str[:100] + "..."
                        print(f"  - {key}: {value_str}")
                    
                    print("\n" + "=" * 60)
                    print("🔍 查找创建时间相关字段:")
                    print("=" * 60)
                    
                    # 查找所有可能包含时间的字段
                    time_fields = []
                    for key, value in user.items():
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
                    print(f"⚠️ 响应数据格式异常: {type(data)}")
            else:
                print("⚠️ API 返回空数据")
        else:
            print(f"❌ API 请求失败")
            print(f"响应内容: {res.text[:500]}")
            
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
