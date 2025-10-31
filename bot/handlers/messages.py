# bot/handlers/messages.py

import logging
import re
import asyncio
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
from telegram import Update, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, ChatMember
from telegram.constants import ChatAction, ChatType, ParseMode
from telegram.ext import ContextTypes, ApplicationHandlerStop
from telegram.error import TelegramError

from . import helpers
from .. import ai_helper, memory, faq_manager, ad_blocker, statistics, user_manager
from ..keyboards import get_copy_code_keyboard

# --- 【核心修正】从 commands.py 导入所需的命令函数 ---
from .commands import checkin_command, points_command, shop_command

logger = logging.getLogger(__name__)

# --- 防刷屏与黑名单 ---
SPAM_MESSAGE_COUNT = 3
SPAM_TIME_WINDOW_SECONDS = 3
BLACKLIST_DURATION_SECONDS = 3600
user_message_timestamps = defaultdict(lambda: deque(maxlen=SPAM_MESSAGE_COUNT))
already_notified_users = set()


async def spam_check_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (update.message and update.message.date and update.effective_user):
        return

    user = update.effective_user
    chat = update.effective_chat
    
    blacklist_entry = statistics.db_get_blacklist_entry(user.id)
    if blacklist_entry:
        try:
            expiration_time = datetime.fromisoformat(blacklist_entry['expiration_timestamp'])
            now = datetime.now(timezone.utc)

            if expiration_time > now:
                remaining_time = expiration_time - now
                time_str = helpers._format_time_delta(remaining_time)
                notification_key = (chat.id, user.id)

                if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                    if notification_key not in already_notified_users:
                        await update.message.reply_text(f"用户 {helpers.escape_markdown_v2(user.full_name)} 已被禁言。剩余时间: *{time_str}*\\.", parse_mode=ParseMode.MARKDOWN_V2)
                        already_notified_users.add(notification_key)
                else:
                    await update.message.reply_text(f"您当前已被禁言。剩余时间: *{time_str}*\\.", parse_mode=ParseMode.MARKDOWN_V2)
                raise ApplicationHandlerStop
            else:
                statistics.db_remove_from_blacklist(user.id)
                for key in list(already_notified_users):
                    if key[1] == user.id:
                        already_notified_users.remove(key)

        except (ValueError, TypeError):
            statistics.db_remove_from_blacklist(user.id)

    message_time = update.message.date
    user_message_timestamps[user.id].append(message_time)
    
    if len(user_message_timestamps[user.id]) == SPAM_MESSAGE_COUNT:
        time_diff = (message_time - user_message_timestamps[user.id][0]).total_seconds()
        
        if time_diff < SPAM_TIME_WINDOW_SECONDS:
            expiration_time = datetime.now(timezone.utc) + timedelta(seconds=BLACKLIST_DURATION_SECONDS)
            statistics.db_add_to_blacklist(user.id, expiration_time.isoformat())
            
            user_message_timestamps[user.id].clear()
            
            user_full_name_escaped = helpers.escape_markdown_v2(user.full_name)
            user_mention = f"用户 *{user_full_name_escaped}* (@{helpers.escape_markdown_v2(user.username)})" if user.username else f"用户 *{user_full_name_escaped}*"
            
            if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                try:
                    bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
                    if bot_member.can_restrict_members:
                        mute_duration_tg = datetime.now() + timedelta(seconds=BLACKLIST_DURATION_SECONDS)
                        await context.bot.restrict_chat_member(
                            chat_id=chat.id,
                            user_id=user.id,
                            permissions=ChatPermissions(can_send_messages=False),
                            until_date=mute_duration_tg
                        )
                        await update.message.reply_text(f"{user_mention} 因刷屏已被禁言1小时。", parse_mode=ParseMode.MARKDOWN_V2)
                    else:
                        await update.message.reply_text(f"检测到来自 {user_mention} 的刷屏行为。请授予我管理员权限以执行禁言。", parse_mode=ParseMode.MARKDOWN_V2)
                except Exception:
                    await update.message.reply_text(f"{user_mention} 因刷屏行为已被临时限制。", parse_mode=ParseMode.MARKDOWN_V2)
            else:
                await update.message.reply_text("您因刷屏已被禁言1小时。")
                
            raise ApplicationHandlerStop

async def message_filter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    lang_code = helpers.get_display_lang(update)
    if not message or not message.text or chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return
    if not user_manager.is_spam_filter_on(chat.id):
        return
    if await helpers._is_admin(update, context):
        return
    is_ad = ad_blocker.is_spam(message.text) or re.search(r'https?://\S+', message.text)
    if is_ad:
        try:
            await message.delete()
            logger.info(f"在群组 {chat.id} 中删除了来自用户 {user.id} 的潜在广告消息。")
            warning_level = memory.record_and_get_warning_level(chat.id, user.id)
            user_name = helpers.escape_markdown_v2(user.first_name)
            if warning_level == 1:
                warn_text = helpers.get_text('spam_warning_first', lang_code, user_name=user_name)
                await helpers.send_or_reply_with_or_without_buttons(update, warn_text, context)
            elif warning_level == 2:
                warn_text = helpers.get_text('spam_warning_second', lang_code, user_name=user_name)
                await helpers.send_or_reply_with_or_without_buttons(update, warn_text, context)
            else:
                mute_duration_seconds = 3600
                warn_text = helpers.get_text('spam_final_warning_mute', lang_code, user_name=user_name)
                try:
                    bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
                    if bot_member.can_restrict_members:
                        mute_until = datetime.now(timezone.utc) + timedelta(seconds=mute_duration_seconds)
                        await context.bot.restrict_chat_member(
                            chat_id=chat.id,
                            user_id=user.id,
                            permissions=ChatPermissions(can_send_messages=False),
                            until_date=mute_until
                        )
                        statistics.db_add_to_blacklist(user.id, mute_until.isoformat())
                        await helpers.send_or_reply_with_or_without_buttons(update, warn_text, context)
                    else:
                        logger.warning(f"尝试禁言用户 {user.id} 失败，没有禁言权限。")
                except TelegramError as e:
                    logger.error(f"禁言用户 {user.id} 时发生错误: {e}")
        except TelegramError as e:
            logger.warning(f"处理广告消息时出错 (可能没有删除权限): {e}")
        raise ApplicationHandlerStop

async def my_chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.my_chat_member:
        return
    chat = update.my_chat_member.chat
    inviter = update.my_chat_member.from_user
    old_status = update.my_chat_member.old_chat_member.status
    new_status = update.my_chat_member.new_chat_member.status
    logger.info(
        f"机器人状态在群组 {chat.id} ({chat.title}) 发生变化: "
        f"由 {old_status} -> {new_status}，操作者: {inviter.id} ({inviter.full_name})"
    )
    is_newly_added = new_status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR] and old_status in [ChatMember.LEFT, ChatMember.BANNED]
    if is_newly_added:
        statistics.update_known_chat(chat.id, chat.title, added_by_user_id=inviter.id)
        logger.info(f"成功记录新群组 {chat.title}，由用户 {inviter.full_name} 添加。")
        lang_code = helpers.get_display_lang(update)
        
        # --- 【核心修正】在所有 get_text 调用前添加 helpers. 前缀 ---
        welcome_text = helpers.get_text('group_welcome', lang_code)
        
        is_checkin_on = user_manager.is_group_checkin_on(chat.id)
        checkin_button_text = helpers.get_text('checkin_status_button_on', lang_code) if is_checkin_on else helpers.get_text('checkin_status_button_off', lang_code)
        # --- 【修正结束】 ---

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("English", callback_data="set_group_lang_en"),
                InlineKeyboardButton("简体中文", callback_data="set_group_lang_zh")
            ],
            [
                InlineKeyboardButton(checkin_button_text, callback_data="toggle_checkin")
            ]
        ])
        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=welcome_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard
            )
        except TelegramError as e:
            logger.error(f"发送欢迎消息失败: {e}")
            plain_text_welcome = "Hello! I'm Stardust Assistant. Thanks for adding me. Admins can use /language to set my language for this group."
            await context.bot.send_message(chat_id=chat.id, text=plain_text_welcome)

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from .commands import search_command
    from .callbacks import generate_ranking_text
    
    message = update.effective_message
    if not message or not message.text: return
    chat = update.effective_chat
    
    if chat.type == ChatType.PRIVATE and context.user_data.get('next_message_is_search'):
        context.user_data['next_message_is_search'] = False
        context.args = message.text.split()
        await search_command(update, context)
        return

    user = update.effective_user
    lang_code = helpers.get_display_lang(update)
    original_user_message = message.text.strip()
    chat_id = chat.id
    user_message_id = message.message_id

    statistics.save_message(
        chat_id=chat_id, chat_title=chat.title if chat.type != ChatType.PRIVATE else "Private Chat",
        chat_username=chat.username, user_id=user.id if user else chat_id,
        user_name=user.full_name if user else chat.title,
        user_username=user.username if user else None, text=original_user_message
    )

    # --- 关键词处理与双向删除 ---
    
    if original_user_message == "签到":
        await checkin_command(update, context)
        return

    if original_user_message == "积分":
        await points_command(update, context)
        return
        
    if original_user_message in ["奖品", "商店"]:
        await shop_command(update, context)
        return

    ranking_keyword_map = {
        "本群今日发言": {'scope': 'local', 'rank_type': 'users', 'period': 'today'},
        "本群本周发言": {'scope': 'local', 'rank_type': 'users', 'period': 'week'},
        "本群本月发言": {'scope': 'local', 'rank_type': 'users', 'period': 'month'},
        "全服今日发言": {'scope': 'global', 'rank_type': 'users', 'period': 'today'},
        "全服本周发言": {'scope': 'global', 'rank_type': 'users', 'period': 'week'},
        "全服本月发言": {'scope': 'global', 'rank_type': 'users', 'period': 'month'},
    }
    if original_user_message in ranking_keyword_map:
        params = ranking_keyword_map[original_user_message]
        ranking_text = await generate_ranking_text(
            scope=params['scope'], rank_type=params['rank_type'], period=params['period'],
            chat_id=chat_id, lang_code=lang_code
        )
        await helpers.send_or_reply_with_or_without_buttons(
            update, ranking_text, context, is_reply=True, user_message_id_to_delete=user_message_id
        )
        return

    SEARCH_KEYWORDS = ['搜索', '搜', 'search']
    for keyword in SEARCH_KEYWORDS:
        if original_user_message.lower().startswith(keyword):
            query_text = original_user_message[len(keyword):].strip()
            if query_text:
                context.args = query_text.split()
                await search_command(update, context)
                return
    
    # --- 发言获取积分逻辑 (最终版，1秒冷却) ---
    if len(original_user_message) > 5 and user and chat.type != ChatType.PRIVATE:
        statistics.db_add_points(user.id, chat.id, 1, cooldown_seconds=1)

    # --- AI 对话 / FAQ 逻辑 ---
    bot_username = (await context.bot.get_me()).username
    is_private_chat = chat.type == ChatType.PRIVATE
    is_mention = f"@{bot_username}" in original_user_message
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id
    is_auto_mode = user_manager.is_auto_chat_on(chat_id)

    if not (is_private_chat or is_mention or is_reply_to_bot or is_auto_mode):
        answer = faq_manager.find_similar_question(chat_id, original_user_message)
        if answer:
            prefix = helpers.get_text('reply_auto_reply_prefix', lang_code)
            escaped_answer = helpers.escape_markdown_v2(answer)
            full_reply = f"{prefix}\n\n{escaped_answer}"
            await helpers.send_or_reply_with_or_without_buttons(
                update, full_reply, context, is_reply=True, user_message_id_to_delete=user_message_id
            )
        return
    
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    prompt_text = original_user_message.replace(f"@{bot_username}", "").strip()
    if not prompt_text: return
    history = memory.get_chat_history(chat_id)
    history.append({"role": "user", "content": prompt_text, "timestamp": datetime.now(timezone.utc).isoformat()})
    try:
        user_full_name = user.full_name if user else chat.title
        ai_response = await asyncio.to_thread(
            ai_helper.generate_ai_response,
            chat_history=list(history), new_prompt=prompt_text,
            user_name=user_full_name, lang_code=lang_code
        )
        history.append({"role": "model", "content": ai_response, "timestamp": datetime.now(timezone.utc).isoformat()})

        reply_markup = None
        code_match = re.search(r"```(?:\w+\n)?(.*?)```", ai_response, re.DOTALL)
        if code_match:
            code_to_copy = code_match.group(1).strip()
            if code_to_copy:
                keyboard, code_id = get_copy_code_keyboard()
                context.bot_data[code_id] = code_to_copy
                reply_markup = keyboard

        await message.reply_text(ai_response, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"chat_handler 调用AI时出错: {e}", exc_info=True)
        await message.reply_text(helpers.get_text('internal_error', lang_code))

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang_code = helpers.get_display_lang(update)
    chat_id = chat.id
    bot_username = (await context.bot.get_me()).username
    is_private_chat = chat.type == ChatType.PRIVATE
    is_mention = update.message.caption and f"@{bot_username}" in update.message.caption
    is_reply_to_bot = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
    is_auto_mode = user_manager.is_auto_chat_on(chat_id)
    if not (is_private_chat or is_mention or is_reply_to_bot or is_auto_mode):
        return
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    prompt_text = (update.message.caption or helpers.get_text('describe_image_prompt', lang_code)).replace(f"@{bot_username}", "").strip()
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
    except Exception as e:
        logger.error(f"下载图片失败: {e}")
        await update.message.reply_text(helpers.get_text('internal_error', lang_code))
        return
    history = memory.get_chat_history(chat_id)
    history.append({"role": "user", "content": prompt_text, "timestamp": datetime.now(timezone.utc).isoformat()})
    try:
        ai_response = await asyncio.to_thread(
            ai_helper.generate_ai_response,
            chat_history=list(history), new_prompt=prompt_text,
            user_name=user.full_name, lang_code=lang_code,
            image_bytes=bytes(photo_bytes)
        )
        history.append({"role": "model", "content": ai_response, "timestamp": datetime.now(timezone.utc).isoformat()})
        reply_markup = None
        code_match = re.search(r"```(?:\w+\n)?(.*?)```", ai_response, re.DOTALL)
        if code_match:
            code_to_copy = code_match.group(1).strip()
            if code_to_copy:
                keyboard, code_id = get_copy_code_keyboard()
                context.bot_data[code_id] = code_to_copy
                reply_markup = keyboard
        await update.message.reply_text(ai_response, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"photo_handler 调用AI时出错: {e}", exc_info=True)
        await update.message.reply_text(helpers.get_text('internal_error', lang_code))

async def sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
    
    is_private_chat = chat.type == ChatType.PRIVATE
    is_reply_to_bot = False
    if message.reply_to_message:
        is_reply_to_bot = message.reply_to_message.from_user.id == context.bot.id
    is_auto_mode = False
    if chat.type != ChatType.PRIVATE:
        is_auto_mode = user_manager.is_auto_chat_on(chat.id)

    if not (is_private_chat or is_reply_to_bot or is_auto_mode):
        return

    await update.message.reply_text("好可爱的贴纸！👍")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("处理更新时发生异常:", exc_info=context.error)