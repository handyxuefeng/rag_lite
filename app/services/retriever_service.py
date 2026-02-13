from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
import jieba
import numpy as np

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

            # 获取在数据库中保存的向量阀值
            vector_threshold = float(self.settings.get("vector_threshold", 0.1))
            vector_threshold = max(0.1, min(vector_threshold, 1.0))

            # 筛选出vector_score大于等于阀值的文档
            filter_docs = [
                doc for doc, score in docs_with_score if score >= vector_threshold
            ]

            # 只返回top_k个文档
            filter_docs = filter_docs[:top_k]

            return filter_docs

        return None

    def _tokenize_chinese(self, text: str) -> list[str]:
        """
        中文分词（使用 jieba）
        Args:
            text: 输入文本
        Returns:
            分词后的词列表
        """
        # 使用 jieba 分词
        words = jieba.lcut(text)
        # 去除停用词和单字
        stopwords = set(
            [
                "的",
                "了",
                "在",
                "是",
                "和",
                "有",
                "与",
                "对",
                "等",
                "为",
                "也",
                "就",
                "都",
                "要",
                "可以",
                "会",
                "能",
                "而",
                "及",
                "与",
                "或",
            ]
        )
        tokens = [
            word.strip()
            for word in words
            if len(word.strip()) > 1 and word.strip() not in stopwords
        ]
        return tokens

    def keyword_search(self, collection_name, questions):
        """
        关键词检索
        """
        top_k = int(self.settings.get("top-k", 5))

        # 获取在数据库中保存的关键词阀值
        keyword_threshold = float(self.settings.get("keyword_threshold", 0.2))
        keyword_threshold = max(0.1, min(keyword_threshold, 1.0))

        # 初始化用于存储所有文档的列表
        all_docs = []

        # 从数据库中获取所有文档内容
        results = vector_db_service.get_all_content_from_collection(collection_name)

        if results:
            ids = results.get("ids", [])
            documents = results.get("documents", [])
            metadatas = results.get("metadatas", [{}])
            for _, (id, doc, metadata) in enumerate(zip(ids, documents, metadatas)):
                doc = Document(
                    page_content=doc,
                    metadata=metadata,
                    id=id,
                )
                all_docs.append(doc)

            all_docs_content = [doc.page_content for doc in all_docs]

            # 1. 对所有文档内容进行分词
            tokenized_docs = [self._tokenize_chinese(doc) for doc in all_docs_content]

            # 2. 把所有文档的分词结果传入 BM25 模型初始化
            bm25 = BM25Okapi(tokenized_docs)

            # 3. 对查询问题进行分词
            tokenized_query = self._tokenize_chinese(questions)

            # 4. 计算查询问题与所有文档的 BM25 分数
            doc_scores = bm25.get_scores(tokenized_query)

            # 计算分数最大值，用于归一化分数到[0,1]范围
            max_score = (
                float(np.max(doc_scores))
                if len(doc_scores) > 0 and np.max(doc_scores) > 0
                else 1.0
            )

            # 让每个文档的分数都除以最大值,归一化 BM25 分数到 [0, 1] 范围
            normalized_scores = [score / max_score for score in doc_scores]

            # 5.从归一化后的分数中获取top_k*3个分数高的文档的索引，便于后续的筛选
            # 注意：这里获取的是索引，不是文档本身,np.argsort返回的是索引数组
            top_incices = np.argsort(normalized_scores)[::-1][: top_k * 3]

            # 6. 筛选出 BM25 分数大于等于阀值的文档
            filter_docs = []

            #根据筛选出来的bm25分数最高分排序索引，筛选出大于等于阀值的文档
            for idx in top_incices:
                if normalized_scores[idx] >= keyword_threshold:
                    doc = all_docs[idx]
                    doc.metadata["retrieval_type"] = "keyword"
                    doc.metadata["keyword_score"] = normalized_scores[idx]
                    filter_docs.append((doc, normalized_scores[idx]))

            # 7. 对筛选出的文档根据bm25分数从高到低排序
            filter_docs.sort(key=lambda x: x[1], reverse=True)

            # 8. 只返回top_k个文档
            final_docs_result = [doc for doc,_ in filter_docs[:top_k]]
            
            logger.info(
                f"bm25关键词检索成功,返回文档数={len(final_docs_result)}"
            )

            return final_docs_result

        else:
            logger.error(f"从数据库中获取集合{collection_name}所有文档内容失败")
            return None

        


retriever_service = RetrieverService()
