from io import BytesIO

# 导入 Flask 所需模块和方法
from flask import (
    Blueprint,
    render_template,
    request,
    abort,
    url_for,
    session,
    send_file,
    redirect,
)
from app.utils.auth import check_permission
from app.services.storage.storage_service import storage_service
from app.models.knowledgebase import Knowledgebase
from app.services.document_service import document_service


from app.http.utils import (
    success_response,
    handler_api_error,
    get_pagination_params,
    error_response,
)

from app.utils.auth import get_current_user

# 导入日志获取方法（日志系统会在首次使用时自动从 Config 获取配置并初始化）
from app.utils.logger import get_logger

# 导入知识库的Service层
from app.services.knowledge_service import knowledge_service

logger = get_logger(__name__)

# 定义知识库的路由名称为knowledge，前缀为knowledge
# 这样访问知识库的所有接口都是以/knowledge/开都
bp = Blueprint("knowledge", __name__, url_prefix="/knowledge")


@bp.route("/create", methods=["POST", "GET"])
@handler_api_error
def create_knowledge():
    """
    创建知识库的方法
    前端访问接口：http://127.0.0.1:5000/knowledge/create
    通过requst.get_json方法获取前端传递过来的json数据
    """
    current_user = get_current_user()

    # 表单提交
    if request.content_type and "multipart/form-data;" in request.content_type:
        # logger.info(f"表单数据={request.form}")
        name = request.form.get("name")
        description = request.form.get("description")
        chunk_size = request.form.get("chunk_size")
        chunk_overlap = request.form.get("chunk_overlap")
        cover_image = request.files.get("cover_image", None)
        cover_iamge_filename = None
        cover_image_data = None
        cover_imagae_filename = None

        # 判断请求过来的文件中是否包含cover_image字段
        if "cover_image" in request.files:
            cover_file = cover_image
            if cover_file and cover_file.filename:
                # 读取文件的内容为二进制数据
                cover_image_data = cover_file.read()
                # 获取上传的文件名
                cover_imagae_filename = cover_file.filename

                logger.info(
                    f"上传的封面图片文件名={cover_imagae_filename}, 大小={len(cover_image_data)}字节,内容类型={cover_file.content_type}   "
                )

            logger.info(f"上传的封面图片文件名={cover_iamge_filename}")

    user_id = current_user.get("id")

    kb_dict = knowledge_service.create(
        user_id=user_id,
        name=name,
        description=description,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        cover_image_data=cover_image_data,
        cover_image_filename=cover_imagae_filename,
    )

    # 把响应报文返回给客户端
    return success_response(kb_dict)


@bp.route("/update/<string:kb_id>", methods=["PUT"])
@handler_api_error
def update_knowledge(kb_id):
    """
    创建知识库的方法
    前端访问接口：http://127.0.0.1:5000/knowledge/create
    通过requst.get_json方法获取前端传递过来的json数据
    """

    current_user = get_current_user()

    kb_model_dict = knowledge_service.query_knowlege_by_id(kb_id)

    logger.info(f"kb_model_dict={kb_model_dict}")

    # 1.先判断知识库是否存在
    if not kb_model_dict:
        return error_response("知识库未找到", 404)

    logger.info(f"找到了该知识库{kb_model_dict['name']}")

    # 2.判断当前登录的用户是否有权限删除该知识库，每个人只能删除自己创建的知识库
    has_permission, err = check_permission(
        current_user["id"], kb_model_dict["user_id"], "knowledge"
    )

    if not has_permission:
        return err

    # 表单提交
    if request.content_type and "multipart/form-data;" in request.content_type:
        logger.info(f"表单数据={request.form}")

        name = request.form.get("name")
        description = request.form.get("description")
        chunk_size = request.form.get("chunk_size")
        chunk_overlap = request.form.get("chunk_overlap")
        cover_image_data = None
        cover_image_filename = None
        delete_cover = request.form.get("delete_cover") == "true"

        print("delete_cover====", delete_cover)

        # 判断请求过来的文件中是否包含cover_image字段
        if "cover_image" in request.files:
            cover_file = request.files["cover_image"]

            if cover_file and cover_file.filename:
                # 读取文件的内容为二进制数据
                cover_image_data = cover_file.read()
                # 获取上传的文件名
                cover_image_filename = cover_file.filename

                logger.info(
                    f"上传的封面图片文件名={cover_image_filename}, 大小={len(cover_image_data)}字节,内容类型={cover_file.content_type}   "
                )

            logger.info(f"上传的封面图片文件名={cover_image_filename}")

    update_data = {}
    if name:
        update_data["name"] = name
    if description:
        update_data["description"] = description
    if chunk_size:
        update_data["chunk_size"] = chunk_size
    if chunk_overlap:
        update_data["chunk_overlap"] = chunk_overlap

    kb_dict = knowledge_service.update(
        id=kb_id,
        cover_image_data=cover_image_data,
        cover_image_filename=cover_image_filename,
        delete_cover=delete_cover,
        **update_data,
    )

    # 把响应报文返回给客户端
    return success_response(kb_dict)


@bp.route("/list", methods=["POST", "GET"])
def knowledge_list():
    """
    查询知识库列表方法
    """

    # 获取当前登录的用户
    current_user = get_current_user()

    logger.info("开始查询")

    # 获取分页参数
    page, page_size = get_pagination_params(max_page_size=100)

    # 获取url上面的参数
    # http://localhost:5000/knowledge/list?search=qqweqeq&sort_by=created_at&sort_order=desc&page=1&page_size=10
    search = request.args.get("search", "").strip()
    sort_by = request.args.get("sort_by", "created_at").strip()
    sort_order = request.args.get("sort_order", "desc").strip()

    result = knowledge_service.list(
        user_id=current_user["id"],
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    """
    result ={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    """

    return render_template(
        "knowledge.html",
        knowledge_list=result["items"],
        pagination=result,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@bp.route("/delete/<string:id>", methods=["DELETE"])
@handler_api_error
def delete_knowledge(id):
    """
    删除知识库的方法
    前端访问接口：http://127.0.0.1:5000/knowledge/delete/1
    """
    current_user = get_current_user()

    kb_model_dict = knowledge_service.query_knowlege_by_id(id)

    # 1.先判断知识库是否存在
    if not kb_model_dict:
        return error_response("知识库未找到", 404)

    logger.info(f"找到了该知识库{kb_model_dict['name']}")

    # 2.判断当前登录的用户是否有权限删除该知识库，每个人只能删除自己创建的知识库
    has_permission, err = check_permission(
        current_user["id"], kb_model_dict["user_id"], "knowledge"
    )

    if not has_permission:
        return err

    success = knowledge_service.delete(id, kb_model_dict, current_user["id"])

    # success = knowledge_service.delete_knowledge(
    #     id,
    #     kb_model_dict,
    # )

    if not success:
        return error_response("知识库删除失败", 500)

    return success_response(message="删除成功")


@bp.route("/kb/<string:kb_id>/cover")
# /knowledge/kb/fdac351f0f6d4ab8a7bf48c96784c008/cover
def get_knowledge_cover_image(kb_id):
    """
    获取知识库封面图片的方法
    前端访问接口：http://
    """
    logger.info(f"获取知识库封面图片，kb_id={kb_id}")
    current_user = get_current_user()

    # 使用正确的参数kb_id而不是id
    kb_model_dict = knowledge_service.query_knowlege_by_id(kb_id)
    logger.info(f"查询知识库结果：{kb_model_dict}")

    # 1.先判断知识库是否存在
    if not kb_model_dict:
        logger.info(f"知识库不存在，kb_id={kb_id}")
        return error_response("知识库未找到", 404)

    logger.info(f"找到了该知识库：id={kb_id}, name={kb_model_dict['name']}")

    # 2.判断当前登录的用户是否有权限获取该知识库封面
    has_permission, err = check_permission(
        current_user["id"], kb_model_dict["user_id"], "knowledge"
    )

    if not has_permission:
        logger.info(
            f"用户无权限获取知识库封面，kb_id={kb_id}, user_id={current_user['id']}"
        )
        return err

    cover_image = kb_model_dict.get("cover_image")
    # logger.info(f"知识库封面图片路径：{cover_image}")
    if not cover_image:
        # logger.info(f"知识库id={kb_id}没有封面图片")
        # 返回默认图片或者404
        return error_response("封面图片不存在", 404)

    # 如果有图片，则开始下载图片
    try:
        logger.info(f"开始下载图片，路径：{cover_image}")
        image_data = storage_service.download_file(cover_image)
        logger.info(f"下载图片结果：{image_data is not None}")
        if not image_data:
            # logger.info(f"知识库id={kb_id}封面图片不存在于存储服务中")
            return error_response("封面图片不存在于存储服务", 404)

        file_name = storage_service.get_file_name(cover_image)
        content_type = storage_service.get_file_mime_type(file_name)
        # logger.info(f"知识库id={kb_id}封面图片的content_type={content_type}")

        # 通过send_file响应图片数据和MIME类型，不以附件形式发送
        return send_file(
            BytesIO(image_data),  # 图片数据
            mimetype=content_type,  # MIME类型
            as_attachment=False,  # 不以附件形式发送
        )

    except FileNotFoundError as e:
        # logger.error(f"下载知识库封面图片失败,错误信息:{str(e)}")
        return error_response(f"封面图片不存在{str(e)}", 404)
    except Exception as e:
        # logger.error(f"下载知识库封面图片失败,错误信息:{str(e)}")
        return error_response(f"获取封面图片失败{str(e)}", 500)


@bp.route("/detail/<string:kb_id>", methods=["GET"])
def knowledge_detail(kb_id):
    # 根据知识库id查询到知识库模型
    kb = knowledge_service.get_by_id(kb_id)
    if not kb:
        return redirect(url_for("knowledge.knowledge_list"))
    page, page_size = get_pagination_params(max_page_size=100)

    # 根据知识库id去查询这个知识库有多少个文档
    result = document_service.get_documents_list_by_kbid(
        kb_id, page=page, page_size=page_size
    )

    # 根据知识库kb_id查询到所有的文档列表，传递给kb_detail.html

    return render_template(
        "kb_detail.html",
        kb=kb,
        documents=result["items"],
        pagination=result["pagination"],
    )
