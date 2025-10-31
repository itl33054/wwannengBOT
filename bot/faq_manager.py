# bot/faq_manager.py (已完全改造为使用数据库)
from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from typing import List, Dict, Optional

# 导入 statistics 模块作为数据库访问的唯一入口
from . import statistics as db

logger = logging.getLogger(__name__)

# --- 相似度阈值 ---
# 当一个新问题的相似度得分高于这个值时，就会触发自动回复
# 【修改】从 0.50 提高到 0.75，以大幅减少误判，提高准确性
SIMILARITY_THRESHOLD = 0.75

# --- 删除了所有与 JSON 文件、路径、全局 faqs 字典相关的代码 ---


# --- 核心功能 ---

def _extract_keywords(text: str) -> str:
    """
    从文本中提取有意义的关键词，并返回一个以空格分隔的字符串，以便存入数据库。
    """
    # 移除标点符号和多余空格
    cleaned_text = re.sub(r'[^\w\s]', '', text.lower()).strip()
    # 按空格分割，并移除空字符串，最后重新组合
    return " ".join([word for word in cleaned_text.split() if word])

def add_faq(chat_id: int, question: str, answer: str) -> bool:
    """
    为指定群组在数据库中添加一条新的FAQ。
    """
    keywords = _extract_keywords(question)
    
    # 直接调用数据库函数进行添加
    success = db.db_add_faq(chat_id, question, answer, keywords)
    
    if success:
        logger.info(f"为群组 {chat_id} 添加了新FAQ到数据库: '{question[:20]}...'")
    else:
        logger.warning(f"尝试为群组 {chat_id} 添加已存在的FAQ (数据库操作被阻止): '{question[:20]}...'")
        
    return success

def delete_faq(chat_id: int, index: int) -> Optional[str]:
    """
    根据用户看到的列表索引 (从0开始) 删除指定群组的一条FAQ。
    """
    # 因为数据库没有'列表索引'的概念，我们必须先获取列表
    all_faqs = get_faqs_for_chat(chat_id)
    
    # 检查索引是否有效
    if not (0 <= index < len(all_faqs)):
        logger.warning(f"尝试为群组 {chat_id} 删除无效的FAQ索引: {index}")
        return None

    # 从列表中找到要删除项的数据库主键 ID
    item_to_delete = all_faqs[index]
    faq_id_to_delete = item_to_delete['id']
    deleted_question_text = item_to_delete['question']
    
    # 根据主键 ID 调用数据库删除函数
    if db.db_delete_faq(faq_id_to_delete):
        logger.info(f"从群组 {chat_id} 的数据库中删除了FAQ (ID: {faq_id_to_delete})")
        return deleted_question_text
    else:
        # 这种情况很少发生，但作为保障
        logger.error(f"尝试从数据库删除FAQ (ID: {faq_id_to_delete}) 失败")
        return None

def get_faqs_for_chat(chat_id: int) -> List[Dict]:
    """
    从数据库获取指定群组的所有FAQ列表。
    """
    # 从数据库获取 sqlite3.Row 对象列表
    results_from_db = db.db_get_faqs_for_chat(chat_id)
    
    # 将其转换为标准的字典列表，以保持与旧代码的兼容性
    return [dict(row) for row in results_from_db]

def find_similar_question(chat_id: int, new_question: str) -> Optional[str]:
    """
    在指定群组的FAQ库中查找与新问题最相似的问题。
    如果找到相似度超过阈值的问题，则返回其答案。
    """
    # 核心逻辑不变，只是数据源变了
    all_faqs = get_faqs_for_chat(chat_id)
    
    if not all_faqs:
        return None

    best_match_answer = None
    highest_similarity = 0.0

    # 简单优化：如果消息过短，则不进行匹配
    if len(new_question) < 1:
        return None
        
    # 将新问题转换为小写以进行不区分大小写的比较
    lower_new_question = new_question.lower()

    for item in all_faqs:
        # 使用SequenceMatcher计算两个字符串的相似度
        similarity = SequenceMatcher(None, lower_new_question, item['question'].lower()).ratio()
        
        if similarity > highest_similarity:
            highest_similarity = similarity
            best_match_answer = item['answer']

    if highest_similarity >= SIMILARITY_THRESHOLD:
        logger.info(f"为问题 '{new_question[:30]}...' 找到了相似度为 {highest_similarity:.2f} 的匹配。")
        return best_match_answer
        
    return None

# --- 启动时不再需要加载任何数据 ---
# _load_faqs()