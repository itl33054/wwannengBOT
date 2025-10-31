# bot/blacklist_manager.py
from __future__ import annotations
from typing import Optional

import os
import json
from datetime import datetime, timedelta, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
BLACKLIST_FILE = os.path.join(DATA_DIR, 'blacklist.json')
os.makedirs(DATA_DIR, exist_ok=True)

blacklisted_users = {}

def _save_blacklist():
    """将内存中的黑名单（datetime对象）转换为ISO格式字符串并保存到文件。"""
    try:
        serializable_blacklist = {
            str(uid): dt.isoformat() for uid, dt in blacklisted_users.items()
        }
        with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(serializable_blacklist, f, indent=2)
    except Exception as e:
        print(f"保存黑名单时出错: {e}")

def _load_blacklist():
    """从文件加载黑名单，并将ISO格式字符串转换回datetime对象。"""
    global blacklisted_users
    if not os.path.exists(BLACKLIST_FILE):
        return

    try:
        with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
            serialized_blacklist = json.load(f)

        now = datetime.now(timezone.utc)
        temp_blacklist = {}
        for uid_str, dt_str in serialized_blacklist.items():
            try:
                expiration_dt = datetime.fromisoformat(dt_str)
                if expiration_dt > now:
                    temp_blacklist[int(uid_str)] = expiration_dt
            except (ValueError, TypeError):
                continue # 忽略格式错误的数据
        blacklisted_users = temp_blacklist
        _save_blacklist()
    except (json.JSONDecodeError, Exception) as e:
        print(f"加载黑名单时出错: {e}")
        blacklisted_users = {}

def add_to_blacklist(user_id: int, duration_seconds: int = 3600):
    """将用户添加到黑名单。"""
    expiration_time = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
    blacklisted_users[user_id] = expiration_time
    print(f"用户 {user_id} 已被添加到黑名单，直到 {expiration_time.isoformat()}")
    _save_blacklist()

def remove_from_blacklist(user_id: int):
    """从黑名单中移除用户。"""
    if user_id in blacklisted_users:
        del blacklisted_users[user_id]
        print(f"用户 {user_id} 已从内部黑名单中移除。")
        _save_blacklist()
        return True
    return False

def get_user_blacklist_expiration(user_id: int) -> Optional[datetime]:
    """
    检查用户是否在黑名单中。
    如果被拉黑，则返回其解封时间的datetime对象。
    如果未被拉黑或已过期，则返回 None。
    """
    expiration_time = blacklisted_users.get(user_id)
    if not expiration_time:
        return None

    if datetime.now(timezone.utc) > expiration_time:
        remove_from_blacklist(user_id) # 使用新函数来移除
        print(f"用户 {user_id} 的黑名单已过期并被移除。")
        return None

    return expiration_time

_load_blacklist()