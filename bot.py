import ccxt
import pandas as pd
import time
import json
import os
from datetime import datetime

exchange = ccxt.binance({'enableRateLimit': True})
symbol = 'BTC/USDT'
timeframe = '1h'
short_window = 9
long_window = 21
macro_window = 200
rsi_period = 14

STATE_FILE = 'estado_bot.json'

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        'capital_usdt': 1000.0,
        'crypto_balance': 0.0,
        'in_position': False,
        'entry_price': 0.0
    }

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

state = load_state()

def fetch_candle_data():
    # Puxa 250 velas para garantir o cálculo correto da EMA 200
    candles = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=250)
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def calculate_indicators(df):
    df['ema_short'] = df['close'].ewm(span=short_window, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=long_window, adjust=False).mean()
    df['ema_macro'] = df['close'].ewm(span=macro_window, adjust=False).mean()

    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def run_bot():
    global state
    print(f"=== BOT DE TRADING QUANTITATIVO ATIVO | {symbol} ({timeframe}) ===")
    print(f"Estratégia: EMA9 x EMA21 + Filtro Macro (EMA200) + RSI")
    print(f"Saldo Carregado: ${state['capital_usdt']:.2f} USDT | {state['crypto_balance']:.5f} BTC\n")

    while True:
        try:
            df = fetch_candle_data()
            df = calculate_indicators(df)

            last_row = df.iloc[-2]
            prev_row = df.iloc[-3]
            current_price = df.iloc[-1]['close']

            now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            print(f"[{now}] BTC: ${current_price:.2f} | EMA9: ${last_row['ema_short']:.2f} | EMA21: ${last_row['ema_long']:.2f} | EMA200: ${last_row['ema_macro']:.2f} | RSI: {last_row['rsi']:.1f}")

            # Condição de COMPRA
            if (prev_row['ema_short'] <= prev_row['ema_long']) and (last_row['ema_short'] > last_row['ema_long']):
                if (current_price > last_row['ema_macro']) and (last_row['rsi'] < 60) and not state['in_position']:
                    state['crypto_balance'] = state['capital_usdt'] / current_price
                    state['entry_price'] = current_price
                    state['capital_usdt'] = 0.0
                    state['in_position'] = True
                    save_state(state)
                    print(f"\n[SINAL DE COMPRA EXECUTADO] Preço: ${state['entry_price']:.2f}")
                    print(f"Novo Saldo: {state['crypto_balance']:.5f} BTC\n")

            # Condição de VENDA
            elif (prev_row['ema_short'] >= prev_row['ema_long']) and (last_row['ema_short'] < last_row['ema_long']):
                if state['in_position']:
                    state['capital_usdt'] = state['crypto_balance'] * current_price
                    pnl = ((current_price - state['entry_price']) / state['entry_price']) * 100
                    print(f"\n[SINAL DE VENDA EXECUTADO] Preço: ${current_price:.2f} | Resultado: {pnl:+.2f}%")
                    state['crypto_balance'] = 0.0
                    state['in_position'] = False
                    save_state(state)
                    print(f"Novo Saldo: ${state['capital_usdt']:.2f} USDT\n")

            time.sleep(60)

        except Exception as e:
            print(f"Erro na execução: {e}")
            time.sleep(10)

if __name__ == '__main__':
    run_bot()