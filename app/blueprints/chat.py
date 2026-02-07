"""
和大模型进行聊天的路由
"""

import json
import time

# 导入 Flask 所需模块和方法
from flask import Blueprint, render_template, request, Response, stream_with_context

# 导入日志获取方法（日志系统会在首次使用时自动从 Config 获取配置并初始化）
from app.utils.logger import get_logger

from app.http.utils import error_response, success_response
from app.services.chat_service import chat_service

from app.utils.auth import get_current_user 

from app.http.utils import get_pagination_params 




# 导入用户服务
from app.services.user_service import user_service

# 获取当前模块日志记录器（会自动初始化日志系统）
logger = get_logger(__name__)

# 创建名为 'auth' 的 Blueprint 实例,url_prefix="/auth" 表示添加前缀
# bp = Blueprint("auth", __name__,url_prefix="/auth")，如果接口要加前缀的话，就用这个
bp = Blueprint("chat", __name__, url_prefix="/chat")


@bp.route("")
def llm_chat():
    return render_template("chat.html")


@bp.route("/llm", methods=["POST"])
def chat_with_llm():
    request_json_params = request.get_json()
    questions = request_json_params.get("questions")
    stream = request_json_params.get("stream")

    logger.info(f"前端提交的参数={questions},stream={stream}")

    if not questions:
        return error_response("用户的提问为空", 400)

    @stream_with_context
    def generate_message():

        # for i in range(10):
        #     chunk = {"message": f"hello_{i}"}
        #     time.sleep(1)
        #     yield f"data: {json.dumps(chunk)}\n\n"

        try:
            # 用于缓存完整的答案内容
            full_answer = ""
            results = chat_service.chat_stream(questions=questions)
            for chunk in results:
                if chunk.get("type") == "content":
                    full_answer += chunk.get("content")
                yield f"data: {json.dumps(chunk,ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"流式输出出错:{str(e)}")
            error_chunk = {"type": "error", "content": str(e)}
            yield f"data: {json.dumps(error_chunk,ensure_ascii=False)}\n\n"

    response = Response(
        generate_message(),  # 生成器
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-buffering": "no",
            "Content-Type": "text/event-stream;charset=utf-8",
        },
    )

    return response


@bp.route("/createSession", methods=["POST"])
def create_session():

    current_user = get_current_user()
    if not current_user:
        return error_response("用户未登录", 401)

    data = request.get_json()
    #获取会话标题
    title = data.get("title","")
    
    try:
        session_id = chat_service.create_session(user_id=current_user.get("id"),title=title)
        return success_response(session_id)
    except Exception as e:
        logger.error(f"创建会话出错:{str(e)}")
        return error_response(f"创建会话出错:{str(e)}", 500)


@bp.route("/initSessionList", methods=["POST"])
def init_session_list():
    current_user = get_current_user()
    if not current_user:
        return error_response("用户未登录", 401)
    
    #从请求体中获取kb_id
    request_json_params = request.get_json()
    kb_id = request_json_params.get("kb_id")

    #获取分页参数
    page, page_size = get_pagination_params(max_page_size=1000)

    try:
        sessions_dict = chat_service.init_session_list(user_id=current_user.get("id"),kb_id=kb_id,page=page,page_size=page_size)
        return success_response(sessions_dict)
    except Exception as e:
        logger.error(f"初始化会话列表出错:{str(e)}")
        return error_response(f"初始化会话列表出错:{str(e)}", 500)

@bp.route("/deleteSession/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    current_user = get_current_user()
    if not current_user:
        return error_response("用户未登录", 401)
    
    try:
        chatSession_dict = chat_service.delete_session(user_id=current_user.get("id"),session_id=session_id)
        if not chatSession_dict:
            return error_response(f"删除会话失败,会话ID={session_id},用户ID={current_user.get('id')},会话不存在", 400)
        return success_response(chatSession_dict)
    except Exception as e:
        logger.error(f"删除会话出错:{str(e)}")
        return error_response(f"删除会话出错:{str(e)}", 500)