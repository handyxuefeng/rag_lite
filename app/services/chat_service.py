from langchain_core.prompts import ChatPromptTemplate
from app.services.settings_service import settings_service
from app.services.base_service import BaseService
from app.utils.logger import get_logger
from app.utils.llm_factory import LLMFactory
from app.models.chat_session import ChatSession


logger = get_logger(__name__)


class ChatService(BaseService):

    def __init__(self):
        self.settings = settings_service.get_user_settings()

    def chat_stream(self, questions):
        # 获取
        temperature = float(self.settings.get("llm_temperature", " 0.7"))
        temperature = max(0.0, min(temperature, 2.0))

        # 获取设置的提示词
        chat_system_prompt = self.settings.get("chat_system_prompt")
        if not chat_system_prompt:
            chat_system_prompt = "你是一个专业的AI助手。请友好、准确地回答用户的问题。"

        # settings=None, temperature=0.7, max_tokens=1024, streaming=True
        llm = LLMFactory.create_llm(self.settings,temperature=temperature)
        messages = [
            # system表示是系统角色
            ("system", chat_system_prompt),
            # human表示用户角色
            ("human", questions),
        ]

        # 通过ChatPromptTemplate模板构建一个聊天提示词模板
        chatPromptTemplate = ChatPromptTemplate.from_messages(messages)

        # 构建链式调用，因为llm 和 ChatPromptTemplate 都继承了Runnable，只要是继承Runnable，那么通过 | 可以构建链式调用，都实现了invoke,stream
        chain = chatPromptTemplate | llm  

        # 服务器开始向客户端发送消息
        yield {"type": "start", "content": ""}

        full_answer = ""
        try:
            # 遍历大模型生成的每一段内容
            for chunk in chain.stream({}):
                if hasattr(chunk, "content") and chunk.content:
                    llm_content = chunk.content
                    full_answer += llm_content
                    # 生成器生成一个内容给control层（blueprint）
                    yield {"type": "content", "content": llm_content}
        except Exception as e:
            logger.error(f"流式生成时出错:{str(e)}")
            yield {"type": "error", "content": f"流式生成时出错:{str(e)}"}

        # 最后结束时，给一个done标记
        yield {"type": "done", "content": "", "metadata": {"questions": questions}}


    def create_session(self,user_id,kb_id=None,title=None):
        """
        创建一个新的会话
        """

        if not title:
            title = "新会话"

        with self.create_db_transaction() as session:
            # 创建一个新的会话
            chatSession = ChatSession(
                user_id=user_id,
                kb_id=kb_id,
                title=title,
            )
            session.add(chatSession)
            session.flush()
            session.refresh(chatSession)
            logger.info(f"创建会话成功,会话ID={chatSession.id},用户ID={user_id},知识库ID={kb_id},会话标题={title}")
            return chatSession.to_dict()


    def init_session_list(self,user_id,kb_id=None,page=1,page_size=10):
        """
        初始化会话列表
        """
        with self.create_db_session() as session:
            # 查询用户的所有会话
            query = session.query(ChatSession).filter(ChatSession.user_id == user_id)
            if kb_id:
                query = query.filter(ChatSession.kb_id == kb_id)

            chatSessions_dict = self.pagination_query(query, page, page_size, order_by=ChatSession.updated_at.desc())
            # 分页查询
            
            return chatSessions_dict

    def delete_session(self,user_id,session_id):
        """
        删除一个会话
        """
        with self.create_db_transaction() as session:
            # 查询用户的所有会话
            query = session.query(ChatSession).filter(ChatSession.user_id == user_id, ChatSession.id == session_id)
            chatSession = query.first()
            if not chatSession:
                logger.error(f"删除会话失败,会话ID={session_id},用户ID={user_id},会话不存在")
                return None
            session.delete(chatSession)
            session.flush()
            logger.info(f"删除会话成功,会话ID={session_id},用户ID={user_id}")
            return chatSession.to_dict()



chat_service = ChatService()
