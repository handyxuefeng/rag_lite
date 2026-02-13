from app.services.base_service import BaseService
from app.utils.logger import get_logger
from app.services.vector_db.vector_sevice import vector_db_service
from app.services.settings_service import settings_service

logger = get_logger(__name__)


class RetrieverService(BaseService):

    def __init__(self):
        self.settings = settings_service.get_user_settings()

    # 向量检索
    def vector_search(self, collection_name, questions):
        """
        向量检索
        """
        top_k = int(self.settings.get("top-k", 5))

        # 调用向量数据库进行相似度检索,这里先扩大top_k * 3倍进行搜索
        results = vector_db_service.similarity_search_with_score(
            collection_name=collection_name, query=questions, k=top_k * 3
        )
        if results:
            docs_with_score = []
            for doc, distance in results:
                """
                对查询出来的文档分数进行归一化处理并加入元数据
                归一化公式：vector_score = 1.0 / (1.0 + distance)
                距离越小，相似度越高，归一化后的值越接近1
                """
                vector_score = 1.0 / (1.0 + float(distance))
                doc.metadata["vector_score"] = vector_score
                doc.metadata["retrieval_type"] = "vector"
                docs_with_score.append((doc, vector_score))

            # 对文档列表按vector_score进行排序，score高的排在前面
            docs_with_score.sort(key=lambda x: x[1], reverse=True)

            #获取在数据库中保存的向量阀值
            vector_threshold = float(self.settings.get("vector_threshold", 0.1))
            vector_threshold = max(0.1, min(vector_threshold, 1.0))

            # 筛选出vector_score大于等于阀值的文档
            filter_docs = [doc for doc, score in docs_with_score if score >= vector_threshold]
            
            # 只返回top_k个文档
            filter_docs = filter_docs[:top_k]

            return filter_docs

        return None


retriever_service = RetrieverService()
