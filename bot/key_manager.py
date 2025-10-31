# bot/key_manager.py (新增文件)
from __future__ import annotations

import logging
from typing import Optional
from .config import GOOGLE_API_KEYS

logger = logging.getLogger(__name__)

class ApiKeyManager:
    """负责管理和轮换Google AI API密钥的单例类。"""
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ApiKeyManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):  # 防止重复初始化
            self.keys = GOOGLE_API_KEYS
            self.current_key_index = 0
            self.initialized = True
            if not self.keys:
                logger.warning("警告：Google AI的API密钥列表为空！AI对话功能将无法使用。")
            else:
                logger.info(f"成功加载 {len(self.keys)} 个Google AI API密钥。")

    def get_current_key(self) -> Optional[str]:
        """获取当前正在使用的密钥。"""
        if self.current_key_index < len(self.keys):
            return self.keys[self.current_key_index]
        return None

    def switch_to_next_key(self) -> Optional[str]:
        """切换到下一个可用的密钥。"""
        self.current_key_index += 1
        new_key = self.get_current_key()
        
        if new_key:
            logger.warning(f"密钥用量耗尽，已自动切换到下一个密钥 (索引: {self.current_key_index})。")
        else:
            logger.error("所有Google AI API密钥均已耗尽！")
            
        return new_key

# 创建一个全局唯一的密钥管理器实例，供其他模块导入和使用
api_key_manager = ApiKeyManager()