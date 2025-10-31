# run.py (最终的、正确的、简化的启动版本)

from bot import main

if __name__ == '__main__':
    # 直接调用 main.run()，不再需要 asyncio
    main.run()