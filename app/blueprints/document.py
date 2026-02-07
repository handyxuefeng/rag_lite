import os
from flask import Blueprint, request, url_for, redirect, render_template
from app.http.utils import error_response, success_response, get_pagination_params
from app.utils.logger import get_logger
from app.config import Config
from app.utils.tool import allowed_file, get_file_extension

from app.services.document_service import document_service
from app.services.knowledge_service import knowledge_service
from app.utils.auth import get_current_user 

logger = get_logger(__name__)

# 定义路由
bp = Blueprint("documents", __name__, url_prefix="/documents")


# @bp.route("/create", methods=["POST", "GET"])
@bp.route("/<string:kb_id>/upload", methods=["POST"])
def uplaod_document(kb_id):

    logger.info("开始对文件进行处理")
    # 如果form表单中没有<input type="file" class="form-control" name="file" accept=".pdf,.docx,.txt,.md" required>
    if "file" not in request.files:
        return error_response("没有上传文件file组件", 400)

    file_obj = request.form.get("file") or request.files["file"]

    file_name = file_obj.filename

    if file_name is None:
        return error_response("没有选择文件", 400)

    if not allowed_file(file_name):
        return error_response(
            f"文件类型不允许上传，只允许{Config.ALLOWED_EXTENSIONS}", 400
        )
    # 读取文件内容
    file_data = file_obj.read()
    if len(file_data) > Config.MAX_FILE_SIZE:
        return error_response(f"文件大小超出了{Config.MAX_FILE_SIZE } byts", 400)

    # 获取表单里面自定义的文档名
    custom_document_name = request.form.get("name")

    if custom_document_name:
        # 得到上传文件时，原始文件aaa.pdf的扩展名pdf
        original_ext = get_file_extension(file_name)

        # 如果源文件有扩展名 且 用户自定义的文档名没有扩展名
        if original_ext and not os.path.splitext(custom_document_name)[1]:
            file_name = f"{custom_document_name}.{original_ext}"
        else:
            file_name = custom_document_name

    # 开始上传文件
    doc_model_dict = document_service.upload(kb_id, file_data, file_name)

    return success_response(doc_model_dict)


@bp.route("/process", methods=["POST"])
def document_submit_process():
    # 获取前端提交的post请求参数
    request_params_dict = request.get_json()
    logger.info(f"前端传递过来的参数{request_params_dict}")

    if not request_params_dict:
        return error_response("参数格式错误，需传递 JSON 数据", 400)

    doc_id = request_params_dict.get("documentId")
    doc_name = request_params_dict.get("documentName")
    logger.info(f"接受到要处理的文档名称为{doc_name},文档id={doc_id}")

    try:
        document_service.process(doc_id, doc_name)

        return success_response(None, f"{doc_name}已经提交处理")
    except Exception as e:
        return error_response(f"{doc_name}已经提交处理失败,{str(e)}", 500)

    
@bp.route("/<string:document_id>/delete", methods=["POST"])
def delete_document(document_id):

    current_user = get_current_user()
    if not current_user:
        return error_response("用户未登录", 401)
    
    doc_model_dict = document_service.query_document_model_by_id(document_id)
    if not doc_model_dict:
        return error_response(f"文档id={document_id}不存在", 400)
    
    #查询知识库模型
    kb_id = doc_model_dict.get("kb_id")
    kb_model_dict = knowledge_service.query_knowlege_by_id(kb_id)
    if not kb_model_dict:
        return error_response(f"知识库id={kb_id}不存在", 400)

    if kb_model_dict.get("user_id") != current_user.get("id"):
        return error_response(f"文档id={document_id}不属于用户{current_user.get('username')}", 403)

    doc_id = document_id
    doc_name = doc_model_dict.get("name")
    doc_file_path = doc_model_dict.get("file_path")
    logger.info(f"要删除的文档名称为{doc_name},知识库id={kb_id},文档id={doc_id}")

    try:
        document_service.delete_document(kb_id, doc_id,  doc_file_path, doc_name,)

        return success_response(None, f"{doc_name}已经删除")
    except Exception as e:
        return error_response(f"{doc_name}已经删除失败,{str(e)}", 500)


@bp.route("/<string:document_id>/chunks", methods=["GET"])
def get_document_chunks(document_id):
    logger.info(f"要查询的文档id={document_id}" )

    doc_model_dict = document_service.query_document_model_by_id(document_id)
    if not doc_model_dict:
        return error_response(f"文档id={document_id}不存在", 400)

    logger.info(f"查询到的文档模型={doc_model_dict}" )

    #查询知识库模型
    kb_id = doc_model_dict.get("kb_id")
    kb_model_dict = knowledge_service.query_knowlege_by_id(kb_id)
    if not kb_model_dict:
        return error_response(f"知识库id={kb_id}不存在", 400)
    try:
        logger.info(f"查询到的知识库模型={kb_model_dict}" )
        chunks = document_service.query_chunks(kb_id,document_id)
        return  render_template("document_chunks.html",kb=kb_model_dict, chunks=chunks,document=doc_model_dict)
    except Exception as e:
        return error_response(f"查询文档id={document_id}的分块失败,{str(e)}", 500)
