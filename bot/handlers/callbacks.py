import logging
import asyncio
import uuid
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent, CallbackQuery, User
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import TelegramError

# 【修改】从 .. (bot/) 导入外部模块
from .. import memory, user_manager, chart_generator, ai_helper, statistics, faq_manager
# 【修改】从 . (handlers/) 导入内部模块
from . import helpers 
from ..localization import get_text
from ..statistics import (
    get_top_users_by_period, get_top_topics_by_period, get_global_top_users_by_period,
    get_global_top_topics_by_period, get_global_top_groups_by_period
)
from .helpers import (
    get_display_lang, create_search_pagination_keyboard,
    escape_markdown_v2, SEARCH_RESULTS_PER_PAGE, _is_admin,
    send_or_reply_with_or_without_buttons
)

logger = logging.getLogger(__name__)

# --- ConversationHandler states ---
ASK_REPLY_QUESTION, ASK_REPLY_ANSWER = range(2)
# --- 【新增】为添加商店奖品定义新的状态 ---
ASK_ITEM_NAME, ASK_ITEM_DESC, ASK_ITEM_COST, ASK_ITEM_STOCK = range(2, 6)

# ==============================================================================
# Section 0: 可复用的辅助函数 (Reusable Helpers)
# ==============================================================================

async def _send_single_group_stats_pm(user: User, chat_id: int, chat_title: str, context: ContextTypes.DEFAULT_TYPE, lang_code: str):
    """生成单个群组的战绩报告并私聊发送给用户。"""
    try:
        # --- 【核心修正】恢复被遗漏的数据库查询和变量解包部分 ---
        (
            chat_stats,
            (rank_today, count_today),
            (rank_week, count_week),
            (rank_month, count_month),
        ) = await asyncio.gather(
            asyncio.to_thread(statistics.get_user_stats_in_chat, user.id, chat_id),
            asyncio.to_thread(statistics.get_user_rank_in_chat, user.id, chat_id, 'today'),
            asyncio.to_thread(statistics.get_user_rank_in_chat, user.id, chat_id, 'week'),
            asyncio.to_thread(statistics.get_user_rank_in_chat, user.id, chat_id, 'month'),
        )
        # --- 【修正结束】 ---
    except Exception as e:
        logger.error(f"获取用户 {user.id} 在群 {chat_id} 的数据时出错: {e}", exc_info=True)
        await context.bot.send_message(user.id, get_text('internal_error', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
        return

    if chat_stats.get('total_count', 0) == 0:
        await context.bot.send_message(user.id, get_text('mystats_not_enough_data', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
        return

    # 对从 Telegram API 或数据库获取的群组标题进行转义
    group_name = escape_markdown_v2(chat_title)
    
    # 组合文本
    text_parts = [get_text('mystats_title_group', lang_code, group_name=group_name)]
    text_parts.append(get_text('mystats_total_messages', lang_code, count=chat_stats['total_count']))
    if chat_stats.get('first_date'):
        text_parts.append(get_text('mystats_first_message_date', lang_code, date=chat_stats['first_date']))
    
    rank_today_str = get_text('mystats_rank_today', lang_code, rank=rank_today, count=count_today) if rank_today > 0 else get_text('mystats_rank_no_data', lang_code)
    text_parts.append(rank_today_str)
    rank_week_str = get_text('mystats_rank_week', lang_code, rank=rank_week, count=count_week) if rank_week > 0 else get_text('mystats_rank_no_data', lang_code)
    text_parts.append(rank_week_str)
    rank_month_str = get_text('mystats_rank_month', lang_code, rank=rank_month, count=count_month) if rank_month > 0 else get_text('mystats_rank_no_data', lang_code)
    text_parts.append(rank_month_str)
    final_text = "\n".join(text_parts)

    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=final_text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except TelegramError as e:
        logger.warning(f"无法向用户 {user.id} 私聊发送战绩报告: {e}")

async def generate_ranking_text(scope: str, rank_type: str, period: str, chat_id: int, lang_code: str) -> str:
    period_str = get_text(f'period_{period}', lang_code)
    scope_str = get_text(f'scope_{scope}', lang_code) if scope != "groups" else ""
    data, title = [], ""

    # --- 【核心修正】在所有 get_text 之后，但在 format 之前，对动态内容进行转义 ---
    if rank_type == 'users':
        title = get_text('rank_header_users', lang_code).format(scope=scope_str, period=period_str)
        data = await asyncio.to_thread(get_top_users_by_period, chat_id, period) if scope == 'local' else await asyncio.to_thread(get_global_top_users_by_period, period)
    elif rank_type == 'topics':
        title = get_text('rank_header_topics', lang_code).format(scope=scope_str, period=period_str)
        data = await asyncio.to_thread(get_top_topics_by_period, chat_id, period) if scope == 'local' else await asyncio.to_thread(get_global_top_topics_by_period, period)
    elif rank_type == 'groups':
        title = get_text('rank_header_groups', lang_code).format(period=period_str)
        data = await asyncio.to_thread(get_global_top_groups_by_period, period)

    text_parts = [title]
    if not data:
        text_parts.append(get_text('no_records', lang_code))
    else:
        rank_emojis = ["🥇", "🥈", "🥉"]
        for i, item in enumerate(data):
            rank_icon = rank_emojis[i] if i < len(rank_emojis) else f"*{i+1}*\\."
            
            if rank_type == 'users':
                user_id, name, username, count = item
                # 【关键修复】对从数据库读取的 name 进行转义
                escaped_name = escape_markdown_v2(name)
                link = f"tg://user?id={user_id}"
                display_name = f"[{escaped_name}]({link})"
                # get_text 内部已经转义了静态部分，我们只需传入已转义的动态内容
                text_parts.append(get_text('rank_line_item_user', lang_code, rank_icon=rank_icon, display_name=display_name, count=count))
            elif rank_type == 'groups':
                name, username, count = item
                # 【关键修复】对从数据库读取的 name 进行转义
                escaped_name = escape_markdown_v2(name)
                if username and username != 'None':
                    display_name = f"[{escaped_name}](https://t.me/{username})"
                else:
                    display_name = escaped_name
                text_parts.append(get_text('rank_line_item_group', lang_code, rank_icon=rank_icon, display_name=display_name, count=count))
            elif rank_type == 'topics':
                topic, count = item
                # 【关键修复】对从数据库读取的 topic 进行转义
                escaped_topic = escape_markdown_v2(topic[:30])
                text_parts.append(get_text('rank_line_item_topic', lang_code, rank_icon=rank_icon, topic=escaped_topic, count=count))

    return "\n".join(text_parts)

async def _send_group_admin_menu(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """
    【最终修正版】
    发送单个群组的管理面板。
    “返回”按钮的回调数据被修正为 'menu_action_admin_groups'，以便能返回到群组选择列表。
    """
    lang_code = get_display_lang(query)
    try:
        chat = await context.bot.get_chat(chat_id)
        group_name = escape_markdown_v2(chat.title)
    except TelegramError:
        group_name = "Unknown Group"

    text = get_text('admin_group_panel_title', lang_code, group_name=group_name)
    autochat_status_icon = "✅" if user_manager.is_auto_chat_on(chat_id) else "❌"
    spam_filter_status_icon = "✅" if user_manager.is_spam_filter_on(chat_id) else "❌"

    # --- 【核心修改】重构键盘布局为 2*2 + 1 + 1 ---
    keyboard = [
        # Row 1: 2个按钮
        [
            InlineKeyboardButton(get_text('admin_group_button_language', lang_code), callback_data=f"admin_action_lang_{chat_id}"),
            InlineKeyboardButton(get_text('admin_group_button_replies', lang_code), callback_data=f"admin_action_replies_{chat_id}")
        ],
        # Row 2: 2个按钮
        [
            InlineKeyboardButton(f"{spam_filter_status_icon} {get_text('admin_group_button_spam_filter', lang_code)}", callback_data=f"admin_action_spamfilter_{chat_id}"),
            InlineKeyboardButton(get_text('admin_group_button_shop', lang_code), callback_data=f"admin_action_shop_{chat_id}") # <-- 新增商店按钮
        ],
        # Row 3: 1个按钮
        [
            InlineKeyboardButton(f"{autochat_status_icon} {get_text('admin_group_button_autochat', lang_code)}", callback_data=f"admin_action_autochat_{chat_id}")
        ],
        # Row 4: 1个按钮
        [
            InlineKeyboardButton(get_text('button_back', lang_code), callback_data='menu_action_admin_groups')
        ]
    ]
    # --- 【修改结束】 ---
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    await send_or_reply_with_or_without_buttons(
        query, text, context, reply_markup=reply_markup
    )

# ==============================================================================
# Section 0.5: 主菜单回调处理器 (Main Menu Callback)
# ==============================================================================

# bot/handlers/callbacks.py

# ... (文件顶部的其他 import 保持不变)

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    【最终修正版】
    处理主菜单的所有按钮点击。
    现在它也是“我的群组管理”功能的唯一入口和导航中心。
    """
    from .commands import send_main_menu, mystats_command
    
    query = update.callback_query
    await query.answer()
    
    action = query.data.replace('menu_action_', '')
    lang_code = get_display_lang(query)
    
    if action == 'back':
        await send_main_menu(update, context)
        return

    if action == 'admin_groups':
        user = query.from_user
        
        # <--- 修改开始：优化获取群组列表的逻辑 --->
        # 不再获取所有群组，而是只获取用户发言过的群组
        potential_groups = await asyncio.to_thread(statistics.db_get_groups_for_user, user.id)
        # <--- 修改结束 --->

        text = get_text('admin_groups_menu_title', lang_code)
        admin_groups = []
        if potential_groups:
            tasks = [context.bot.get_chat_member(chat_id, user.id) for chat_id, _ in potential_groups]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if not isinstance(result, TelegramError) and hasattr(result, 'status') and result.status in ['creator', 'administrator']:
                    admin_groups.append(potential_groups[i])
        
        keyboard = []
        if admin_groups:
            text += f"\n\n{get_text('admin_groups_select_group', lang_code)}"
            for chat_id, chat_title in sorted(admin_groups, key=lambda x: x[1]):
                button_text = chat_title if len(chat_title) < 20 else f"{chat_title[:20]}..."
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"admin_group_menu_{chat_id}")])
        else:
            text = get_text('admin_groups_no_groups', lang_code)
        
        # “群组选择列表”的返回按钮指向主菜单
        keyboard.append([InlineKeyboardButton(get_text('menu_button_back', lang_code), callback_data="menu_action_back")])
        
        await send_or_reply_with_or_without_buttons(
            query, text, context, reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
        
    elif action == 'search':
        context.user_data['next_message_is_search'] = True
        back_button = InlineKeyboardButton(get_text('menu_button_back', lang_code), callback_data='menu_action_back')
        await send_or_reply_with_or_without_buttons(
            query, 
            text=get_text('search_callback_prompt', lang_code), 
            context=context, 
            reply_markup=InlineKeyboardMarkup([[back_button]])
        )

    elif action == 'help':
        back_button = InlineKeyboardButton(get_text('menu_button_back', lang_code), callback_data='menu_action_back')
        await send_or_reply_with_or_without_buttons(
            query,
            text=get_text('help_text', lang_code),
            context=context,
            reply_markup=InlineKeyboardMarkup([[back_button]])
        )

    elif action == 'summary':
        await handle_category_menu_button(update, context)

    elif action == 'settings':
        await settings_menu_callback(update, context)
    
    elif action == 'mystats':
        await mystats_command(update, context)



# ==============================================================================
# Section 1: 设置与语言 (Settings & Language)
# ==============================================================================

async def settings_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    
    # 检查 action 是否已定义，如果未定义（从主菜单直接调用），则默认为 'settings_main'
    action = query.data if query.data.startswith('settings_') else 'settings_main'
    
    # 只有在需要更新界面时才应答回调，避免不必要的操作
    if action != 'settings_main':
        await query.answer()

    lang_code = get_display_lang(query)

    # 处理切换排名的逻辑
    if action == 'settings_toggle_ranking':
        new_status = user_manager.toggle_user_ranking_participation(user.id)
        status_text = get_text('settings_ranking_status_on', lang_code) if new_status else get_text('settings_ranking_status_off', lang_code)
        await query.answer(text=status_text, show_alert=False)
        # 更新后，重新显示主设置菜单
        action = 'settings_main'

    # 显示主设置菜单
    if action == 'settings_main':
        text = get_text('settings_menu_title', lang_code)
        is_ranking_enabled = user_manager.is_user_ranking_enabled(user.id)
        ranking_button_text = get_text('settings_button_ranking_on', lang_code) if is_ranking_enabled else get_text('settings_button_ranking_off', lang_code)
        
        # 【最终版本】这里不再有“我的群组管理”按钮
        keyboard = [
            [InlineKeyboardButton(get_text('settings_button_language', lang_code), callback_data='settings_language')],
            [InlineKeyboardButton(ranking_button_text, callback_data='settings_toggle_ranking')],
            [InlineKeyboardButton(get_text('menu_button_back', lang_code), callback_data='menu_action_back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await send_or_reply_with_or_without_buttons(
            query, text, context, reply_markup=reply_markup
        )

    # 显示语言设置子菜单
    elif action == 'settings_language':
        menu_title = get_text('language_menu_title_settings', lang_code)
        keyboard = [
            [InlineKeyboardButton("English", callback_data="set_lang_en"),
             InlineKeyboardButton("简体中文", callback_data="set_lang_zh")],
            # 返回按钮指向设置主菜单
            [InlineKeyboardButton(get_text('button_back', lang_code), callback_data="settings_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await send_or_reply_with_or_without_buttons(
            query, text=menu_title, context=context, reply_markup=reply_markup
        )

async def set_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    new_lang_code = query.data.split('_')[-1]
    await query.answer(get_text('language_switched', new_lang_code))
    user_manager.set_user_language(query.from_user.id, new_lang_code)
    menu_title = get_text('language_menu_title_settings', new_lang_code)
    keyboard = [
        [InlineKeyboardButton("English", callback_data="set_lang_en"),
         InlineKeyboardButton("简体中文", callback_data="set_lang_zh")],
        [InlineKeyboardButton(get_text('button_back', new_lang_code), callback_data="settings_main")]
    ]
    await send_or_reply_with_or_without_buttons(
        query, menu_title, context, reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def set_group_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await _is_admin(query, context):
        await query.answer(get_text('admin_only_alert', get_display_lang(query)), show_alert=True)
        return
    new_lang = query.data.split('_')[-1]
    user_manager.set_group_language(query.message.chat.id, new_lang)
    lang_name_map = {'en': 'English', 'zh': '简体中文'}
    success_text = get_text('language_set_success', new_lang, lang_name=lang_name_map.get(new_lang, new_lang))
    await send_or_reply_with_or_without_buttons(query, success_text, context)


# ==============================================================================
# Section 2: 搜索、复制与内联 (Search, Copy & Inline)
# ==============================================================================

async def search_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        _, search_id, page_str = query.data.split(':')
        page = int(page_str)
    except (ValueError, IndexError):
        await send_or_reply_with_or_without_buttons(query, "无效的分页请求。", context)
        return
    lang_code = get_display_lang(query)
    original_query_text = memory.get_search_query(search_id)
    items = context.bot_data.get(search_id)
    if not original_query_text or not items:
        await send_or_reply_with_or_without_buttons(query, "抱歉，此搜索结果已过期，请重新发起搜索。", context)
        return
    start_index = page * SEARCH_RESULTS_PER_PAGE
    end_index = start_index + SEARCH_RESULTS_PER_PAGE
    text_parts = [get_text('search_results_title', lang_code, query=escape_markdown_v2(original_query_text))]
    for i, item in enumerate(items[start_index:end_index]):
        title = escape_markdown_v2(item.get('title', 'No Title'))
        link = item.get('link')
        snippet = escape_markdown_v2(item.get('snippet', 'No snippet available.').replace('\n', ' '))
        text_parts.append(f"*{start_index + i + 1}*\\. [{title}]({link})\n_{snippet}_")
    reply_markup = create_search_pagination_keyboard(search_id, page, len(items), lang_code)
    await send_or_reply_with_or_without_buttons(
        query, "\n\n".join(text_parts), context, reply_markup=reply_markup
    )

async def copy_code_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    code_id = query.data.replace("copy_code_", "")
    code_to_copy = context.bot_data.get(code_id)
    if code_to_copy:
        await query.answer(text=code_to_copy, show_alert=True)
    else:
        await query.answer(text="抱歉，此代码已过期或未找到。", show_alert=True)

async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return
        
    logger.info(f"收到内联搜索请求: '{query}'")
    search_results = await asyncio.to_thread(ai_helper.google_search, query, num_results=10)
    results = []
    
    if search_results and 'items' in search_results:
        for item in search_results['items']:
            title = item.get('title', 'No Title')
            link = item.get('link')
            snippet = item.get('snippet', 'No snippet available.').replace('\n', ' ')
            message_content = f"🔍 *{escape_markdown_v2(title)}*\n\n{escape_markdown_v2(snippet)}\n\n[阅读原文]({link})"
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid.uuid4()),
                    title=title,
                    description=snippet,
                    input_message_content=InputTextMessageContent(
                        message_text=message_content,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_web_page_preview=False
                    ),
                    thumbnail_url="https://i.imgur.com/4x0Av9C.png"
                )
            )
            
    # 【修改】在这里添加 try...except 块
    try:
        await update.inline_query.answer(results, cache_time=10)
    except TelegramError as e:
        # 专门捕获超时错误，并静默处理
        if "Query is too old" in str(e):
            logger.warning(f"内联搜索请求 '{query}' 已超时，放弃响应。")
        else:
            # 如果是其他类型的错误，仍然记录下来
            logger.error(f"响应内联查询时发生未知错误: {e}", exc_info=True)


# ==============================================================================
# Section 3: 统计、图表与战绩 (Statistics, Charts & MyStats)
# ==============================================================================

async def mystats_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from .commands import mystats_command
    query = update.callback_query
    user = query.from_user
    lang_code = get_display_lang(query)
    action = query.data.split('_', 1)[1]

    if action == 'back_to_main':
        await mystats_command(update, context)
        return

    await query.answer()

    if action == 'global':
        try:
            global_rank, global_count = await asyncio.to_thread(statistics.get_user_global_stats, user.id)
        except Exception as e:
            logger.error(f"获取用户 {user.id} 的全服数据时出错: {e}", exc_info=True)
            await send_or_reply_with_or_without_buttons(query, get_text('internal_error', lang_code), context)
            return
        
        text_parts = [get_text('mystats_title_global', lang_code)]
        is_ranking_enabled = user_manager.is_user_ranking_enabled(user.id)
        if is_ranking_enabled:
            if global_rank > 0:
                 rank_text = get_text('mystats_global_rank', lang_code, rank=global_rank, count=global_count)
            else:
                 rank_text = get_text('mystats_not_enough_data', lang_code) + f" (总发言: {global_count} 条)"
        else:
            rank_text = get_text('settings_ranking_status_off', lang_code) + f" (总发言: {global_count} 条)"
        text_parts.append(rank_text)
        final_text = "\n".join(text_parts)
        
        keyboard = [[InlineKeyboardButton(get_text('button_back', lang_code), callback_data='mystats_back_to_main')]]
        await send_or_reply_with_or_without_buttons(
            query, final_text, context, reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif action == 'select_group':
        user_groups = await asyncio.to_thread(statistics.db_get_groups_for_user, user.id)
        if not user_groups:
            keyboard = [[InlineKeyboardButton(get_text('button_back', lang_code), callback_data='mystats_back_to_main')]]
            await send_or_reply_with_or_without_buttons(
                query, get_text('mystats_no_shared_groups', lang_code), context, reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        keyboard = []
        for chat_id, chat_title in user_groups:
            button_text = chat_title if len(chat_title) < 25 else f"{chat_title[:25]}..."
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"mystats_show_group_{chat_id}")])
        
        keyboard.append([InlineKeyboardButton(get_text('button_back', lang_code), callback_data='mystats_back_to_main')])
        
        await send_or_reply_with_or_without_buttons(
            query,
            text=get_text('mystats_select_group_title', lang_code),
            context=context,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def mystats_group_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    lang_code = get_display_lang(query)
    
    try:
        chat_id = int(query.data.split('_')[-1])
    except (ValueError, IndexError):
        await query.answer("Error: Invalid group ID.", show_alert=True)
        return

    try:
        chat = await context.bot.get_chat(chat_id)
        chat_title = chat.title
    except TelegramError:
        chat_title = "一个未知的群组"
    
    await send_or_reply_with_or_without_buttons(
        query,
        f"正在为您生成群组 *{escape_markdown_v2(chat_title)}* 的报告\\.\\.\\.",
        context
    )

    await _send_single_group_stats_pm(user, chat_id, chat_title, context, lang_code)

    keyboard = [[InlineKeyboardButton(get_text('button_back', lang_code), callback_data='mystats_select_group')]]
    await send_or_reply_with_or_without_buttons(
        query,
        text=get_text('mystats_report_sent', lang_code),
        context=context,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def mystats_all_groups_rank_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    lang_code = get_display_lang(query)
    await query.answer()

    # 这个函数调用的是 statistics.db_get_user_activity_across_groups
    # 我需要确认这个函数是否存在
    # 是的，它在之前的步骤中被添加了。

    user_groups_activity = await asyncio.to_thread(
        statistics.db_get_user_activity_across_groups, user.id
    )

    text_parts = [get_text('mystats_title_all_groups_rank', lang_code)]
    
    if not user_groups_activity:
        bot_username = (await context.bot.get_me()).username
        add_to_group_url = f"https://t.me/{bot_username}?startgroup=true"
        text_parts.append(f"\n_{get_text('mystats_no_shared_groups_rank', lang_code)}_")
        keyboard = [
            [InlineKeyboardButton(get_text('mystats_button_add_to_group', lang_code), url=add_to_group_url)],
            [InlineKeyboardButton(get_text('button_back', lang_code), callback_data='mystats_back_to_main')]
        ]
    else:
        rank_emojis = ["🥇", "🥈", "🥉"]
        for i, (group_title, group_username, count) in enumerate(user_groups_activity):
            rank_icon = rank_emojis[i] if i < 3 else f"*{i + 1}*\\."
            
            # 对动态内容进行转义
            escaped_title = escape_markdown_v2(group_title)
            
            if group_username and group_username != 'None':
                display_name = f"[{escaped_title}](https://t.me/{group_username})"
            else:
                display_name = escaped_title
            
            # 使用一个简单的、安全的格式
            line_item = f"{rank_icon} 在群组 *{display_name}* 中，您总共发言: `{count}` 条"
            text_parts.append(line_item)
            
        keyboard = [[InlineKeyboardButton(get_text('button_back', lang_code), callback_data='mystats_back_to_main')]]

    final_text = "\n".join(text_parts)
    
    await send_or_reply_with_or_without_buttons(
        query,
        text=final_text,
        context=context,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# bot/handlers/callbacks.py

# ... (文件顶部的其他 import 保持不变)

async def handle_category_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang_code = get_display_lang(query)
    
    menu_type = query.data
    chat_type = query.message.chat.type

    # 1. 处理返回到群组统计主菜单的请求
    if menu_type == 'summary_main_group':
        from .commands import summary_command
        await summary_command(update, context)
        return

    # 2. 根据聊天类型，确定正确的“返回”目标
    # 在私聊中，返回到全局排行榜选择菜单
    # 在群聊中，返回到群组统计主菜单
    back_target = 'menu_action_summary' if chat_type == ChatType.PRIVATE else 'summary_main_group'

    # 3. 处理从私聊主菜单初次进入 /summary 的情况
    if menu_type == 'menu_action_summary':
        text = get_text('summary_private_intro', lang_code)
        keyboard = [
            [InlineKeyboardButton(get_text('button_global_user_rank', lang_code), callback_data='menu_rank_global_users')],
            [InlineKeyboardButton(get_text('button_global_topic_rank', lang_code), callback_data='menu_rank_global_topics')],
            [InlineKeyboardButton(get_text('button_global_group_rank', lang_code), callback_data='menu_rank_global_groups')],
            [InlineKeyboardButton(get_text('menu_button_back', lang_code), callback_data='menu_action_back')]
        ]
        await send_or_reply_with_or_without_buttons(
            query, text, context, reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # 4. 定义菜单数据，并使用正确的 back_target
    # 【核心修正】统一了 callback_data 格式，特别是 'groups' 类型
    menu_map = {
        'menu_rank_local_users': ('rank_local_title', [
             (get_text('rank_user_today', lang_code), 'rank_local_users_today'),
             (get_text('rank_user_week', lang_code), 'rank_local_users_week'),
             (get_text('rank_user_month', lang_code), 'rank_local_users_month')
        ]),
        'menu_rank_local_topics': ('rank_local_topics_title', [
             (get_text('rank_topic_today', lang_code), 'rank_local_topics_today'),
             (get_text('rank_topic_week', lang_code), 'rank_local_topics_week'),
             (get_text('rank_topic_month', lang_code), 'rank_local_topics_month')
        ]),
        'menu_rank_global_users': ('rank_users_title', [
            (get_text('rank_user_today', lang_code), 'rank_global_users_today'),
            (get_text('rank_user_week', lang_code), 'rank_global_users_week'),
            (get_text('rank_user_month', lang_code), 'rank_global_users_month')
        ]),
        'menu_rank_global_topics': ('rank_topics_title', [
            (get_text('rank_topic_today', lang_code), 'rank_global_topics_today'),
            (get_text('rank_topic_week', lang_code), 'rank_global_topics_week'),
            (get_text('rank_topic_month', lang_code), 'rank_global_topics_month')
        ]),
        # 【核心修正】旧名称 'menu_rank_groups' 对应 'rank_global_groups' 类型
        'menu_rank_global_groups': ('rank_groups_title', [
            (get_text('rank_group_today', lang_code), 'rank_global_groups_today'),
            (get_text('rank_group_week', lang_code), 'rank_global_groups_week'),
            (get_text('rank_group_month', lang_code), 'rank_global_groups_month')
        ])
    }

    # 为了兼容旧按钮（menu_rank_groups），我们做一个映射
    if menu_type == 'menu_rank_groups':
        menu_type = 'menu_rank_global_groups'
    
    # 5. 动态生成菜单
    if menu_type in menu_map:
        title_key, buttons_data = menu_map[menu_type]
        text = get_text(title_key, lang_code)
        keyboard_buttons = [[InlineKeyboardButton(btn_text, callback_data=btn_cb)] for btn_text, btn_cb in buttons_data]
        # 使用动态确定的 back_target
        keyboard_buttons.append([InlineKeyboardButton(get_text('button_back', lang_code), callback_data=back_target)])
        
        await send_or_reply_with_or_without_buttons(
            query, text, context, reply_markup=InlineKeyboardMarkup(keyboard_buttons)
        )

async def handle_statistics_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang_code = get_display_lang(query)
    chat_id = query.message.chat.id
    chat_type = query.message.chat.type

    try:
        # 新的、统一的解析逻辑
        parts = query.data.split('_')
        # e.g., rank_local_users_today -> ['rank', 'local', 'users', 'today']
        # e.g., rank_global_groups_today -> ['rank', 'global', 'groups', 'today']
        if len(parts) == 4:
            _, scope, rank_type, period = parts
        else:
            logger.warning(f"无法解析的回调数据格式: {query.data}")
            return
    except ValueError:
        logger.warning(f"回调数据解析失败: {query.data}")
        return
    
    # 生成排行榜文本
    text = await generate_ranking_text(scope, rank_type, period, chat_id, lang_code)
    
    # 确定正确的返回目标
    # 如果是群组内的本地榜单，返回到群组统计主菜单
    # 如果是全局榜单，根据榜单类型返回到对应的全局榜单选择菜单
    back_button_callback = 'summary_main_group'
    if scope == 'global':
        back_button_callback = f'menu_rank_global_{rank_type}'
    
    keyboard = [[InlineKeyboardButton(get_text('button_back', lang_code), callback_data=back_button_callback)]]

    await send_or_reply_with_or_without_buttons(
        query, text, context, reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_activity_chart_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang_code = get_display_lang(query)
    keyboard = [
        [InlineKeyboardButton(get_text('chart_button_7_days', lang_code), callback_data='chart_generate_7'),
         InlineKeyboardButton(get_text('chart_button_30_days', lang_code), callback_data='chart_generate_30')],
        [InlineKeyboardButton(get_text('button_back', lang_code), callback_data='summary_main_group')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = get_text('chart_menu_title', lang_code)
    await send_or_reply_with_or_without_buttons(
        query, text=text, context=context, reply_markup=reply_markup
    )

async def handle_activity_chart_generate_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang_code = get_display_lang(query)
    chat_id = query.message.chat.id
    placeholder_text = get_text('chart_generating', lang_code)
    await send_or_reply_with_or_without_buttons(query, placeholder_text, context)

    try:
        days = int(query.data.split('_')[-1])
    except (IndexError, ValueError): days = 7
    chart_image_buffer = await asyncio.to_thread(chart_generator.generate_activity_chart, chat_id=chat_id, lang_code=lang_code, days=days)
    
    try:
        await query.delete_message()
    except TelegramError as e:
        logger.warning(f"删除图表占位消息时出错: {e}")
    
    if chart_image_buffer:
        await context.bot.send_photo(chat_id=chat_id, photo=chart_image_buffer, caption=get_text('chart_title_7_days' if days == 7 else 'chart_title_30_days', lang_code))
    else:
        no_data_text = get_text('chart_no_data', lang_code)
        await send_or_reply_with_or_without_buttons(query, no_data_text, context)


# ==============================================================================
# Section 4: 远程群组管理 (Remote Group Admin)
# ==============================================================================

async def group_admin_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        _, _, _, chat_id_str = query.data.split('_')
        chat_id = int(chat_id_str)
    except (ValueError, IndexError):
        logger.warning(f"无法从回调数据 {query.data} 中解析 chat_id")
        return
    await _send_group_admin_menu(query, context, chat_id)

async def group_admin_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        # 解析出动作和 chat_id
        action_parts = query.data.split('_')
        action = action_parts[2]
        chat_id = int(action_parts[-1])
    except (ValueError, IndexError):
        await query.answer()
        logger.warning(f"无法从回调数据 {query.data} 中解析 action 或 chat_id")
        return

    lang_code = get_display_lang(query)

    # --- 分支一：显示语言设置菜单 ---
    if action == 'lang':
        await query.answer()
        menu_title = get_text('language_menu_title', lang_code)
        keyboard = [
            [InlineKeyboardButton("English", callback_data=f"admin_set_lang_en_{chat_id}"),
             InlineKeyboardButton("简体中文", callback_data=f"admin_set_lang_zh_{chat_id}")],
            [InlineKeyboardButton(get_text('button_back', lang_code), callback_data=f'admin_group_menu_{chat_id}')]
        ]
        await send_or_reply_with_or_without_buttons(
            query, menu_title, context, reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # --- 分支二：切换自由对话开关 ---
    elif action == 'autochat':
        new_status = not user_manager.is_auto_chat_on(chat_id)
        user_manager.set_auto_chat_mode(chat_id, new_status)
        status_text = "已开启" if new_status else "已关闭"
        await query.answer(f"自由对话模式已 {status_text}", show_alert=False)
        await _send_group_admin_menu(query, context, chat_id)
        return

    # --- 分支三：切换垃圾拦截开关 ---
    elif action == 'spamfilter':
        new_status = not user_manager.is_spam_filter_on(chat_id)
        user_manager.set_spam_filter_mode(chat_id, new_status)
        status_text = get_text('status_on' if new_status else 'status_off', lang_code)
        alert_text = get_text('spam_filter_status_alert', lang_code, status=status_text)
        await query.answer(alert_text, show_alert=False)
        await _send_group_admin_menu(query, context, chat_id)
        return

    # --- 分支四：显示关键词回复管理菜单 ---
    elif action == 'replies':
        await query.answer()
        faqs = faq_manager.get_faqs_for_chat(chat_id)
        text_parts = [get_text('reply_list_title', lang_code)]
        if not faqs:
            text_parts.append(f"\n_{get_text('reply_list_empty', lang_code)}_")
        else:
            for i, item in enumerate(faqs):
                # --- 【核心修正】对从数据库读取的关键词问题进行转义 ---
                question_escaped = escape_markdown_v2(item['question'])
                text_parts.append(f"*{i + 1}\\.* _{question_escaped}_")
        
        text = "\n".join(text_parts)
        keyboard = [
            [
                InlineKeyboardButton(get_text('admin_group_button_add_reply', lang_code), callback_data=f"admin_action_addreply_start_{chat_id}"),
                InlineKeyboardButton(get_text('admin_group_button_del_reply', lang_code), callback_data=f"admin_action_delreply_menu_{chat_id}")
            ],
            [InlineKeyboardButton(get_text('button_back', lang_code), callback_data=f'admin_group_menu_{chat_id}')]
        ]
        await send_or_reply_with_or_without_buttons(
            query, text, context, reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
        
    # --- 分支五：显示商店管理菜单 ---
    elif action == 'shop':
        await query.answer()
        await remote_shop_management_menu(update, context)
        return

async def remote_add_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try:
        chat_id = int(query.data.split('_')[-1])
        context.user_data['admin_reply_chat_id'] = chat_id
    except (ValueError, IndexError): return ConversationHandler.END
    lang_code = get_display_lang(query)
    await send_or_reply_with_or_without_buttons(
        query, text=get_text('remote_add_reply_start', lang_code), context=context
    )
    return ASK_REPLY_QUESTION

async def remote_add_reply_question_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    question = update.message.text
    context.user_data['admin_reply_question'] = question
    lang_code = get_display_lang(update)
    # 这是一个普通的回复，不应该自动删除，所以保留原始发送方式
    await update.message.reply_text(text=get_text('remote_add_reply_ask_answer', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
    return ASK_REPLY_ANSWER

async def remote_add_reply_answer_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    answer = update.message.text
    question = context.user_data.get('admin_reply_question')
    chat_id = context.user_data.get('admin_reply_chat_id')
    lang_code = get_display_lang(update)
    if question and chat_id:
        if faq_manager.add_faq(chat_id, question, answer):
            await update.message.reply_text(get_text('remote_add_reply_success', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
        else:
            await update.message.reply_text(get_text('reply_add_exists', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
    context.user_data.pop('admin_reply_question', None)
    context.user_data.pop('admin_reply_chat_id', None)
    return ConversationHandler.END

async def remote_add_reply_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang_code = get_display_lang(update)
    await update.message.reply_text(get_text('remote_add_reply_cancel', lang_code), parse_mode=ParseMode.MARKDOWN_V2)
    context.user_data.pop('admin_reply_question', None)
    context.user_data.pop('admin_reply_chat_id', None)
    return ConversationHandler.END

async def toggle_checkin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理开启/关闭群组签到功能的回调，并提供清晰的UI反馈。"""
    query = update.callback_query
    chat = query.message.chat
    lang_code = get_display_lang(query)

    if not await helpers._is_admin(query, context):
        await query.answer(get_text('admin_only_alert', lang_code), show_alert=True)
        return
    
    # 1. 切换数据库中的状态
    new_status = user_manager.toggle_group_checkin(chat.id)
    
    # 2. 根据新状态，准备新的消息文本和按钮文本
    base_welcome_text = get_text('group_welcome', lang_code)
    
    if new_status: # 如果新状态是“开启”
        status_update_text = get_text('checkin_status_update_on', lang_code)
        checkin_button_text = get_text('checkin_status_button_on', lang_code)
    else: # 如果新状态是“关闭”
        status_update_text = get_text('checkin_status_update_off', lang_code)
        checkin_button_text = get_text('checkin_status_button_off', lang_code)
        
    # 3. 组合成最终的消息和键盘
    final_message_text = base_welcome_text + status_update_text
    
    new_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("English", callback_data="set_group_lang_en"),
            InlineKeyboardButton("简体中文", callback_data="set_group_lang_zh")
        ],
        [
            InlineKeyboardButton(checkin_button_text, callback_data="toggle_checkin")
        ]
    ])

    # 4. 同时编辑消息文本和键盘，并移除旧的弹窗提示
    try:
        await query.edit_message_text(
            text=final_message_text,
            reply_markup=new_keyboard,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except TelegramError as e:
        if "message is not modified" not in str(e).lower():
            logger.error(f"更新签到状态消息时出错: {e}")
    
    # 5. 我们用编辑消息的强反馈替代了旧的弱反馈
    await query.answer() # 只需简单应答即可

async def remote_del_reply_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示一个带有删除按钮的FAQ列表，用于远程删除。"""
    query = update.callback_query
    await query.answer()
    lang_code = get_display_lang(query)
    try:
        chat_id = int(query.data.split('_')[-1])
    except (ValueError, IndexError):
        return

    faqs = faq_manager.get_faqs_for_chat(chat_id)
    text = get_text('admin_del_reply_menu_title', lang_code)
    
    keyboard = []
    if not faqs:
        text += f"\n\n_{get_text('reply_list_empty', lang_code)}_"
    else:
        for item in faqs:
            q_text = item['question']
            button_text = q_text if len(q_text) < 25 else f"{q_text[:25]}..."
            # 每个按钮的回调包含 faq_id 和 chat_id
            keyboard.append([InlineKeyboardButton(f"🗑️ {button_text}", callback_data=f"admin_del_faq_{item['id']}_{chat_id}")])

    # 返回按钮指向关键词管理主菜单
    keyboard.append([InlineKeyboardButton(get_text('button_back', lang_code), callback_data=f"admin_action_replies_{chat_id}")])
    
    await send_or_reply_with_or_without_buttons(
        query, text, context, reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def remote_del_reply_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理具体的FAQ删除动作。"""
    query = update.callback_query
    lang_code = get_display_lang(query)
    try:
        _, _, _, faq_id_str, chat_id_str = query.data.split('_')
        faq_id = int(faq_id_str)
        chat_id = int(chat_id_str)
    except (ValueError, IndexError):
        await query.answer()
        return

    # 从数据库删除，需要先获取内容以便提示用户
    all_faqs = faq_manager.get_faqs_for_chat(chat_id)
    faq_to_delete = next((faq for faq in all_faqs if faq['id'] == faq_id), None)

    if faq_to_delete:
        # 在数据库中删除该条目
        # delete_faq 需要的是列表索引，但我们直接用ID删除更可靠
        # 我们需要一个通过ID删除的函数，或者修改现有函数
        # 让我们直接调用 db_delete_faq
        if statistics.db_delete_faq(faq_id):
            alert_text = get_text('admin_del_reply_success_alert', lang_code, question=faq_to_delete['question'][:20])
            await query.answer(alert_text, show_alert=False)
            # 刷新删除菜单
            await remote_del_reply_menu_callback(update, context)
        else:
            await query.answer("删除失败，请重试。", show_alert=True)
    else:
        await query.answer("该条目已被删除或不存在。", show_alert=True)

async def remote_shop_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示商店管理菜单，列出当前商品并提供管理选项。"""
    query = update.callback_query
    lang_code = get_display_lang(query)
    
    try:
        # 从回调数据中解析 chat_id
        chat_id_str = query.data.split('_')[-1]
        chat_id = int(chat_id_str)
        chat = await context.bot.get_chat(chat_id)
        group_name = escape_markdown_v2(chat.title)
    except (ValueError, IndexError, TelegramError):
        # 如果解析失败或获取群组信息失败，优雅地回退
        await query.answer("无法获取群组信息，请重试。", show_alert=True)
        return

    # 获取所有商店商品（当前为全局）
    items = statistics.db_get_shop_items()
    
    # 构建消息文本
    text_parts = [get_text('admin_shop_menu_title', lang_code, group_name=group_name)]
    if not items:
        text_parts.append(f"\n_{get_text('shop_list_empty', lang_code)}_")
    else:
        for item in items:
            stock_str = get_text('shop_item_stock_infinite', lang_code) if item['stock'] == -1 else str(item['stock'])
            item_line = get_text('shop_item_line', lang_code,
                id=item['id'], name=escape_markdown_v2(item['name']),
                description=escape_markdown_v2(item['description'] or ''),
                cost=item['cost'], stock=stock_str
            )
            text_parts.append(item_line)
    
    final_text = "\n\n".join(text_parts)

    # 构建键盘
    keyboard = [
        [
            InlineKeyboardButton(get_text('admin_shop_button_add', lang_code), callback_data=f"admin_shop_add_{chat_id}"),
            InlineKeyboardButton(get_text('admin_shop_button_del', lang_code), callback_data=f"admin_shop_del_{chat_id}")
        ],
        [
            InlineKeyboardButton(get_text('button_back', lang_code), callback_data=f"admin_group_menu_{chat_id}")
        ]
    ]

    await send_or_reply_with_or_without_buttons(
        query,
        text=final_text,
        context=context,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def remote_shop_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """对话开始：请求输入奖品名称。"""
    # --- 【核心修正】在函数开头从 update 对象中获取 query ---
    query = update.callback_query
    # --- 【修正结束】 ---
    
    await query.answer()
    
    # 将 chat_id 存入 user_data 以便后续返回
    chat_id = int(query.data.split('_')[-1])
    context.user_data['admin_shop_chat_id'] = chat_id
    
    reply_text = "好的，我们来添加一个新奖品。\n\n*第一步*：请发送新奖品的 *名称*。"
    await query.edit_message_text(helpers.escape_markdown_v2(reply_text), parse_mode=ParseMode.MARKDOWN_V2)
    return ASK_ITEM_NAME

async def remote_shop_add_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """接收名称，请求输入描述。"""
    context.user_data['admin_shop_item_name'] = update.message.text
    reply_text = "名称已收到！\n\n*第二步*：请发送奖品的 *描述*。"
    await update.message.reply_text(helpers.escape_markdown_v2(reply_text), parse_mode=ParseMode.MARKDOWN_V2)
    return ASK_ITEM_DESC

async def remote_shop_add_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """接收描述，请求输入所需积分。"""
    context.user_data['admin_shop_item_desc'] = update.message.text
    reply_text = "描述已收到！\n\n*第三步*：请发送兑换此奖品需要多少 *积分* (纯数字)？"
    await update.message.reply_text(helpers.escape_markdown_v2(reply_text), parse_mode=ParseMode.MARKDOWN_V2)
    return ASK_ITEM_COST

async def remote_shop_add_cost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """接收积分，验证后请求输入库存。"""
    try:
        cost = int(update.message.text)
        if cost <= 0:
            await update.message.reply_text(helpers.escape_markdown_v2("积分必须是大于0的整数，请重新输入。"))
            return ASK_ITEM_COST
        context.user_data['admin_shop_item_cost'] = cost
        reply_text = f"需要 {cost} 积分已收到！\n\n*第四步*：请发送奖品的 *库存数量* (纯数字，输入 `-1` 代表无限库存)。"
        await update.message.reply_text(helpers.escape_markdown_v2(reply_text), parse_mode=ParseMode.MARKDOWN_V2)
        return ASK_ITEM_STOCK
    except ValueError:
        await update.message.reply_text(helpers.escape_markdown_v2("无效的输入。请输入一个纯数字作为积分。"))
        return ASK_ITEM_COST

async def remote_shop_add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """接收库存，验证后将奖品写入数据库，结束对话。"""
    try:
        stock = int(update.message.text)
        context.user_data['admin_shop_item_stock'] = stock
        
        name = context.user_data['admin_shop_item_name']
        desc = context.user_data['admin_shop_item_desc']
        cost = context.user_data['admin_shop_item_cost']
        
        success = await asyncio.to_thread(statistics.db_add_shop_item, name, desc, cost, stock)
        
        if success:
            await update.message.reply_text(f"✅ *添加成功！* 奖品“{escape_markdown_v2(name)}”已上架。", parse_mode=ParseMode.MARKDOWN_V2)
        else:
            await update.message.reply_text(f"⚠️ *添加失败！* 可能是因为该奖品名称已经存在了。", parse_mode=ParseMode.MARKDOWN_V2)
            
        chat_id = context.user_data.get('admin_shop_chat_id')
        context.user_data.clear()

        if chat_id:
            # 使用 message.chat (因为这是用户回复的，不是按钮)
            fake_query = type('FakeQuery', (), {'data': f'admin_action_shop_{chat_id}', 'message': update.message})()
            fake_update = type('FakeUpdate', (), {'callback_query': fake_query})()
            await remote_shop_management_menu(fake_update, context)

        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text(helpers.escape_markdown_v2("无效的输入。请输入一个纯数字作为库存。"))
        return ASK_ITEM_STOCK

async def remote_shop_add_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """取消对话。"""
    context.user_data.clear()
    await update.message.reply_text("操作已取消。")
    return ConversationHandler.END