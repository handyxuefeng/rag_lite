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
    session_id = request_json_params.get("session_id")

    logger.info(f"前端提交的参数={questions},stream={stream},session_id={session_id}")

    current_user = get_current_user()

    if not questions:
        return error_response("用户的提问为空", 400)


    #初始化历史消息
    history = None

    if session_id:
        #如果会话id存在，则获取用户次会话id的历史聊天信息
        chat_history_message_list = chat_service.get_history_message(session_id,user_id=current_user.get("id"))

        #将历史消息抓换为对话的格式，保留最近的10条消息
        history = [
            {"role": message.get("role"), "content": message.get("content")}
            for message in chat_history_message_list[-10:]
        ]

    # 如果没有会话ID，创建一个新会话
    else:
        chat_session_model_dict = chat_service.create_session(user_id=current_user.get("id"))
        session_id = chat_session_model_dict.get("id")
        logger.info(f"创建新会话ID={session_id}")

    # 记录用户的问题
    chat_service.add_message(session_id,role="user",content=questions)


    @stream_with_context
    def generate_message():

        # for i in range(10):
        #     chunk = {"message": f"hello_{i}"}
        #     time.sleep(1)
        #     yield f"data: {json.dumps(chunk)}\n\n"

        try:
            # 用于缓存完整的答案内容
            full_answer = ""
            results = chat_service.chat_stream(questions=questions,history=history)
            for chunk in results:
                if chunk.get("type") == "content":
                    full_answer += chunk.get("content")
                yield f"data: {json.dumps(chunk,ensure_ascii=False)}\n\n"


            #循环介绍后，告诉前端答案结束
            yield f"data: [DONE]\n\n"
            
            #大模型回答结束后，也要把大模型回答的内容记录到数据库中
            if full_answer: 
                chat_service.add_message(session_id,role="assistant",content=full_answer)
                
                

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

@bp.route("/deleteAllSessions", methods=["DELETE"])
def delete_all_sessions():
    current_user = get_current_user()
    if not current_user:
        return error_response("用户未登录", 401)
    
    try:
        deleted_count = chat_service.delete_all_sessions(user_id=current_user.get("id"))
        if not deleted_count:
            return error_response(f"删除所有会话失败,用户ID={current_user.get('id')},会话不存在", 400)
        return success_response(data={"affected_rows": deleted_count},message="所有会话删除成功")
    except Exception as e:
        logger.error(f"删除所有会话出错:{str(e)}")
        return error_response(f"删除所有会话出错:{str(e)}", 500)

@bp.route("/eidtTitle", methods=["POST"])
def eidt_session_title():
    current_user = get_current_user()
    if not current_user:
        return error_response("用户未登录", 401)
    
    request_json_params = request.get_json()
    session_id = request_json_params.get("sessionId")
    title = request_json_params.get("title")
    
    try:
        chatSession_dict = chat_service.eidt_session_title(user_id=current_user.get("id"),session_id=session_id,title=title)
        if not chatSession_dict:
            return error_response(f"编辑会话标题失败,会话ID={session_id},用户ID={current_user.get('id')},会话不存在", 400)
        return success_response(chatSession_dict)
    except Exception as e:
        logger.error(f"编辑会话标题出错:{str(e)}")
        return error_response(f"编辑会话标题出错:{str(e)}", 500)

@bp.route("/getSession/<session_id>", methods=["GET"])
def get_session(session_id):
    current_user = get_current_user()
    if not current_user:
        return error_response("用户未登录", 401)
    
    try:

        # 1.先获取会话model
        chatSession_dict = chat_service.get_session(user_id=current_user.get("id"),session_id=session_id)
        if not chatSession_dict:
            return error_response(f"获取会话失败,会话ID={session_id},用户ID={current_user.get('id')},会话不存在", 400)

        #2.根据会话ID，获取该会话的所有消息
        messages_dict = chat_service.get_messages(user_id=current_user.get("id"),session_id=session_id)
        
        return success_response({
            "session": chatSession_dict,
            "messages": messages_dict,
        })
    except Exception as e:
        logger.error(f"获取会话出错:{str(e)}")
        return error_response(f"获取会话出错:{str(e)}", 500)