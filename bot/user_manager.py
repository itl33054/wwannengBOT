# bot/user_manager.py (已添加垃圾拦截开关功能的最终完整版)
from __future__ import annotations

import logging
from typing import Optional
from .config import DEFAULT_LANGUAGE # 仍然需要默认语言设置
from . import statistics as db # 将 statistics 模块作为数据库访问层导入，并简称为 db

logger = logging.getLogger(__name__)

# --- 删除了所有与 JSON 文件路径、加载、保存相关的代码 ---
# --- 删除了全局变量 user_database 和 group_database ---


# ==============================================================================
# 用户设置 (User Settings)
# ==============================================================================

def set_user_language(user_id: int, lang_code: str):
    """
    在数据库中设置指定用户的语言偏好。
    """
    db.db_update_user_setting(user_id, language_code=lang_code)
    logger.info(f"用户 {user_id} 的语言已在数据库中更新为: {lang_code}")

def get_user_language(user_id: int) -> Optional[str]:
    """
    从数据库中获取指定用户的语言偏好。
    """
    settings = db.db_get_user_settings(user_id)
    # 如果 settings 不为 None 且 language_code 字段有值，则返回它
    if settings and settings['language_code']:
        return settings['language_code']
    return None

def is_user_ranking_enabled(user_id: int) -> bool:
    """
    从数据库检查用户是否选择参与全服排名。
    默认值为 True (参与)。
    """
    settings = db.db_get_user_settings(user_id)
    # 如果没有设置记录，或者 ranking_enabled 字段为 1 (或 True)，则视为参与
    if not settings:
        return True # 新用户默认为参与
    return bool(settings['ranking_enabled'])

def toggle_user_ranking_participation(user_id: int) -> bool:
    """
    切换用户的全服排名参与状态，并返回更新后的新状态。
    """
    current_status = is_user_ranking_enabled(user_id)
    new_status = not current_status
    
    # 将布尔值转换为整数 1 或 0 存入数据库
    db.db_update_user_setting(user_id, ranking_enabled=int(new_status))
    logger.info(f"用户 {user_id} 的全服排名参与状态已在数据库中切换为: {new_status}")
    return new_status

def get_all_ranking_opt_out_users() -> list[str]:
    """
    获取所有选择不参与排名的用户ID列表（字符串形式）。
    此函数现在直接调用 statistics 模块中的对应函数。
    """
    return db.db_get_all_ranking_opt_out_users()


# ==============================================================================
# 群组设置 (Group Settings)
# ==============================================================================

def set_group_language(chat_id: int, lang_code: str):
    """
    在数据库中设置指定群组的语言。
    """
    db.db_update_group_setting(chat_id, language_code=lang_code)
    logger.info(f"群组 {chat_id} 的语言已在数据库中更新为: {lang_code}")

def get_group_language(chat_id: int) -> Optional[str]:
    """
    从数据库中获取指定群组的语言。
    """
    settings = db.db_get_group_settings(chat_id)
    if settings and settings['language_code']:
        return settings['language_code']
    return None
    
def set_auto_chat_mode(chat_id: int, is_on: bool):
    """
    在数据库中设置群组的自由对话模式状态。
    """
    # 将布尔值转换为整数 1 或 0
    db.db_update_group_setting(chat_id, autochat_enabled=int(is_on))
    logger.info(f"群组 {chat_id} 的自由对话模式已在数据库中更新为: {is_on}")
    
def is_auto_chat_on(chat_id: int) -> bool:
    """
    从数据库检查群组的自由对话模式是否开启。
    """
    settings = db.db_get_group_settings(chat_id)
    if not settings:
        return False # 默认关闭
    return bool(settings['autochat_enabled'])

def set_spam_filter_mode(chat_id: int, is_on: bool):
    """
    在数据库中设置群组的垃圾拦截模式状态。
    """
    db.db_update_group_setting(chat_id, spam_filter_enabled=int(is_on))
    logger.info(f"群组 {chat_id} 的垃圾拦截模式已在数据库中更新为: {is_on}")

def is_spam_filter_on(chat_id: int) -> bool:
    """
    从数据库检查群组的垃圾拦截模式是否开启。
    """
    settings = db.db_get_group_settings(chat_id)
    # 如果没有设置记录，默认为开启
    if not settings:
        return True
    # 处理可能为空的情况，虽然我们设置了默认值，但这是个好习惯
    if settings['spam_filter_enabled'] is None:
        return True
    return bool(settings['spam_filter_enabled'])

def toggle_group_checkin(chat_id: int) -> bool:
    """切换群组的签到功能状态，并返回更新后的新状态。"""
    current_status = is_group_checkin_on(chat_id)
    new_status = not current_status
    
    db.db_update_group_setting(chat_id, checkin_enabled=int(new_status))
    logger.info(f"群组 {chat_id} 的签到功能已在数据库中切换为: {new_status}")
    return new_status

def is_group_checkin_on(chat_id: int) -> bool:
    """从数据库检查群组的签到功能是否开启。"""
    settings = db.db_get_group_settings(chat_id)
    if not settings:
        return False # 默认关闭
    return bool(settings['checkin_enabled'])

# --- 启动时不再需要加载任何数据 ---
# _load_data()