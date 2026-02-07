"""
认证相关路由（视图）
"""

# 导入 Flask 所需模块和方法
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

# 导入日志获取方法（日志系统会在首次使用时自动从 Config 获取配置并初始化）
from app.utils.logger import get_logger


# 导入用户服务
from app.services.user_service import user_service

# 获取当前模块日志记录器（会自动初始化日志系统）
logger = get_logger(__name__)

# 创建名为 'auth' 的 Blueprint 实例,url_prefix="/auth" 表示添加前缀
# bp = Blueprint("auth", __name__,url_prefix="/auth")，如果接口要加前缀的话，就用这个
bp = Blueprint("auth", __name__)


# 首页路由
@bp.route("/")
def home():
    return render_template("home.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # 因为前端提交的是一个表单，获取表单元素的值
        logger.info(f"注册提交的表单,{type(request.form)}")
        username = request.form.get("username").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        email = request.form.get("email", "")

        if password != password_confirm:
            flash("两次输入的密码不一致", "error")
            return render_template("register.html")

        try:
            # 调用service开始注册
            print("username=", username, "password=", password, "email=", email)
            user_service.register(username, password, email)
            flash("用户注册成功", "success")
            return redirect(url_for("auth.home"))
        except ValueError as e:
            logger.error(f"注册失败{str(e)}")
            flash(str(e), "error")
        except Exception as e:
            logger.error(f"注册失败{str(e)}")
            flash("注册失败，请稍后再试", "error")

    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        passowrd = request.form.get("password")
        redirect_url = (
            request.form.get("next") or request.args.get("next") or url_for("auth.home")
        )
        logger.info("登录成功后，要跳转去的地址:", redirect_url)

        try:
            user = user_service.login(username, passowrd)

            print("登录成功返回的用户信息=", user)

            # 这个session是Flask的app应用的session
            session["user_id"] = user["id"]
            session["username"] = user["username"]

            # 设置会话为31天内有效
            session.permanent = True
            flash("登录成功", "success")
            return redirect(redirect_url)
        except ValueError as e:
            logger.error(f"登录失败{e}")
            flash(f"{str(e)}", "error")
        except Exception as e:
            logger.error(f"登录失败{str(e)}")

    # 获取登录成功后要跳转的url地址
    next_url = request.args.get("next")
    return render_template("login.html", next_url=next_url)


@bp.route("/logout")
def logout():
    logger.info(f"{session['username']}:用户退出登录")
    session.clear()
    flash("已成功登出", "success")
    return redirect(url_for("auth.home"))
