from langchain_milvus import Milvus
from app.services.vector_db.vector_base import VectorBaseService
from app.config import Config
from app.utils.logger import get_logger
from app.utils.embedding_factory import EmbeddingFactory


logger = get_logger(__name__)


class MilvusVectorDB(VectorBaseService):

    def __init__(self):
        """
        对Milvus向量数据库进行初始化
        """

        # 处理Milvus连接参数, 如果是localhost或127.0.0.1, 则使用host和port, 否则使用uri
        if Config.MILVUS_HOST in ["localhost", "127.0.0.1"]:
            self.connection_args = {
                "host": Config.MILVUS_HOST,
                "port": Config.MILVUS_PORT,
            }
        else:
            # 如果milvus是部署在云服务器上，而应用是运行在本地，需要使用uri连接
            self.connection_args = {
                "uri": f"http://{Config.MILVUS_HOST}:{Config.MILVUS_PORT}"
            }
        self.embeddings = EmbeddingFactory.create_embeddings()
        logger.info(f"Milvus已经初始化，连接参数{self.connection_args}")

    def get_or_create_collection(self, collection_name):
        vector_store_db = Milvus(
            collection_name=collection_name,  # 集合的名称
            embedding_function=self.embeddings,  # 嵌入向量
            connection_args=self.connection_args,  # 连接参数
        )
        if hasattr(vector_store_db, "_collection"):
            try:
                vector_store_db._collection.load()
                logger.info(f"已经加载集合{collection_name}")
            except Exception as e:
                logger.info(f"集合可能不存在：{e}")
        return vector_store_db

    def add_documents(self, collection_name, documents, ids=None):
        logger.info(f"开始向Milvus中的{collection_name}添加{len(documents)}条记录")
        vector_store_db = self.get_or_create_collection(collection_name)

        if ids:
            results = vector_store_db.add_documents(documents=documents, ids=ids)
        else:
            results = vector_store_db.add_documents(documents=documents)

        if hasattr(vector_store_db, "_collection"):
            # 刷新内存中的数据到Milvus数据库
            vector_store_db._collection.flush()

        logger.info(f"向Milvus中添加了{len(documents)}条记录")

        return results

    def delete_document_from_collection(self, collection_name, ids=None, filter=None):
        vector_store_db = self.get_or_create_collection(collection_name)
        if ids:
            vector_store_db.delete(ids=ids)
        elif filter:
            expr = f"doc_id == '{filter["doc_id"]}'"
            vector_store_db.delete(expr=expr)
        else:
            raise ValueError("ids 和 filter 都没有传，无法删除")

        if hasattr(vector_store_db, "_collection"):
            # 刷新内存中的数据到Milvus数据库
            vector_store_db._collection.flush()

        logger.info(f"已经从Milvus中的{collection_name}删除了{ids}")

    def query_documents(self, collection_name, document_id, k=10, filter=None):
        """
        查询文档向量
        """
        vector_store_db = self.get_or_create_collection(collection_name)

        # Milvus默认是懒加载，需要手动加载集合
        if hasattr(vector_store_db, "_collection"):
            try:
                vector_store_db._collection.load()
                logger.info(f"已经加载集合{collection_name}")
            except Exception as e:
                raise Exception(f"集合可能不存在：{e}")

        if filter:
            expr = f"doc_id == '{filter["doc_id"]}'"

        results = vector_store_db.similarity_search_with_score(
            query=document_id, expr=expr, k=k
        )
        if results:
            return results
        return None

    def delete_collection(self, collection_name):
        """
        删除整个集合
        """
        try:
            vector_store_db = self.get_or_create_collection(collection_name)
            if hasattr(vector_store_db, "_collection"):
                vector_store_db._collection.drop()
                logger.info(f"成功删除Milvus集合: {collection_name}")
                return True
            else:
                logger.warning(f"集合{collection_name}不存在")
                return False
        except Exception as e:
            logger.error(f"删除Milvus集合{collection_name}失败，错误信息={e}")
            return False

    def similarity_search_with_score(self, collection_name, query, k=10, filter=None):
        """
        向量检索
        """
        vector_store_db = self.get_or_create_collection(collection_name)

        # Milvus默认是懒加载，需要手动加载集合
        if hasattr(vector_store_db, "_collection"):
            try:
                vector_store_db._collection.load()
                logger.info(f"已经加载集合{collection_name}")
            except Exception as e:
                raise Exception(f"集合可能不存在：{e}")

        if filter:
            expr = f"doc_id == '{filter["doc_id"]}'"

        results = vector_store_db.similarity_search_with_score(
            query=query, expr=expr, k=k
        )
        if results:
            return results
        return None
