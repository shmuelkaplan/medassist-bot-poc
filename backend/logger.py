# backend/logger.py
import logging
import sys

def setup_logger(name: str) -> logging.Logger:
    """
    Creates and configures a standard logger for the application.
    
    Args:
        name (str): The name of the module invoking the logger.
        
    Returns:
        logging.Logger: A configured logger instance.
    """
    logger = logging.getLogger(name)
    
    # Prevent adding duplicate handlers if the logger already exists
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Create a console handler to output logs to the terminal
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Define the strict format of our logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        
    return logger