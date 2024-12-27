import logging
import json
import requests
import hashlib
import hmac
import base64
import time

# Logging Configuration
logging.basicConfig(
    filename="shib_sniping_bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Constants
BUY_THRESHOLD = 0.0000075
SELL_THRESHOLD = 0.0000085
MIN_TRADE_VOLUME = 5000  # Minimum SHIB volume for trades
TRADE_AMOUNT_USD = 3.0  # Maximum trade amount in USD
TARGET_PROFIT = 100.0  # Target profit in USD
API_CALL_LIMIT_SHORT = 5.0  # Minimum seconds between short API calls
API_CALL_LIMIT_LONG = 10.0  # Minimum seconds between long API calls

class SHIBSnipingBot:
    def __init__(self, api_key, private_key):
        self.api_key = api_key
        self.private_key = private_key
        self.wallet_balance = {}
        self.last_api_call = 0
        self.open_orders = []
        self.pnl = 0.0

    def throttle_api_calls(self, long_interval=False):
        """Ensure we respect Kraken's API call limits."""
        now = time.time()
        elapsed = now - self.last_api_call
        limit = API_CALL_LIMIT_LONG if long_interval else API_CALL_LIMIT_SHORT
        if elapsed < limit:
            time.sleep(limit - elapsed)
        self.last_api_call = time.time()

    def fetch_wallet_balance(self):
        """Fetch wallet balance for all assets."""
        self.throttle_api_calls()
        url = "https://api.kraken.com/0/private/Balance"
        payload = {"nonce": int(time.time() * 1000)}
        headers = self._generate_headers("/0/private/Balance", payload)

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response_data = response.json()
            if response.status_code == 200 and not response_data.get("error"):
                self.wallet_balance = {k: float(v) for k, v in response_data["result"].items()}
                logging.info(f"Wallet balance: {self.wallet_balance}")
                print(f"Wallet balance: {self.wallet_balance}")
            else:
                logging.error(f"Error fetching wallet balance: {response_data}")
        except Exception as e:
            logging.error(f"Error fetching wallet balance: {e}")
            print(f"Error fetching wallet balance: {e}")

    def fetch_open_orders(self):
        """Fetch open orders from Kraken."""
        self.throttle_api_calls()
        url = "https://api.kraken.com/0/private/OpenOrders"
        payload = {"nonce": int(time.time() * 1000)}
        headers = self._generate_headers("/0/private/OpenOrders", payload)

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response_data = response.json()
            if response.status_code == 200 and not response_data.get("error"):
                self.open_orders = response_data["result"]["open"]
                logging.info(f"Open orders: {self.open_orders}")
                print("Open Orders:")
                for order_id, details in self.open_orders.items():
                    print(f"Order ID: {order_id}, Details: {details}")
            else:
                logging.error(f"Error fetching open orders: {response_data}")
        except Exception as e:
            logging.error(f"Error fetching open orders: {e}")
            print(f"Error fetching open orders: {e}")

    def update_pnl(self, trade_profit):
        """Update PnL based on trade profit."""
        self.pnl += trade_profit
        logging.info(f"Updated PnL: {self.pnl}")
        print(f"Current PnL: {self.pnl} USD")

    @staticmethod
    def fetch_price(pair):
        """Fetch current price of a trading pair using REST API."""
        url = "https://api.kraken.com/0/public/Ticker"
        payload = {"pair": pair}

        try:
            response = requests.get(url, params=payload)
            response_data = response.json()
            if response.status_code == 200 and not response_data.get("error"):
                price = float(response_data["result"][list(response_data["result"].keys())[0]]["c"][0])
                logging.info(f"Fetched price for {pair}: {price}")
                return price
            else:
                logging.error(f"Error fetching price for {pair}: {response_data}")
        except Exception as e:
            logging.error(f"Error fetching price for {pair}: {e}")
            print(f"Error fetching price for {pair}: {e}")
        return None

    def execute_trade_rest(self, side, volume, price=None, pair="SHIB/USD"):
        """Execute a trade using Kraken's REST API."""
        self.throttle_api_calls()
        url = "https://api.kraken.com/0/private/AddOrder"
        payload = {
            "nonce": int(time.time() * 1000),
            "ordertype": "limit" if price else "market",
            "type": side,
            "volume": str(volume),
            "pair": pair,
        }
        if price:
            payload["price"] = str(price)

        headers = self._generate_headers("/0/private/AddOrder", payload)
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response_data = response.json()
            if response.status_code == 200 and not response_data.get("error"):
                logging.info(f"Trade executed: {response_data}")
                print(f"Trade executed successfully: {response_data}")
            else:
                logging.error(f"Trade failed: {response_data}")
                print(f"Error executing trade: {response_data}")
        except Exception as e:
            logging.error(f"Error executing trade: {e}")
            print(f"Exception during trade execution: {e}")

    def _generate_headers(self, endpoint, payload):
        """Generate headers for Kraken API requests."""
        post_data = json.dumps(payload)
        message = (str(payload['nonce']) + post_data).encode()
        sha256_hash = hashlib.sha256(message).digest()
        mac = hmac.new(base64.b64decode(self.private_key), endpoint.encode() + sha256_hash, hashlib.sha512)
        api_sign = base64.b64encode(mac.digest()).decode()

        return {
            'Content-Type': 'application/json',
            'API-Key': self.api_key,
            'API-Sign': api_sign
        }

    def start_trading(self):
        """Main trading loop."""
        profit = 0.0
        while profit < TARGET_PROFIT:
            self.fetch_wallet_balance()
            self.fetch_open_orders()
            for asset, asset_balance in self.wallet_balance.items():
                if asset == "SHIB" and asset_balance >= MIN_TRADE_VOLUME:
                    pair = "SHIB/USD"
                    current_price = self.fetch_price(pair)
                    if current_price:
                        max_volume = TRADE_AMOUNT_USD / current_price
                        volume = min(asset_balance, max_volume)
                        trade_profit = self.trade_decision(volume, current_price)
                        if trade_profit:
                            profit += trade_profit
                            self.update_pnl(trade_profit)

    def trade_decision(self, volume, current_price):
        """Make trade decisions based on current price."""
        print(f"Current price: {current_price}, Buy Threshold: {BUY_THRESHOLD}, Sell Threshold: {SELL_THRESHOLD}")
        print(f"Available Volume: {volume} SHIB")
        if current_price < BUY_THRESHOLD:
            print("Placing buy order...")
            self.execute_trade_rest("buy", volume, current_price)
            return -TRADE_AMOUNT_USD
        elif current_price > SELL_THRESHOLD:
            print("Placing sell order...")
            self.execute_trade_rest("sell", volume, current_price)
            return TRADE_AMOUNT_USD
        return 0

if __name__ == "__main__":
    print("Welcome to the SHIB Sniping Bot!")
    print("Please enter your Kraken API credentials to proceed.")

    API_KEY = input("Enter your Kraken API Key: ").strip()
    PRIVATE_KEY = input("Enter your Kraken API Secret: ").strip()

    if not API_KEY or not PRIVATE_KEY:
        print("API Key and Secret are required to proceed. Exiting.")
        exit(1)

    bot = SHIBSnipingBot(API_KEY, PRIVATE_KEY)

    print("Starting SHIB trading bot...")
    bot.start_trading()
