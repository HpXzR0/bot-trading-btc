import os
import http.server
import socketserver
import threading
import ccxt
import pandas as pd
import time
import json
import requests
from datetime import datetime

# ==========================================
# CONFIGURAÇÕES DO TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "8630684870:AAHc6IdnwB4EiVs18oC_5NqREltWS-N1w88"
TELEGRAM_CHAT_ID = "1402944096"

def send_telegram_message(message):
    """Envia uma mensagem de notificação para o Telegram."""
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            }
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"Erro ao enviar mensagem no Telegram: {e}", flush=True)

# ==========================================
# SERVIDOR HTTP DUMMY PARA O RENDER
# ==========================================
class SimpleHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot de Trading BTC rodando 24/7!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = socketserver.TCPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# ==========================================
# CONFIGURAÇÃO DA EXCHANGE E INDICADORES
# ==========================================
exchange = ccxt.kucoin({'enableRateLimit': True})
symbol = 'BTC/USDT'
timeframe = '1h'
short_window = 9
long_window = 21
macro_window = 200
rsi_period = 14

STATE_FILE = 'estado_bot.json'

def load_state():
    default_state = {'position': None, 'usdt': 1000.0, 'btc': 0.0}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                default_state.update(data)
        except Exception:
            pass
    return default_state

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

state = load_state()

print("=== BOT DE TRADING QUANTITATIVO ATIVO | BTC/USDT (1h) ===", flush=True)
print("Estratégia: EMA9 x EMA21 + Filtro Macro (EMA200) + RSI", flush=True)
print(f"Saldo Carregado: ${state['usdt']:.2f} USDT | {state['btc']:.5f} BTC\n", flush=True)

# Envia mensagem inicial no Telegram confirmando que o bot iniciou
send_telegram_message(f"🚀 *Bot de Trading Iniciado!*\nPar: {symbol}\nEstratégia: EMA9 x EMA21 + EMA200 + RSI")

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ==========================================
# LOOP PRINCIPAL
# ==========================================
while True:
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=250)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        df['ema_short'] = df['close'].ewm(span=short_window, adjust=False).mean()
        df['ema_long'] = df['close'].ewm(span=long_window, adjust=False).mean()
        df['ema_macro'] = df['close'].ewm(span=macro_window, adjust=False).mean()
        df['rsi'] = calculate_rsi(df['close'], period=rsi_period)

        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        price = last_row['close']
        ema_s = last_row['ema_short']
        ema_l = last_row['ema_long']
        ema_m = last_row['ema_macro']
        rsi = last_row['rsi']

        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print(f"[{now}] BTC: ${price:.2f} | EMA9: ${ema_s:.2f} | EMA21: ${ema_l:.2f} | EMA200: ${ema_m:.2f} | RSI: {rsi:.1f}", flush=True)

        # Condição de Compra
        if prev_row['ema_short'] <= prev_row['ema_long'] and ema_s > ema_l:
            if price > ema_m and rsi < 70:
                if state['position'] != 'BUY':
                    msg = f"🟢 *SINAL DE COMPRA DETECTADO!*\nPreço: ${price:.2f}\nEMA9 superou EMA21 acima da EMA200 (RSI: {rsi:.1f})"
                    print(msg, flush=True)
                    send_telegram_message(msg)
                    state['position'] = 'BUY'
                    save_state(state)

        # Condição de Venda
        elif prev_row['ema_short'] >= prev_row['ema_long'] and ema_s < ema_l:
            if state['position'] != 'SELL':
                msg = f"🔴 *SINAL DE VENDA DETECTADO!*\nPreço: ${price:.2f}\nEMA9 cruzou abaixo da EMA21 (RSI: {rsi:.1f})"
                print(msg, flush=True)
                send_telegram_message(msg)
                state['position'] = 'SELL'
                save_state(state)

    except Exception as e:
        print(f"Erro na execução: {e}", flush=True)

    time.sleep(60)
