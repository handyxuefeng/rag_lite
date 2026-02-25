from app.services.base_service import BaseService
from app.services.settings_service import settings_service
from app.utils.logger import get_logger
from app.utils.llm_factory import LLMFactory
from app.services.vector_db.vector_sevice import vector_db_service
from app.services.retriever_service import retriever_service

# 定义RAG聊天提示模板
from langchain_core.prompts import ChatPromptTemplate

logger = get_logger(__name__)

class RagService(BaseService):
    def __init__(self):
      self.settings = settings_service.get_user_settings()
      #知识库系统提示词
      self.rag_system_prompt = self.settings.get("rag_system_prompt", "")
      
      #知识库查询提示词
      self.rag_query_prompt = self.settings.get("rag_query_prompt", "")


      #构建大模型对话提示词
      self.rag_prompt = ChatPromptTemplate.from_messages([
        ("system", self.rag_system_prompt),
        ("human", self.rag_query_prompt),
      ])

    def _retrieve_knowledgebase_context(self,kb_id,questions):
        """
        从知识库中获取相关文档
        """
        # 从知识库中获取集合
        collection_name = f"kb_{kb_id}_collection"
        collection = vector_db_service.get_or_create_collection(collection_name)
        if not collection:
            logger.error(f"知识库ID={kb_id}不存在")
            return ""

        #根据用户在设置页面设置的检索模式
        retriever_mode = self.settings.get("retrieval_mode", "vector")

        if retriever_mode == "vector":
            # 从知识库中获取相关文档
            docs = retriever_service.vector_search(collection_name,questions)

        elif retriever_mode == "keyword":
            # 从知识库中获取相关文档
            docs = retriever_service.keyword_search(collection_name,questions)
        
        elif retriever_mode == "hybrid":
            # 从知识库中获取相关文档
            docs = retriever_service.hybrid_search(collection_name,questions)
                
        else:
            logger.info(f"未知的检索模式={retriever_mode}")
            #默认走向量检索
            docs = retriever_service.vector_search(collection_name,questions)

        logger.info(f"知识库查询完成,知识库ID={kb_id},问题={questions},检索模式={retriever_mode},文档数量={len(docs)}")
        
        return docs

    def ask_quetions_by_knowledgebase(self,kb_id,questions):
        # 从知识库中获取相关文档
        llm = LLMFactory.create_llm(self.settings)

        # 服务器开始向客户端发送消息
        yield {"type": "start", "content": ""}

        chain = self.rag_prompt | llm

        # 从知识库中获取相关文档
        filter_docs = self._retrieve_knowledgebase_context(kb_id,questions)

        context = "\n\n".join(
            [f"文档{idx} {doc.metadata.get("doc_name","未知文档")} : \n{doc.page_content}" for idx,doc in enumerate(filter_docs,1)]
        )

        logger.info(f"从知识库ID={kb_id}中检索到{len(filter_docs)}个相关文档，拼装成的上下文如下:\n{context}")

        # 从知识库检索到filter_docs后，拼装成文档上下文，调用大模型生成回答
        resuts  = chain.stream({"context": context, "question": questions})

        for chunk in resuts:
            content = chunk.content
            if content:
                yield {"type": "content", "content": content}
        logger.info(f"知识库查询完成,知识库ID={kb_id},问题={questions}")

        # 从filter_docs中提取引用来源
        sources = self._extract_citations(filter_docs)

        yield {
            "type": "done", 
            "content": "",
            "sources": sources,
            "metadata": {
                "kb_id": kb_id,
                "questions": questions,
                "retrieval_chunks": len(filter_docs),
            }
        }

    def _extract_citations(self,filter_docs):
        """
        从filter_docs中提取引用来源
        1. 向量检索分数 vector_score
        2. 全文检索分数 keyword_score
        3. 融合检索分数 rff_score
        4. 重排序分数 rerank_score
        5. 检索类型 retrieval_type （向量、bm25、混合）
        """
        sources = []
        for doc in filter_docs:
            metadata = doc.metadata
            vector_score = metadata.get("vector_score",0.0)
            keyword_score = metadata.get("keyword_score",0.0)
            rff_score = metadata.get("rff_score",0.0)
            rerank_score = metadata.get("rerank_score",0.0)
            retrieval_type = metadata.get("retrieval_type","unknown")
            doc_name = metadata.get("doc_name","未知文档")
            chunk_id = metadata.get("chunk_id","未知chunk_id")
            doc_id = metadata.get("doc_id","未知doc_id")
            content = doc.page_content

            sources.append({
                "doc_name": doc_name,
                "vector_score": vector_score * 100,
                "keyword_score": keyword_score * 100,
                "rff_score": rff_score * 100,
                "rerank_score": rerank_score * 100,
                "retrieval_type": retrieval_type,
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "content": content,
            })
        return sources




rag_service = RagService()




