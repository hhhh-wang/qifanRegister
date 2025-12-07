import logging
import os
import sys
from datetime import datetime

# ===============================
# 路径：保证日志生成在 exe 同级目录
# ===============================

def _get_app_dir():
    """
    返回程序所在目录
    - exe：exe 文件所在路径
    - py ：当前文件所在路径
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(sys.argv[0]))


BASE_DIR = _get_app_dir()
LOG_DIR = os.path.join(BASE_DIR, "log")

# 确保目录存在
os.makedirs(LOG_DIR, exist_ok=True)

# ===============================
# Logger 缓存（避免重复创建）
# ===============================

_LOGGERS = {}


def get_logger(name: str = "app", level=logging.DEBUG):
    """
    获取一个 logger（同名只创建一次）

    用法：
        from logger import get_logger
        log = get_logger(__name__)
        log.info("xxx")
    """
    global _LOGGERS

    if name in _LOGGERS:
        return _LOGGERS[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # 防止重复输出

    # ===============================
    # 文件日志（每天一个文件）
    # ===============================

    log_file = os.path.join(
        LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.log"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
    )

    # ===============================
    # 控制台日志（INFO 以上）
    # ===============================

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(message)s")
    )

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    _LOGGERS[name] = logger
    return logger
