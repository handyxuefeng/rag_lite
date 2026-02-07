# 导入 Flask 所需模块和方法
from flask import (
    Blueprint,
    render_template,
    request,
    abort,
    url_for,
    session,
    send_file,
)
from app.utils.auth import check_permission
from app.utils.model_config import EMBEDDING_MODELS, LLM_MODELS
from app.services.settings_service import settings_service

from app.http.utils import (
    success_response,
    handler_api_error,
    get_pagination_params,
    error_response,
    require_json_body,
)

from app.utils.auth import get_current_user

# 导入日志获取方法（日志系统会在首次使用时自动从 Config 获取配置并初始化）
from app.utils.logger import get_logger


logger = get_logger(__name__)


bp = Blueprint("settings", __name__, url_prefix="/rag")


@bp.route("/settings", methods=["GET"])
def settings_view():
    """设置页面"""
    return render_template("settings.html")


@bp.route("/models", methods=["GET"])
def get_avaiable_model():
    return success_response(
        {"embedding_models": EMBEDDING_MODELS, "llm_models": LLM_MODELS}
    )


@bp.route("/userSettings", methods=["GET"])
def get_user_settings():
    user_settings = settings_service.get_user_settings()
    return success_response(user_settings)


@bp.route("/saveSettings", methods=["PUT"])
def save_settings():
    json_data, error = require_json_body()
    return settings_service.update(json_data)
