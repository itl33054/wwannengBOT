# bot/main.py

import logging
import atexit
import asyncio
from telegram import BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler,
    InlineQueryHandler, ConversationHandler, ContextTypes, ChatMemberHandler
)

from . import persistence_manager, statistics as db
from .handlers import *

from .config import TELEGRAM_BOT_TOKEN

async def post_init(application):
    """在机器人启动后设置命令菜单。"""
    commands = [
        BotCommand("start", "✨ 开始 / 显示主菜单"),
        BotCommand("menu", "📖 显示功能主菜单"),
        BotCommand("new", "🧠 开启全新对话"),
        BotCommand("checkin", "签到领积分"),
        BotCommand("points", "💰 查询我的积分"),
        BotCommand("shop", "🎁 积分商店"),
        BotCommand("redeem", "🛒 兑换奖品 (用法: /redeem ID)"),
        BotCommand("search", "🔍 搜索全网信息"),
        BotCommand("summary", "📊 (群组)查看数据统计"),
        BotCommand("mystats", "🏆 我的战绩"),
    ]
    admin_commands = [
        BotCommand("addreply", "🔑 (管理员)添加关键词回复"),
        BotCommand("delreply", "🗑️ (管理员)删除关键词回复"),
        BotCommand("listreply", "📋 (管理员)查看关键词回复"),
    ]
    try:
        await application.bot.set_my_commands(commands + admin_commands)
        logging.getLogger(__name__).info("成功设置机器人命令菜单。")
    except Exception as e:
        logging.getLogger(__name__).error(f"设置机器人命令时出错: {e}")


async def discover_chats_job(context: ContextTypes.DEFAULT_TYPE):
    """定时扫描并更新已知群组信息。"""
    await asyncio.to_thread(db.db_discover_and_update_known_chats)

async def clear_blacklist_job(context: ContextTypes.DEFAULT_TYPE):
    """定时清理过期的黑名单条目。"""
    await asyncio.to_thread(db.db_clear_expired_blacklist_entries)


def run():
    """启动机器人的主函数。"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    if not TELEGRAM_BOT_TOKEN:
        logger.error("错误: 未设置 TELEGRAM_BOT_TOKEN！程序即将退出。")
        return

    logger.info("机器人正在启动...")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    job_queue = application.job_queue
    job_queue.run_repeating(persistence_manager.periodic_save_job, interval=300, first=10)
    job_queue.run_repeating(clear_blacklist_job, interval=21600, first=60)
    job_queue.run_repeating(discover_chats_job, interval=600, first=15)
    
    atexit.register(persistence_manager.save_all_data)

    add_reply_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(remote_add_reply_start, pattern="^admin_action_addreply_start_")],
        states={
            ASK_REPLY_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, remote_add_reply_question_received)],
            ASK_REPLY_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, remote_add_reply_answer_received)],
        },
        fallbacks=[CommandHandler('cancel', remote_add_reply_cancel)],
        conversation_timeout=120
    )

    add_shop_item_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(remote_shop_add_start, pattern="^admin_shop_add_")],
        states={
            ASK_ITEM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, remote_shop_add_name)],
            ASK_ITEM_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, remote_shop_add_desc)],
            ASK_ITEM_COST: [MessageHandler(filters.TEXT & ~filters.COMMAND, remote_shop_add_cost)],
            ASK_ITEM_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, remote_shop_add_stock)],
        },
        fallbacks=[CommandHandler('cancel', remote_shop_add_cancel)],
        conversation_timeout=300
    )

    application.add_handler(MessageHandler(filters.ALL & (~filters.UpdateType.CHANNEL_POST), proactive_chat_recorder), group=-10)
    application.add_handler(MessageHandler(filters.ALL & (~filters.UpdateType.CHANNEL_POST), spam_check_handler), group=-2)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND) & (~filters.UpdateType.CHANNEL_POST), message_filter_handler), group=-1)
    
    application.add_handler(add_reply_conv_handler)
    application.add_handler(add_shop_item_conv_handler)

    # --- 命令处理器 ---
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("new", new_command))
    application.add_handler(CommandHandler("summary", summary_command))
    application.add_handler(CommandHandler("mystats", mystats_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("autochat_on", auto_chat_on_command))
    application.add_handler(CommandHandler("autochat_off", auto_chat_off_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("privacy", privacy_command))
    application.add_handler(CommandHandler("rules", rules_command))
    application.add_handler(CommandHandler("addreply", add_reply_command))
    application.add_handler(CommandHandler("delreply", del_reply_command))
    application.add_handler(CommandHandler("listreply", listreply_command))
    application.add_handler(CommandHandler("checkin", checkin_command))
    application.add_handler(CommandHandler("points", points_command))
    application.add_handler(CommandHandler("shop", shop_command))
    application.add_handler(CommandHandler("redeem", redeem_command))

    # --- 按钮回调处理器 ---
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^menu_action_"))
    application.add_handler(CallbackQueryHandler(settings_menu_callback, pattern="^settings_"))
    application.add_handler(CallbackQueryHandler(set_language_callback, pattern="^set_lang_"))
    application.add_handler(CallbackQueryHandler(set_group_language_callback, pattern="^set_group_lang_"))
    application.add_handler(CallbackQueryHandler(toggle_checkin_callback, pattern="^toggle_checkin$"))
    application.add_handler(CallbackQueryHandler(handle_category_menu_button, pattern="^menu_rank_"))
    application.add_handler(CallbackQueryHandler(handle_category_menu_button, pattern="^summary_main_"))
    application.add_handler(CallbackQueryHandler(handle_statistics_button, pattern=r"^rank_.*_(today|week|month)$"))
    
    application.add_handler(CallbackQueryHandler(mystats_group_selection_callback, pattern="^mystats_show_group_"))
    application.add_handler(CallbackQueryHandler(mystats_all_groups_rank_callback, pattern="^mystats_all_groups_rank$"))
    application.add_handler(CallbackQueryHandler(mystats_menu_callback, pattern="^mystats_"))
    
    application.add_handler(CallbackQueryHandler(search_page_callback, pattern=r"^search_page:"))
    application.add_handler(CallbackQueryHandler(copy_code_callback, pattern="^copy_code_"))
    application.add_handler(CallbackQueryHandler(handle_activity_chart_button, pattern="^chart_activity_menu$"))
    application.add_handler(CallbackQueryHandler(handle_activity_chart_generate_button, pattern="^chart_generate_"))
    application.add_handler(CallbackQueryHandler(group_admin_menu_callback, pattern="^admin_group_menu_"))
    application.add_handler(CallbackQueryHandler(group_admin_action_callback, pattern="^admin_action_"))
    
    # 【核心修正】使用正确的函数名 set_group_language_callback
    application.add_handler(CallbackQueryHandler(set_group_language_callback, pattern="^admin_set_lang_"))
    
    application.add_handler(CallbackQueryHandler(remote_del_reply_menu_callback, pattern="^admin_action_delreply_menu_"))
    application.add_handler(CallbackQueryHandler(remote_del_reply_action_callback, pattern="^admin_del_faq_"))
    application.add_handler(CallbackQueryHandler(remote_shop_management_menu, pattern="^admin_action_shop_"))

    application.add_handler(InlineQueryHandler(inline_query_handler))
    
    application.add_handler(ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))

    application.add_handler(MessageHandler(filters.PHOTO & (~filters.UpdateType.CHANNEL_POST), photo_handler))
    application.add_handler(MessageHandler(filters.Sticker.ALL & (~filters.UpdateType.CHANNEL_POST), sticker_handler))
    chat_filter = filters.TEXT & (~filters.COMMAND) & (~filters.UpdateType.CHANNEL_POST)
    application.add_handler(MessageHandler(chat_filter, chat_handler))

    application.add_error_handler(error_handler)
    
    logger.info("机器人已启动，开始轮询...")
    application.run_polling()