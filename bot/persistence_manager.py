# bot/persistence_manager.py (最终清理版)

import logging
from . import memory # 现在只需要保存聊天记录

logger = logging.getLogger(__name__)

def save_all_data():
    """
    持久化所有需要定期保存的内存数据。
    目前只剩下聊天记录缓存。
    """
    try:
        logger.info("正在执行数据持久化保存 (聊天记录)...")
        memory._save_chat_histories()
        logger.info("聊天记录保存成功。")
    except Exception as e:
        logger.error(f"持久化保存聊天记录时发生错误: {e}", exc_info=True)

async def periodic_save_job(context):
    save_all_data()