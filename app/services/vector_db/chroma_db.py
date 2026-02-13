from langchain_chroma import Chroma
from app.services.vector_db.vector_base import VectorBaseService
from app.config import Config
from app.utils.logger import get_logger
from app.utils.embedding_factory import EmbeddingFactory
import chromadb


logger = get_logger(__name__)


class ChromaVectorDB(VectorBaseService):

    def __init__(self):
        """
        初始化chromadb的相关参数
        # 创建数据库
        persistentClient = PersistentClient(path=Path(__file__).parent / "custom_store")
        """
        self.persistent_dirtory = Config.CHROMA_PERSIST_DIRECTORY
        self.embeddings = EmbeddingFactory.create_embeddings()

        logger.info("chroma_db已经初始化数据保存目录={self.persistent_dirtory}")

    def get_or_create_collection(self, collection_name):

        logger.info(f"初始化chroma向量数据库，需要embeddings={self.embeddings}")

        vector_store_db = Chroma(
            collection_name=collection_name,  # 集合的名称
            embedding_function=self.embeddings,  # 嵌入向量
            persist_directory=self.persistent_dirtory,  # 数据保存目录
            collection_metadata={"hnsw:space": "cosine"}, # 向量距离计算方式
        )

        return vector_store_db

    def add_documents(self, collection_name, documents, ids):
        vector_store_db = self.get_or_create_collection(collection_name)

        if ids:
            results = vector_store_db.add_documents(documents=documents, ids=ids)
        else:
            results = vector_store_db.add_documents(documents=documents)

        logger.info(f"向chromadb中添加了{len(documents)}条记录")

        return results

    def query_documents(self, collection_name, document_id, k=10, filter=None):
        """
        查询文档向量
        """
        vector_store_db = self.get_or_create_collection(collection_name)
        results = vector_store_db.similarity_search_with_score(
            query=document_id, filter=filter, k=k
        )
        if results:
            return results
        return None

    def delete_document_from_collection(self, collection_name, ids=None, filter=None):
        """
        删除文档的时候，要删除向量数据库中的向量数据，上传的文件，删除数据库里的文档数据
        """
        vector_store_db = self.get_or_create_collection(collection_name)
        # 直接使用ChromaDB客户端访问集合
        client = chromadb.PersistentClient(path=self.persistent_dirtory)

        # 通过客户端获得集合名称
        collection = client.get_collection(name=collection_name)
        try:
            results = collection.get(where=filter)
            if results and "ids" in results and len(results["ids"]) > 0:
                ids = results["ids"]
                vector_store_db.delete(ids=ids)
                logger.info(f"根据filter={filter}查询到的文档数据={ids}，已经删除")
            else:
                logger.info(f"根据filter={filter}查询到的文档数据为空，无法删除")
        except Exception as e:
            raise ValueError(f"从chromadb中获取集合{collection_name}失败，错误信息={e}")

    def delete_collection(self, collection_name):
        """
        删除整个集合
        """
        try:
            client = chromadb.PersistentClient(path=self.persistent_dirtory)
            client.delete_collection(name=collection_name)
            logger.info(f"成功删除集合: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"删除集合{collection_name}失败，错误信息={e}")
            return False


    def similarity_search_with_score(self, collection_name, query, k=10, filter=None):
        """
        相似度检索
        """
        vector_store_db = self.get_or_create_collection(collection_name)
        results = vector_store_db.similarity_search_with_score(
            query=query, filter=filter, k=k
        )
        if results:
            return results
        return None
