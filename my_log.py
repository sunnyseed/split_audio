import logging
import os


def log(message: str, debug_text: str = "", level: str = "DEBUG"):
    if message is not None:
        if level.upper() == "DEBUG":
            logging.debug(f'{message}')
        if level.upper() == "INFO":
            logging.info(f'{message}')
        if level.upper() == "WARNING":
            logging.warning(f'{message}')
        if level.upper() == "ERROR":
            logging.error(f'{message}')
        if level.upper() == "CRITICAL":
            logging.critical(f'{message}')

    if debug_text != "":
        logging.debug(f'{debug_text}')


# 日志
def log_config(logfile: str, console_level: str = "INFO"):
    # 创建logger对象
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # 设置日志级别

    # 创建一个输出到控制台的处理器
    console_handler = logging.StreamHandler()
    if console_level.upper() == "DEBUG":
        console_handler.setLevel(logging.DEBUG)
    if console_level.upper() == "INFO":
        console_handler.setLevel(logging.INFO)
    if console_level.upper() == "WARNING":
        console_handler.setLevel(logging.WARNING)  # 只显示WARNING级别及以上的日志
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 创建一个输出到文件的处理器
    if not os.path.exists("./log.nosync"):
        os.makedirs("./log.nosync")
    file_handler = logging.FileHandler(f'./log.nosync/{logfile}', mode='a')  # 输出到log文件
    file_handler.setLevel(logging.DEBUG)  # 输出所有级别的日志
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
