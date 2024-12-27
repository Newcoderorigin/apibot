import json
import logging
import os
from typing import TextIO

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# ============================ Configuration ============================

CONFIG_FILE = 'config.json'
TRADE_LOG_FILE = 'trade_log.csv'
PORTFOLIO_FILE = 'portfolio_values.csv'
LOG_FILE = 'bot.log'

# Setup logging
logging.basicConfig(filename='dashboard.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

# ============================ Helper Functions ============================

def load_data():
    if os.path.exists(TRADE_LOG_FILE):
        trade_df = pd.read_csv(TRADE_LOG_FILE)
    else:
        trade_df = pd.DataFrame()
    if os.path.exists(PORTFOLIO_FILE):
        portfolio_df = pd.read_csv(PORTFOLIO_FILE, parse_dates=['timestamp'])
    else:
        portfolio_df = pd.DataFrame()
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as file:
            logs = file.read()
    else:
        logs = "No logs available."
    return trade_df, portfolio_df, logs

def save_config(config):
    """Saves configuration to the config.json file."""
    file: TextIO
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config, file, indent=4)

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

# ============================ Streamlit Dashboard ============================

def main():
    st.title("Smart Trading Bot Dashboard")

    # Sidebar for API Key Input
    st.sidebar.header("API Configuration")

    config = load_config()

    api_key = st.sidebar.text_input("Kraken API Key", type="password",
                                    value=config.get('api_key', ''))
    api_secret = st.sidebar.text_input("Kraken API Secret", type="password",
                                       value=config.get('api_secret', ''))

    # Update API keys if provided
    if st.sidebar.button("Update API Keys"):
        if api_key and api_secret:
            config['api_key'] = api_key
            config['api_secret'] = api_secret
            save_config(config)
            st.sidebar.success("API keys updated successfully.")
        else:
            st.sidebar.error("Please provide both API Key and Secret.")

    # Live Trading Toggle
    live_trading = st.sidebar.checkbox("Enable Live Trading",
                                       value=config.get('live_trading', False))
    config['live_trading'] = live_trading

    # Risk Management Parameters
    st.sidebar.subheader("Risk Management Settings")
    stop_loss = st.sidebar.number_input("Stop-Loss Multiplier (e.g., 0.95 for 5% loss)",
                                        min_value=0.80, max_value=1.00,
                                        value=config.get('stop_loss', 0.95), step=0.01)
    take_profit = st.sidebar.number_input("Take-Profit Multiplier (e.g., 1.05 for 5% profit)",
                                          min_value=1.00, max_value=1.50,
                                          value=config.get('take_profit', 1.05), step=0.01)
    risk_per_trade = st.sidebar.number_input("Risk per Trade (e.g., 0.01 for 1%)",
                                             min_value=0.005, max_value=0.05,
                                             value=config.get('risk_per_trade', 0.01), step=0.005)
    config['stop_loss'] = stop_loss
    config['take_profit'] = take_profit
    config['risk_per_trade'] = risk_per_trade

    # Save configuration
    if st.sidebar.button("Update Configuration"):
        save_config(config)
        st.sidebar.success("Configuration updated successfully.")

    # Display Trade Log
    st.subheader("Trade Log")
    trade_df, portfolio_df, logs = load_data()
    if not trade_df.empty:
        st.dataframe(trade_df)
    else:
        st.write("No trades to display.")

    # Display Portfolio Performance
    st.subheader("Portfolio Performance Over Time")
    if not portfolio_df.empty:
        fig, ax = plt.subplots(figsize=(14, 7))
        ax.plot(portfolio_df['timestamp'], portfolio_df['Portfolio_Value'],
                label='Portfolio Value', color='green')
        ax.set_xlabel('Date')
        ax.set_ylabel('Portfolio Value (USD)')
        ax.set_title('Portfolio Value Over Time')
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)
    else:
        st.write("No portfolio data to display.")

    # Display Logs
    st.subheader("Trading Bot Logs")
    st.text_area("Logs", logs, height=200)

if __name__ == "__main__":
    main()
