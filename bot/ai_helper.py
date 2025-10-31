# bot/ai_helper.py (已改进错误处理和反馈的最终完整版)
from __future__ import annotations

import logging
import os
import hashlib
from PIL import Image
from io import BytesIO
from typing import Optional
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import diskcache

from .key_manager import api_key_manager
from .config import GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_ENGINE_ID
from .localization import get_text

# --- 缓存设置 ---
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'ai_cache')
os.makedirs(CACHE_DIR, exist_ok=True)
response_cache = diskcache.Cache(CACHE_DIR, size_limit=256 * 1024 * 1024)

logger = logging.getLogger(__name__)


def get_system_instruction(lang_code: str) -> str:
    """根据语言代码生成完整的系统指令。"""
    base_prompt = get_text('ai_sys_prompt_base', lang_code)
    formatting_prompt = get_text('ai_sys_prompt_formatting', lang_code)
    # 强制要求AI使用指定语言回复
    language_enforcement_prompt = f"\n\n--- Language Mandate ---\nYou MUST reply in the following language code: {lang_code}"
    return base_prompt + formatting_prompt + language_enforcement_prompt


def google_search(query: str, num_results: int = 5) -> Optional[dict]:
    """执行Google自定义搜索并返回原始结果。"""
    logger.info(f"正在执行谷歌搜索，查询: '{query}'")
    if not GOOGLE_SEARCH_API_KEY or not GOOGLE_SEARCH_ENGINE_ID:
        logger.error("谷歌搜索的 API_KEY 或 SEARCH_ENGINE_ID 未配置。")
        return None
    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_SEARCH_API_KEY)
        res = service.cse().list(q=query, cx=GOOGLE_SEARCH_ENGINE_ID, num=num_results).execute()
        if 'items' not in res or not res['items']:
            logger.warning(f"谷歌搜索'{query}'没有返回结果。")
            return None
        return res
    except Exception as e:
        logger.error(f"谷歌搜索时发生未知错误: {e}", exc_info=True)
        return None


def generate_ai_response(chat_history: list, new_prompt: str, user_name: str, lang_code: str, image_bytes: bytes = None) -> str:
    """
    通过轮换API密钥来生成AI响应，并提供更清晰的错误反馈。
    """
    # 如果没有图片，为纯文本请求创建缓存键
    cache_key = None
    if not image_bytes:
        history_str = "".join([msg.get('content', '') for msg in chat_history])
        raw_key = f"{lang_code}-{history_str}-{new_prompt}"
        cache_key = hashlib.sha256(raw_key.encode('utf-8')).hexdigest()

        if cache_key in response_cache:
            logger.info(f"缓存命中: 为哈希键 '{cache_key[:8]}...' 返回缓存的响应。")
            return response_cache.get(cache_key)

    # 加上初始尝试，总共可以尝试 len(keys) + 1 次
    max_retries = len(api_key_manager.keys)
    attempt = 0
    while attempt <= max_retries:
        current_key = api_key_manager.get_current_key()
        if not current_key:
            # 如果一开始就没有可用的密钥
            logger.error("配置中没有任何可用的Google AI API密钥。")
            return get_text('internal_error', lang_code)

        try:
            genai.configure(api_key=current_key)
            system_instruction = get_system_instruction(lang_code)
            model = genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                system_instruction=system_instruction
            )
            
            content_parts = []
            if image_bytes:
                img = Image.open(BytesIO(image_bytes))
                content_parts.append(img)
            content_parts.append(new_prompt)
            
            # 过滤掉不含 'content' 的历史记录项
            gemini_history = [
                {"role": "user" if msg["role"] == "user" else "model", "parts": [{"text": msg["content"]}]}
                for msg in chat_history if "content" in msg and msg["content"]
            ]
            
            chat_session = model.start_chat(history=gemini_history)
            response = chat_session.send_message(content_parts)
            final_response_text = response.text

            # 如果响应成功且是纯文本，则存入缓存
            if not image_bytes and cache_key:
                response_cache.set(cache_key, final_response_text, expire=3600)
            
            return final_response_text

        except google_exceptions.ResourceExhausted as e:
            logger.warning(f"API密钥配额耗尽: {e}")
            api_key_manager.switch_to_next_key()
            attempt += 1
            if attempt <= max_retries:
                logger.info("正在尝试使用下一个密钥重试...")
            continue
        
        except Exception as e:
            # 【修改】添加强制打印，以便在终端直接看到任何未知错误
            print(f"DEBUG: AI call failed with a non-retriable error: {e}")
            logger.error(f"调用 Gemini API 时发生未知错误: {e}", exc_info=True)
            # 遇到未知错误，直接返回，不再尝试其他密钥
            return get_text('internal_error', lang_code)

    # 【修改】如果 while 循环正常结束，说明所有密钥都已尝试过且均因用量耗尽而失败
    logger.error("所有Google AI API密钥均已耗尽或无效！机器人已放弃尝试。")
    return get_text('internal_error', lang_code)