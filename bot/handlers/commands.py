# bot/handlers/commands.py

import re
import telegram
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes
from telegram.error import TelegramError

# 【最终修正】导入所有需要的模块
from . import helpers
from .. import memory, ai_helper, faq_manager, user_manager, statistics
from ..localization import get_text


logger = logging.getLogger(__name__)

# --- 主菜单构建与发送函数 ---
async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    lang_code = helpers.get_display_lang(update)
    user_name = helpers.escape_markdown_v2(user.first_name)
    
    keyboard = [
        [
            InlineKeyboardButton(get_text('settings_button_admin_groups', lang_code), callback_data='menu_action_admin_groups'),
            InlineKeyboardButton(get_text('menu_button_search', lang_code), callback_data='menu_action_search')
        ],
        [
            InlineKeyboardButton(get_text('menu_button_summary', lang_code), callback_data='menu_action_summary'),
            InlineKeyboardButton(get_text('menu_button_mystats', lang_code), callback_data='menu_action_mystats')
        ],
        [
            InlineKeyboardButton(get_text('menu_button_settings', lang_code), callback_data='menu_action_settings'),
            InlineKeyboardButton(get_text('menu_button_help', lang_code), callback_data='menu_action_help')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    menu_text = get_text('menu_title', lang_code, user_name=user_name)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        try:
            await update.callback_query.edit_message_text(text=menu_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
            context.chat_data['last_menu_id'] = update.callback_query.message.message_id
        except TelegramError as e:
            if "message is not modified" not in str(e).lower():
                logger.error(f"返回主菜单时编辑消息失败: {e}")
    else:
        if 'last_menu_id' in context.chat_data:
            try:
                await context.bot.delete_message(chat_id=chat.id, message_id=context.chat_data['last_menu_id'])
            except TelegramError:
                pass
        sent_message = await update.effective_message.reply_text(text=menu_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
        context.chat_data['last_menu_id'] = sent_message.message_id


# --- 命令处理器 ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == ChatType.PRIVATE:
        await send_main_menu(update, context)
    else:
        lang_code = helpers.get_display_lang(update)
        welcome_text = get_text('group_welcome', lang_code)
        
        # --- 【核心修改】使用新的、更清晰的按钮文本 ---
        is_checkin_on = user_manager.is_group_checkin_on(chat.id)
        checkin_button_text = get_text('checkin_status_button_on', lang_code) if is_checkin_on else get_text('checkin_status_button_off', lang_code)
        # --- 【修改结束】 ---

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("English", callback_data="set_group_lang_en"),
                InlineKeyboardButton("简体中文", callback_data="set_group_lang_zh")
            ],
            [
                InlineKeyboardButton(checkin_button_text, callback_data="toggle_checkin")
            ]
        ])
        
        await helpers.send_or_reply_with_or_without_buttons(
            update,
            text=welcome_text,
            context=context,
            reply_markup=keyboard,
            is_reply=True,
            user_message_id_to_delete=update.effective_message.message_id
        )

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang_code = helpers.get_display_lang(update)

    if chat.type == ChatType.PRIVATE:
        await send_main_menu(update, context)
    else:
        bot_username = (await context.bot.get_me()).username
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("前往私聊", url=f"https://t.me/{bot_username}?start=menu")]
        ])
        text = "主菜单的完整功能请在与我私聊时使用哦！点击下方按钮即可跳转。"
        await helpers.send_or_reply_with_or_without_buttons(
            update,
            text=text,
            context=context,
            reply_markup=keyboard,
            is_reply=True,
            user_message_id_to_delete=update.effective_message.message_id
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = helpers.get_display_lang(update)
    back_button = InlineKeyboardButton(get_text('menu_button_back', lang_code), callback_data='menu_action_back')
    if update.effective_chat.type == ChatType.PRIVATE:
        await update.message.reply_text(get_text('help_text', lang_code), parse_mode=ParseMode.MARKDOWN_V2, reply_markup=InlineKeyboardMarkup([[back_button]]))
    else:
        await update.message.reply_text(get_text('help_text', lang_code), parse_mode=ParseMode.MARKDOWN_V2)


async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = helpers.get_display_lang(update)
    memory.clear_chat_history(update.effective_chat.id)
    await update.message.reply_text(get_text('new_conversation', lang_code), parse_mode=ParseMode.MARKDOWN_V2)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = helpers.get_display_lang(update)
    query = " ".join(context.args)

    if not query:
        await update.message.reply_text(get_text('search_prompt', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
        return

    # 【关键修复】对用户输入的查询内容进行转义，以防它包含特殊字符
    escaped_query = helpers.escape_markdown_v2(query)

    placeholder_message = await update.message.reply_text(
        get_text('searching_for', lang_code, query=escaped_query),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    search_results = await asyncio.to_thread(ai_helper.google_search, query, num_results=10)
    if not search_results or 'items' not in search_results:
        await placeholder_message.edit_text(
            get_text('search_no_results', lang_code, query=escaped_query),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    items = search_results['items']
    search_id = memory.store_search_query(query)
    context.bot_data[search_id] = items
    start_index = 0
    end_index = helpers.SEARCH_RESULTS_PER_PAGE
    text_parts = [get_text('search_results_title', lang_code, query=escaped_query)]
    for i, item in enumerate(items[start_index:end_index]):
        # 【关键修复】对从Google API获取的 title 和 snippet 进行转义
        title = helpers.escape_markdown_v2(item.get('title', 'No Title'))
        link = item.get('link') # 链接本身不需要转义
        snippet = helpers.escape_markdown_v2(item.get('snippet', 'No snippet available.').replace('\n', ' '))
        text_parts.append(f"{i + 1}\\. [{title}]({link})\n_{snippet}_")

    reply_markup = helpers.create_search_pagination_keyboard(search_id, 0, len(items), lang_code)
    await placeholder_message.edit_text(
        "\n\n".join(text_parts),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )
    
    if update.effective_chat.type == ChatType.PRIVATE:
        back_button = InlineKeyboardButton(get_text('menu_button_back', lang_code), callback_data='menu_action_back')
        await placeholder_message.reply_text("👆 这是您的搜索结果。", reply_markup=InlineKeyboardMarkup([[back_button]]))


async def privacy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = helpers.get_display_lang(update)
    privacy_policy_url = "https://telegra.ph/Stardust-Assistant-Privacy-Policy-08-15"
    text = get_text('privacy_policy_text', lang_code)
    keyboard = [[InlineKeyboardButton(get_text('privacy_button', lang_code), url=privacy_policy_url)]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = helpers.get_display_lang(update)
    rules_url = "https://telegra.ph/Stardust-Assistant-Terms-of-Service-08-15"
    text = get_text('rules_text', lang_code)
    keyboard = [[InlineKeyboardButton(get_text('rules_button', lang_code), url=rules_url)]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)

async def listreply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    lang_code = helpers.get_display_lang(update)
    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text(get_text('group_only_command', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
        return
    faqs = faq_manager.get_faqs_for_chat(chat.id)
    if not faqs:
        await update.message.reply_text(get_text('reply_list_empty', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
        return
    text_parts = [get_text('reply_list_title', lang_code)]
    for i, item in enumerate(faqs):
        question_escaped = helpers.escape_markdown_v2(item['question'])
        text_parts.append(f"*{i + 1}\\.* _{question_escaped}_")
    await update.message.reply_text("\n".join(text_parts), parse_mode=ParseMode.MARKDOWN_V2)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    lang_code = helpers.get_display_lang(update)

    if chat.type != ChatType.PRIVATE:
        await helpers.send_or_reply_with_or_without_buttons(
            update, "请私聊我以进行个人设置哦！", context, is_reply=True,
            user_message_id_to_delete=update.effective_message.message_id
        )
        return
    
    if 'last_menu_id' in context.chat_data:
        try:
            await context.bot.delete_message(chat_id=chat.id, message_id=context.chat_data['last_menu_id'])
            del context.chat_data['last_menu_id']
        except TelegramError:
            pass

    text = get_text('settings_menu_title', lang_code)
    is_ranking_enabled = user_manager.is_user_ranking_enabled(user.id)
    ranking_button_text = get_text('settings_button_ranking_on', lang_code) if is_ranking_enabled else get_text('settings_button_ranking_off', lang_code)
    keyboard = [
        [InlineKeyboardButton(get_text('settings_button_language', lang_code), callback_data='settings_language')],
        [InlineKeyboardButton(ranking_button_text, callback_data='settings_toggle_ranking')],
        [InlineKeyboardButton(get_text('menu_button_back', lang_code), callback_data='menu_action_back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    sent_message = await update.effective_message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
    context.chat_data['last_menu_id'] = sent_message.message_id
    
async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = helpers.get_display_lang(update)
    chat = update.effective_chat
    
    if chat.type == ChatType.PRIVATE:
        if 'last_menu_id' in context.chat_data:
            try:
                await context.bot.delete_message(chat_id=chat.id, message_id=context.chat_data['last_menu_id'])
                del context.chat_data['last_menu_id']
            except TelegramError:
                pass
        text = get_text('summary_private_intro', lang_code)
        keyboard = [
            [InlineKeyboardButton(get_text('button_global_user_rank', lang_code), callback_data='menu_rank_global_users')],
            [InlineKeyboardButton(get_text('button_global_topic_rank', lang_code), callback_data='menu_rank_global_topics')],
            [InlineKeyboardButton(get_text('button_global_group_rank', lang_code), callback_data='menu_rank_groups')],
            [InlineKeyboardButton(get_text('menu_button_back', lang_code), callback_data='menu_action_back')]
        ]
        sent_message = await update.effective_message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN_V2)
        context.chat_data['last_menu_id'] = sent_message.message_id
        return

    try: 
        if update.effective_message:
            await update.effective_message.delete()
    except TelegramError: 
        pass
    
    keyboard = [
        [InlineKeyboardButton(get_text('button_activity_chart', lang_code), callback_data='chart_activity_menu')],
        [
            InlineKeyboardButton(get_text('button_local_user_rank', lang_code), callback_data='menu_rank_local_users'),
            InlineKeyboardButton(get_text('button_local_topic_rank', lang_code), callback_data='menu_rank_local_topics')
        ],
        [
            InlineKeyboardButton(get_text('button_global_group_rank', lang_code), callback_data='menu_rank_groups'),
            InlineKeyboardButton(get_text('button_global_user_rank', lang_code), callback_data='menu_rank_global_users')
        ],
        [InlineKeyboardButton(get_text('button_global_topic_rank', lang_code), callback_data='menu_rank_global_topics')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = get_text('summary_menu_title', lang_code)
    
    await helpers.send_or_reply_with_or_without_buttons(
        update, text=text, context=context, reply_markup=reply_markup
    )

async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from .callbacks import _send_single_group_stats_pm
    
    chat = update.effective_chat
    user = update.effective_user
    lang_code = helpers.get_display_lang(update)

    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await _send_single_group_stats_pm(user, chat.id, chat.title, context, lang_code)
        await helpers.send_or_reply_with_or_without_buttons(
            update, get_text('mystats_group_notification', lang_code), context,
            user_message_id_to_delete=update.effective_message.message_id
        )
        return

    if chat.type == ChatType.PRIVATE:
        keyboard = [
            [InlineKeyboardButton(get_text('mystats_button_select_group', lang_code), callback_data='mystats_select_group')],
            [InlineKeyboardButton(get_text('mystats_button_all_groups_rank', lang_code), callback_data='mystats_all_groups_rank')],
            [InlineKeyboardButton(get_text('mystats_button_global', lang_code), callback_data='mystats_global')]
        ]
        
        if hasattr(update, 'callback_query') and update.callback_query:
            keyboard.append([InlineKeyboardButton(get_text('menu_button_back', lang_code), callback_data='menu_action_back')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        menu_text = get_text('mystats_private_menu_title', lang_code)
        
        if hasattr(update, 'callback_query') and update.callback_query:
            try:
                await update.callback_query.edit_message_text(menu_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
            except TelegramError as e:
                if "not modified" not in str(e).lower():
                    logger.error(f"编辑 /mystats 菜单失败: {e}")
        else:
            await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)


# --- 积分与商店命令 (仅处理命令，关键词由 chat_handler 负责) ---

async def checkin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    lang_code = helpers.get_display_lang(update)
    
    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text("请在群组中进行签到哦！")
        return

    text_to_send = ""
    if not user_manager.is_group_checkin_on(chat.id):
        text_to_send = "本群的签到功能尚未开启哦，请联系管理员开启。"
    elif statistics.db_check_if_user_checked_in_today(user.id, chat.id):
        text_to_send = get_text('points_checkin_already', lang_code)
    else:
        statistics.db_record_checkin(user.id, chat.id)
        # 【修正】db_add_points 返回一个元组 (success, new_total)
        _, new_total = statistics.db_add_points(user.id, chat.id, 10, cooldown_seconds=0) # 签到不应该有冷却
        text_to_send = get_text('points_checkin_success', lang_code, points=10, total_points=new_total)

    try:
        sent_message = await update.message.reply_text(text_to_send, parse_mode=ParseMode.MARKDOWN_V2)
    except telegram.error.BadRequest as e:
        if "Can't parse entities" in str(e):
            logger.warning(f"MarkdownV2 解析失败，将尝试使用纯文本模式发送: {text_to_send}")
            plain_text = re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text_to_send) # 这是错误的，应该是去掉
            plain_text = re.sub(r'[_*`\[\]~]', '', text_to_send) # 正确的方式是移除格式
            sent_message = await update.message.reply_text(plain_text)
        else:
            raise e

    context.job_queue.run_once(
        helpers.delete_message_job, 15,
        data={'chat_id': chat.id, 'message_id': sent_message.message_id, 'user_message_id': update.effective_message.message_id},
        name=f"delete_checkin_{chat.id}_{sent_message.message_id}"
    )

async def points_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    lang_code = helpers.get_display_lang(update)

    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text("请在群组中查询您的积分。")
        return

    current_points = statistics.db_get_user_points(user.id, chat.id)
    text_to_send = get_text('points_current_balance', lang_code, points=current_points)
    
    try:
        sent_message = await update.message.reply_text(text_to_send, parse_mode=ParseMode.MARKDOWN_V2)
    except telegram.error.BadRequest as e:
        if "Can't parse entities" in str(e):
            plain_text = re.sub(r'[_*`\[\]~]', '', text_to_send)
            sent_message = await update.message.reply_text(plain_text)
        else:
            raise e

    context.job_queue.run_once(
        helpers.delete_message_job, 15,
        data={'chat_id': chat.id, 'message_id': sent_message.message_id, 'user_message_id': update.effective_message.message_id},
        name=f"delete_points_{chat.id}_{sent_message.message_id}"
    )

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    lang_code = helpers.get_display_lang(update)

    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text("请在群组中使用商店功能。")
        return

    user_points = statistics.db_get_user_points(user.id, chat.id)
    
    items = statistics.db_get_shop_items()
    text_parts = [get_text('shop_menu_title', lang_code, points=user_points)]
    if not items:
        text_parts.append(get_text('shop_list_empty', lang_code))
    else:
        for item in items:
            stock_str = get_text('shop_item_stock_infinite', lang_code) if item['stock'] == -1 else str(item['stock'])
            item_line = get_text('shop_item_line', lang_code,
                id=item['id'], name=helpers.escape_markdown_v2(item['name']),
                description=helpers.escape_markdown_v2(item['description'] or ''),
                cost=item['cost'], stock=stock_str
            )
            text_parts.append(item_line)
    
    text_to_send = "\n\n".join(text_parts)
    sent_message = await update.message.reply_text(text_to_send, parse_mode=ParseMode.MARKDOWN_V2)
    context.job_queue.run_once(
        helpers.delete_message_job, 30,
        data={'chat_id': chat.id, 'message_id': sent_message.message_id, 'user_message_id': update.effective_message.message_id},
        name=f"delete_shop_{chat.id}_{sent_message.message_id}"
    )

async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    lang_code = helpers.get_display_lang(update)
    
    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text("请在群组中兑换奖品。")
        return

    try:
        item_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text(get_text('redeem_usage', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
        return
        
    item = statistics.db_get_shop_item_by_id(item_id)
    if not item:
        await update.message.reply_text(get_text('redeem_item_not_found', lang_code, item_id=item_id), parse_mode=ParseMode.MARKDOWN_V2)
        return

    user_points = statistics.db_get_user_points(user.id, chat.id)
    if user_points < item['cost']:
        await update.message.reply_text(get_text('redeem_not_enough_points', lang_code, item_name=helpers.escape_markdown_v2(item['name']), cost=item['cost'], user_points=user_points), parse_mode=ParseMode.MARKDOWN_V2)
        return
        
    if item['stock'] == 0:
        await update.message.reply_text(get_text('redeem_out_of_stock', lang_code, item_name=helpers.escape_markdown_v2(item['name'])), parse_mode=ParseMode.MARKDOWN_V2)
        return
        
    if statistics.db_redeem_item(user.id, chat.id, item):
        await update.message.reply_text(get_text('redeem_success', lang_code, item_name=helpers.escape_markdown_v2(item['name'])), parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await update.message.reply_text(get_text('redeem_error', lang_code), parse_mode=ParseMode.MARKDOWN_V2)