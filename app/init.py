# RAG Lite 应用模块说明
"""
RAG Lite 项目应用入口
"""

# 导入系统相关模块
import os

# 导入应用的主模块flask
from flask import Flask, request

# 导入Flask跨域资源共享支持
from flask_cors import CORS

# 导入应用配置类
from app.config import Config

# 导入日志工具，用于获取日志记录器
from app.utils.logger import get_logger

# 导入数据库初始化工具方法
from app.utils.db import init_db

# 导入认证相关工具
from app.utils.auth import get_current_user
from app.http.utils import request_interceptor,response_interceptor


def create_app(config_class=Config):

    # 获取名称为当前模块的日志记录器
    logger = get_logger(__name__)

    try:
        logger.info("1.开始初始化数据库.....")
        init_db()
        logger.info("2.初始化数据库成功")
    except Exception as e:
        logger.error(f"2.数据库初始化失败{e}")

    # 创建 Flask 应用对象，并指定模板和静态文件目录
    base_dir = os.path.abspath(os.path.dirname(__file__))

    # print("base_dir====", base_dir)

    # 创建Flask应用实例
    app = Flask(
        __name__,
        # 指定模板文件目录
        template_folder=os.path.join(base_dir, "templates"),
        # 指定静态文件目录
        static_folder=os.path.join(base_dir, "static"),
    )

    # 注册上下文管理器，使current_user指向当前登录的用户，并且在所有的模板里可用
    @app.context_processor
    def inject_global_data():
        return dict(current_user=get_current_user())

    # 从给定配置类加载配置信息到应用,把配置项传递flask app
    app.config.from_object(config_class)

    # 初始化Flask-CORS，允许所有来源跨域访问
    CORS(app)

    # 记录应用创建日志信息
    logger.info(
        f"3.Flask应用实例创建完成，模板目录：{app.template_folder}，静态文件目录：{app.static_folder}"
    )

    # 定义项目中所有请求的拦截器，做接口的鉴权
    @app.before_request
    def before_request_auth():
        """
        所有请求的前置鉴权处理
        """
        # 直接调用认证拦截器并返回结果
        return request_interceptor()

    # 定义一个接口响应报文的拦截器，
    @app.after_request
    def after_request(response):
        """
        所有请求的后置处理
        统一处理各种状态码的响应格式
        """

        return response_interceptor(response)

    # 导入路由并批量注册蓝图
    from app.blueprints import get_all_blueprints

    for blueprint in get_all_blueprints():
        app.register_blueprint(blueprint)

    # 返回创建的Flask应用实例
    return app
