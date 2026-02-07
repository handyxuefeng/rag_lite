from flask import request
from app.http.utils import error_response


# 定义函数：检查请求体是否为 JSON
def require_json_body():
    """
    检查请求是否有 JSON 体

    Returns:
        如果存在返回 (data, None)，如果不存在返回 (None, error_response)
    """
    # 从请求中获取 JSON 数据
    data = request.get_json()
    # 如果没有获取到数据，则返回错误响应
    if not data:
        return None, error_response("请参数不能为空", 400)
    # 如果获取到了数据，则返回数据和None表示没有错误
    return data, None
