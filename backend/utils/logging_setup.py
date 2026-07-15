import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Main root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # General search and api logging
    search_handler = RotatingFileHandler(
        os.path.join(log_dir, "search.log"), maxBytes=5*1024*1024, backupCount=3
    )
    search_handler.setLevel(logging.INFO)
    search_handler.setFormatter(log_format)

    # Scrapers logging
    scraper_handler = RotatingFileHandler(
        os.path.join(log_dir, "scraper.log"), maxBytes=5*1024*1024, backupCount=3
    )
    scraper_handler.setLevel(logging.INFO)
    scraper_handler.setFormatter(log_format)

    # Errors logging
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, "error.log"), maxBytes=5*1024*1024, backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)

    # Assign handlers to relevant loggers
    root_logger.addHandler(search_handler)
    root_logger.addHandler(error_handler)

    # Explicit loggers configuration
    scraper_logger = logging.getLogger("services.scrapers")
    scraper_logger.setLevel(logging.INFO)
    scraper_logger.addHandler(scraper_handler)
    scraper_logger.propagate = False # prevent double logging to root

    # Console handler to output logs to terminal
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    
    root_logger.addHandler(console_handler)
    scraper_logger.addHandler(console_handler)

    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully.")
