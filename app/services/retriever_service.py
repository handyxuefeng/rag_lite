from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
import jieba
import numpy as np

from app.services.base_service import BaseService
from app.utils.logger import get_logger
from app.services.vector_db.vector_sevice import vector_db_service
from app.services.settings_service import settings_service

# 引入重排序
from app.utils.rerank_factory import RerankFactory


logger = get_logger(__name__)


class RetrieverService(BaseService):

    def __init__(self):
        self.settings = settings_service.get_user_settings()
        self.reranker = RerankFactory.create_reranker(self.settings)

    # 向量检索
    def vector_search(self, collection_name, questions,rerank=True):
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

            # 对文档列表进行重排序
            if self.reranker and rerank:
                filter_docs = self.apply_rerank_results(questions, filter_docs, top_k=top_k)

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

    # 关键词检索
    def keyword_search(self, collection_name, questions,rerank=True):
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

            # 根据筛选出来的bm25分数最高分排序索引，筛选出大于等于阀值的文档
            for idx in top_incices:
                if normalized_scores[idx] >= keyword_threshold:
                    doc = all_docs[idx]
                    doc.metadata["retrieval_type"] = (
                        "keyword"  # 设置检索类型为关键词检索
                    )
                    doc.metadata["keyword_score"] = normalized_scores[idx]
                    filter_docs.append((doc, normalized_scores[idx]))

            # 7. 对筛选出的文档根据bm25分数从高到低排序
            filter_docs.sort(key=lambda x: x[1], reverse=True)

            # 8. 只返回top_k个文档
            final_docs_result = [doc for doc, _ in filter_docs[:top_k]]

            # 9. 对文档列表进行重排序
            if self.reranker and rerank:
                final_docs_result = self.apply_rerank_results(questions, final_docs_result, top_k=top_k)

            logger.info(f"bm25关键词检索成功,返回文档数={len(final_docs_result)}")

            return final_docs_result

        else:
            logger.error(f"从数据库中获取集合{collection_name}所有文档内容失败")
            return None

    # 混合检索
    def hybrid_search(self, collection_name, questions, rff_k=60):
        """
        混合检索,使用rff 融合向量检索和全文检索
        """

        # 向量检索的结果
        vector_docs = self.vector_search(collection_name, questions,rerank=False)

        # 全文检索的结果
        keyword_docs = self.keyword_search(collection_name, questions,rerank=False)

        """
        创建字典用于存储文本及其排名信息
        doc_rankings = {
          "100011_1":{
            "doc": Document(
                page_content="这是一个文档",
                metadata={
                    "id": "100011_1",
                    "vector_score": 0.8,
                    "keyword_score": 0.7,
                },
            ),
            "vector_rank": 1,
            "keyword_rank": 2,
          }
        }
        """
        doc_rankings = {}

        # 遍历向量检索结果,将每个文档的id作为键,分数作为值存储到字典中
        for rank, doc in enumerate(vector_docs, start=1):
            chunk_id = doc.metadata.get("id", None)
            # 文档不存在时,初始化文档信息
            if chunk_id not in doc_rankings:
                doc_rankings[chunk_id] = {"doc": doc}
            # 记录向量检索的排名
            doc_rankings[chunk_id]["vector_rank"] = rank
            # 记录向量检索的分数
            doc_rankings[chunk_id]["vector_score"] = doc.metadata.get(
                "vector_score", 0.0
            )

        # 遍历全文检索结果,将每个文档的id作为键,分数作为值存储到字典中
        for rank, doc in enumerate(keyword_docs, start=1):
            chunk_id = doc.metadata.get("id", None)
            # 文档不存在时,初始化文档信息
            if chunk_id not in doc_rankings:
                doc_rankings[chunk_id] = {"doc": doc}
            # 记录全文检索的排名
            doc_rankings[chunk_id]["keyword_rank"] = rank
            # 记录全文检索的分数
            doc_rankings[chunk_id]["keyword_score"] = doc.metadata.get(
                "keyword_score", 0.0
            )

        # 从设置中读取向量检索的权重
        vector_weight = float(self.settings.get("vector_weight", 0.1))

        # 从设置中读取全文检索的权重
        keyword_weight = 1 - vector_weight


        # 计算每个文档的融合分数
        """
        doc_rankings = {
          "100011_1":{
            "doc": Document(
                page_content="这是一个文档",
                metadata={
                    "id": "100011_1",
                    "vector_score": 0.8,
                    "keyword_score": 0.7,
                },
            ),
            "vector_rank": 1,
            "keyword_rank": 2,

          }
        }
        """
        for chunk_id, rank_info in doc_rankings.items():
            # 获取向量排名
            vector_rank = rank_info.get("vector_rank", rff_k+1)
            # 获取全文排名
            keyword_rank = rank_info.get("keyword_rank", rff_k+1)

            # 初始化rff排名
            rff_score = 0.0

            # 计算rff排名
            rff_score += vector_weight / (rff_k + vector_rank)
            rff_score += keyword_weight / (rff_k + keyword_rank)

            # 存储rff排名
            doc_rankings[chunk_id]["rff_score"] = rff_score

        # 提取排序后的文档
        combined_results = [(chunk_id, rank_info) for chunk_id, rank_info in doc_rankings.items()]

        combined_results.sort(key=lambda x: x[1].get("rff_score", 0.0), reverse=True)

        # 提取排序后的文档
        top_k = int(self.settings.get("top_k", 5))

        # 提取前top_k个文档
        final_results = []
        for chunk_id, rank_info in combined_results[:top_k]:
            doc = rank_info["doc"]
            doc.metadata["vector_score"] = rank_info.get("vector_score", 0.0)
            doc.metadata["keyword_score"] = rank_info.get("keyword_score", 0.0)
            doc.metadata["rff_score"] = rank_info.get("rff_score", 0.0)
            doc.metadata["vector_rank"] = rank_info.get("vector_rank", 0)
            doc.metadata["keyword_rank"] = rank_info.get("keyword_rank", 0)
            doc.metadata["retrieval_type"] = "hybrid"
            final_results.append(doc)

        # 对文档列表进行重排序
        if self.reranker:
            final_results = self.apply_rerank_results(questions, final_results, top_k=top_k)

        logger.info(f"混合检索返回{len(final_results)}个文档,检索到文档为：{final_results}")

        return final_results

    #对检索后的结果重排序
    def apply_rerank_results(self, query, documents, top_k=None):
        """
        对检索后的文档列表进行重排序
        """
        if not self.reranker or not documents:
            logger.warning("未配置重排序模型，无法对文档进行重排序")
            return documents
        try:
            reranked_docs = self.reranker.rerank(query, documents, top_k=top_k)
            for doc,rerank_score in reranked_docs:
                doc.metadata["rerank_score"] = rerank_score
                logger.info(f"已经应用了重排序:{len(reranked_docs)}个文档")

            return [doc for doc,_ in reranked_docs]

        except Exception as e:
            logger.error(f"重排序文档时出错：{e}")
            return documents


retriever_service = RetrieverService()

"""
文档的检索服务，包括bm25关键词检索、向量检索、混合检索等。返回检索到的文档列表。文档中包含的分数有
1. 向量检索分数 vector_score
2. 全文检索分数 keyword_score
3. 融合检索分数 rff_score
4. 重排序分数 rerank_score
5. 检索类型 retrieval_type （向量、bm25、混合）

"""
