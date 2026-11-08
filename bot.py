import subprocess
import sys

# تثبيت المكتبات تلقائياً
subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "yfinance", "pandas"])

import requests
import time
import yfinance as yf
import pandas as pd

TOKEN = "9206676062:AAH8_U0dY7UDCbJFQiNvoJ0p3EjmOf-ZzwI"
CHAT_ID = "-1003911614530"
CAPITAL = 1000
RISK_PERCENT = 1.0

open_trades = {}
daily_alerts_sent = {}

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def analyze_smc(df):
    if df is None or len(df) < 20:
        return None
    current_price = df['close'].iloc[-1]
    last_high = df['high'].tail(10).max()
    last_low = df['low'].tail(10).min()
    if current_price > last_high:
        direction = "UP"
    elif current_price < last_low:
        direction = "DOWN"
    else:
        direction = "SIDEWAYS"
    return {"price": current_price, "direction": direction, "high": last_high, "low": last_low}

def open_trade(symbol, name, price, direction):
    risk_usd = (CAPITAL * RISK_PERCENT) / 100
    distance = 10.0
    if direction == "UP":
        entry = price
        sl = entry - distance
        tp1 = entry + distance
        tp2 = entry + (distance * 2)
        tp3 = entry + (distance * 3)
        tp4 = entry + (distance * 4)
        trade_type = "BUY"
    elif direction == "DOWN":
        entry = price
        sl = entry + distance
        tp1 = entry - distance
        tp2 = entry - (distance * 2)
        tp3 = entry - (distance * 3)
        tp4 = entry - (distance * 4)
        trade_type = "SELL"
    else:
        return

    lot = risk_usd / abs(entry - sl)

    open_trades[symbol] = {
        'name': name, 'type': trade_type, 'entry': entry, 'sl': sl,
        'tp1': tp1, 'tp2': tp2, 'tp3': tp3, 'tp4': tp4, 'lot': lot
    }
    
    msg = f"🟢 *فتح صفقة {trade_type} (تجريبي)*\n"
    msg += f"{name} | سعر الدخول: `{entry:.2f}`\n"
    msg += f"🛑 وقف الخسارة: `{sl:.2f}` (10$)\n"
    msg += f"🎯 الهدف 1: `{tp1:.2f}` (10$)\n"
    msg += f"🎯 الهدف 2: `{tp2:.2f}` (20$)\n"
    msg += f"🎯 الهدف 3: `{tp3:.2f}` (30$)\n"
    msg += f"🎯 الهدف 4: `{tp4:.2f}` (40$)\n"
    msg += f"📦 اللوت: `{lot:.4f}`\n"
    send_telegram(msg)
    print(f"Opened {trade_type} for {name} at {entry:.2f}")

def manage_trades():
    for symbol, trade in list(open_trades.items()):
        try:
            if "USDT" in symbol:
                coin_id = symbol.replace("USDT", "").lower()
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
                data = requests.get(url).json()
                if coin_id in data:
                    price = data[coin_id]['usd']
                else:
                    continue
            else:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period="1d")
                if data.empty:
                    continue
                price = data['Close'].iloc[-1]

            if trade['type'] == 'BUY':
                if price >= trade['tp4']:
                    send_telegram(f"✅ *تم ضرب الهدف الرابع!* 🎯\n{trade['name']} | شراء\nالربح: +40$")
                    del open_trades[symbol]
                elif price >= trade['tp3']:
                    send_telegram(f"✅ *تم ضرب الهدف الثالث!* 🎯\n{trade['name']} | شراء\nالربح: +30$")
                    del open_trades[symbol]
                elif price >= trade['tp2']:
                    send_telegram(f"✅ *تم ضرب الهدف الثاني!* 🎯\n{trade['name']} | شراء\nالربح: +20$")
                    del open_trades[symbol]
                elif price >= trade['tp1']:
                    send_telegram(f"✅ *تم ضرب الهدف الأول!* 🎯\n{trade['name']} | شراء\nالربح: +10$")
                    del open_trades[symbol]
                elif price <= trade['sl']:
                    send_telegram(f"❌ *تم ضرب وقف الخسارة!* 🛑\n{trade['name']} | شراء\nالخسارة: -10$")
                    del open_trades[symbol]
            elif trade['type'] == 'SELL':
                if price <= trade['tp4']:
                    send_telegram(f"✅ *تم ضرب الهدف الرابع!* 🎯\n{trade['name']} | بيع\nالربح: +40$")
                    del open_trades[symbol]
                elif price <= trade['tp3']:
                    send_telegram(f"✅ *تم ضرب الهدف الثالث!* 🎯\n{trade['name']} | بيع\nالربح: +30$")
                    del open_trades[symbol]
                elif price <= trade['tp2']:
                    send_telegram(f"✅ *تم ضرب الهدف الثاني!* 🎯\n{trade['name']} | بيع\nالربح: +20$")
                    del open_trades[symbol]
                elif price <= trade['tp1']:
                    send_telegram(f"✅ *تم ضرب الهدف الأول!* 🎯\n{trade['name']} | بيع\nالربح: +10$")
                    del open_trades[symbol]
                elif price >= trade['sl']:
                    send_telegram(f"❌ *تم ضرب وقف الخسارة!* 🛑\n{trade['name']} | بيع\nالخسارة: -10$")
                    del open_trades[symbol]
        except Exception as e:
            print(f"Error managing {trade['name']}: {e}")

def check_asset(symbol, name, data_source, coin_id=None):
    try:
        df = None
        daily_high = None
        daily_low = None
        
        if data_source == "crypto":
            if not coin_id:
                coin_id = symbol.lower()
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency=usd&days=1"
            data = requests.get(url).json()
            if len(data) >= 20:
                df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close'])
                daily_high = df['high'].max()
                daily_low = df['low'].min()
        elif data_source == "yahoo":
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="5d", interval="1h")
            if not df.empty:
                df = df.rename(columns={'Close': 'close', 'High': 'high', 'Low': 'low'})
                daily_high = df['high'].max()
                daily_low = df['low'].min()
        
        if df is not None and len(df) >= 20:
            analysis = analyze_smc(df)
            if analysis:
                current_price = analysis['price']
                
                if daily_high and daily_low:
                    if current_price >= daily_high * 0.995:
                        alert_key = f"{symbol}_HIGH"
                        if alert_key not in daily_alerts_sent:
                            msg = f"🚨 *تنبيه: اقتراب من أعلى سعر اليوم*\n{name} | السعر: `{current_price:.2f}`\nأعلى سعر: `{daily_high:.2f}`"
                            send_telegram(msg)
                            daily_alerts_sent[alert_key] = True
                    elif current_price <= daily_low * 1.005:
                        alert_key = f"{symbol}_LOW"
                        if alert_key not in daily_alerts_sent:
                            msg = f"🚨 *تنبيه: اقتراب من أدنى سعر اليوم*\n{name} | السعر: `{current_price:.2f}`\nأدنى سعر: `{daily_low:.2f}`"
                            send_telegram(msg)
                            daily_alerts_sent[alert_key] = True

                if analysis['direction'] != "SIDEWAYS" and symbol not in open_trades:
                    open_trade(symbol, name, current_price, analysis['direction'])
                
                print(f"Checked {name} | {analysis['direction']}")
    except Exception as e:
        print(f"Error checking {name}: {e}")

print("🚀 بدأ تشغيل البوت الشامل...")

while True:
    try:
        print("--- دورة جديدة ---")
        
        check_asset("BTCUSDT", "Bitcoin", "crypto", "bitcoin")
        check_asset("ETHUSDT", "Ethereum", "crypto", "ethereum")
        check_asset("SOLUSDT", "Solana", "crypto", "solana")
        check_asset("BNBUSDT", "Binance Coin", "crypto", "binancecoin")
        check_asset("XRPUSDT", "XRP", "crypto", "ripple")
        check_asset("ADAUSDT", "Cardano", "crypto", "cardano")
        check_asset("DOGEUSDT", "Dogecoin", "crypto", "dogecoin")
        check_asset("AVAXUSDT", "Avalanche", "crypto", "avalanche-2")
        check_asset("DOTUSDT", "Polkadot", "crypto", "polkadot")
        check_asset("LINKUSDT", "Chainlink", "crypto", "chainlink")
        
        check_asset("EURUSD=X", "EUR/USD", "yahoo")
        check_asset("GBPUSD=X", "GBP/USD", "yahoo")
        check_asset("USDJPY=X", "USD/JPY", "yahoo")
        check_asset("USDCAD=X", "USD/CAD", "yahoo")
        check_asset("EURGBP=X", "EUR/GBP", "yahoo")
        
        check_asset("AAPL", "Apple", "yahoo")
        check_asset("TSLA", "Tesla", "yahoo")
        check_asset("^GSPC", "SPX500", "yahoo")
        check_asset("^NDX", "NDQ", "yahoo")
        
        manage_trades()
        
        print("✅ تمت الدورة. في انتظار 5 دقائق...")
        time.sleep(300)
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        time.sleep(60)
