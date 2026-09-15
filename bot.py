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
# CORREÇÃO DE SEGURANÇA: nunca deixar token/chat_id hardcoded no código
# versionado. Configure estas duas variáveis na aba "Environment" do Render.
# Revogue o token antigo no BotFather (/revoke) e gere um novo antes de usar.
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
STATE_FILE = "v14_paper_state.json"

def send_telegram(message):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception:
            pass
    else:
        print("Aviso: TELEGRAM_TOKEN/TELEGRAM_CHAT_ID não configurados nas variáveis de ambiente.", flush=True)

# ==========================================
# GESTÃO DE ESTADO (PERSISTÊNCIA DA BANCA)
# ==========================================
# O disco local do Render NÃO sobrevive a redeploys/reinícios no plano
# gratuito. Por isso o estado agora é salvo num Gist privado do GitHub
# (gratuito, sobrevive a qualquer reinício). Configure GITHUB_TOKEN
# (Personal Access Token clássico, escopo "gist") nas variáveis de
# ambiente do Render. Deixe GIST_ID vazio na primeira execução — o bot
# cria o Gist sozinho e avisa o ID por log e Telegram; copie esse ID
# para a variável GIST_ID no Render para reutilizá-lo nas próximas vezes.
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GIST_ID = os.environ.get("GIST_ID", "")
GIST_FILENAME = "v14_paper_state.json"
GITHUB_API = "https://api.github.com"

def _default_state():
    return {
        "paper_capital": 1000.0,
        "positions": {"BTC/USDT": None, "ETH/USDT": None, "SOL/USDT": None},
        "last_candle": {"BTC/USDT": None, "ETH/USDT": None, "SOL/USDT": None}
    }

def _gist_headers():
    return {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}

def _load_state_local():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                if "last_candle" not in state:
                    state["last_candle"] = {"BTC/USDT": None, "ETH/USDT": None, "SOL/USDT": None}
                return state
        except Exception:
            pass
    return _default_state()

def _save_state_local(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        print(f"Erro ao salvar estado local: {e}", flush=True)

def _create_gist(initial_state):
    payload = {
        "description": "Estado do Bot V14 (paper trading) - NAO APAGAR",
        "public": False,
        "files": {GIST_FILENAME: {"content": json.dumps(initial_state, indent=4)}}
    }
    r = requests.post(f"{GITHUB_API}/gists", headers=_gist_headers(), json=payload, timeout=15)
    r.raise_for_status()
    new_id = r.json()["id"]
    aviso = (f"\n>>> NOVO GIST CRIADO: {new_id}\n"
             f">>> Copie esse ID e salve como variável de ambiente GIST_ID no Render,\n"
             f">>> senão um novo Gist será criado a cada reinício e o histórico se perde de novo.\n")
    print(aviso, flush=True)
    send_telegram(f"⚠️ <b>Novo Gist de estado criado</b>\n\nID: <code>{new_id}</code>\n\nSalve isso como <b>GIST_ID</b> nas variáveis de ambiente do Render agora, ou o progresso será perdido no próximo restart.")
    return new_id

def load_state():
    global GIST_ID
    if not GITHUB_TOKEN:
        print("Aviso: GITHUB_TOKEN não configurado — usando estado local (NÃO sobrevive a redeploys).", flush=True)
        return _load_state_local()
    try:
        if not GIST_ID:
            state = _default_state()
            GIST_ID = _create_gist(state)
            return state
        r = requests.get(f"{GITHUB_API}/gists/{GIST_ID}", headers=_gist_headers(), timeout=15)
        r.raise_for_status()
        content = r.json()["files"][GIST_FILENAME]["content"]
        state = json.loads(content)
        if "last_candle" not in state:
            state["last_candle"] = {"BTC/USDT": None, "ETH/USDT": None, "SOL/USDT": None}
        return state
    except Exception as e:
        print(f"Erro ao carregar estado do Gist: {e}. Usando estado padrão.", flush=True)
        return _default_state()

def save_state(state):
    if not GITHUB_TOKEN or not GIST_ID:
        _save_state_local(state)
        return
    try:
        payload = {"files": {GIST_FILENAME: {"content": json.dumps(state, indent=4)}}}
        requests.patch(f"{GITHUB_API}/gists/{GIST_ID}", headers=_gist_headers(), json=payload, timeout=15)
    except Exception as e:
        print(f"Erro ao salvar estado no Gist: {e}", flush=True)
        _save_state_local(state)

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
print("   INICIANDO BOT V14 FIDEDIGNO — LONG ONLY (BINANCE 24/7)", flush=True)
print("==================================================", flush=True)

state = load_state()
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'adjustForTimeDifference': True}
})
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
fee = 0.001

send_telegram(f"🚀 <b>BOT QUANTITATIVO V14 ATIVO NO RENDER (FRANKFURT)</b>\n\n• <b>Estratégia:</b> Long Only — Double Pyramid + Climax Exit\n• <b>Banca Simulada:</b> ${state['paper_capital']:.2f} USDT\n• <b>Modo:</b> Paper Trading 24/7")

def fetch_data(symbol, timeframe, limit=300):
    try:
        candles = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        if '429' in str(e) or '-1003' in str(e):
            print(f"[{symbol}] Rate limit atingido (429). Aguardando 60 segundos de castigo...", flush=True)
            time.sleep(60)
        raise e

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

            # --- LOG VISUAL ---
            live_price = df1['close'].iloc[-1]
            live_ema21_4h = df4['ema21'].iloc[-1]
            live_ema50_4h = df4['ema50'].iloc[-1]
            live_ema200_4h = df4['ema200'].iloc[-1]
            live_atr = df1['atr'].iloc[-1]

            now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            print(f"[{now_str}] {symbol} | Preço Atual: ${live_price:.2f} | EMA21_4h: ${live_ema21_4h:.2f} | EMA50_4h: ${live_ema50_4h:.2f} | EMA200_4h: ${live_ema200_4h:.2f} | ATR_1h: ${live_atr:.2f}", flush=True)

            # --- TRAVA TEMPORAL ---
            candle_fechado_time = str(df1.index[-2])
            if state["last_candle"].get(symbol) == candle_fechado_time:
                time.sleep(5)
                continue

            state["last_candle"][symbol] = candle_fechado_time
            save_state(state)

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

            # 1. ENTRADA LONG (única entrada — SHORT extinto, alinhado ao
            # backtest de 5 anos que mostrou Long-Only superior e mais
            # robusto no crash de 2022)
            if pos is None:
                if ema21_4h > ema50_4h > ema200_4h and low <= ema21_1h and price > ema21_1h:
                    # CORREÇÃO: debita o valor BRUTO alocado do capital,
                    # não o líquido pós-taxa (mesma correção do backtest).
                    gross_alloc = paper_capital * alloc_pct
                    alloc = gross_alloc * (1 - fee)
                    units = alloc / price
                    positions[symbol] = {
                        'side': 'LONG', 'entry_price': price, 'units': units,
                        'stop_loss': price - (3.0 * atr1h), 'highest_price': price,
                        'pyramid_count': 0, 'alloc': alloc
                    }
                    paper_capital -= gross_alloc
                    state["paper_capital"] = paper_capital
                    state["positions"] = positions
                    save_state(state)

                    print(f"\n==================================================\n [ORDEM LONG EXECUTADA] {symbol} @ ${price:.2f}\n==================================================", flush=True)
                    send_telegram(f"🟢 <b>[ORDEM LONG EXECUTADA]</b>\n\n• <b>Ativo:</b> {symbol}\n• <b>Preço:</b> ${price:.2f}\n• <b>Valor Usado:</b> ${gross_alloc:.2f}\n• <b>Stop Loss:</b> ${positions[symbol]['stop_loss']:.2f}\n• <b>Banca Livre:</b> ${paper_capital:.2f}")

            # 2. GESTÃO, PIRAMIDAGEM E SAÍDA (só existe o caso LONG)
            elif pos is not None:
                entry = pos['entry_price']
                units = pos['units']
                is_climax = vol_4h > (3.5 * vol_sma_4h)

                if high > pos['highest_price']:
                    pos['highest_price'] = high

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

            # Pausa de 10 segundos entre cada moeda para zerar o peso na Binance
            time.sleep(10)

        except Exception as e:
            print(f"Erro em {symbol}: {e}", flush=True)
            time.sleep(10)

while True:
    process_signals()
    time.sleep(60)
