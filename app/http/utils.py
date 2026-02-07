from flask import jsonify, session, request, redirect, url_for
import json
import functools
from app.config import Config
from app.utils.logger import get_logger

logger = get_logger(__name__)


def success_response(data=None, message="success"):
    """
    请求成功，返回给前端的成功响应报文
    返回一个元组
    """

    return (jsonify({"code": 200, "message": message, "data": data}), 200)


def error_response(message="success", code: int = 500, data=None):
    """
    请求失败，返回给前端的失败的响应报文
    返回一个元组
    """
    return (jsonify({"code": code, "message": message, "data": data}), code)


def handler_api_error(func):
    """
    封装一个接口请求异常处理的装饰器
    用于处理接口请求过程中可能出现的异常，如数据库操作异常、参数校验异常等
    确保接口在出现异常时能够返回统一的错误响应报文，而不是抛出异常导致服务中断
    通过functools.wraps装饰器保留原函数的元数据，如函数名、文档字符串等，确保在装饰器中使用时，wrapper函数的行为与原函数一致
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            # 记录异常日志
            logger.error(f"接口 {func.__name__} 出现参数校验异常: {e}")
            # 返回统一的错误响应报文
            return error_response(message=str(e), code=400)
        except Exception as e:
            # 记录异常日志
            logger.error(f"接口 {func.__name__} 出现异常: {e}")
            # 返回统一的错误响应报文
            return error_response(message=str(e), code=500)

    return wrapper


def is_path_in_whitelist(request_path, whitelist):
    """
    检查请求路径是否在白名单中

    Args:
        request_path: 请求路径
        whitelist: 白名单路径列表

    Returns:
        bool: 是否在白名单中
    """
    # 标准化请求路径（移除尾部斜杠，确保匹配一致性）
    normalized_path = request_path.rstrip("/")

    for path in whitelist:
        # 标准化白名单路径
        normalized_whitelist_path = path.rstrip("/")

        # 支持精确匹配和前缀匹配
        if normalized_path == normalized_whitelist_path or normalized_path.startswith(
            f"{normalized_whitelist_path}/"
        ):
            return True

    return False


def request_interceptor():
    """
    定义拦截器处理逻辑,没有登录的话，携带页面url地址跳转到登录页面，登录后根据url进行回跳
    """
    logger.info(f"请求拦截: {request.method} {request.url}")

    # 根路径直接放行
    if request.path == "/":
        logger.info(f"请求放行（根路径）: {request.path}")
        return

    # 检查是否在白名单中
    if is_path_in_whitelist(request.path, Config.NO_AUTH_URLS):
        logger.info(f"请求放行（白名单）: {request.path}")
        return

    # 执行认证逻辑
    if "user_id" not in session:
        logger.info(f"用户未登录，重定向到登录页: {request.url}")
        return redirect(url_for("auth.login", next=request.url))


def response_interceptor(response):
    """
    接口响应报文的拦截器
    用于统一处理接口的响应报文，确保所有接口返回的响应报文格式一致
    """
    # 定义状态码对应的消息
    status_messages = {
        301: "资源已永久移动",
        302: "资源已临时移动",
        400: "请求参数错误",
        401: "未授权访问",
        403: "禁止访问",
        404: "资源不存在",
        405: "方法不允许",
        500: "服务器内部错误",
    }

    # 序列化原始响应并记录日志
    try:
        # 获取请求URL
        request_url = request.url

        # 获取原始响应内容
        original_response_data = {
            "request_url": request_url,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content_type": response.headers.get("Content-Type", ""),
        }

        # 仅对JSON内容进行序列化
        if response.is_json:
            original_response_data["json_data"] = response.get_json()
        else:
            # 对于非JSON内容，记录内容长度而不是实际内容
            original_response_data["content_length"] = response.headers.get(
                "Content-Length", 0
            )
    except Exception as e:
        original_response_data = f"原始响应序列化失败: {str(e)}"

    # 记录原始响应日志
    logger.info(
        f"原始响应拦截==={json.dumps(original_response_data, ensure_ascii=False)}"
    )

    # 如果响应已经是JSON格式（由success_response或error_response生成），则直接返回
    if response.is_json and response.status_code == 200:
        return response

    # 处理需要统一格式的状态码
    if response.status_code in status_messages:
        code = response.status_code
        message = status_messages[code]

        # 如果是重定向，保留Location头信息
        if code in [301, 302]:
            data = {"location": response.headers.get("Location", "")}
        else:
            data = None

        # 创建统一格式的响应
        new_response = jsonify({"code": code, "message": message, "data": data})

        # 复制原始响应的头信息
        for header_name, header_value in response.headers.items():
            if header_name not in ["Content-Type", "Content-Length"]:
                new_response.headers[header_name] = header_value

        # 设置状态码和内容类型
        new_response.status_code = code
        new_response.headers["Content-Type"] = "application/json"

        # 序列化处理后的响应并记录日志
        try:
            # 获取处理后的响应内容
            processed_response_data = {
                "request_url": request.url,
                "status_code": new_response.status_code,
                "headers": dict(new_response.headers),
                "content_type": new_response.headers.get("Content-Type", ""),
            }

            # 处理后的响应应该是JSON格式
            if new_response.is_json:
                processed_response_data["json_data"] = new_response.get_json()
        except Exception as e:
            processed_response_data = f"处理后响应序列化失败: {str(e)}"

        # 记录处理后的响应日志
        logger.info(
            f"处理后响应==={json.dumps(processed_response_data, ensure_ascii=False)}"
        )

        return new_response
    else:
        # 对于未经过特殊处理的响应，也记录日志
        try:
            # 获取未处理响应内容
            unprocessed_response_data = {
                "request_url": request.url,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_type": response.headers.get("Content-Type", ""),
            }

            # 仅对JSON内容进行序列化
            if response.is_json:
                unprocessed_response_data["json_data"] = response.get_json()
            else:
                # 对于非JSON内容，记录内容长度而不是实际内容
                unprocessed_response_data["content_length"] = response.headers.get(
                    "Content-Length", 0
                )
        except Exception as e:
            unprocessed_response_data = f"未处理响应序列化失败: {str(e)}"

        # 记录未处理响应日志
        logger.info(
            f"未处理响应==={json.dumps(unprocessed_response_data, ensure_ascii=False)}"
        )

    return response


def get_pagination_params(max_page_size=100):
    # 获取分页参数，当前查询第几页
    page = int(request.args.get("page", 1) or request.get_json().get("page", 1))
    page_size = int(
        request.args.get("page_size", 10) or request.get_json().get("page_size", 10)
    )

    page = max(1, min(page, 1000))
    page_size = max(1, min(page_size, max_page_size))

    return page, page_size


def require_json_body():
    data = request.get_json()
    if not data:
        return None, error_response("请求体不能为空", 400)
    return data, None
