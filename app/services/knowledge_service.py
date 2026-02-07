import os
from app.services.base_service import BaseService
from app.models.knowledgebase import Knowledgebase
from app.models.document import DocumentModel
from app.services.document_service import document_service

from app.utils.db import db_transaction, db_session

from app.utils.logger import get_logger

from app.services.storage.storage_service import storage_service

from app.services.vector_db.vector_sevice import vector_db_service

from app.config import Config


class KnowledgeService(BaseService[Knowledgebase]):

    def __init__(self):
        super().__init__()

        self.logger = get_logger(self.__class__.__name__)

    def create(self, **json_kwargs):
        # self.logger.info(f"control层传递过来的参数:{json_kwargs}")

        model_data = {
            "user_id": json_kwargs.get("user_id"),
            "name": json_kwargs.get("name"),
            "description": json_kwargs.get("description"),
            "chunk_size": json_kwargs.get("chunk_size"),
            "chunk_overlap": json_kwargs.get("chunk_overlap"),
        }

        # 通过控制层传递过来的json数据创建知识库模型对象
        kb_model = Knowledgebase(**model_data)

        cover_image_data = json_kwargs.get("cover_image_data", None)
        cover_image_filename = json_kwargs.get("cover_image_filename", "")

        if cover_image_data and cover_image_filename:
            # 获取不带.的文件扩展名
            file_ext_with_dot = os.path.splitext(cover_image_filename)[1][1:].lower()
            if not file_ext_with_dot:
                raise ValueError("封面图片文件名不包含扩展名")
            if file_ext_with_dot not in Config.ALLOWED_IMAGE_EXTENSIONS:
                raise ValueError(
                    f"不支持的封面图片格式,支持的格式有:{''.join(Config.ALLOWED_IMAGE_EXTENSIONS)}"
                )
            if len(cover_image_data) > Config.MAX_IMAGE_SIZE:
                raise ValueError(
                    f"封面图片大小超过限制,最大支持{Config.MAX_IMAGE_SIZE}字节"
                )

        with db_transaction() as db_session_transaction:
            # 将知识库对象模型添加到数据库会话中
            db_session_transaction.add(kb_model)

            # 刷新session，生成知识库id,这里就是执行数据库的insert语句
            db_session_transaction.flush()

            if cover_image_data and cover_image_filename:

                # 构建图片存储路径，take .jpg .png等后缀
                file_ext_with_dot = os.path.splitext(cover_image_filename)[1].lower()

                # 构建文件存储路径
                cover_image_path = f"covers/{kb_model.id}{file_ext_with_dot}"

                # 上传封面图片到存储服务
                storage_service.upload_file(
                    file_path=cover_image_path, file_data=cover_image_data
                )
                kb_model.cover_image = cover_image_path
                db_session_transaction.flush()

            # refresh表示从数据库中加载最新的状态，强制刷新kb_model对象的属性
            # 确保kb_model对象的属性与数据库中的最新状态一致，确保获取该记录的最新修改
            db_session_transaction.refresh(kb_model)

            kb_model_dict = kb_model.to_dict([])
            self.logger.info(f"创建知识库成功:id={kb_model.id}")

            return kb_model_dict

    def list(
        self,
        page=1,
        page_size=10,
        user_id=None,
        search="",
        sort_by="created_at",
        sort_order="desc",
    ):
        """
        查询知识库列表方法
        """

        self.logger.info(
            f"查询参数,page={page},page_size={page_size},user_id={user_id}"
        )
        with db_session() as db_session_transaction:
            query = db_session_transaction.query(Knowledgebase)

            # 如果是查询指定用户的记录
            if user_id:
                query = query.filter(Knowledgebase.user_id == user_id)

            # 如果有搜索关键词
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    (Knowledgebase.name.like(search_pattern))
                    | (Knowledgebase.description.like(search_pattern))
                )
            # 处理排序逻辑
            """
            sort_column = None
            if sort_by == "name":
                sort_column = Knowledgebase.name
            elif sort_by == "created_at":
                sort_column = Knowledgebase.created_at
            else:
                sort_column = Knowledgebase.updated_at
            以上代码优化为下面代码
            """

            sort_column = getattr(Knowledgebase, sort_by, None)

            if sort_order == "asc":
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())

            # 统计总记录数
            total = query.count()

            # 计算分页的偏移量
            offset = (page - 1) * page_size

            # 查询到所有模型 page=1 时 offset=0  ; page=2 时 offset=10 ；page=3 offset=20
            knowledge_model_list = query.offset(offset).limit(page_size).all()

            self.logger.info(f"查询到知识库模型列表1111===={knowledge_model_list}")

            items = []

            for kb in knowledge_model_list:
                items.append(kb.to_dict())

            self.logger.info(f"查询到的数据===={items}")

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    def query_knowlege_by_id(self, kb_id):
        """
        根据id，查找知识库
        """
        with db_session() as session:
            kb_model = (
                session.query(Knowledgebase).filter(Knowledgebase.id == kb_id).first()
            )
            if not kb_model:
                return None
        return kb_model.to_dict()

    def delete(self, kb_id, kb_model_dict, user_id):
        """
        删除知识库的方法
        """
        is_delete_knowledge = None
        is_delete_document = None

        # 1. 删除该知识库下面所有的文档
        with db_session() as session:
            doc_model_list = (
                session.query(DocumentModel).filter(DocumentModel.kb_id == kb_id).all()
            )

        """
        如果文档不为空，则调用文档删除方法,kb_id,doc_id,doc_file_path,doc_name=None
        document_service.delete_document(self,kb_id,doc_id,doc_file_path,doc_name=None):
        """
        try:
            if doc_model_list:
                for doc_model in doc_model_list:
                    doc_id = doc_model.id
                    doc_file_path = doc_model.file_path
                    doc_name = doc_model.name
                    document_service.delete_document(
                        kb_id, doc_id, doc_file_path, doc_name
                    )
                is_delete_document = True
                self.logger.info(
                    f"1.删除知识库{kb_id}下的文档，向量数据，存储的文件成功"
                )
            else:
                self.logger.info("该知识库下没有文档，不需要删除，可直接删除知识库")
                # 删除知识库的封面文件
                kb_cover_file = kb_model_dict.get("cover_image")
                storage_service.delete_file(kb_cover_file)

        except Exception as e:
            raise ValueError(
                f"删除知识库{kb_id}下的文档，向量库，文件失败，原因{str(e)}"
            )

        # 如果已经成功删除了该知识库下的文档，则开始删除知识库的记录
        if is_delete_document:
            try:
                with db_transaction() as db_session_transaction:
                    kb_model = (
                        db_session_transaction.query(Knowledgebase)
                        .filter(
                            Knowledgebase.id == kb_id, Knowledgebase.user_id == user_id
                        )
                        .first()
                    )

                    if kb_model:
                        kb_cover_file = kb_model.cover_image
                        # 执行删除模型操作，从数据库会话中删除kb_model对象，底层就是通过delete语句删除数据库中的记录
                        db_session_transaction.delete(kb_model)
                        is_delete_knowledge = True
                        storage_service.delete_file(kb_cover_file)
                    else:
                        return False

            except Exception as e:
                raise ValueError(f"删除知识库{kb_id}失败，原因{str(e)}")

        if is_delete_knowledge and is_delete_document:
            self.logger.info(f"2.删除知识库成功:id={id}")
            return True

    def delete_knowledge(self, kb_id, kb_model_dict):
        """
        删除知识库的方法, 直接先删除知识库对应集合，这样也就把该知识库下所有文档都删除了
        """
        is_delete_document = None
        # 1.直接删除集合
        collection_name = f"kb_{kb_id}_collection"
        try:
            vector_db_service.delete_collection(collection_name)
            kb_cover_file = kb_model_dict.get("cover_image")
            is_delete_knowledge = True
            storage_service.delete_file(kb_cover_file)

        except Exception as e:
            self.logger.error(f"删除知识库{kb_id}失败，原因{str(e)}")
            return False
        
        # 2.删除文档和知识库记录
        try:
            with db_transaction() as session:
                session.query(DocumentModel).filter(DocumentModel.kb_id == kb_id).delete()
                session.query(Knowledgebase).filter(Knowledgebase.id == kb_id).delete()
                session.flush()
                is_delete_document = True

        except Exception as e:
            self.logger.error(f"删除知识库下的文档记录失败:{str(e)}")

        if is_delete_knowledge and is_delete_document:
            self.logger.info(f"2.删除知识库成功:id={id}")
            return True

        return False

    def update(
        self,
        id: str,
        cover_image_data=None,
        cover_image_filename=None,
        delete_cover=False,
        **kwargs,
    ) -> dict:
        """
        根据id更新记录
        """

        # 1.先根据知识库id，查询到这个知识库模型
        with db_transaction() as db_session_transaction:
            kb_model = (
                db_session_transaction.query(Knowledgebase)
                .filter(Knowledgebase.id == id)
                .first()
            )

            if not kb_model:
                return None

            # print(" kb_model.cover_image===", kb_model.cover_image)

            old_cover_image = kb_model.cover_image if kb_model.cover_image else None

            if delete_cover:
                # 删除封面图片
                if old_cover_image:
                    storage_service.delete_file(old_cover_image)
                    self.logger.info(f"成功删除知识库老的封面图片:{old_cover_image}")
                    kb_model.cover_image = None
                    kwargs["cover_image"] = None

            elif cover_image_data and cover_image_filename:
                # 上传新的封面图片
                file_ext_with_dot = os.path.splitext(cover_image_filename)[1][
                    1:
                ].lower()
                if not file_ext_with_dot:
                    raise ValueError("封面图片文件名不包含扩展名")
                if file_ext_with_dot not in Config.ALLOWED_IMAGE_EXTENSIONS:
                    raise ValueError(
                        f"不支持的封面图片格式,支持的格式有:{''.join(Config.ALLOWED_IMAGE_EXTENSIONS)}"
                    )
                if len(cover_image_data) > Config.MAX_IMAGE_SIZE:
                    raise ValueError(
                        f"封面图片大小超过限制,最大支持{Config.MAX_IMAGE_SIZE}字节"
                    )

                # 构建图片存储路径，take .jpg .png等后缀
                file_ext_with_dot = os.path.splitext(cover_image_filename)[1].lower()

                # 构建文件存储路径,covers/fdac351f0f6d4ab8a7bf48c96784c008.png

                cover_image_path = f"covers/{kb_model.id}{file_ext_with_dot}"

                # 删除老的封面图片
                if old_cover_image:
                    storage_service.delete_file(old_cover_image)
                    # self.logger.info(f"成功删除知识库老的封面图片:{old_cover_image}")

                # 上传封面图片到存储服务
                storage_service.upload_file(
                    file_path=cover_image_path, file_data=cover_image_data
                )
                kb_model.cover_image = cover_image_path
                # self.logger.info(f"成功上传知识库新的封面图片:{cover_image_path}")

            # 更新模型对象上的属性
            for key, value in kwargs.items():
                if hasattr(kb_model, key) and value is not None:
                    setattr(kb_model, key, value)

            # flush表示通过kb_model去更新数据库
            db_session_transaction.flush()

            # 利用跟新的收据刷新kb_model
            db_session_transaction.refresh(kb_model)

            self.logger.info(f"更新知识库{id}")

            return kb_model.to_dict()

    def get_by_id(self, kb_id: str):
        with self.create_db_session() as db_session:
            try:
                return (
                    db_session.query(Knowledgebase)
                    .filter(Knowledgebase.id == kb_id)
                    .first()
                    .to_dict()
                )
            except Exception as e:
                self.logger.error("获取ID对应的对象失败:{e}")
                return None


knowledge_service = KnowledgeService()
