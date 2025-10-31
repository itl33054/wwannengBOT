# bot/chart_generator.py (最终修复版 - 直接加载字体文件)
from __future__ import annotations

import logging
import os
from io import BytesIO
from typing import Optional
from datetime import datetime, timedelta
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties # <--- 新增导入

from .statistics import get_daily_activity_for_chat
from .localization import get_text

logger = logging.getLogger(__name__)

# --- 解决 Matplotlib 中文乱码问题的最终方案 ---

# 定义字体文件的相对路径
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'simhei.ttf')

# 检查字体文件是否存在
if os.path.exists(FONT_PATH):
    # 从文件路径加载字体
    custom_font = FontProperties(fname=FONT_PATH)
    logger.info(f"成功从路径 '{FONT_PATH}' 加载中文字体。")
else:
    custom_font = None
    logger.error(f"字体文件未找到！请确保 'simhei.ttf' 已放置在项目根目录的 'assets' 文件夹下。")

# 告诉 Matplotlib 在非 GUI 线程中安全地工作
matplotlib.use('Agg')


def generate_activity_chart(chat_id: int, lang_code: str, days: int = 7) -> Optional[BytesIO]:
    """
    生成指定群组在过去N天的每日消息活跃度图表。
    """
    logger.info(f"开始为群组 {chat_id} 生成过去 {days} 天的活跃度图表...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    activity_data = get_daily_activity_for_chat(chat_id, start_date, end_date)
    
    if not activity_data:
        logger.warning(f"群组 {chat_id} 在指定日期范围内没有活跃数据。")
        return None

    dates = [(start_date + timedelta(days=i)).date() for i in range(days + 1)]
    counts = [activity_data.get(d, 0) for d in dates]
    
    try:
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, ax = plt.subplots(figsize=(12, 7))

        ax.plot(dates, counts, marker='o', linestyle='-', color='#4C84FF', label=get_text('chart_label_messages', lang_code))

        # --- 修改：在所有设置文本的地方，都应用我们的自定义字体 ---
        title_key = 'chart_title_7_days' if days == 7 else 'chart_title_30_days'
        ax.set_title(get_text(title_key, lang_code), fontsize=18, pad=20, fontproperties=custom_font)
        
        ax.set_xlabel(get_text('chart_xlabel_date', lang_code), fontsize=12, fontproperties=custom_font)
        ax.set_ylabel(get_text('chart_ylabel_count', lang_code), fontsize=12, fontproperties=custom_font)
        
        # 为图例设置字体
        legend = ax.legend(prop=custom_font)

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

        ax.grid(True, which='both', linestyle='--', linewidth=0.5)
        
        ax.yaxis.get_major_locator().set_params(integer=True)
        ax.set_ylim(bottom=0)

        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        plt.close(fig)
        
        logger.info(f"为群组 {chat_id} 成功生成活跃度图表。")
        return buf
        
    except Exception as e:
        logger.error(f"生成图表时发生错误: {e}", exc_info=True)
        return None