# Import all necessary modules and functions for the package
import logging

# For self-upgrader functionality
from scripts.uilities.xrp_self_upgrader import SelfUpgrader
# For trading bot functionality
# For fallback web knowledge trader functionality
from scripts.uilities.xrp_web_knowledge_trader import WebKnowledgeTrader
# For machine learning model
from .xrp_ml_model import MLModel

# Initialize logging for the package
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="../logs/trading_bot.log",
    filemode="a",
)


def utilities():
    return None