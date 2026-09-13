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
        self.wfile.write(b"Bot de TESTE no Telegram rodando!")

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
# CONFIGURAÇÃO DE TESTE (1 MINUTO)
# ==========================================
exchange = ccxt.kucoin({'enableRateLimit': True})
symbol = 'BTC/USDT'
timeframe = '1m'  # Muda para 1 minuto para alta frequência

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

print("=== MODO DE TESTE DE NOTIFICAÇÕES (ALTA FREQUÊNCIA) ===", flush=True)
send_telegram_message("🧪 *MODO DE TESTE ATIVADO*\nO bot enviará ordens frequentes a cada variação do candle de 1m.")

# ==========================================
# LOOP PRINCIPAL DE TESTE (CHECAGEM A CADA 15 SEG)
# ==========================================
while True:
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=5)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        last_row = df.iloc[-1]
        open_price = last_row['open']
        close_price = last_row['close']

        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print(f"[{now}] TESTE 1m - Abertura: ${open_price:.2f} | Atual: ${close_price:.2f}", flush=True)

        # SE O CANDLE ATUAL ESTIVER VERDE (COMPRA)
        if close_price > open_price:
            if state['position'] != 'BUY':
                msg = f"🟢 *[TESTE] SINAL DE COMPRA!*\nPreço: ${close_price:.2f}\n(Candle de 1m fechando em alta)"
                print(msg, flush=True)
                send_telegram_message(msg)
                state['position'] = 'BUY'
                save_state(state)

        # SE O CANDLE ATUAL ESTIVER VERMELHO (VENDA)
        elif close_price < open_price:
            if state['position'] != 'SELL':
                msg = f"🔴 *[TESTE] SINAL DE VENDA!*\nPreço: ${close_price:.2f}\n(Candle de 1m fechando em baixa)"
                print(msg, flush=True)
                send_telegram_message(msg)
                state['position'] = 'SELL'
                save_state(state)

    except Exception as e:
        print(f"Erro no teste: {e}", flush=True)

    time.sleep(15)  # Checa a cada 15 segundos
