import os
import time
import json
import requests
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
import http.server
import socketserver
import threading

# ==========================================
# CONFIGURAÇÕES DO TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "8630684870:AAHc6IdnwB4EiVs18oC_5NqREltWS-N1w88"
TELEGRAM_CHAT_ID = "1402944096"
STATE_FILE = "v14_paper_state.json"

def send_telegram(message):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception:
            pass

# ==========================================
# GESTÃO DE ESTADO (PERSISTÊNCIA DA BANCA)
# ==========================================
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                # Garante que a trava temporal exista se for um arquivo antigo
                if "last_candle" not in state:
                    state["last_candle"] = {"BTC/USDT": None, "ETH/USDT": None, "SOL/USDT": None}
                return state
        except Exception:
            pass
    return {
        "paper_capital": 1000.0,
        "positions": {"BTC/USDT": None, "ETH/USDT": None, "SOL/USDT": None},
        "last_candle": {"BTC/USDT": None, "ETH/USDT": None, "SOL/USDT": None}
    }

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        print(f"Erro ao salvar estado: {e}", flush=True)

# ==========================================
# DUMMY SERVER PARA UPTIMEROBOT (24/7)
# ==========================================
class SimpleHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot V14 Live and Running 24/7!")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    with socketserver.TCPServer(("", port), SimpleHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# ==========================================
# INICIALIZAÇÃO E EXCHANGE
# ==========================================
print("==================================================", flush=True)
print("   INICIANDO BOT V14 FIDEDIGNO (BINANCE 24/7)", flush=True)
print("==================================================", flush=True)

state = load_state()
exchange = ccxt.binance({'enableRateLimit': True})
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
fee = 0.001

send_telegram(f"🚀 <b>BOT QUANTITATIVO V14 ATIVO NO RENDER</b>\n\n• <b>Estratégia:</b> Double Pyramid + Climax Exit\n• <b>Banca Simulada:</b> ${state['paper_capital']:.2f} USDT\n• <b>Modo:</b> Paper Trading 24/7 (Binance API)")

def fetch_data(symbol, timeframe, limit=300):
    candles = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def process_signals():
    global state
    paper_capital = state["paper_capital"]
    positions = state["positions"]
    
    for symbol in symbols:
        try:
            df4 = fetch_data(symbol, '4h', limit=250)
            df1 = fetch_data(symbol, '1h', limit=200)
            
            df4['ema21'] = df4['close'].ewm(span=21, adjust=False).mean()
            df4['ema50'] = df4['close'].ewm(span=50, adjust=False).mean()
            df4['ema200'] = df4['close'].ewm(span=200, adjust=False).mean()
            df4['vol_sma20'] = df4['volume'].rolling(window=20).mean()
            
            df1['ema21'] = df1['close'].ewm(span=21, adjust=False).mean()
            hl = df1['high'] - df1['low']
            hc = np.abs(df1['high'] - df1['close'].shift())
            lc = np.abs(df1['low'] - df1['close'].shift())
            tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
            df1['atr'] = tr.rolling(window=14).mean()
            
            # --- LOG VISUAL: Usa o candle em tempo real (-1) para o Log ficar se mexendo ---
            live_price = df1['close'].iloc[-1]
            live_ema21_4h = df4['ema21'].iloc[-1]
            live_ema50_4h = df4['ema50'].iloc[-1]
            live_ema200_4h = df4['ema200'].iloc[-1]
            live_atr = df1['atr'].iloc[-1]
            
            now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            print(f"[{now_str}] {symbol} | Preço Atual: ${live_price:.2f} | EMA21_4h: ${live_ema21_4h:.2f} | EMA50_4h: ${live_ema50_4h:.2f} | EMA200_4h: ${live_ema200_4h:.2f} | ATR_1h: ${live_atr:.2f}", flush=True)

            # --- TRAVA TEMPORAL: O robô só executa uma vez por hora ---
            candle_fechado_time = str(df1.index[-2])
            if state["last_candle"].get(symbol) == candle_fechado_time:
                continue # Se a hora ainda não virou, encerra aqui e espera o próximo minuto
            
            # Se passou pela trava, atualiza o registro da hora processada
            state["last_candle"][symbol] = candle_fechado_time
            save_state(state)

            # --- DADOS PARA A ESTRATÉGIA: Usa estritamente o último candle 100% fechado (-2) ---
            price = df1['close'].iloc[-2]
            high = df1['high'].iloc[-2]
            low = df1['low'].iloc[-2]
            ema21_1h = df1['ema21'].iloc[-2]
            atr1h = df1['atr'].iloc[-2]
            
            ema21_4h = df4['ema21'].iloc[-2]
            ema50_4h = df4['ema50'].iloc[-2]
            ema200_4h = df4['ema200'].iloc[-2]
            vol_4h = df4['volume'].iloc[-2]
            vol_sma_4h = df4['vol_sma20'].iloc[-2]
            
            pos = positions[symbol]
            alloc_pct = 0.35
            
            # 1. ENTRADA LONG
            if pos is None:
                if ema21_4h > ema50_4h > ema200_4h and low <= ema21_1h and price > ema21_1h:
                    alloc = paper_capital * alloc_pct * (1 - fee)
                    units = alloc / price
                    positions[symbol] = {
                        'side': 'LONG', 'entry_price': price, 'units': units,
                        'stop_loss': price - (3.0 * atr1h), 'highest_price': price,
                        'pyramid_count': 0, 'alloc': alloc
                    }
                    paper_capital -= alloc
                    state["paper_capital"] = paper_capital
                    state["positions"] = positions
                    save_state(state)
                    
                    print(f"\n==================================================\n [ORDEM LONG EXECUTADA] {symbol} @ ${price:.2f}\n==================================================", flush=True)
                    
                    msg = (f"🟢 <b>[ORDEM LONG EXECUTADA]</b>\n\n"
                           f"• <b>Ativo:</b> {symbol}\n"
                           f"• <b>Preço:</b> ${price:.2f}\n"
                           f"• <b>Valor Usado:</b> ${alloc:.2f}\n"
                           f"• <b>Stop Loss:</b> ${positions[symbol]['stop_loss']:.2f}\n"
                           f"• <b>Banca Livre:</b> ${paper_capital:.2f}")
                    send_telegram(msg)

            # 2. ENTRADA SHORT
            elif pos is None:
                if ema21_4h < ema50_4h < ema200_4h and high >= ema21_1h and price < ema21_1h:
                    alloc = paper_capital * alloc_pct * (1 - fee)
                    units = alloc / price
                    positions[symbol] = {
                        'side': 'SHORT', 'entry_price': price, 'units': units,
                        'stop_loss': price + (3.0 * atr1h), 'lowest_price': price,
                        'pyramid_count': 0, 'alloc': alloc
                    }
                    paper_capital -= alloc
                    state["paper_capital"] = paper_capital
                    state["positions"] = positions
                    save_state(state)
                    
                    print(f"\n==================================================\n [ORDEM SHORT EXECUTADA] {symbol} @ ${price:.2f}\n==================================================", flush=True)
                    
                    msg = (f"🔴 <b>[ORDEM SHORT EXECUTADA]</b>\n\n"
                           f"• <b>Ativo:</b> {symbol}\n"
                           f"• <b>Preço:</b> ${price:.2f}\n"
                           f"• <b>Valor Usado:</b> ${alloc:.2f}\n"
                           f"• <b>Stop Loss:</b> ${positions[symbol]['stop_loss']:.2f}\n"
                           f"• <b>Banca Livre:</b> ${paper_capital:.2f}")
                    send_telegram(msg)
                    
            # 3. GESTÃO E PIRAMIDAGEM
            elif pos is not None:
                side = pos['side']
                entry = pos['entry_price']
                units = pos['units']
                is_climax = vol_4h > (3.5 * vol_sma_4h)
                
                if side == 'LONG':
                    if high > pos['highest_price']: pos['highest_price'] = high
                    
                    # Piramidagem 1
                    if pos['pyramid_count'] == 0 and price >= entry + (2.8 * atr1h) and ema21_4h > ema50_4h:
                        unrealized = (units * price) - (units * entry)
                        if unrealized > 0:
                            add_units = (unrealized * 0.8) / price
                            pos['units'] += add_units
                            pos['entry_price'] = (entry + price) / 2
                            pos['pyramid_count'] = 1
                            state["positions"] = positions
                            save_state(state)
                            print(f"\n==================================================\n [PIRAMIDAGEM 1 LONG] {symbol} @ ${price:.2f}\n==================================================", flush=True)
                            send_telegram(f"⬆️ <b>[PIRAMIDAGEM 1 LONG]</b> {symbol} | Preço: ${price:.2f}")
                            
                    # Piramidagem 2
                    elif pos['pyramid_count'] == 1 and price >= entry + (5.0 * atr1h) and ema21_4h > ema50_4h:
                        unrealized = (units * price) - (units * entry)
                        if unrealized > 0:
                            add_units = (unrealized * 0.6) / price
                            pos['units'] += add_units
                            pos['pyramid_count'] = 2
                            state["positions"] = positions
                            save_state(state)
                            print(f"\n==================================================\n [PIRAMIDAGEM 2 LONG] {symbol} @ ${price:.2f}\n==================================================", flush=True)
                            send_telegram(f"⬆️⬆️ <b>[PIRAMIDAGEM 2 LONG]</b> {symbol} | Preço: ${price:.2f}")

                    # Saída LONG
                    if low <= pos['stop_loss'] or ema21_4h < ema50_4h or is_climax:
                        exit_price = pos['stop_loss'] if low <= pos['stop_loss'] else price
                        returned = (pos['units'] * exit_price) * (1 - fee)
                        paper_capital += returned
                        pnl = returned - pos['alloc']
                        reason = "Clímax de Volume" if is_climax else ("Stop Loss" if low <= pos['stop_loss'] else "Tendência Revertida")
                        
                        positions[symbol] = None
                        state["paper_capital"] = paper_capital
                        state["positions"] = positions
                        save_state(state)
                        
                        print(f"\n==================================================\n [FECHAMENTO LONG] {symbol} | PnL: ${pnl:+.2f}\n==================================================", flush=True)
                        send_telegram(f"💰 <b>[FECHAMENTO LONG]</b> {symbol}\n• <b>Motivo:</b> {reason}\n• <b>PnL:</b> ${pnl:+.2f}\n• <b>Novo Saldo:</b> ${paper_capital:.2f}")
                        
                elif side == 'SHORT':
                    if low < pos['lowest_price']: pos['lowest_price'] = low
                    
                    # Piramidagem 1
                    if pos['pyramid_count'] == 0 and price <= entry - (2.8 * atr1h) and ema21_4h < ema50_4h:
                        unrealized = (units * entry) - (units * price)
                        if unrealized > 0:
                            add_units = (unrealized * 0.8) / price
                            pos['units'] += add_units
                            pos['entry_price'] = (entry + price) / 2
                            pos['pyramid_count'] = 1
                            state["positions"] = positions
                            save_state(state)
                            print(f"\n==================================================\n [PIRAMIDAGEM 1 SHORT] {symbol} @ ${price:.2f}\n==================================================", flush=True)
                            send_telegram(f"⬇️ <b>[PIRAMIDAGEM 1 SHORT]</b> {symbol} | Preço: ${price:.2f}")
                            
                    # Piramidagem 2
                    elif pos['pyramid_count'] == 1 and price <= entry - (5.0 * atr1h) and ema21_4h < ema50_4h:
                        unrealized = (units * entry) - (units * price)
                        if unrealized > 0:
                            add_units = (unrealized * 0.6) / price
                            pos['units'] += add_units
                            pos['pyramid_count'] = 2
                            state["positions"] = positions
                            save_state(state)
                            print(f"\n==================================================\n [PIRAMIDAGEM 2 SHORT] {symbol} @ ${price:.2f}\n==================================================", flush=True)
                            send_telegram(f"⬇️⬇️ <b>[PIRAMIDAGEM 2 SHORT]</b> {symbol} | Preço: ${price:.2f}")

                    # Saída SHORT
                    if high >= pos['stop_loss'] or ema21_4h > ema50_4h or is_climax:
                        exit_price = pos['stop_loss'] if high >= pos['stop_loss'] else price
                        diff = entry - exit_price
                        returned = (pos['alloc'] + (pos['units'] * diff)) * (1 - fee)
                        paper_capital += returned
                        pnl = returned - pos['alloc']
                        reason = "Clímax de Volume" if is_climax else ("Stop Loss" if high >= pos['stop_loss'] else "Tendência Revertida")
                        
                        positions[symbol] = None
                        state["paper_capital"] = paper_capital
                        state["positions"] = positions
                        save_state(state)
                        
                        print(f"\n==================================================\n [FECHAMENTO SHORT] {symbol} | PnL: ${pnl:+.2f}\n==================================================", flush=True)
                        send_telegram(f"💰 <b>[FECHAMENTO SHORT]</b> {symbol}\n• <b>Motivo:</b> {reason}\n• <b>PnL:</b> ${pnl:+.2f}\n• <b>Novo Saldo:</b> ${paper_capital:.2f}")
                        
        except Exception as e:
            print(f"Erro em {symbol}: {e}", flush=True)

# Loop principal (Monitoramento contínuo minuto a minuto)
while True:
    process_signals()
    time.sleep(60)
