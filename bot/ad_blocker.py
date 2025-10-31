# bot/ad_blocker.py

import os
import logging

logger = logging.getLogger(__name__)

# --- 路径定义 ---
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
KEYWORD_FILE = os.path.join(DATA_DIR, 'blacklist_keywords.txt')

# 使用集合(set)来存储关键词，查询速度极快
BLOCKED_KEYWORDS = set()

def load_blocked_keywords():
    """从 blacklist_keywords.txt 文件加载关键词到内存中。"""
    global BLOCKED_KEYWORDS
    try:
        if os.path.exists(KEYWORD_FILE):
            with open(KEYWORD_FILE, 'r', encoding='utf-8') as f:
                # 读取文件，去除每行首尾的空白，并转换为小写，忽略空行
                keywords = {line.strip().lower() for line in f if line.strip()}
                BLOCKED_KEYWORDS = keywords
                logger.info(f"成功加载 {len(BLOCKED_KEYWORDS)} 个广告关键词。")
        else:
            logger.warning(f"关键词黑名单文件 {KEYWORD_FILE} 不存在，将创建一个空文件。")
            # 创建一个空文件，防止下次启动时报错
            with open(KEYWORD_FILE, 'w', encoding='utf-8') as f:
                pass
            BLOCKED_KEYWORDS = set()
    except Exception as e:
        logger.error(f"加载广告关键词时出错: {e}", exc_info=True)
        BLOCKED_KEYWORDS = set()

def is_spam(text: str) -> bool:
    """
    检查给定文本是否包含任何被屏蔽的关键词。
    """
    if not text or not BLOCKED_KEYWORDS:
        return False
    
    # 将输入文本也转换为小写以进行不区分大小写的比较
    lower_text = text.lower()
    
    for keyword in BLOCKED_KEYWORDS:
        if keyword in lower_text:
            return True
            
    return False

# 在模块加载时，立即执行一次关键词加载
load_blocked_keywords()