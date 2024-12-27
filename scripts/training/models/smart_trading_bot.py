import os
import json
import time
import hmac
import hashlib
import base64
import urllib.parse
import threading
import asyncio
import websockets
import logging
from datetime import datetime
import requests
import pandas as pd

# ============================ Configuration ============================

CONFIG_FILE = 'config.json'
TRADE_LOG_FILE = 'trade_log.csv'
PORTFOLIO_FILE = 'portfolio_values.csv'
LOG_FILE = 'bot.log'

# Setup logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

# Global variables
ws_stop_event = threading.Event()

# ============================ Helper Functions ============================

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
            config = json.load(file)
    else:
        config = {
            "api_key": "",
            "api_secret": "",
            "live_trading": False,
            "stop_loss": 0.95,
            "take_profit": 1.05,
            "risk_per_trade": 0.01
        }
    return config

def get_kraken_signature(url_path, data, secret):
    """Generates Kraken API signature."""
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = url_path.encode() + hashlib.sha256(encoded).digest()
    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()

def kraken_private_api(endpoint, data, config):
    """Makes a private API call to Kraken."""
    url = f"https://api.kraken.com{endpoint}"
    data['nonce'] = str(int(time.time() * 1000))
    headers = {
        'API-Key': config['api_key'],
        'API-Sign': get_kraken_signature(endpoint, data, config['api_secret'])
    }
    response = requests.post(url, headers=headers, data=data)
    response_json = response.json()
    if response_json.get('error'):
        logging.error(f"API Error: {response_json['error']}")
    return response_json

def get_ws_token(config):
    """Fetches WebSockets API token."""
    response = kraken_private_api('/0/private/GetWebSocketsToken', {}, config)
    if response.get('error'):
        logging.error(f"Failed to get WebSocket token: {response['error']}")
        return None
    return response['result']['token']

def log_trade(trade_info):
    if os.path.exists(TRADE_LOG_FILE):
        trade_df = pd.read_csv(TRADE_LOG_FILE)
    else:
        trade_df = pd.DataFrame()
    trade_df = trade_df.append(trade_info, ignore_index=True)
    trade_df.to_csv(TRADE_LOG_FILE, index=False)

def update_portfolio_value(value):
    timestamp = datetime.now()
    data = {'timestamp': timestamp, 'Portfolio_Value': value}
    if os.path.exists(PORTFOLIO_FILE):
        portfolio_df = pd.read_csv(PORTFOLIO_FILE)
    else:
        portfolio_df = pd.DataFrame()
    portfolio_df = portfolio_df.append(data, ignore_index=True)
    portfolio_df.to_csv(PORTFOLIO_FILE, index=False)

# ============================ Kraken API Functions ============================

def kraken_add_order(order_details, config):
    endpoint = '/0/private/AddOrder'
    response = kraken_private_api(endpoint, order_details, config)
    return response

def kraken_cancel_all(config):
    endpoint = '/0/private/CancelAll'
    data = {}
    response = kraken_private_api(endpoint, data, config)
    return response

# ============================ WebSocket Functions ============================

async def kraken_ws_subscribe(token, ws_stop_event):
    uri = 'wss://ws-auth.kraken.com/'
    try:
        async with websockets.connect(uri) as websocket:
            # Subscribe to desired channels
            subscribe_msg = {
                "event": "subscribe",
                "subscription": {"name": "ownTrades", "token": token}
            }
            await websocket.send(json.dumps(subscribe_msg))
            logging.info("Subscribed to ownTrades channel.")

            while not ws_stop_event.is_set():
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1)
                    data = json.loads(message)
                    if isinstance(data, dict) and data.get("event"):
                        # Handle subscription status and other events
                        logging.info(f"WebSocket event: {data}")
                    else:
                        # Handle trade data
                        process_ws_message(data)
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logging.warning("WebSocket connection closed.")
                    break
    except Exception as e:
        logging.error(f"WebSocket error: {e}")

def process_ws_message(data):
    # Process incoming WebSocket messages (trades, balance updates, etc.)
    logging.info(f"WebSocket data received: {data}")
    # Example: Update trade log or portfolio value
    # Implement processing logic as per requirements

def start_ws_listener(token):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(kraken_ws_subscribe(token, ws_stop_event))
    loop.close()

# ============================ Trading Logic ============================

def trading_strategy(config):
    # Implement your trading strategy here
    # This is a placeholder for the actual trading logic
    # For example, periodically check market data and place orders
    while not ws_stop_event.is_set():
        # Example action: Place a market buy order
        if config['live_trading']:
            order_details = {
                "ordertype": "market",
                "type": "buy",
                "volume": "0.5",
                "pair": "XRPUSD"
            }
            response = kraken_add_order(order_details, config)
            logging.info(f"Order placed: {response}")
        # Wait before next action
        time.sleep(60)  # Adjust the interval as needed

def main():
    config = load_config()

    # Check if live trading is enabled
    if not config['live_trading']:
        logging.info("Live trading is disabled. Exiting bot.")
        return

    # Get WebSocket token
    token = get_ws_token(config)
    if not token:
        logging.error("Could not get WebSocket token. Exiting bot.")
        return

    # Start WebSocket listener in a background thread
    ws_thread = threading.Thread(target=start_ws_listener, args=(token,), daemon=True)
    ws_thread.start()

    try:
        # Start trading strategy loop
        trading_strategy(config)
    except KeyboardInterrupt:
        logging.info("Stopping trading bot...")
        ws_stop_event.set()
        ws_thread.join()
        logging.info("Bot stopped.")

if __name__ == "__main__":
    main()
