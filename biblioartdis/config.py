import logging

def configurar_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    #handler = logging.FileHandler('chatbot_errors.log')
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger
