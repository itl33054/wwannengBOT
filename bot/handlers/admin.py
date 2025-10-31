# bot/handlers/admin.py

import logging
from datetime import datetime, timedelta, timezone # <--- 新增导入
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from telegram import ChatPermissions

from . import helpers
# 【修改】不再导入 blacklist_manager，直接使用 statistics
from .. import faq_manager, user_manager, statistics
from ..localization import get_text
from ..config import DEVELOPER_IDS
from ..statistics import get_user_id_by_username

logger = logging.getLogger(__name__)

# --- 开发者命令 ---
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in DEVELOPER_IDS:
        await update.message.reply_text("抱歉，此命令仅限开发者使用。")
        return
    try:
        username_to_ban = context.args[0]
        user_id_to_ban = get_user_id_by_username(username_to_ban) or int(username_to_ban)
    except (IndexError, ValueError):
        await update.message.reply_text("用法: /ban <@username 或 user_id>")
        return
        
    # <--- 修改开始 --->
    # 计算24小时后的过期时间戳
    duration_seconds = 86400
    expiration_time = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
    # 调用数据库函数写入黑名单
    statistics.db_add_to_blacklist(user_id_to_ban, expiration_time.isoformat())
    # <--- 修改结束 --->
    
    await update.message.reply_text(f"用户 {user_id_to_ban} 已被封禁24小时。")

# bot/handlers/admin.py

# ... (文件顶部的其他 import 保持不变)
from telegram import ChatPermissions # <--- 确保导入了 ChatPermissions

# ...

# 【函数替换】用下面的新版 unban_command 替换掉旧的
async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang_code = helpers.get_display_lang(update)

    # 1. 权限检查：必须是群聊且使用者是管理员
    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text("请在群组中使用此命令来为用户解除禁言。")
        return
        
    # 同时检查是否为开发者或群管理员
    is_dev = user.id in DEVELOPER_IDS
    is_group_admin = await helpers._is_admin(update, context)
    
    if not (is_dev or is_group_admin):
        await update.message.reply_text(get_text('admin_only_command', lang_code))
        return

    # 2. 参数解析：获取目标用户ID
    try:
        target_user_id = None
        # 方式一：回复消息
        if update.message.reply_to_message:
            target_user_id = update.message.reply_to_message.from_user.id
            target_user_name = update.message.reply_to_message.from_user.full_name
        # 方式二：使用 @username 或 user_id
        elif context.args:
            user_identifier = context.args[0]
            target_user_id = get_user_id_by_username(user_identifier) or int(user_identifier)
            target_user_name = user_identifier # 显示用作标识符的文本
        else:
            await update.message.reply_text("用法: /unban <@username 或 user_id>，或回复某人的消息使用 /unban。")
            return
    except (IndexError, ValueError):
        await update.message.reply_text("无效的用户标识符。请提供有效的 @username 或 user_id。")
        return

    # 3. 执行双重解封
    try:
        # 第一重：解除Telegram群组禁言 (恢复所有默认权限)
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target_user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,  # 一般不恢复
                can_invite_users=True,
                can_pin_messages=False, # 一般不恢复
            )
        )

        # 第二重：从机器人内部黑名单移除
        statistics.db_remove_from_blacklist(target_user_id)
        
        await update.message.reply_text(f"用户 {helpers.escape_markdown_v2(str(target_user_name))} ({target_user_id}) 已在本群成功解除禁言。")

    except TelegramError as e:
        logger.error(f"在群组 {chat.id} 解除用户 {target_user_id} 禁言时出错: {e}")
        await update.message.reply_text(f"操作失败，可能是权限不足或用户不存在。错误: {e}")
    except Exception as e:
        logger.error(f"在群组 {chat.id} 解除用户 {target_user_id} 禁言时发生未知错误: {e}")
        await update.message.reply_text(f"发生未知错误: {e}")

# ... (文件其余部分无需改动)
async def auto_chat_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang_code = helpers.get_display_lang(update)
    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text(get_text('group_only_command', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
        return
    if not await helpers._is_admin(update, context):
        await update.message.reply_text(get_text('admin_only_command', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
        return
    
    user_manager.set_auto_chat_mode(chat.id, True)
    await update.message.reply_text("✅ 自由对话模式已 **开启**。", parse_mode=ParseMode.MARKDOWN)

async def auto_chat_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang_code = helpers.get_display_lang(update)
    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text(get_text('group_only_command', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
        return
    if not await helpers._is_admin(update, context):
        await update.message.reply_text(get_text('admin_only_command', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
        return
        
    user_manager.set_auto_chat_mode(chat.id, False)
    await update.message.reply_text("❌ 自由对话模式已 **关闭**。", parse_mode=ParseMode.MARKDOWN)

async def add_reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang_code = helpers.get_display_lang(update)

    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text(get_text('group_only_command', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
        return
    if not await helpers._is_admin(update, context):
        await helpers.send_or_reply_with_or_without_buttons(
            update, get_text('admin_only_command', lang_code), context
        )
        return
        
    if not (update.message.reply_to_message and update.message.reply_to_message.text):
        await update.message.reply_text(get_text('reply_add_usage', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
        return
        
    question = update.message.reply_to_message.text
    answer = update.message.text.replace('/addreply', '').strip()

    if not answer:
        await update.message.reply_text(get_text('reply_add_usage', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
        return

    if faq_manager.add_faq(chat.id, question, answer):
        await update.message.reply_text(get_text('reply_add_success', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await update.message.reply_text(get_text('reply_add_exists', lang_code), parse_mode=ParseMode.MARKDOWN_V2)

async def del_reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang_code = helpers.get_display_lang(update)

    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text(get_text('group_only_command', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
        return
    if not await helpers._is_admin(update, context):
        await helpers.send_or_reply_with_or_without_buttons(
            update, get_text('admin_only_command', lang_code), context
        )
        return

    try:
        index_to_delete = int(context.args[0]) - 1
    except (IndexError, ValueError):
        await update.message.reply_text(get_text('reply_del_usage', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
        return
    
    deleted_question = faq_manager.delete_faq(chat.id, index_to_delete)
    
    if deleted_question:
        text = get_text('reply_del_success', lang_code, index=index_to_delete + 1, question=helpers.escape_markdown_v2(deleted_question[:20]))
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        text = get_text('reply_del_not_found', lang_code, index=index_to_delete + 1)
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
        
async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang_code = helpers.get_display_lang(update)

    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text(
            "您可以在统一的设置中心更改语言。\n请使用 /settings 命令打开菜单。",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not await helpers._is_admin(update, context):
        try: 
            if update.effective_message:
                await update.effective_message.delete()
        except TelegramError: 
            pass
        await helpers.send_or_reply_with_or_without_buttons(
            update, get_text('admin_only_command', lang_code), context
        )
        return

    try:
        if update.effective_message:
            await update.effective_message.delete()
    except TelegramError:
        pass

    menu_title = get_text('language_menu_title', lang_code)
    buttons = [
        [
            InlineKeyboardButton("English", callback_data="set_group_lang_en"),
            InlineKeyboardButton("简体中文", callback_data="set_group_lang_zh")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await helpers.send_or_reply_with_or_without_buttons(
        update, text=menu_title, context=context, reply_markup=reply_markup
    )