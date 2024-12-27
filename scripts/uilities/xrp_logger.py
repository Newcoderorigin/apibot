import logging

# Configure logging
logging.basicConfig(
    filename="../../logs/xrp_trading.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

def log_info(message):
    logging.info(message)

def log_error(message):
    logging.error(message)
