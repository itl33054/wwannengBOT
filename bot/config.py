# bot/config.py (最终完整版)

import os
from dotenv import load_dotenv

load_dotenv()

# ### 语言配置 ###
DEFAULT_LANGUAGE = 'zh'  # 设置默认语言为中文
SUPPORTED_LANGUAGES = ['zh', 'en'] # 添加所有支持的语言代码

# ### 读取由逗号分隔的多个Google AI密钥 ###
google_api_keys_str = os.getenv("GOOGLE_API_KEYS")
if google_api_keys_str:
    GOOGLE_API_KEYS = [key.strip() for key in google_api_keys_str.split(',')]
else:
    GOOGLE_API_KEYS = []


# 从环境变量中获取密钥
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Google Search API 配置
GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

# 个人信息配置
YOUR_TELEGRAM_ID = int(os.getenv("YOUR_TELEGRAM_ID", "0"))
YOUR_TELEGRAM_USERNAME = os.getenv("YOUR_TELEGRAM_USERNAME", "YourUsername")
YOUR_NAME = os.getenv("YOUR_NAME", "Stardust")

developer_ids_str = os.getenv("DEVELOPER_IDS")
if developer_ids_str:
    DEVELOPER_IDS = [int(dev_id.strip()) for dev_id in developer_ids_str.split(',')]
else:
    DEVELOPER_IDS = []
    # bot/config.py

# ... (其他配置)

# --- 新增：用户排行榜黑名单 ---
# 在这里添加所有你不想让其出现在用户排行榜上的 user_id
# 默认包含 Telegram 官方账号 (777000)
# 你可以继续添加其他不想看到的 bot 或特殊账号的 ID
USER_RANKING_BLACKLIST = [
    '777000',  # Telegram 官方账号
    # '12345678', # 示例：添加另一个你想屏蔽的 bot ID
    # '87654321', # 示例：再添加一个
]