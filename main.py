import os
from app import create_app, Config

# 导入日志获取方法（日志系统会在首次使用时自动从 Config 获取配置并初始化）
from app.utils.logger import get_logger

# 获取当前模块日志记录器（会自动初始化日志系统）
logger = get_logger(__name__)


if __name__ == "__main__":

    app = create_app()

    # 记录应用启动的信息到日志
    logger.info(f"正在启动raglite，服务在{Config.APP_HOST}:{Config.APP_PORT}")

    # 启动 Flask 应用，监听指定主机和端口，是否开启调试模式由配置决定
    app.run(host=Config.APP_HOST, port=Config.APP_PORT, debug=Config.APP_DEBUG)
