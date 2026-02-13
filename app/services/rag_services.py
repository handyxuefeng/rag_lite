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
        retriever_mode = self.settings.get("retriever_mode", "vector")

        if retriever_mode == "vector":
            # 从知识库中获取相关文档
            docs = retriever_service.vector_search(collection_name,questions)
                
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
        yield {
            "type": "done", 
            "content": "",
            "metadata": {
                "kb_id": kb_id,
                "questions": questions,
            }
        }




rag_service = RagService()




