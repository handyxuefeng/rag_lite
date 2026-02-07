from flask import g, session, redirect, url_for, request
from functools import wraps
from app.utils.logger import get_logger
from app.services.user_service import user_service
from app.http.utils import error_response

logger = get_logger(__name__)


def get_current_user():
    # print("从全局变量中获取用户信息=", session)
    if not hasattr(g, "current_user"):
        if "user_id" in session:
            g.current_user = user_service.get_user_by_id(session["user_id"])
        else:
            g.current_user = None

    return g.current_user


def log_required(func):
    @wraps(func)
    def login_decorated_function(*args, **kwargs):
        # 用户没有登录，则重定向到登录页，携带回跳的url
        if "user_id" not in session:
            return redirect(url_for("auth.login", next=request.url))

        # 如果登录了，则直接执行被装饰的函数逻辑
        return func(*args, **kwargs)

    return login_decorated_function


def check_permission(current_user_id, user_id_in_entity, resource_name):
    if user_id_in_entity != current_user_id:
        return False, error_response(f"未授权访问该{resource_name}")
    return True, None
