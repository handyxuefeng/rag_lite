import uuid
from app.models.knowledgebase import Knowledgebase
from app.models.document import DocumentModel
from app.services.base_service import BaseService
from app.utils.logger import get_logger
from app.utils.tool import get_file_extension

from app.utils.text_splitter import TextSplitter

# 导入线程池来优化并发问题,一般线程数的设置个数，推荐的原则是cpu的核数+4
from concurrent.futures import ThreadPoolExecutor


# 导入文件上传的存储服务storage_service
from app.services.storage.storage_service import storage_service

# 导入文件解析服务
from app.services.parse_service import parse_service

# 导入将分块的文本进行向量化的服务
from app.services.vector_db.vector_sevice import vector_db_service

from langchain_core.documents import Document


class DocumentService(BaseService[DocumentModel]):

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

        # 初始化线程池执行器
        self.thread_pool_executor = ThreadPoolExecutor(max_workers=4)

    def upload(self, kb_id, file_data, file_name):
        self.logger.info(f"document_service====={file_name}")
        # 1.先查询知识库是否存在
        with self.create_db_session() as session:
            kb_model = session.query(Knowledgebase).filter_by(id=kb_id).first()
            if not kb_model:
                raise ValueError(f"知识库{kb_id}不存在")
        # 2.获取文件扩展名
        file_ext = get_file_extension(file_name)

        if not file_ext:
            raise ValueError(f"{file_name}必须包含扩展名")

        # 文档表主键，利用uuid生成
        doc_id = uuid.uuid4().hex[:32]

        # file_path=documents/fdac351f0f6d/4ab8a7bf48c96784c008/aa.pdf
        file_path = f"documents/{kb_id}/{doc_id}/{file_name}"

        file_upload = None
        try:
            self.logger.info(f"要上传的文件路径为{file_path}")

            storage_service.upload_file(file_path, file_data)

            file_upload = True  # 文件上传成功后，设置一个标记

        except Exception as e:
            self.logger.error(f"上传文件到存储时出错,{str(e)}")
            raise ValueError(f"{file_name}上传失败,str{str(e)}")

        # 文件上传成功后，开始在document表中创建记录
        try:
            # 1.
            with self.create_db_transaction() as session:
                document_model = DocumentModel(
                    id=doc_id,
                    kb_id=kb_id,
                    name=file_name,  #  aa.pdf
                    file_path=file_path,  # /documents/fdac351f0f6d/4ab8a7bf48c96784c008/aa.pdf
                    file_type=file_ext,  # 文件扩展名pdf
                    file_size=len(file_data),
                    status="pending",
                )
                session.add(document_model)
                session.flush()
                session.refresh(document_model)
                self.logger.info(f"{file_name} 文档记录保存成功")
                return document_model.to_dict()
        except Exception as e:
            self.logger.error(f"{file_name}的记录保存失败,{str(e)}")
            # 保存记录失败后，则要删除刚刚上传成功的文件
            if file_upload and file_path:
                try:
                    storage_service.delete_file(file_path)
                except Exception as e:
                    self.logger.error(f"从{file_path}删除文件{file_name}失败")

    def get_documents_list_by_kbid(self, kb_id, page, page_size, status=None):
        with self.create_db_session() as session:
            query_document_model = session.query(DocumentModel).filter(
                DocumentModel.kb_id == kb_id
            )
            # 开始拼sql语句
            if status:
                query_document_model = query_document_model.filter(
                    DocumentModel.status == status
                )

            # 调用父类BaseService的分页查询方法
            query_data = self.pagination_query(
                query_document_model,
                page=page,
                page_size=page_size,
                order_by=DocumentModel.created_at.desc(),
            )
            self.logger.info(f"查询到的文档列表分页信息{query_data}")
            return query_data

    def process(self, doc_id, doc_name):
        with self.create_db_session() as session:
            document_model = (
                session.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
            )
            if not document_model:
                self.logger.info(f"提交{doc_name}文档处理失败")
                raise ValueError(f"{doc_name}不存在")

        """
        把self._process_document(doc_id, doc_name)
        用下面的线程池来提交
        利用线程池来优化前端并发 提交的文档处理,future类似promise
        
        """

        future = self.thread_pool_executor.submit(
            self._process_document, doc_id, doc_name
        )

        # 线程执行的回调函数
        def get_thread_executor_result_callback(future):
            try:
                res = future.result()
            except Exception as e:
                raise ValueError(f"文档处理任务异常:{doc_id},原因:{str(e)}")

        # 添加回调
        future.add_done_callback(get_thread_executor_result_callback)

    def _process_document(self, doc_id, doc_name):
        try:
            # 考虑到文件比较大，要利用多线程处理文档，
            self.logger.info(f"开始利用多线程处理{doc_name}文档")
            with self.create_db_transaction() as session:
                doc_model = (
                    session.query(DocumentModel)
                    .filter(DocumentModel.id == doc_id)
                    .first()
                )

                if not doc_model:
                    self.logger.error(f"未找到文档:{doc_id}")
                    return

                # 如果当前文档是之前处理失败或者处理成功的的，表示用户可能点击了重新处理按钮
                need_cleaned = doc_model.status in ["completed", "failed"]
                if need_cleaned:
                    doc_model.error_message = ""
                    doc_model.chunk_count = 0

                # 如果是点击了处理，则文档状态由pending 设置为 processing
                doc_model.status = "processing"
                session.flush()  # flush  把本地缓存的操作推送到数据库（但不提交事务）

                # 加载文档前，确认该该文档是属于哪个知识库,文档路径，文档类型(是pdf，word)
                kb_id = doc_model.kb_id
                file_path = doc_model.file_path
                file_type = doc_model.file_type

                kb_model = (
                    session.query(Knowledgebase)
                    .filter(Knowledgebase.id == kb_id)
                    .first()
                )
                if not kb_model:
                    raise ValueError(f"该文档{doc_name}对应知识库不存在")

                """
                因为用langchain对文档进行分割时，需要chunk_size 和 chunk_overlap,
                这两个参数都在知识库表的每个知识库行记录中
                """
                kb_chunk_size = kb_model.chunk_size
                kb_chunk_overlap = kb_model.chunk_overlap

                self.logger.info(f"{doc_name}文档的状态已经更新为processing")

                # 1.根据file_path从本地磁盘或者云盘minio,s3或者其他云盘中下载文档
                file_data = storage_service.download_file(file_path)

                # 2.根据文档的类型，按不同的方法得到的文件内容
                langchain_docs_list = parse_service.parse(file_data, file_type)

                self.logger.info(
                    f"通过langchain的DocumentLoader工具，加载{doc_name}后，加载到了{len(langchain_docs_list)}个文档"
                )

                # 3.创建文本分割器，根据chunk_size,chunk_overlap通过文本分割器对加载的文档进行分割,得到更细的文档分块
                textSpliterObj = TextSplitter(
                    chunk_size=kb_chunk_size, chunk_overlap=kb_chunk_overlap
                )
                chunks = textSpliterObj.split_document(
                    langchain_docs_list, doc_id=doc_id
                )
                if not chunks:
                    raise ValueError("分档切分为chunk失败")

                self.logger.info(f"{doc_name} 通过分割后，得到了{len(chunks)}个分块")

            # 4.对文档分块成功后，把文档记录的状态修改为completed
            with self.create_db_transaction() as session:
                doc_model = (
                    session.query(DocumentModel)
                    .filter(DocumentModel.id == doc_id)
                    .first()
                )
                if doc_model:
                    doc_model.status = "completed"
                    doc_model.chunk_count = len(chunks)

            self.logger.info(f"文档{doc_id}处理完成,分块数量为{len(chunks)}")

            if need_cleaned:
                # TODO 要清理文档表的该文档的状态为pending
                # TODO 要清理向量数据库改文档的所有的分块数据
                pass

            # 一个知识库在chromdb数据库对应一个集合
            collection_name = f"kb_{kb_id}_collection"

            # 5.开始对文档分块后的得到若干个分块信息进行向量化
            if chunks:
                langchain_documents = []
                chunk_ids = []
                for chunk in chunks:
                    """
                    #创建一个langchain的document对象,把chunk里面的字段拼接为Document需要的字段
                    chunk= {
                        "id": chunk_id,   f"{doc_id}_{idx}"
                        "chunk_index": idx,
                        "text": chunk.page_content,
                        "metadata": chunk.metadata
                    }
                    """
                    # 创建一个langchain的document对象,把chunk里面的字段拼接为Document需要的字段
                    doc_obj = Document(
                        # 分块内容
                        page_content=chunk["text"],
                        # 元数据
                        metadata={
                            "doc_id": doc_id,  # 文档id
                            "doc_name": doc_name,  # 文档名称
                            "chunk_index": chunk["chunk_index"],  # 分块的索引
                            "chunk_id": chunk["id"],  # 分块id
                            "id": chunk["id"],  # 分块id
                        },
                    )
                    langchain_documents.append(doc_obj)
                    chunk_ids.append(chunk["id"])

                # 将数据插入到用户配置好的向量数据库chroma或者milvus中
                vector_db_service.add_documents(
                    collection_name=collection_name,
                    documents=langchain_documents,
                    ids=chunk_ids,
                )

        except Exception as e:
            self.logger.info(f"处理{doc_name}时发生异常,{str(e)}")
            # 如果文档处理失败，把表中该文档的status=failed,error_message=str(e)
            with self.create_db_transaction() as session:
                doc_model = (
                    session.query(DocumentModel)
                    .filter(DocumentModel.id == doc_id)
                    .first()
                )
                if doc_model:
                    doc_model.status = "failed"
                    doc_model.error_message = str(e)[:500]
                    session.flush()
                    session.refresh(
                        doc_model
                    )  # refresh(doc_model) 表示从数据反向拉取数据，刷新doc_model
            raise ValueError(f"处理{doc_name}时发生异常,{str(e)}")

    def query_document_model_by_id(self, document_id):
        """
         根据文档id，查询文档模型
        """
        with self.create_db_session() as session:
            doc_model = (
                session.query(DocumentModel)
                .filter(DocumentModel.id == document_id)
                .first()
            )
            if not doc_model:
                return None
        return doc_model.to_dict()

    def delete_document(self,kb_id,doc_id,doc_file_path,doc_name=None):
        
        """
          删除文档的时候，要删除向量数据库中的向量数据，上传的文件，删除数据库里的文档数据
        """
        collection_name = f"kb_{kb_id}_collection"

        try:
            #1.删除向量数据库中的向量数据
            vector_db_service.delete_document_from_collection(
                collection_name=collection_name,
                filter={"doc_id": doc_id}
            )
            self.logger.info(f"已经删除文档{doc_id}的向量数据")
        except Exception as e:
            raise ValueError(f"删除文档{doc_id}在向量数据库中的数据失败,{str(e)}")
        
        # 2.删除上传的文件
        try:
            storage_service.delete_file(doc_file_path)
            self.logger.info(f"已经删除文档{doc_id}的存储文件:{doc_file_path}")
        except Exception as e:
            raise ValueError(f"删除文档{doc_id}的文件{doc_file_path}失败,{str(e)}")


        # 3.删除mysql数据库里的文档数据
        try:
            with self.create_db_transaction() as session:
                doc_model = (
                    session.query(DocumentModel)
                    .filter(DocumentModel.id == doc_id)
                    .first()
                )
                if doc_model:
                    session.delete(doc_model)
                    session.flush()
            self.logger.info(f"已经删除文档{doc_id}的数据库数据")
        except Exception as e:
            raise ValueError(f"删除文档{doc_id}的数据库数据失败,{str(e)}")
            
    def query_chunks(self, kb_id,document_id):
        """
        根据文档id，查询文档的分块数据
        filter = {"doc_id": document_id}
        chunk={
            "id": chunk_id,   f"{doc_id}_{idx}"
            "chunk_index": idx,
            "text": chunk.page_content,
            "metadata": chunk.metadata
        }
        Document(
            # 分块内容
            page_content=chunk["text"],
            # 元数据
            metadata={
                "doc_id": doc_id,  # 文档id
                "doc_name": doc_name,  # 文档名称
                "chunk_index": chunk["chunk_index"],  # 分块的索引
                "chunk_id": chunk["id"],  # 分块id
                "id": chunk["id"],  # 分块id
            },
        )
        """
        collection_name = f"kb_{kb_id}_collection"
        results = vector_db_service.query_documents(
            collection_name=collection_name,
            document_id=document_id,
            k=1000,
            filter = {"doc_id": document_id}
           
        ) 
        
        self.logger.info(f"1------查询到的文档向量结果,results={results}")

        if results:
            langchain_documents = [doc for doc,score in results]
            langchain_documents.sort(key=lambda doc: doc.metadata.get("chunk_index", 0))
        chunks_data=[]
        if langchain_documents:
            for langchain_document in langchain_documents:
               chunks_data.append({
                    "id": langchain_document.metadata["id"],  # 分块id
                    "content": langchain_document.page_content,  # 分块内容
                    "chunk_index": langchain_document.metadata["chunk_index"],  # 分块在文档中的索引
                    "metadata": langchain_document.metadata
               })
        self.logger.info(f"2------查询到的文档分块数据{chunks_data}")
        return chunks_data
        

        

document_service = DocumentService()
