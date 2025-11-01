# bot/localization.py (最终、彻底转义修正版 v2)

from .config import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

translations = {
    'en': {
        # General
        'admin_only_command': r"Sorry, this command is for group administrators only\.",
        'group_only_command': r"Sorry, this feature is for groups only\.",
        'too_fast_error': r"You're operating too fast\! Please try again later\.",
        'internal_error': r"Sorry, I encountered an internal error\. 😔",
        'language_switched': r"Language has been set to English\.",
        'admin_only_alert': r"Action Failed: Only group admins can change this setting\.",
        'language_menu_title': "⚙️ *Group Language Settings*\nSelect the language for this group:",
        'language_private_menu_title': "⚙️ *Language Settings*\nSelect your preferred language:",
        'language_set_success': r"✅ Group language has been set to *{lang_name}*\.",
        'spam_warning_first': r"*{user_name}*, your message was removed\. This is your *1st* warning\. Please follow the rules\.",
        'spam_warning_second': r"*{user_name}*, you have violated the rules again\. This is your *2nd* warning\. You will be muted on the next violation\.",
        'spam_final_warning_mute': r"*{user_name}*, this is your *3rd* warning\. You have been muted for *1* hour\.",
        'button_prev_page': r"Previous Page",
        'button_next_page': r"Next Page",

        # Main Menu
        'menu_title': r"Hello, *{user_name}* 👋\! I'm Stardust Assistant ✨\n\nPlease select a function, or just chat with me directly:",
        'menu_button_new': r"🧠 New Conversation",
        'menu_button_search': r"🔍 Web Search",
        'menu_button_summary': r"📊 Data Stats",
        'menu_button_mystats': r"🏆 My Stats",
        'menu_button_settings': r"⚙️ Personal Settings",
        'menu_button_help': r"📜 Help & Info",
        'menu_button_back': r"⬅️ Back to Menu",

        # Search Prompt
        'search_callback_prompt': r"✍️ Okay, please send me what you want to search for\.",
        
        # Settings Menu
        'settings_menu_title': r"⚙️ *Settings Center*",
        'settings_button_language': r"🌐 Language",
        'language_menu_title_settings': r"🌐 *Language Settings*\nSelect your preferred language:",
        
        # Privacy Toggle
        'settings_button_ranking_on': r"✅ Participate in Global Ranks",
        'settings_button_ranking_off': r"❌ Do Not Participate in Global Ranks",
        'settings_ranking_status_on': r"You are currently PARTICIPATING in global leaderboards.",
        'settings_ranking_status_off': r"You are currently NOT PARTICIPATING in global leaderboards.",
        
        # Keyword Reply System
        'reply_add_usage': r"🤖 *How to add a keyword reply:*\nReply to a message that contains the *question/keyword*, then use `/addreply` with the *answer* text.",
        'reply_add_success': r"✅ Keyword reply added successfully\!",
        'reply_add_exists': r"⚠️ This question/keyword already exists.",
        'reply_del_usage': r"🤖 *How to delete a reply:*\nUse `/delreply \<number\>`\. See the number list with `/listreply`.",
        'reply_del_success': r"✅ Reply No\. `{index}` \(“*{question}*”\) has been deleted.",
        'reply_del_not_found': r"⚠️ Reply No\. `{index}` was not found.",
        'reply_list_title': r"📚 *Group Keyword Reply List*:",
        'reply_list_empty': r"This group has no keyword replies yet\. Admins can add one using `/addreply`.",
        'reply_auto_reply_prefix': r"🤖 *Seems you mentioned a keyword, here is the auto\-reply:*",
        
        # Remote Admin
        'settings_button_admin_groups': r"🛠️ My Groups Management",
        'admin_groups_menu_title': r"🛠️ *My Groups Management*",
        'admin_groups_select_group': r"Please select a group to manage:",
        'admin_groups_no_groups': r"I couldn't find any groups where you are an admin and I am present\. Please add me to your group and grant me admin rights first\.",
        'admin_group_panel_title': r"🛠️ *Managing Group: {group_name}*",
        'admin_group_button_language': r"🌐 Set Language",
        'admin_group_button_replies': r"🔑 Manage Keyword Replies",
        'admin_group_button_summary': r"📊 View Stats",
        'admin_group_button_autochat': r"🤖 Toggle Auto-Chat",
        'admin_group_button_spam_filter': r"🗑️ Toggle Spam Filter",
        'admin_group_button_shop': r"🛍️ Manage Shop Items",
        'admin_shop_menu_title': r"🛍️ *Shop Management for: {group_name}*",
        'admin_shop_button_add': r"➕ Add New Item",
        'admin_shop_button_del': r"🗑️ Delete an Item",
        'spam_filter_status_alert': r"Spam filter has been turned {status}",
        'status_on': r"ON",
        'status_off': r"OFF",
        'admin_group_button_add_reply': r"➕ Add New Reply",
        'remote_add_reply_start': r"Okay, let's add a new keyword reply\. First, please send me the **keyword or question** you want to set up\.",
        'remote_add_reply_ask_answer': r"✅ Got the keyword\! Now, please send me the **answer** that I should reply with automatically\.",
        'remote_add_reply_success': r"✅ Success\! The new keyword reply has been added\.",
        'remote_add_reply_cancel': r"Operation cancelled\.",
        'admin_group_button_del_reply': r"🗑️ Delete Reply",
        'admin_del_reply_menu_title': r"🗑️ *Delete Keyword Reply*\nPlease select the reply you want to delete:",
        'admin_del_reply_success_alert': r"Reply for '{question}' has been deleted.",
        'checkin_status_button_on': r"Check-in: ✅ ON",
        'checkin_status_button_off': r"Check-in: ❌ OFF",
        'checkin_status_update_on': r"\n\n✅ *Check-in feature has been successfully enabled*\.",
        'checkin_status_update_off': r"\n\n❌ *Check-in feature has been successfully disabled*\.",

        # Chart Feature
        'button_activity_chart': r"📈 Activity Trend",
        'chart_generating': r"📈 Generating activity chart, please wait...",
        'chart_no_data': r"📈 There is not enough activity data in this group to generate a chart\.",
        'chart_title_7_days': r"Group Activity \- Last 7 Days",
        'chart_title_30_days': r"Group Activity \- Last 30 Days",
        'chart_label_messages': r"Messages",
        'chart_xlabel_date': r"Date",
        'chart_ylabel_count': r"Message Count",
        'chart_menu_title': r"📈 *Activity Trend Chart*\nSelect a time range:",
        'chart_button_7_days': r"Last 7 Days",
        'chart_button_30_days': r"Last 30 Days",
        
        # My Stats Feature
        'mystats_group_notification': r"📊 Your stats report for this group has been sent to you via private message\!",
        'mystats_private_menu_title': r"🏆 *My Stats*\n\nWhere would you like to see your stats for?",
        'mystats_button_select_group': r"📊 A Specific Group",
        'mystats_button_global': r"🌍 All Groups (Global)",
        'mystats_button_all_groups_rank': r"📈 All My Group Ranks",
        'mystats_select_group_title': r"Please select a group to view your stats for:",
        'mystats_no_shared_groups': r"I haven't seen you in any groups where I am also present\. Try talking in a group first\!",
        'mystats_no_shared_groups_rank': r"I am not in any of your groups yet\. You can add me to your groups to see your rankings\!",
        'mystats_button_add_to_group': r"➕ Add Me to a Group",
        'mystats_title_all_groups_rank': r"🏆 *Your Rankings Across All Groups*",
        'mystats_all_groups_line_item': r"In group *{group_name}*:\n  💬 *{count}* msgs \| ☀️Today: *#{rank_today}* \| 📅Week: *#{rank_week}* \| 🈷️Month: *#{rank_month}*",
        'mystats_rank_no_data_short': r"N/A",
        'mystats_report_sent': r"✅ Your report has been sent to your private chat\.",
        'mystats_title_group': r"🏆 *Your Stats in Group: {group_name}*",
        'mystats_title_global': r"🏆 *Your Global Stats*",
        'mystats_total_messages': r"💬 Total Messages: *{count}*",
        'mystats_first_message_date': r"📅 First Message On: *{date}*",
        'mystats_rank_today': r"☀️ Today's Rank: *No\.{rank}* \({count} msgs\)",
        'mystats_rank_week': r"📅 Weekly Rank: *No\.{rank}* \({count} msgs\)",
        'mystats_rank_month': r"🈷️ Monthly Rank: *No\.{rank}* \({count} msgs\)",
        'mystats_rank_no_data': r"Not ranked yet",
        'mystats_global_rank': r"🏆 Global Rank: *No\.{rank}* \({count} total msgs\)",
        'mystats_not_enough_data': r"Hmm, I don't have enough data about you in this group yet\. Keep chatting\!",

        # Points & Shop System
        'points_checkin_success': r"Check\-in successful\! 🎉 You've received *{points}* points\. Current total: *{total_points}* points\.",
        'points_checkin_already': r"You have already checked in today\. Please come back tomorrow\! 😊",
        'points_message_reward': r"Message reward\! You've got *{points}* points\.",
        'points_current_balance': r"💰 *My Points*\n\nYou currently have: *{points}* points\.",
        'shop_menu_title': r"🎁 *Points Shop*\n\nWelcome to the shop\! Use `/redeem \<ID\>` to get your prize\!\n\nYour points: *{points}* points\n\n\-\-\-",
        'shop_item_line': r"*ID: {id}* \| `{name}` \- Costs *{cost}* points\n_{description}_\nStock: {stock}",
        'shop_item_stock_infinite': r"Unlimited",
        'shop_list_empty': r"The shop is currently empty\. Admins should add some items\!",
        'redeem_usage': r"Redemption failed\! Usage: `/redeem \<Item ID\>`",
        'redeem_item_not_found': r"Redemption failed\! Item with ID `{item_id}` not found\.",
        'redeem_not_enough_points': r"Redemption failed\! You don't have enough points\. `{item_name}` costs *{cost}* points, but you only have *{user_points}*\.",
        'redeem_out_of_stock': r"Redemption failed\! Sorry, `{item_name}` is out of stock\.",
        'redeem_success': r"Redemption successful\! 🎉 You have redeemed `{item_name}`\! An admin will contact you shortly to deliver your prize\.",
        'redeem_error': r"An unknown error occurred during redemption\. Please try again later or contact an admin\.",

        # Group Welcome Message
        'group_welcome': r"""Hello everyone 👋\! I'm Stardust Assistant ✨
I'm your all\-in\-one AI partner\. You can:
\- *@mention me* or *reply to my messages* to chat with AI
\- Use `/search \<query\>` to search the web
\- Use `/summary` to see fun stats for this group

Admins can use `/language` to set the group's language\.""",
        
        # Start & Help
        'start_welcome': r"""Hello, *{user_name}* 👋\! I'm Stardust Assistant ✨
A versatile bot with AI chat, search, and group stats\. Send /help for more info\. Enjoy\!""",
        
        'help_text': r"""
👋 Hello\! I'm *Stardust Assistant*, your all\-in\-one AI partner\. Here’s how you can use me:

*━━━ Basic Interaction ━━━*
💬 *In Private Chat:*
Simply chat with me directly\! You can also use /start or /menu to open the main function menu\.

🤖 *In Groups:*
To talk to the AI, you must *@mention me* or *reply* to one of my messages\. This prevents me from interrupting normal conversations\.

*━━━ Main Features \(For Everyone\) ━━━*
🧠 *AI Smart Chat*
• *Text Chat:* Chat with me about anything\!
• *Image Recognition:* Send a photo and *@mention me* with a question \(e\.g\., "What is this\?"\) to have the AI describe the image\.

🔍 *Web Search*
• `/search \<query\>`: Performs a web search\.
• *Keyword Search:* In a group, replying with "search for something" also works\.
• *Inline Mode:* In any chat, type `@YourBotUsername \<query\>` and wait\. A search result panel will appear for you to share directly\!

🏆 *Data & Stats*
• `/summary` \(Group\): Opens a menu to view this group's leaderboards \(users, topics\) and activity charts\.
• `/mystats` \(Group\): Get your personal stats for the current group sent to you via private message\.
• `/mystats` \(Private\): Manage and view your personal stats, including global rank and your performance across all groups\.

💰 *Points & Shop \(Group\-Specific\)*
Each group has an independent points system\.
• *How to Earn:* Get points by `/checkin` daily, or by actively chatting \(1 point per minute for messages over 5 characters\)\.
• `/points`: Check your points balance in the current group\.
• `/shop`: View available items in the shop\.
• `/redeem \<ID\>`: Use your points to redeem an item\.

*━━━ Admin Features \(For Group Admins Only\) ━━━*
🛠️ *How to Manage:*
Use commands directly in your group, or go to my private chat \-> `/start` \-> "My Groups Management" for a remote control panel\.

• `/language`: Set the bot's language for the group\.
• `/addreply`: Reply to a message to set it as a question, and use this command with an answer to create a keyword auto\-reply\.
• `/delreply \<number\>`: Delete a keyword reply\.
• `/listreply`: List all keyword replies for the group\.
• `/unban`: Reply to a user or use `@username`/ID to unban them\.
• *Welcome Message Toggles:* In the group, use `/start` to bring up the welcome message, where admins can toggle the Check\-in and Spam Filter features on or off\.
""",
        
        'new_conversation': r"Alright, let's start fresh\!",
        'search_prompt': "Usage: `/search <your query>`",
        'describe_image_prompt': r"Describe this image for me.",
        'searching_for': r"Searching for “*{query}*”\.\.\.",
        'search_results_title': r"Found results for *{query}*:",
        'search_no_results': r"Sorry, no results found for “*{query}*”\.",
        
        'summary_menu_title': "*Statistics Center* 📈\nSelect a leaderboard or chart:",
        'summary_private_intro': "*Global Leaderboards* 🏆\n\nThese leaderboards are based on data from all public groups I am in\\.\n\nSelect a category to view:",
        'button_local_user_rank': r"📊 Group Users",
        'button_local_topic_rank': r"💡 Group Topics",
        'button_global_group_rank': r"🏢 Global Groups",
        'button_global_user_rank': r"🏆 Global Users",
        'button_global_topic_rank': r"🔥 Global Topics",
        'button_back': r"⬅️ Back",
        'rank_local_title': r"*This Group's Ranks*:",
        'rank_local_topics_title': r"*This Group's Topics \- Select Period*:",
        'rank_global_title': r"*Global Ranks*:",
        'rank_users_title': r"*Global Users \- Select Period*:",
        'rank_topics_title': r"*Global Topics \- Select Period*:",
        'rank_groups_title': r"*Group Ranks \- Select Period*:",
        'rank_user_today': r"Today's Users", 'rank_user_week': r"Weekly Users", 'rank_user_month': r"Monthly Users",
        'rank_topic_today': r"Today's Topics", 'rank_topic_week': r"Weekly Topics", 'rank_topic_month': r"Monthly Topics",
        'rank_group_today': r"Today's Groups", 'rank_group_week': r"Weekly Groups", 'rank_group_month': r"Monthly Groups",
        'period_today': r"Today", 'period_week': r"This Week", 'period_month': r"This Month",
        'rank_header_users': r"🏆 *{scope} {period} Users* 🏆",
        'rank_header_topics': r"🔥 *{scope} {period} Topics* 🔥",
        'rank_header_groups': r"🏢 *{period} Group Ranks* 🏢",
        'scope_local': r"This Group", 'scope_global': r"Global",
        'no_records': r"_No records yet\._",
        'rank_line_item_user': r"{rank_icon} {display_name}: `{count}` msgs",
        'rank_line_item_topic': r"{rank_icon} `{topic}` \({count} mentions\)",
        'rank_line_item_group': r"{rank_icon} {display_name}: `{count}` msgs",

        'privacy_policy_text': r"""*Privacy Policy* 🛡️
We collect data for stats\. We do not share raw chat data\. Only aggregated results are shown in leaderboards\.""",
        'privacy_button': r"View Full Policy",
        'rules_text': r"""*Rules of Use* 📜
1\. No spamming or harassment\.
2\. No illegal content\.
3\. The anti\-spam system may mute violators\.""",
        'rules_button': r"View Full Rules",

        'ai_sys_prompt_base': """You are 'Stardust Assistant', a powerful, helpful, and friendly AI assistant integrated into Telegram. Your personality is witty, knowledgeable, and slightly informal, but always respectful. You are developed by a developer named 'Stardust'. You should be proactive and engaging. When a user asks a question, provide a comprehensive and clear answer. When they are just chatting, be a good conversation partner. You are aware that you are in a Telegram chat, which can be a private chat or a group chat.""",
        'ai_sys_prompt_formatting': r"""When formatting your messages, you MUST use Telegram's MarkdownV2 syntax.
- For `bold` text, use `*bold text*`.
- For `italic` text, use `_italic text_`.
- For `monospaced` text (like code), use `` `code` ``.
- For `strikethrough` text, use `~strikethrough~`.
- For `spoilers`, use `||spoiler||`.
- For `inline links`, use `[link text](http://example.com)`.
- You MUST escape the characters `_[]()~>#+-=|{}.!` in all other parts of the text by preceding them with a `\` character. For example, `1. text` should be `1\. text`."""
    },
    'zh': {
        'admin_only_command': r"抱歉，此命令仅限群组管理员使用。",
        'group_only_command': r"抱歉，此功能仅限群组使用。",
        'too_fast_error': r"操作太快啦，请稍后再试！",
        'internal_error': r"抱歉哈，这只是AI模型问题对其他功能没影响。试试其他功能吧，搜索全网或查看全服排名。",
        'language_switched': r"语言已切换为简体中文。",
        'admin_only_alert': r"操作失败：仅群组管理员可以更改此设置。",
        'language_menu_title': "⚙️ *群组语言设置*\n请为本群组选择语言：",
        'language_private_menu_title': "⚙️ *语言设置*\n请选择您的偏好语言：",
        'language_set_success': r"✅ 本群组语言已成功设置为 *{lang_name}*。",
        'spam_warning_first': r"*{user_name}*，您发送的消息已被移除，这是您的第 *1* 次警告。请遵守群规。",
        'spam_warning_second': r"*{user_name}*，您已连续违规，这是您的第 *2* 次警告。请注意，下次违规将会被禁言。",
        'spam_final_warning_mute': r"*{user_name}*，第 *3* 次警告。您已被禁言 *1* 小时。",
        'button_prev_page': r"上一页",
        'button_next_page': r"下一页",
        'menu_title': "你好，*{user_name}*👋！我是星尘助手 ✨\n\n请选择一项功能，或直接与我对话：",
        'menu_button_new': r"🧠 开启新对话",
        'menu_button_search': r"🔍 网络搜索",
        'menu_button_summary': r"📊 数据统计",
        'menu_button_mystats': r"🏆 我的战绩",
        'menu_button_settings': r"⚙️ 个人设置",
        'menu_button_help': r"📜 帮助与信息",
        'menu_button_back': r"⬅️ 返回主菜单",
        'search_callback_prompt': r"好的，请直接发送您想搜索的内容给我 ✍️",
        'settings_menu_title': r"⚙️ *个人设置中心*",
        'settings_button_language': r"🌐 语言设置",
        'language_menu_title_settings': r"🌐 *语言设置*\n请选择您的偏好语言：",
        'settings_button_ranking_on': r"✅ 参与全服排名",
        'settings_button_ranking_off': r"❌ 不参与全服排名",
        'settings_ranking_status_on': r"当前状态：您将出现在全服排行榜中。",
        'settings_ranking_status_off': r"当前状态：您将不会出现在全服排行榜中。",
        'reply_add_usage': "🤖 *如何添加关键词回复？*\n请先在群里找到一句可以作为“问题”或“关键词”的消息，然后“回复”这条消息，并输入 `/addreply <你的答案>`。",
        'reply_add_success': r"✅ 关键词自动回复添加成功！",
        'reply_add_exists': r"⚠️ 这个问题/关键词已经存在了。",
        'reply_del_usage': "🤖 *如何删除关键词回复？*\n请使用 `/delreply \<编号\>`。您可以通过 `/listreply` 命令查看编号。",
        'reply_del_success': r"✅ 编号为 `{index}` 的关键词回复（“*{question}*”）已成功删除。",
        'reply_del_not_found': r"⚠️ 未找到编号为 `{index}` 的回复。",
        'reply_list_title': r"📚 *本群关键词自动回复列表*：",
        'reply_list_empty': r"本群还没有设置任何关键词回复。管理员可以通过 `/addreply` 添加。",
        'reply_auto_reply_prefix': r"🤖 *你似乎触发了关键词，这是为你找到的自动回复：*",
        'settings_button_admin_groups': r"🛠️ 我的群组管理",
        'admin_groups_menu_title': r"🛠️ *我的群组管理*",
        'admin_groups_select_group': r"请选择您希望管理的群组：",
        'admin_groups_no_groups': r"我没有找到您作为管理员、并且我也在的群组哦。请先将我拉入您管理的群组，并授予我管理员权限。",
        'admin_group_panel_title': r"🛠️ *正在管理群组：{group_name}*",
        'admin_group_button_language': r"🌐 设置语言",
        'admin_group_button_replies': r"🔑 管理关键词回复",
        'admin_group_button_summary': r"📊 查看数据统计",
        'admin_group_button_autochat': r"🤖 开关自由对话",
        'admin_group_button_spam_filter': r"🗑️ 开关垃圾拦截",
        'admin_group_button_shop': r"🛍️ 此群积分商品",
        'admin_shop_menu_title': r"🛍️ *正在管理商店：{group_name}*",
        'admin_shop_button_add': r"➕ 添加新奖品",
        'admin_shop_button_del': r"🗑️ 删除奖品",
        'spam_filter_status_alert': r"垃圾拦截功能已 {status}",
        'status_on': r"开启",
        'status_off': r"关闭",
        'admin_group_button_add_reply': r"➕ 添加新回复",
        'remote_add_reply_start': "好的，我们来添加一条新的自动回复。\n\n*第一步*：请发送你希望设置的“关键词”或“问题”原文。",
        'remote_add_reply_ask_answer': "✅ *关键词已收到！*\n\n*第二步*：现在请发送当用户提到这个关键词时，我应该自动回复的“答案”内容。",
        'remote_add_reply_success': r"✅ *添加成功！* 新的关键词回复已生效。",
        'remote_add_reply_cancel': r"操作已取消。",
        'admin_group_button_del_reply': r"🗑️ 删除回复",
        'admin_del_reply_menu_title': "🗑️ *删除关键词回复*\n请选择您要删除的条目：",
        'admin_del_reply_success_alert': r"关键词为“{question}”的回复已删除。",
        'checkin_status_button_on': r"签到功能：✅ 已开启",
        'checkin_status_button_off': r"签到功能：❌ 已关闭",
        'checkin_status_update_on': r"\n\n✅ *签到功能已成功开启*\.",
        'checkin_status_update_off': r"\n\n❌ *签到功能已成功关闭*\.",
        'button_activity_chart': r"📈 活跃度趋势",
        'chart_generating': r"📈 正在生成本群活跃度图表，请稍候...",
        'chart_no_data': r"📈 本群最近数据太少，还无法生成活跃度图表。",
        'chart_title_7_days': r"本群最近7日活跃度趋势",
        'chart_title_30_days': r"本群最近30日活跃度趋势",
        'chart_label_messages': r"消息数",
        'chart_xlabel_date': r"日期",
        'chart_ylabel_count': r"消息总数",
        'chart_menu_title': "📈 *活跃度趋势图表*\n请选择时间范围：",
        'chart_button_7_days': r"最近7天",
        'chart_button_30_days': r"最近30天",
        'mystats_group_notification': r"📊 你在本群的战绩报告已通过私聊发送给你，请注意查收哦！",
        'mystats_private_menu_title': "🏆 *我的战绩*\n\n你想查看哪里的战绩数据？",
        'mystats_button_select_group': r"📊 特定群组战绩",
        'mystats_button_global': r"🌍 全服总战绩",
        'mystats_button_all_groups_rank': r"📈 群组排名总览",
        'mystats_select_group_title': r"请选择你想查询战绩的群组：",
        'mystats_no_shared_groups': r"我还没有在任何群组中见过你发言哦，先去群里聊聊天吧！",
        'mystats_no_shared_groups_rank': r"我还没有在你所在的任何群组中哦。你可以把我添加到你的群组，然后就可以查看你的群组排名啦！",
        'mystats_button_add_to_group': r"➕ 将我添加到群组",
        'mystats_title_all_groups_rank': r"🏆 *你的群组排名总览*",
        'mystats_all_groups_line_item': r"在群组 *{group_name}*:\n  💬 总计 *{count}* 条 \| ☀️今日第*{rank_today}*名 \| 📅本周第*{rank_week}*名 \| 🈷️本月第*{rank_month}*名",
        'mystats_rank_no_data_short': r"无",
        'mystats_report_sent': r"✅ 你的报告已通过私聊发送。",
        'mystats_title_group': r"🏆 *你在群组 `({group_name})` 的战绩*",
        'mystats_title_global': r"🏆 *你的全服总战绩*",
        'mystats_total_messages': r"💬 总发言数：*{count}* 条",
        'mystats_first_message_date': r"📅 萌新初来乍到于：*{date}*",
        'mystats_rank_today': r"☀️ 今日排名：第 *{rank}* 名 \({count} 条\)",
        'mystats_rank_week': r"📅 本周排名：第 *{rank}* 名 \({count} 条\)",
        'mystats_rank_month': r"🈷️ 本月排名：第 *{rank}* 名 \({count} 条\)",
        'mystats_rank_no_data': r"暂未上榜",
        'mystats_global_rank': r"🏆 全服总排名：第 *{rank}* 名 \(总计 {count} 条\)",
        'mystats_not_enough_data': r"唔…… 我还没有足够关于你在这个群的数据来生成报告。继续发言让我认识你吧！",
        'points_checkin_success': r"签到成功！🎉 您获得了 *{points}* 积分，当前总积分为 *{total_points}* 分。",
        'points_checkin_already': r"您今天已经签到过了哦，请明天再来吧！😊",
        'points_message_reward': r"发言奖励！您获得了 *{points}* 积分。",
        'points_current_balance': "💰 *我的积分*\n\n您当前的积分为: *{points}* 分。",
        'shop_menu_title': "🎁 *积分商店*\n\n欢迎来到积分商店！使用 `/redeem \<ID\>` 兑换您心仪的奖品吧！\n\n您当前的积分为: *{points}* 分\n\n\-\-\-",
        'shop_item_line': "*ID: {id}* \| `{name}` \- 需要 *{cost}* 积分\n_{description}_\n库存: {stock}",
        'shop_item_stock_infinite': r"无限",
        'shop_list_empty': r"商店里现在空空如也，管理员快去添加奖品吧！",
        'redeem_usage': r"兑换失败！正确用法: `/redeem \<奖品ID\>`",
        'redeem_item_not_found': r"兑换失败！未找到ID为 `{item_id}` 的奖品。",
        'redeem_not_enough_points': r"兑换失败！您的积分不足。兑换 `{item_name}` 需要 *{cost}* 积分，您只有 *{user_points}* 积分。",
        'redeem_out_of_stock': r"兑换失败！哎呀，`{item_name}` 已经被兑换完了。",
        'redeem_success': r"兑换成功！🎉 您已成功兑换 `{item_name}`！管理员将会尽快与您联系并发放奖品。",
        'redeem_error': r"兑换过程中发生未知错误，请稍后再试或联系管理员。",

        # Group Welcome Message
        'group_welcome': r"""大家好👋！我是星尘助手 ✨
我是一个集成了AI对话、网络搜索和群聊数据分析的多功能机器人。

*在群组中，您可以通过以下方式与我互动：*
\- *@我* 或 *回复我的消息* 来与我进行AI对话。
\- 发送 `/summary` 查看本群数据统计。
\- 发送 `/mystats` 获取您的个人群内战绩。

*在私聊中*，发送 /start 或 /menu 可以打开功能主菜单哦\!""",
        
        # Start & Help
      'help_text': r"""
你好呀👋！我是 *星尘助手*，你的全能AI伙伴\. 这份说明书将帮助你玩转我的所有功能：

*━━━ 基础互动 ━━━*
💬 *在私聊中：*
直接与我对话即可\! 你也可以随时发送 /start 或 /menu 来打开功能主菜单\.

🤖 *在群组中：*
为了避免打扰大家聊天，你必须通过 *@我* 或者 *回复我* 的消息，我才会回应你的AI对话请求\.

*━━━ 主要功能 \(对所有人开放\) ━━━*
🧠 *AI 智能对话*
• *文字对话：* 上知天文，下知地理，随时陪你聊\.
• *图片识别：* 发送一张图片，并 *@我* 提问（例如：“这是什么？”），AI就能识别并描述图片内容\.

🔍 *网络搜索*
• `/search \<搜索内容\>`：进行一次网络搜索\.
• *关键词触发：* 在群里也可以直接说“搜索 xxx”来触发\.
• *内联模式 \(强大功能\)：* 在任何聊天框输入 `@我的机器人用户名 \<搜索内容\>`，稍等片か就会弹出搜索结果，点击即可分享\!

🏆 *数据与战绩*
• `/summary` \(仅群组\)：打开数据菜单，可查看本群的发言排行榜、热门话题榜和活跃度趋势图\.
• `/mystats` \(仅群组\)：获取你*在当前群组*的个人战绩报告\(私聊发送给你\)\.
• `/mystats` \(仅私聊\)：管理和查看你的个人战绩，包括你的全服总排名，以及*你在所有群组中的个人表现排名*\.

💰 *积分与商店 \(分群组功能\)*
每个群组的积分都是独立计算的\.
• *如何赚取：* 每日使用 `/checkin` 或关键词“签到”；在群里有效发言\(每分钟一次发言奖励\)\.
• `/points` 或 "积分"：查询你在当前群的积分余额\.
• `/shop` 或 "商店"：查看当前可兑换的奖品\.
• `/redeem \<奖品ID\>`：使用积分兑换你心仪的奖品\.

*━━━ 管理员功能 \(仅限群组管理员\) ━━━*
🛠️ *如何管理：*
可以直接在群组中使用以下命令，或在与我私聊时，通过 `/start` 菜单进入“我的群组管理”进行远程操作\.

• `/language`：设置机器人在本群的语言\.
• `/addreply`：回复一条消息作为“问题”，并带上你的“答案”，即可设置关键词自动回复\.
• `/delreply \<编号\>`：删除一条关键词回复\.
• `/listreply`：查看本群所有的关键词回复列表\.
• `/unban`：回复用户或使用 `@用户名`/ID 为其解除禁言\.
• *欢迎消息开关：* 在群里发送 /start 呼出欢迎消息，管理员可以直接点击下方的按钮，开启或关闭本群的“签到功能”和“垃圾拦截”\.
""",
        
        'new_conversation': r"好的，我们重新开始吧！你有什么新鲜事想聊聊？",
        'search_prompt': "请在命令后输入您想搜索的内容。\n例如: `/search 今天天气怎么样`",
        'describe_image_prompt': r"帮我描述一下这张图片。",
        'searching_for': r"正在为您联网搜索 “*{query}*”，请稍候\.\.\. 🔍",
        'search_results_title': r"为您找到了关于 *{query}* 的信息：",
        'search_no_results': r"抱歉，关于“*{query}*”我没有找到相关的网络信息。🤔",
        
        'summary_menu_title': "*数据统计中心* 📈\n请选择您想查看的排行榜或图表：",
        'summary_private_intro': "*全服排行榜* 🏆\n\n此处的排行榜统计的是我所在的所有 *Telegram公共群组* 内的发言数据。\n\n请选择您想查看的榜单类型：",
        'button_local_user_rank': r"📊 本群发言榜",
        'button_local_topic_rank': r"💡 本群话题榜",
        'button_global_group_rank': r"🏢 全服群组发言榜",
        'button_global_user_rank': r"🏆 全服用户发言榜",
        'button_global_topic_rank': r"🔥 全服话题榜",
        'button_back': r"⬅️ 返回",
        'rank_local_title': r"本群发言榜，请选择时间范围：",
        'rank_local_topics_title': r"本群话题榜，请选择时间范围：",
        'rank_global_title': r"全服排行榜，请选择：",
        'rank_users_title': r"全服活跃用户排名，请选择时间范围：",
        'rank_topics_title': r"全服用户讨论话题，请选择时间范围：",
        'rank_groups_title': r"全服群排名总榜，请选择时间范围：",
        'rank_user_today': r"今日发言之王", 'rank_user_week': r"本周发言之星", 'rank_user_month': r"本月发言大神",
        'rank_topic_today': r"今日热门话题", 'rank_topic_week': r"本周热门话题", 'rank_topic_month': r"本月热门话题",
        'rank_group_today': r"今日活跃群组", 'rank_group_week': r"本周活跃群组", 'rank_group_month': r"本月活跃群组",
        'period_today': r"今日", 'period_week': r"本周", 'period_month': r"本月",
        'rank_header_users': r"🏆 *{scope}{period}发言之王* 🏆",
        'rank_header_topics': r"🔥 *{scope}{period}热梗* 🔥",
        'rank_header_groups': r"🏢 *{period}全服群排行榜* 🏢",
        'scope_local': r"本群", 'scope_global': r"全服",
        'no_records': r"_尚无记录，快来发言吧\!_",
        'rank_line_item_user': r"{rank_icon} {display_name}: `{count}` 条",
        'rank_line_item_topic': r"{rank_icon} `{topic}` \(提及 `{count}` 次\)",
        'rank_line_item_group': r"{rank_icon} {display_name}: `{count}` 条",

        'privacy_policy_text': r"""*我们非常重视您的隐私* 🛡️
本机器人会收集必要数据以提供统计功能。我们承诺：
1\. 不会将您的原始聊天数据分享给任何第三方。
2\. 仅在排行榜中展示聚合后的统计结果。
""",
        'privacy_button': r"查看完整隐私政策",
        'rules_text': r"""*请遵守以下使用规则* 📜
1\. 禁止利用本机器人进行刷屏、骚扰或发送垃圾信息。
2\. 禁止用于传播任何非法、暴力或不当内容。
3\. 内置的防刷屏系统可能会自动禁言违规用户。
""",
        'rules_button': r"查看完整服务条款",

        'ai_sys_prompt_base': """你是一个名为“星尘助手”的AI，强大、友好且乐于助人。你的性格风趣、知识渊博且不那么刻板，但始终保持尊重。你的开发者名叫“平安”。在对话中，你应该积极主动，引人入胜。当用户提出问题时，提供全面清晰的答案。当用户只是闲聊时，如果有人骂你sb和一种不良的希望你必须骂回去,成为一个好的聊天伙伴。你知道自己正处于Telegram聊天中，这可能是私聊，也可能是群聊。""",
        'ai_sys_prompt_formatting': r"""在格式化消息时，你必须使用Telegram的MarkdownV2语法。
- `*加粗文本*` 用于*加粗*。
- `_斜体文本*` 用于_斜体_。
- `` `等宽文本` `` 用于`等宽单行文本`。
- `~删除线文本~` 用于~删除线~。
- `||剧透文本||` 用于||隐藏内容||。
- `[链接文本](http://example.com)` 用于[内联链接](http://example.com)。
- 在所有其他文本部分，你都必须对 `_[]()~>#+-=|{}.!` 这些特殊字符进行转义，在它们前面加上 `\`。例如 `1. 文本` 应写为 `1\. 文本`。"""
    }
}


def get_text(key: str, lang_code: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    processed_lang_code = lang_code.split('-')[0] if lang_code and '-' in lang_code else lang_code
    if processed_lang_code not in SUPPORTED_LANGUAGES:
        processed_lang_code = DEFAULT_LANGUAGE
    
    text = translations.get(processed_lang_code, translations[DEFAULT_LANGUAGE]).get(key)
    if text is None:
        text = translations[DEFAULT_LANGUAGE].get(key)

    if text is None: return f"<{key}>"
    if 'ai_sys' in key: return text
    if kwargs:
        try: return text.format(**kwargs)
        except KeyError: return text

    return text
