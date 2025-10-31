# bot/statistics.py
from __future__ import annotations

import os
import sqlite3
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Optional

from .config import USER_RANKING_BLACKLIST

try:
    import jieba
except ImportError:
    print("警告: 未找到 'jieba' 库。中文话题统计功能将无法正常工作。")
    print("请通过 'pip install -r requirements.txt' 安装。")
    jieba = None

logger = logging.getLogger(__name__)

# --- 路径与数据库初始化 ---
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
DB_FILE = os.path.join(DATA_DIR, 'statistics.db')
os.makedirs(DATA_DIR, exist_ok=True)


def _get_db_connection() -> sqlite3.Connection:
    """获取一个数据库连接，并设置 Row Factory 以便返回类似字典的结果。"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _initialize_database():
    """初始化数据库，创建所有需要的表。"""
    conn = _get_db_connection()
    cursor = conn.cursor()

    # --- 核心聊天记录表 ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT NOT NULL,
        chat_title TEXT,
        chat_username TEXT,
        user_id TEXT NOT NULL,
        user_name TEXT,
        user_username TEXT,
        timestamp TEXT NOT NULL,
        text TEXT
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_id_timestamp ON messages (chat_id, timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id_timestamp ON messages (user_id, timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages (timestamp);")

    # --- 已知群组信息表 ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS known_chats (
        chat_id TEXT PRIMARY KEY,
        chat_title TEXT,
        added_by_user_id TEXT,
        date_added TEXT
    )
    """)

    # --- 用户设置表 ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id TEXT PRIMARY KEY,
        language_code TEXT,
        ranking_enabled INTEGER NOT NULL DEFAULT 1
    )
    """)

    # --- 群组设置表 ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS group_settings (
        chat_id TEXT PRIMARY KEY,
        language_code TEXT,
        autochat_enabled INTEGER NOT NULL DEFAULT 0,
        spam_filter_enabled INTEGER NOT NULL DEFAULT 1,
        checkin_enabled INTEGER NOT NULL DEFAULT 0
    )
    """)

    # --- 关键词回复 (FAQ) 表 ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faqs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        keywords TEXT,
        UNIQUE(chat_id, question)
    )
    """)

    # --- 黑名单表 ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blacklist (
        user_id TEXT PRIMARY KEY,
        expiration_timestamp TEXT NOT NULL
    )
    """)

    # --- 用户警告记录表 ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_warnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        warning_count INTEGER NOT NULL,
        last_warning_timestamp TEXT NOT NULL,
        UNIQUE(chat_id, user_id)
    )
    """)

    # --- 用户积分表 (分群组) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_points (
        chat_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        points INTEGER NOT NULL DEFAULT 0,
        last_update_timestamp TEXT,
        PRIMARY KEY (chat_id, user_id)
    )
    """)

    # --- 签到记录表 (分群组) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS checkin_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        checkin_date TEXT NOT NULL,
        UNIQUE(chat_id, user_id, checkin_date)
    )
    """)

    # --- 商店奖品表 ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shop_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        cost INTEGER NOT NULL,
        stock INTEGER NOT NULL DEFAULT -1,
        is_active INTEGER NOT NULL DEFAULT 1
    )
    """)

    conn.commit()
    conn.close()


# ==============================================================================
# Section 1: 消息保存与基础查询 (Message Saving & Basic Queries)
# ==============================================================================

def update_known_chat(chat_id: int, chat_title: str, added_by_user_id: int = None):
    if not str(chat_id).startswith('-100') or not chat_title:
        return
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        if added_by_user_id:
            cursor.execute("""
            INSERT INTO known_chats (chat_id, chat_title, added_by_user_id, date_added)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                chat_title = excluded.chat_title,
                added_by_user_id = COALESCE(known_chats.added_by_user_id, excluded.added_by_user_id),
                date_added = COALESCE(known_chats.date_added, excluded.date_added)
            """, (str(chat_id), chat_title, str(added_by_user_id), datetime.now().isoformat()))
        else:
            cursor.execute("""
            INSERT INTO known_chats (chat_id, chat_title)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET chat_title = excluded.chat_title
            """, (str(chat_id), chat_title))

        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"更新已知群组信息时出错: {e}")

def db_discover_and_update_known_chats():
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT T1.chat_id, T1.chat_title
            FROM messages AS T1
            INNER JOIN (
                SELECT chat_id, MAX(timestamp) AS max_ts
                FROM messages
                WHERE chat_id LIKE '-100%' AND chat_title IS NOT NULL AND chat_title != ''
                GROUP BY chat_id
            ) AS T2 ON T1.chat_id = T2.chat_id AND T1.timestamp = T2.max_ts
        """)
        discovered_chats = cursor.fetchall()
        
        if not discovered_chats:
            conn.close()
            return

        chats_to_upsert = [(row['chat_id'], row['chat_title']) for row in discovered_chats]
        cursor.executemany("""
            INSERT INTO known_chats (chat_id, chat_title)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET chat_title = excluded.chat_title
        """, chats_to_upsert)
        
        conn.commit()
        conn.close()
        logger.info(f"成功从消息历史中扫描并更新了 {len(discovered_chats)} 个群组信息到 known_chats 表。")
    except Exception as e:
        logger.error(f"扫描并更新已知群组时出错: {e}", exc_info=True)

def save_message(chat_id, chat_title, chat_username, user_id, user_name, user_username, text):
    update_known_chat(chat_id, chat_title)
    timestamp = datetime.now().isoformat()
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO messages (chat_id, chat_title, chat_username, user_id, user_name, user_username, timestamp, text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(chat_id), chat_title or '', chat_username or '', str(user_id), user_name, user_username or '', timestamp, text))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"保存消息到数据库时出错: {e}")

def get_all_known_groups() -> List[Tuple[str, str]]:
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, chat_title FROM known_chats ORDER BY chat_title ASC")
    results = cursor.fetchall()
    conn.close()
    return [(row['chat_id'], row['chat_title']) for row in results]

def db_get_groups_for_user(user_id: int) -> List[Tuple[str, str]]:
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT T1.chat_id, T1.chat_title
        FROM messages AS T1
        INNER JOIN (
            SELECT chat_id, MAX(timestamp) AS max_ts
            FROM messages
            WHERE user_id = ? AND chat_id LIKE '-100%' AND chat_title IS NOT NULL AND chat_title != ''
            GROUP BY chat_id
        ) AS T2 ON T1.chat_id = T2.chat_id AND T1.timestamp = T2.max_ts
        ORDER BY T1.chat_title
    """, (str(user_id),))
    results = cursor.fetchall()
    conn.close()
    return [(row['chat_id'], row['chat_title']) for row in results]

def get_user_id_by_username(username: str) -> Optional[int]:
    cleaned_username = username.lstrip('@').lower()
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM messages WHERE LOWER(user_username) = ? ORDER BY timestamp DESC LIMIT 1", (cleaned_username,))
    result = cursor.fetchone()
    conn.close()
    try:
        return int(result['user_id']) if result else None
    except (ValueError, TypeError):
        return None

def _get_start_time_for_period(period: str) -> Optional[datetime]:
    now = datetime.now()
    if period == 'today':
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        return now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now.weekday())
    elif period == 'month':
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return None

def db_get_user_activity_across_groups(user_id: int) -> List[Tuple[str, str, int]]:
    """
    获取指定用户在所有ta参与的超级群组中的发言统计。
    返回一个列表，每个元素是 (群组标题, 群组用户名, 用户在该群的发言数)。
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    query = """
    SELECT
        T1.chat_title,
        T1.chat_username,
        T2.msg_count
    FROM
        messages AS T1
    INNER JOIN (
        SELECT
            chat_id,
            COUNT(*) AS msg_count,
            MAX(timestamp) AS max_ts
        FROM
            messages
        WHERE
            user_id = ? AND chat_id LIKE '-100%'
        GROUP BY
            chat_id
    ) AS T2 ON T1.chat_id = T2.chat_id AND T1.timestamp = T2.max_ts
    ORDER BY
        T2.msg_count DESC;
    """
    cursor.execute(query, (str(user_id),))
    results = cursor.fetchall()
    conn.close()
    return [(row['chat_title'], row['chat_username'], row['msg_count']) for row in results]

# ==============================================================================
# Section 2: 统计与排行榜函数 (Statistics & Ranking Functions)
# ==============================================================================

def _get_exclusion_list() -> List[str]:
    opt_out_users = db_get_all_ranking_opt_out_users()
    return list(set(USER_RANKING_BLACKLIST + opt_out_users))

def get_daily_activity_for_chat(chat_id: int, start_date: datetime, end_date: datetime) -> Dict:
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT DATE(timestamp) as activity_date, COUNT(*) as msg_count
    FROM messages WHERE chat_id = ? AND timestamp >= ? AND timestamp <= ?
    GROUP BY activity_date ORDER BY activity_date ASC
    """, (str(chat_id), start_date.isoformat(), end_date.isoformat()))
    results = cursor.fetchall()
    conn.close()
    return {datetime.strptime(row['activity_date'], '%Y-%m-%d').date(): row['msg_count'] for row in results}

def get_user_stats_in_chat(user_id: int, chat_id: int) -> dict:
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), MIN(timestamp) FROM messages WHERE user_id = ? AND chat_id = ?", (str(user_id), str(chat_id)))
    result = cursor.fetchone()
    conn.close()
    total_count = result[0] if result else 0
    first_message_iso = result[1] if result and result[1] else None
    first_message_date = None
    if first_message_iso:
        try:
            first_message_date = datetime.fromisoformat(first_message_iso).strftime('%Y年%m月%d日')
        except: pass
    return {"total_count": total_count, "first_date": first_message_date}

def get_user_rank_in_chat(user_id: int, chat_id: int, period: str) -> tuple[int, int]:
    start_time = _get_start_time_for_period(period)
    if not start_time: return 0, 0
    conn = _get_db_connection()
    cursor = conn.cursor()
    exclusion_list = _get_exclusion_list()
    placeholders = ','.join('?' for _ in exclusion_list)
    where_clause = "WHERE chat_id = ? AND timestamp >= ? AND user_id NOT LIKE '-100%'"
    params = [str(chat_id), start_time.isoformat()]
    if exclusion_list:
        where_clause += f" AND user_id NOT IN ({placeholders})"
        params.extend(exclusion_list)
    base_query = f"CREATE TEMP TABLE rank_table AS SELECT user_id, COUNT(*) as msg_count FROM messages {where_clause} GROUP BY user_id ORDER BY msg_count DESC"
    cursor.execute("DROP TABLE IF EXISTS rank_table;")
    cursor.execute(base_query, tuple(params))
    cursor.execute("SELECT rank, msg_count FROM (SELECT user_id, msg_count, RANK() OVER (ORDER BY msg_count DESC) as rank FROM rank_table) WHERE user_id = ?", (str(user_id),))
    result = cursor.fetchone()
    conn.close()
    return (result['rank'], result['msg_count']) if result else (0, 0)

def get_user_global_stats(user_id: int) -> tuple[int, int]:
    conn = _get_db_connection()
    cursor = conn.cursor()
    exclusion_list = _get_exclusion_list()
    user_id_str = str(user_id)
    if user_id_str in exclusion_list: exclusion_list.remove(user_id_str)
    placeholders = ','.join('?' for _ in exclusion_list)
    where_clause = "WHERE user_id NOT LIKE '-100%'"
    params = []
    if exclusion_list:
        where_clause += f" AND user_id NOT IN ({placeholders})"
        params.extend(exclusion_list)
    base_query = f"CREATE TEMP TABLE global_rank_table AS SELECT user_id, COUNT(*) as msg_count FROM messages {where_clause} GROUP BY user_id ORDER BY msg_count DESC"
    cursor.execute("DROP TABLE IF EXISTS global_rank_table;")
    cursor.execute(base_query, tuple(params))
    cursor.execute("SELECT rank, msg_count FROM (SELECT user_id, msg_count, RANK() OVER (ORDER BY msg_count DESC) as rank FROM global_rank_table) WHERE user_id = ?", (user_id_str,))
    result = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_id_str,))
    total_count_result = cursor.fetchone()
    total_count = total_count_result[0] if total_count_result else 0
    conn.close()
    return (result['rank'], total_count) if result else (0, total_count)

def get_top_users_by_period(chat_id: int, period: str, limit: int = 10) -> list:
    start_time = _get_start_time_for_period(period)
    if not start_time: return []
    conn = _get_db_connection()
    cursor = conn.cursor()
    exclusion_list = _get_exclusion_list()
    placeholders = ','.join('?' for _ in exclusion_list)
    where_clause = "WHERE chat_id = ? AND timestamp >= ? AND user_id NOT LIKE '-100%'"
    params = [str(chat_id), start_time.isoformat()]
    if exclusion_list:
        where_clause += f" AND user_id NOT IN ({placeholders})"
        params.extend(exclusion_list)
    
    base_query = f"SELECT T1.user_id, T1.user_name, T1.user_username, T2.msg_count FROM messages AS T1 INNER JOIN (SELECT user_id, COUNT(*) AS msg_count, MAX(timestamp) AS max_ts FROM messages {where_clause} GROUP BY user_id) AS T2 ON T1.user_id = T2.user_id AND T1.timestamp = T2.max_ts ORDER BY T2.msg_count DESC LIMIT ?"
    params.append(limit)
    cursor.execute(base_query, tuple(params))
    results = cursor.fetchall()
    conn.close()
    return [(row['user_id'], row['user_name'], row['user_username'], row['msg_count']) for row in results]

def get_global_top_users_by_period(period: str, limit: int = 10) -> list:
    start_time = _get_start_time_for_period(period)
    if not start_time: return []
    conn = _get_db_connection()
    cursor = conn.cursor()
    exclusion_list = _get_exclusion_list()
    placeholders = ','.join('?' for _ in exclusion_list)
    where_clause = "WHERE timestamp >= ? AND user_id NOT LIKE '-100%'"
    params = [start_time.isoformat()]
    if exclusion_list:
        where_clause += f" AND user_id NOT IN ({placeholders})"
        params.extend(exclusion_list)

    base_query = f"SELECT T1.user_id, T1.user_name, T1.user_username, T2.msg_count FROM messages AS T1 INNER JOIN (SELECT user_id, COUNT(*) AS msg_count, MAX(timestamp) AS max_ts FROM messages {where_clause} GROUP BY user_id) AS T2 ON T1.user_id = T2.user_id AND T1.timestamp = T2.max_ts ORDER BY T2.msg_count DESC LIMIT ?"
    params.append(limit)
    cursor.execute(base_query, tuple(params))
    results = cursor.fetchall()
    conn.close()
    return [(row['user_id'], row['user_name'], row['user_username'], row['msg_count']) for row in results]

def get_global_top_groups_by_period(period: str, limit: int = 10) -> list:
    start_time = _get_start_time_for_period(period)
    if not start_time: return []
    conn = _get_db_connection()
    cursor = conn.cursor()
    query = """
    SELECT 
        T1.chat_title, 
        T1.chat_username, 
        T2.msg_count
    FROM 
        messages AS T1
    INNER JOIN (
        SELECT 
            chat_id, 
            COUNT(*) AS msg_count, 
            MAX(timestamp) AS max_ts 
        FROM 
            messages 
        WHERE 
            timestamp >= ? AND chat_id LIKE '-100%'
        GROUP BY 
            chat_id
    ) AS T2 ON T1.chat_id = T2.chat_id AND T1.timestamp = T2.max_ts
    ORDER BY 
        T2.msg_count DESC 
    LIMIT ?
    """
    cursor.execute(query, (start_time.isoformat(), limit))
    results = cursor.fetchall()
    conn.close()
    return [(row['chat_title'], row['chat_username'], row['msg_count']) for row in results]

def is_valid_topic(text: str) -> bool:
    cleaned_text = text.strip()
    if len(cleaned_text) < 2 or cleaned_text.startswith('/') or not any(char.isalpha() for char in cleaned_text) or (len(cleaned_text) > 4 and len(set(cleaned_text)) <= 2):
        return False
    return True

def _fetch_texts_for_period(period: str, chat_id: str = None) -> list:
    start_time = _get_start_time_for_period(period)
    if not start_time: return []
    conn = _get_db_connection()
    cursor = conn.cursor()
    exclusion_list = _get_exclusion_list()
    placeholders = ','.join('?' for _ in exclusion_list)
    base_query = "SELECT text FROM messages WHERE timestamp >= ? AND user_id NOT LIKE '-100%'"
    params = [start_time.isoformat()]
    if exclusion_list:
        base_query += f" AND user_id NOT IN ({placeholders})"
        params.extend(exclusion_list)
    if chat_id:
        base_query += " AND chat_id = ?"
        params.append(str(chat_id))
    cursor.execute(base_query, tuple(params))
    results = [row[0] for row in cursor.fetchall() if row[0] and is_valid_topic(row[0])]
    conn.close()
    return results

def get_top_topics_by_period(chat_id: int, period: str, limit: int = 10) -> list:
    valid_texts = _fetch_texts_for_period(period, chat_id=str(chat_id))
    if not valid_texts: return []
    return Counter(valid_texts).most_common(limit)

def get_global_top_topics_by_period(period: str, limit: int = 10) -> list:
    valid_texts = _fetch_texts_for_period(period)
    if not valid_texts: return []
    return Counter(valid_texts).most_common(limit)

# ==============================================================================
# Section 3: 设置与数据管理函数 (Settings & Data Management Functions)
# ==============================================================================

def db_get_user_settings(user_id: int) -> Optional[sqlite3.Row]:
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (str(user_id),))
    result = cursor.fetchone()
    conn.close()
    return result

def db_update_user_setting(user_id: int, **kwargs):
    user_id_str = str(user_id)
    if not kwargs: return
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id_str,))
    set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
    params = list(kwargs.values()) + [user_id_str]
    cursor.execute(f"UPDATE user_settings SET {set_clause} WHERE user_id = ?", tuple(params))
    conn.commit()
    conn.close()

def db_get_all_ranking_opt_out_users() -> List[str]:
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM user_settings WHERE ranking_enabled = 0")
    results = [row['user_id'] for row in cursor.fetchall()]
    conn.close()
    return results

def db_get_group_settings(chat_id: int) -> Optional[sqlite3.Row]:
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM group_settings WHERE chat_id = ?", (str(chat_id),))
    result = cursor.fetchone()
    conn.close()
    return result

def db_update_group_setting(chat_id: int, **kwargs):
    chat_id_str = str(chat_id)
    if not kwargs: return
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO group_settings (chat_id) VALUES (?)", (chat_id_str,))
    set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
    params = list(kwargs.values()) + [chat_id_str]
    cursor.execute(f"UPDATE group_settings SET {set_clause} WHERE chat_id = ?", tuple(params))
    conn.commit()
    conn.close()

def db_add_faq(chat_id: int, question: str, answer: str, keywords: str) -> bool:
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO faqs (chat_id, question, answer, keywords) VALUES (?, ?, ?, ?)", (str(chat_id), question, answer, keywords))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def db_delete_faq(faq_id: int) -> bool:
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM faqs WHERE id = ?", (faq_id,))
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"从数据库删除FAQ (ID: {faq_id}) 时出错: {e}")
        return False

def db_get_faqs_for_chat(chat_id: int) -> List[sqlite3.Row]:
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM faqs WHERE chat_id = ? ORDER BY id ASC", (str(chat_id),))
    results = cursor.fetchall()
    conn.close()
    return results

def db_get_blacklist_entry(user_id: int) -> Optional[sqlite3.Row]:
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blacklist WHERE user_id = ?", (str(user_id),))
    result = cursor.fetchone()
    conn.close()
    return result

def db_add_to_blacklist(user_id: int, expiration_timestamp: str):
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO blacklist (user_id, expiration_timestamp) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET expiration_timestamp = excluded.expiration_timestamp", (str(user_id), expiration_timestamp))
    conn.commit()
    conn.close()

def db_remove_from_blacklist(user_id: int) -> bool:
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blacklist WHERE user_id = ?", (str(user_id),))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def db_clear_expired_blacklist_entries():
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blacklist WHERE expiration_timestamp < ?", (now_iso,))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted_count > 0:
        logger.info(f"成功从数据库清除了 {deleted_count} 条过期的黑名单记录。")

def db_get_user_warning(chat_id: int, user_id: int) -> Optional[sqlite3.Row]:
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_warnings WHERE chat_id = ? AND user_id = ?", (str(chat_id), str(user_id)))
    result = cursor.fetchone()
    conn.close()
    return result

def db_update_user_warning(chat_id: int, user_id: int, count: int, timestamp: str):
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_warnings (chat_id, user_id, warning_count, last_warning_timestamp) VALUES (?, ?, ?, ?) ON CONFLICT(chat_id, user_id) DO UPDATE SET warning_count = excluded.warning_count, last_warning_timestamp = excluded.last_warning_timestamp", (str(chat_id), str(user_id), count, timestamp))
    conn.commit()
    conn.close()


# ==============================================================================
# Section 4: 积分与签到系统 (Points & Check-in System)
# ==============================================================================

def db_get_user_points(user_id: int, chat_id: int) -> int:
    """获取用户在指定群组的积分。"""
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM user_points WHERE user_id = ? AND chat_id = ?", (str(user_id), str(chat_id)))
    result = cursor.fetchone()
    conn.close()
    return result['points'] if result else 0

def db_add_points(user_id: int, chat_id: int, points_to_add: int, cooldown_seconds: int = 1) -> tuple[bool, int]:
    """
    为用户在指定群组增加积分，并内置冷却时间检查。
    :param cooldown_seconds: 冷却秒数，如果为0则不检查。默认为1秒。
    :return: 一个元组 (是否成功添加, 新的总积分)
    """
    conn = _get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    
    initial_timestamp = datetime(1970, 1, 1).isoformat()
    cursor.execute(
        "INSERT OR IGNORE INTO user_points (user_id, chat_id, points, last_update_timestamp) VALUES (?, ?, 0, ?)",
        (str(user_id), str(chat_id), initial_timestamp)
    )
    
    cursor.execute("SELECT points, last_update_timestamp FROM user_points WHERE user_id = ? AND chat_id = ?", (str(user_id), str(chat_id)))
    result = cursor.fetchone()
    current_points = result['points']
    
    if cooldown_seconds > 0:
        try:
            last_update_time = datetime.fromisoformat(result['last_update_timestamp'])
            if (now - last_update_time).total_seconds() < cooldown_seconds:
                conn.close()
                return (False, current_points)
        except (ValueError, TypeError):
            pass

    new_points = current_points + points_to_add
    cursor.execute(
        "UPDATE user_points SET points = ?, last_update_timestamp = ? WHERE user_id = ? AND chat_id = ?",
        (new_points, now_iso, str(user_id), str(chat_id))
    )
    
    conn.commit()
    conn.close()
    return (True, new_points)

def db_check_if_user_checked_in_today(user_id: int, chat_id: int) -> bool:
    """检查用户今天是否已在指定群组签到。"""
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM checkin_log WHERE user_id = ? AND chat_id = ? AND checkin_date = ?", (str(user_id), str(chat_id), today_str))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def db_record_checkin(user_id: int, chat_id: int):
    """记录用户在指定群组的签到。"""
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO checkin_log (user_id, chat_id, checkin_date) VALUES (?, ?, ?)", (str(user_id), str(chat_id), today_str))
    conn.commit()
    conn.close()

# ==============================================================================
# Section 5: 商店系统 (Shop System)
# ==============================================================================

def db_get_shop_items() -> List[sqlite3.Row]:
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shop_items WHERE is_active = 1 ORDER BY cost ASC")
    results = cursor.fetchall()
    conn.close()
    return results

def db_get_shop_item_by_id(item_id: int) -> Optional[sqlite3.Row]:
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shop_items WHERE id = ?", (item_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def db_add_shop_item(name: str, description: str, cost: int, stock: int) -> bool:
    """向商店添加一个新奖品。如果名称已存在，则失败。"""
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO shop_items (name, description, cost, stock) VALUES (?, ?, ?, ?)",
            (name, description, cost, stock)
        )
        conn.commit()
        conn.close()
        logger.info(f"成功向数据库添加新奖品: {name}")
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"尝试添加一个已存在的奖品名称: {name}")
        conn.close()
        return False

def db_redeem_item(user_id: int, chat_id: int, item: sqlite3.Row) -> bool:
    """用户在指定群组使用积分兑换商品。"""
    conn = _get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE user_points SET points = points - ? WHERE user_id = ? AND chat_id = ?", (item['cost'], str(user_id), str(chat_id)))
        
        if item['stock'] != -1:
            cursor.execute("UPDATE shop_items SET stock = stock - 1 WHERE id = ?", (item['id'],))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"兑换奖品时发生数据库错误: {e}")
        return False
    finally:
        conn.close()


# ==============================================================================
# 数据库初始化调用
# ==============================================================================
_initialize_database()