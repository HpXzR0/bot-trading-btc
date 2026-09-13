import os
import time
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

def send_telegram(message):
    """Envia mensagens formatadas para o seu Telegram."""
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"Erro ao enviar Telegram: {e}", flush=True)

# ==========================================
# DUMMY SERVER PARA MANTER O RENDER ALIVE
# ==========================================
class SimpleHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot V14 Live and Running!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    with socketserver.TCPServer(("", port), SimpleHandler) as httpd:
        print(f"Servidor Web ativo na porta {port}", flush=True)
        httpd.serve_forever()

# Inicia o servidor web em segundo plano
threading.Thread(target=run_dummy_server, daemon=True).start()

# ==========================================
# MOTOR ESTRATÉGICO V14 (PAPER TRADING)
# ==========================================
print("==================================================", flush=True)
print("   INICIANDO BOT V14 (PAPER TRADING + TELEGRAM)   ", flush=True)
print("==================================================", flush=True)

send_telegram("🚀 <b>BOT QUANTITATIVO V14 INICIALIZADO NO RENDER</b>\n\n- <b>Estratégia:</b> Double Pyramid + Climax Exit\n- <b>Ativos:</b> BTC, ETH, SOL\n- <b>Banca Simulada:</b> $1.000,00 USDT\n- <b>Modo:</b> Paper Trading 24/7")

exchange = ccxt.kraken({'enableRateLimit': True})
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']

paper_capital = 1000.0
fee = 0.001
positions = {s: None for s in symbols}

def fetch_data(symbol, timeframe, limit=300):
    candles = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def process_signals():
    global paper_capital
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now_str}] Checando sinais no mercado...", flush=True)
    
    for symbol in symbols:
        try:
            df4 = fetch_data(symbol, '4h', limit=250)
            df1 = fetch_data(symbol, '1h', limit=50)
            
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
            
            price = df1['close'].iloc[-1]
            high = df1['high'].iloc[-1]
            low = df1['low'].iloc[-1]
            ema21_1h = df1['ema21'].iloc[-1]
            atr1h = df1['atr'].iloc[-1]
            
            ema21_4h = df4['ema21'].iloc[-1]
            ema50_4h = df4['ema50'].iloc[-1]
            ema200_4h = df4['ema200'].iloc[-1]
            vol_4h = df4['volume'].iloc[-1]
            vol_sma_4h = df4['vol_sma20'].iloc[-1]
            
            pos = positions[symbol]
            alloc_pct = 0.35
            
            # 1. ENTRADA LONG
            if pos is None and (ema21_4h > ema50_4h > ema200_4h) and (low <= ema21_1h and price > ema21_1h):
                alloc = paper_capital * alloc_pct * (1 - fee)
                units = alloc / price
                positions[symbol] = {
                    'side': 'LONG', 'entry_price': price, 'units': units,
                    'stop_loss': price - (3.0 * atr1h), 'highest_price': price,
                    'pyramid_count': 0, 'alloc': alloc
                }
                paper_capital -= alloc
                
                msg = (f"🚀 <b>[V14 - COMPRA LONG]</b>\n\n"
                       f"• <b>Ativo:</b> {symbol}\n"
                       f"• <b>Preço de Entrada:</b> ${price:.2f}\n"
                       f"• <b>Alocação:</b> ${alloc:.2f}\n"
                       f"• <b>Stop Loss Inicial:</b> ${positions[symbol]['stop_loss']:.2f}\n"
                       f"• <b>Banca Livre:</b> ${paper_capital:.2f}")
                send_telegram(msg)

            # 2. ENTRADA SHORT
            elif pos is None and (ema21_4h < ema50_4h < ema200_4h) and (high >= ema21_1h and price < ema21_1h):
                alloc = paper_capital * alloc_pct * (1 - fee)
                units = alloc / price
                positions[symbol] = {
                    'side': 'SHORT', 'entry_price': price, 'units': units,
                    'stop_loss': price + (3.0 * atr1h), 'lowest_price': price,
                    'pyramid_count': 0, 'alloc': alloc
                }
                paper_capital -= alloc
                
                msg = (f"🔻 <b>[V14 - VENDA SHORT]</b>\n\n"
                       f"• <b>Ativo:</b> {symbol}\n"
                       f"• <b>Preço de Entrada:</b> ${price:.2f}\n"
                       f"• <b>Alocação:</b> ${alloc:.2f}\n"
                       f"• <b>Stop Loss Inicial:</b> ${positions[symbol]['stop_loss']:.2f}\n"
                       f"• <b>Banca Livre:</b> ${paper_capital:.2f}")
                send_telegram(msg)
                
            # 3. GESTÃO E PIRAMIDAGEM DA POSIÇÃO
            elif pos is not None:
                side = pos['side']
                entry = pos['entry_price']
                units = pos['units']
                is_climax = vol_4h > (3.5 * vol_sma_4h)
                
                if side == 'LONG':
                    if high > pos['highest_price']: pos['highest_price'] = high
                    
                    if pos['pyramid_count'] == 0 and price >= entry + (2.8 * atr1h) and ema21_4h > ema50_4h:
                        unrealized = (units * price) - (units * entry)
                        if unrealized > 0:
                            pos['units'] += (unrealized * 0.8) / price
                            pos['entry_price'] = (entry + price) / 2
                            pos['pyramid_count'] = 1
                            msg = f"⬆️ <b>[V14 - PIRAMIDAGEM 1 LONG]</b>\n\n• <b>Ativo:</b> {symbol}\n• <b>Preço Atual:</b> ${price:.2f}\n• <b>Nova Mão (Reinvestimento)</b>"
                            send_telegram(msg)
                            
                    elif pos['pyramid_count'] == 1 and price >= entry + (5.0 * atr1h) and ema21_4h > ema50_4h:
                        unrealized = (units * price) - (units * entry)
                        if unrealized > 0:
                            pos['units'] += (unrealized * 0.6) / price
                            pos['pyramid_count'] = 2
                            msg = f"⬆️⬆️ <b>[V14 - PIRAMIDAGEM 2 LONG]</b>\n\n• <b>Ativo:</b> {symbol}\n• <b>Preço Atual:</b> ${price:.2f}\n• <b>Mão Máxima Atingida</b>"
                            send_telegram(msg)

                    if low <= pos['stop_loss'] or ema21_4h < ema50_4h or is_climax:
                        exit_price = pos['stop_loss'] if low <= pos['stop_loss'] else price
                        returned = (pos['units'] * exit_price) * (1 - fee)
                        paper_capital += returned
                        pnl = returned - pos['alloc']
                        reason = "Clímax de Volume" if is_climax else ("Stop Loss" if low <= pos['stop_loss'] else "Inversão de Tendência 4h")
                        
                        msg = (f"✅ <b>[V14 - FECHAMENTO LONG]</b>\n\n"
                               f"• <b>Ativo:</b> {symbol}\n"
                               f"• <b>Motivo:</b> {reason}\n"
                               f"• <b>PnL da Operação:</b> ${pnl:+.2f}\n"
                               f"• <b>Banca Simulada Atual:</b> ${paper_capital:.2f}")
                        send_telegram(msg)
                        positions[symbol] = None
                        
                elif side == 'SHORT':
                    if low < pos['lowest_price']: pos['lowest_price'] = low
                    
                    if pos['pyramid_count'] == 0 and price <= entry - (2.8 * atr1h) and ema21_4h < ema50_4h:
                        unrealized = (units * entry) - (units * price)
                        if unrealized > 0:
                            pos['units'] += (unrealized * 0.8) / price
                            pos['entry_price'] = (entry + price) / 2
                            pos['pyramid_count'] = 1
                            msg = f"⬇️ <b>[V14 - PIRAMIDAGEM 1 SHORT]</b>\n\n• <b>Ativo:</b> {symbol}\n• <b>Preço Atual:</b> ${price:.2f}\n• <b>Nova Mão (Reinvestimento)</b>"
                            send_telegram(msg)
                            
                    elif pos['pyramid_count'] == 1 and price <= entry - (5.0 * atr1h) and ema21_4h < ema50_4h:
                        unrealized = (units * entry) - (units * price)
                        if unrealized > 0:
                            pos['units'] += (unrealized * 0.6) / price
                            pos['pyramid_count'] = 2
                            msg = f"⬇️⬇️ <b>[V14 - PIRAMIDAGEM 2 SHORT]</b>\n\n• <b>Ativo:</b> {symbol}\n• <b>Preço Atual:</b> ${price:.2f}\n• <b>Mão Máxima Atingida</b>"
                            send_telegram(msg)

                    if high >= pos['stop_loss'] or ema21_4h > ema50_4h or is_climax:
                        exit_price = pos['stop_loss'] if high >= pos['stop_loss'] else price
                        diff = entry - exit_price
                        returned = (pos['alloc'] + (pos['units'] * diff)) * (1 - fee)
                        paper_capital += returned
                        pnl = returned - pos['alloc']
                        reason = "Clímax de Volume" if is_climax else ("Stop Loss" if high >= pos['stop_loss'] else "Inversão de Tendência 4h")
                        
                        msg = (f"✅ <b>[V14 - FECHAMENTO SHORT]</b>\n\n"
                               f"• <b>Ativo:</b> {symbol}\n"
                               f"• <b>Motivo:</b> {reason}\n"
                               f"• <b>PnL da Operação:</b> ${pnl:+.2f}\n"
                               f"• <b>Banca Simulada Atual:</b> ${paper_capital:.2f}")
                        send_telegram(msg)
                        positions[symbol] = None
                        
        except Exception as e:
            print(f"⚠️ Erro no loop de {symbol}: {e}", flush=True)

# Loop principal
while True:
    process_signals()
    time.sleep(60)
