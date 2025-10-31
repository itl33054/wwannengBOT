# bot/handlers/helpers.py
from __future__ import annotations

import logging
import re
import telegram
from datetime import timedelta
from telegram import Update, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatType, ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes
from typing import Union, Optional

from .. import user_manager, statistics
from ..config import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from ..localization import get_text

logger = logging.getLogger(__name__)

# --- 常量 ---
SEARCH_RESULTS_PER_PAGE = 5

# --- 基础辅助函数 ---

def get_display_lang(update: Union[Update, CallbackQuery]) -> str:
    chat = None
    user = None

    if isinstance(update, Update):
        chat = update.effective_chat
        user = update.effective_user
    elif isinstance(update, CallbackQuery):
        chat = update.message.chat if update.message else None
        user = update.from_user

    if chat and chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        group_lang = user_manager.get_group_language(chat.id)
        if group_lang:
            return group_lang

    if user:
        user_lang = user_manager.get_user_language(user.id)
        if user_lang:
            return user_lang

    if user and hasattr(user, 'language_code') and user.language_code:
        lang_code = user.language_code.split('-')[0]
        if lang_code in SUPPORTED_LANGUAGES:
            return lang_code
            
    return DEFAULT_LANGUAGE

def escape_markdown_v2(text: str) -> str:
    if not isinstance(text, str): return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return "".join(f'\\{char}' if char in escape_chars else char for char in text)

def _format_time_delta(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0: return f"{hours}h {minutes}m"
    if minutes > 0: return f"{minutes}m {seconds}s"
    return f"{seconds}s"

def create_search_pagination_keyboard(search_id: str, current_page: int, total_items: int, lang_code: str) -> Optional[InlineKeyboardMarkup]:
    total_pages = (total_items + SEARCH_RESULTS_PER_PAGE - 1) // SEARCH_RESULTS_PER_PAGE
    if total_pages <= 1:
        return None

    buttons = []
    prev_text = "⬅️ " + get_text('button_prev_page', lang_code, default="Prev")
    next_text = get_text('button_next_page', lang_code, default="Next") + " ➡️"
    
    if current_page > 0:
        buttons.append(InlineKeyboardButton(prev_text, callback_data=f"search_page:{search_id}:{current_page - 1}"))
    if current_page < total_pages - 1:
        buttons.append(InlineKeyboardButton(next_text, callback_data=f"search_page:{search_id}:{current_page + 1}"))

    if not buttons:
        return None
    return InlineKeyboardMarkup([buttons])

async def _is_admin(update_or_query: Union[Update, CallbackQuery], context: ContextTypes.DEFAULT_TYPE) -> bool:
    if isinstance(update_or_query, Update):
        chat = update_or_query.effective_chat
        user = update_or_query.effective_user
    elif isinstance(update_or_query, CallbackQuery):
        chat = update_or_query.message.chat if update_or_query.message else None
        user = update_or_query.from_user
    else:
        return False
        
    if not chat or not user: return False
    if chat.type == ChatType.PRIVATE: return True
    
    cache_key = f"is_admin_{chat.id}_{user.id}"
    if context.chat_data.get(cache_key, False):
        return True
        
    try:
        admins = await context.bot.get_chat_administrators(chat.id)
        if user.id in {admin.user.id for admin in admins}:
            context.chat_data[cache_key] = True
            return True
    except TelegramError as e:
        logger.warning(f"无法获取管理员列表: {e}")
    return False

async def handle_private_summary_back(update: Union[Update, CallbackQuery], context: ContextTypes.DEFAULT_TYPE, is_command: bool = False):
    target = update if is_command else update.callback_query
    lang_code = get_display_lang(target)
    text = get_text('summary_private_intro', lang_code)
    keyboard = [[InlineKeyboardButton(get_text('button_global_user_rank', lang_code), callback_data='menu_rank_global_users')],
        [InlineKeyboardButton(get_text('button_global_topic_rank', lang_code), callback_data='menu_rank_global_topics')],
        [InlineKeyboardButton(get_text('button_global_group_rank', lang_code), callback_data='menu_rank_groups')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if is_command:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)

async def proactive_chat_recorder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """一个前置处理器，用于主动记录机器人遇到的每一个群组信息。"""
    chat = update.effective_chat
    if chat and chat.title and str(chat.id).startswith('-100'):
        statistics.update_known_chat(chat.id, chat.title)

# --- 【核心】统一的消息发送与自动删除模块 ---

async def delete_message_job(context: ContextTypes.DEFAULT_TYPE):
    """计划任务的回调函数，用于删除指定消息（可以是机器人和用户的）。"""
    job_context = context.job.data
    chat_id = job_context.get('chat_id')
    bot_message_id = job_context.get('message_id')
    user_message_id = job_context.get('user_message_id')

    # 1. 删除机器人的消息
    if chat_id and bot_message_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=bot_message_id)
            logger.info(f"成功自动删除了机器人消息 {bot_message_id} (来自群组 {chat_id})。")
        except TelegramError as e:
            if "not found" not in str(e).lower():
                logger.warning(f"自动删除机器人消息 {bot_message_id} 时出错: {e}")

    # 2. 如果有用户消息ID，也一并删除
    if chat_id and user_message_id:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=user_message_id)
            logger.info(f"成功自动删除了用户消息 {user_message_id} (来自群组 {chat_id})。")
        except TelegramError as e:
            if "not found" not in str(e).lower():
                logger.warning(f"自动删除用户消息 {user_message_id} 时出错: {e}")
    
    # 【修复】移除了此处重复的代码块。

async def send_or_reply_with_or_without_buttons(
    update_or_query: Union[Update, CallbackQuery],
    text: str,
    context: ContextTypes.DEFAULT_TYPE,
    reply_markup: InlineKeyboardMarkup = None,
    is_reply: bool = False,
    user_message_id_to_delete: int = None
):
    """
    统一的消息发送/回复/编辑处理器，并增加了对MarkdownV2解析失败的优雅降级处理。
    """
    is_query = isinstance(update_or_query, CallbackQuery)
    
    chat = None
    if is_query and update_or_query.message:
        chat = update_or_query.message.chat
    elif isinstance(update_or_query, Update) and update_or_query.effective_chat:
        chat = update_or_query.effective_chat
    elif hasattr(update_or_query, 'callback_query') and update_or_query.callback_query.message:
        chat = update_or_query.callback_query.message.chat

    if not chat:
        logger.warning("在 send_or_reply_with_or_without_buttons 中无法确定 chat 对象")
        return

    sent_message = None

    # 清理旧的定时删除任务
    if is_query and update_or_query.message:
        job_name = f"delete_menu_{chat.id}_{update_or_query.message.message_id}"
        existing_jobs = context.job_queue.get_jobs_by_name(job_name)
        for job in existing_jobs:
            job.schedule_removal()

    try:
        # --- 核心逻辑：尝试用 MarkdownV2 发送/编辑 ---
        if is_query:
            sent_message = await update_or_query.edit_message_text(
                text=text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True
            )
        elif hasattr(update_or_query, 'callback_query'): 
            sent_message = await context.bot.send_message(
                chat_id=chat.id, text=text, reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        elif is_reply and hasattr(update_or_query, 'message'):
            sent_message = await update_or_query.message.reply_text(
                text=text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            sent_message = await context.bot.send_message(
                chat_id=chat.id, text=text, reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN_V2
            )
    except telegram.error.BadRequest as e:
        # --- 【安全网】如果因为Markdown解析失败，则自动降级为纯文本模式重试 ---
        if "Can't parse entities" in str(e):
            logger.warning(f"MarkdownV2 解析失败: {e}. 将自动降级为纯文本模式重试。")
            try:
                # 移除所有可能的MarkdownV2格式化符号
                plain_text = re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', '', text)
                if is_query:
                    sent_message = await update_or_query.edit_message_text(
                        text=plain_text, reply_markup=reply_markup, parse_mode=None,
                        disable_web_page_preview=True
                    )
                # ... 其他发送方式的纯文本降级
                elif hasattr(update_or_query, 'callback_query'): 
                    sent_message = await context.bot.send_message(
                        chat_id=chat.id, text=plain_text, reply_markup=reply_markup, parse_mode=None
                    )
                elif is_reply and hasattr(update_or_query, 'message'):
                    sent_message = await update_or_query.message.reply_text(
                        text=plain_text, reply_markup=reply_markup, parse_mode=None
                    )
                else:
                    sent_message = await context.bot.send_message(
                        chat_id=chat.id, text=plain_text, reply_markup=reply_markup, parse_mode=None
                    )
            except Exception as final_e:
                logger.error(f"纯文本模式重试失败: {final_e}")
        else:
            # 如果是其他类型的错误，仍然记录下来
            logger.error(f"发送或编辑消息时发生未知错误: {e}")
            return


    if sent_message and chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        delete_after_seconds = 120 if reply_markup else 600

        job_data = {
            'chat_id': chat.id,
            'message_id': sent_message.message_id,
        }
        if user_message_id_to_delete:
            job_data['user_message_id'] = user_message_id_to_delete

        new_job_name = f"delete_menu_{chat.id}_{sent_message.message_id}"
        context.job_queue.run_once(
            delete_message_job,
            delete_after_seconds,
            data=job_data,
            name=new_job_name
        )