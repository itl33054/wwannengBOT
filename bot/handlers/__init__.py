# bot/handlers/__init__.py

# 【第一部分】从各个子模块中导入所有需要被外部（如 main.py）使用的函数
from .admin import (
    ban_command, unban_command, auto_chat_on_command, auto_chat_off_command,
    add_reply_command, del_reply_command, language_command
)
from .callbacks import (
    main_menu_callback, settings_menu_callback, set_language_callback, 
    set_group_language_callback, search_page_callback, handle_category_menu_button, 
    handle_statistics_button, mystats_menu_callback, mystats_group_selection_callback,
    mystats_all_groups_rank_callback, handle_activity_chart_button, 
    handle_activity_chart_generate_button, copy_code_callback, inline_query_handler,
    group_admin_menu_callback, group_admin_action_callback, 
    remote_add_reply_start, 
    remote_add_reply_question_received, remote_add_reply_answer_received, 
    remote_add_reply_cancel,
    remote_del_reply_menu_callback, remote_del_reply_action_callback,
    remote_shop_management_menu,
    toggle_checkin_callback,
    remote_shop_add_start, remote_shop_add_name, remote_shop_add_desc,
    remote_shop_add_cost, remote_shop_add_stock, remote_shop_add_cancel,
    ASK_ITEM_NAME, ASK_ITEM_DESC, ASK_ITEM_COST, ASK_ITEM_STOCK,
    ASK_REPLY_QUESTION, ASK_REPLY_ANSWER
)
from .commands import (
    start_command, menu_command, help_command, new_command, summary_command, 
    mystats_command, search_command, settings_command, privacy_command, 
    rules_command, listreply_command,
    checkin_command, points_command, shop_command, redeem_command
)
from .helpers import (
    get_display_lang, escape_markdown_v2, _format_time_delta, 
    create_search_pagination_keyboard, _is_admin, handle_private_summary_back, 
    proactive_chat_recorder, delete_message_job, 
    send_or_reply_with_or_without_buttons
)
from .messages import (
    chat_handler, photo_handler, sticker_handler, spam_check_handler, 
    message_filter_handler, my_chat_member_handler, error_handler
)

# 【第二部分】定义 __all__ 列表，这是给 main.py 使用的
__all__ = [
    # from admin
    'ban_command', 'unban_command', 'auto_chat_on_command', 'auto_chat_off_command',
    'add_reply_command', 'del_reply_command', 'language_command',
    # from callbacks
    'main_menu_callback', 'settings_menu_callback', 'set_language_callback',
    'set_group_language_callback', 'search_page_callback', 'handle_category_menu_button',
    'handle_statistics_button', 'mystats_menu_callback', 'mystats_group_selection_callback',
    'mystats_all_groups_rank_callback', 'handle_activity_chart_button',
    'handle_activity_chart_generate_button', 'copy_code_callback', 'inline_query_handler',
    'group_admin_menu_callback', 'group_admin_action_callback',
    'remote_add_reply_start',
    'remote_add_reply_question_received', 'remote_add_reply_answer_received',
    'remote_add_reply_cancel',
    'remote_del_reply_menu_callback', 'remote_del_reply_action_callback',
    'remote_shop_management_menu',
    'toggle_checkin_callback',
    'remote_shop_add_start', 'remote_shop_add_name', 'remote_shop_add_desc',
    'remote_shop_add_cost', 'remote_shop_add_stock', 'remote_shop_add_cancel',
    'ASK_ITEM_NAME', 'ASK_ITEM_DESC', 'ASK_ITEM_COST', 'ASK_ITEM_STOCK',
    'ASK_REPLY_QUESTION', 'ASK_REPLY_ANSWER',
    # from commands
    'start_command', 'menu_command', 'help_command', 'new_command', 'summary_command',
    'mystats_command', 'search_command', 'settings_command', 'privacy_command',
    'rules_command', 'listreply_command',
    'checkin_command', 'points_command', 'shop_command', 'redeem_command',
    # from helpers
    'get_display_lang', 'escape_markdown_v2', '_format_time_delta',
    'create_search_pagination_keyboard', '_is_admin', 'handle_private_summary_back',
    'proactive_chat_recorder', 'delete_message_job',
    'send_or_reply_with_or_without_buttons',
    # from messages
    'chat_handler', 'photo_handler', 'sticker_handler', 'spam_check_handler',
    'message_filter_handler', 'my_chat_member_handler', 'error_handler',
]