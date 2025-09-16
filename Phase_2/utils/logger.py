import logging
import sys

def setup_logger():
    """
    Sets up a basic logger.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    return logging.getLogger(__name__)

logger = setup_logger()