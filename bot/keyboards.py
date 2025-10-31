# bot/keyboards.py (已移除多余的键盘)
from __future__ import annotations

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import uuid

# --- 内联键盘 (用于附在消息下方) ---
def get_copy_code_keyboard() -> tuple[InlineKeyboardMarkup, str]:
    """
    创建一个带有唯一ID的“复制代码”按钮。
    返回键盘对象和这个唯一的代码ID。
    """
    # 生成一个独一无二的ID，用于关联代码和按钮
    code_id = str(uuid.uuid4())
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("一键复制", callback_data=f"copy_code_{code_id}")]
        ]
    )
    return keyboard, code_id