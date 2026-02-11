from app.services.base_service import BaseService
from app.services.settings_service import settings_service
from app.utils.logger import get_logger
from app.utils.llm_factory import LLMFactory

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



    def ask_quetions_by_knowledgebase(self,kb_id,questions):
        # 从知识库中获取相关文档
        llm = LLMFactory.create_llm(self.settings)

        # 服务器开始向客户端发送消息
        yield {"type": "start", "content": ""}

        chain = self.rag_prompt | llm

        context = ""
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




