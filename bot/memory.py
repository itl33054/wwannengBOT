# bot/memory.py (修正后，包含所有函数的最终完整版)
from __future__ import annotations

import json
import os
import uuid
import logging
from collections import deque
from datetime import datetime, timedelta, timezone
from cachetools import LRUCache
from typing import Optional
import diskcache

# 导入 statistics 模块作为数据库访问的唯一入口
from . import statistics as db

logger = logging.getLogger(__name__)

# --- 路径定义 ---
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
CHAT_HISTORY_FILE = os.path.join(DATA_DIR, 'chat_histories.json')
SEARCH_CACHE_DIR = os.path.join(DATA_DIR, 'search_cache')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SEARCH_CACHE_DIR, exist_ok=True)


# ==============================================================================
# 聊天历史记录 (Chat History - Kept in Memory/JSON as cache)
# ==============================================================================

chat_histories = LRUCache(maxsize=500)
MEMORY_DEPTH = 40
HISTORY_TTL_HOURS = 24

def get_chat_history(chat_id: int) -> deque:
    if chat_id not in chat_histories:
        _load_chat_histories()
        if chat_id not in chat_histories:
             chat_histories[chat_id] = deque(maxlen=MEMORY_DEPTH)
    return chat_histories[chat_id]

def clear_chat_history(chat_id: int):
    if chat_id in chat_histories:
        chat_histories[chat_id].clear()
        _save_chat_histories()

# --- 【关键补充】以下是之前被省略的函数 ---

def _filter_expired_history(history_list: list) -> list:
    """过滤掉超过指定生存时间（TTL）的聊天记录。"""
    now = datetime.now(timezone.utc)
    cutoff_time = now - timedelta(hours=HISTORY_TTL_HOURS)
    fresh_history = []
    for record in history_list:
        if 'timestamp' not in record:
            fresh_history.append(record)
            continue
        try:
            record_time = datetime.fromisoformat(record['timestamp'])
            if record_time > cutoff_time:
                fresh_history.append(record)
        except (TypeError, ValueError):
            fresh_history.append(record)
    return fresh_history

def _save_chat_histories():
    """将内存中的聊天记录（未过期的部分）保存到 JSON 文件。"""
    try:
        serializable_histories = {}
        current_histories = dict(chat_histories.items())
        for chat_id, history in current_histories.items():
            fresh_history = _filter_expired_history(list(history))
            if fresh_history:
                serializable_histories[str(chat_id)] = fresh_history
        with open(CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(serializable_histories, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存聊天历史时出错: {e}")

def _load_chat_histories():
    """从 JSON 文件加载聊天记录到内存中。"""
    if not os.path.exists(CHAT_HISTORY_FILE): return
    try:
        with open(CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
            serialized_histories = json.load(f)
        for chat_id_str, history_list in serialized_histories.items():
            chat_id = int(chat_id_str)
            fresh_history = _filter_expired_history(history_list)
            if fresh_history:
                chat_histories[chat_id] = deque(fresh_history, maxlen=MEMORY_DEPTH)
    except Exception as e:
        logger.error(f"加载聊天历史时出错: {e}")

# --- 补充结束 ---


# ==============================================================================
# 分页搜索缓存 (Search Pagination Cache - using diskcache)
# ==============================================================================

search_query_cache = diskcache.Cache(SEARCH_CACHE_DIR, size_limit=32 * 1024 * 1024)

def store_search_query(query: str) -> str:
    search_id = str(uuid.uuid4())
    search_query_cache.set(search_id, query, expire=3600)
    return search_id

def get_search_query(search_id: str) -> Optional[str]:
    return search_query_cache.get(search_id)


# ==============================================================================
# 用户警告系统 (User Warning System - Logic here, persistence via DB)
# ==============================================================================

WARNING_EXPIRY_HOURS = 24 # 警告在24小时后重置

def record_and_get_warning_level(chat_id: int, user_id: int) -> int:
    """
    记录一次违规，并返回用户当前的警告等级。
    数据持久化通过数据库完成。
    """
    now = datetime.now(timezone.utc)
    
    current_warning = db.db_get_user_warning(chat_id, user_id)
    
    new_count = 1
    if current_warning:
        try:
            last_warning_time = datetime.fromisoformat(current_warning['last_warning_timestamp'])
            if now - last_warning_time > timedelta(hours=WARNING_EXPIRY_HOURS):
                new_count = 1
            else:
                new_count = current_warning['warning_count'] + 1
        except (ValueError, TypeError):
            new_count = 1
    
    db.db_update_user_warning(chat_id, user_id, new_count, now.isoformat())
    
    logger.info(f"用户 {user_id} 在群组 {chat_id} 的警告等级更新为: {new_count}")
    return new_count


# --- 启动时加载聊天记录 ---
_load_chat_histories()