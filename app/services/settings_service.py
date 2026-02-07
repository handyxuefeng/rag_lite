import os
from app.services.base_service import BaseService
from app.models.settings import Settings

# 导入配置类

from app.config import Config

from app.utils.logger import get_logger


class SettingsService(BaseService[Settings]):
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

        root_dir = os.getcwd()

        # 部署在本地的嵌入模型所在目录
        local_model_path = os.path.join(root_dir, "embeddingModels", "all-MiniLM-L6-v2")

        self.logger.info(f"在设置中配置本地模型路径={local_model_path}")
        self.local_embedding_path = str(local_model_path)

    def get_user_settings(self):
        with self.create_db_session() as session:
            settings_model = session.query(Settings).filter_by(id="global").first()
            # self.logger.info(f" Config.settings_model={ settings_model.to_dict()}")
            if settings_model:
                return settings_model.to_dict()
            else:
                self.logger.info("返回默认的设置信息")
                return self._get_default_settings()

    def _get_default_settings(self):
        """获取默认设置"""
        self.logger.info(f" Config.DEEPSEEK_CHAT_MODEL={ Config.DEEPSEEK_CHAT_MODEL}")
        self.logger.info(f" Config.DEEPSEEK_API_KEY={ Config.DEEPSEEK_API_KEY}")
        self.logger.info(f" Config.DEEPSEEK_BASE_URL={ Config.DEEPSEEK_BASE_URL}")

        return {
            "id": "global",  # 设置主键
            "embedding_provider": "huggingface",  # 默认 embedding provider
            # "embedding_model_name": "sentence-transformers/all-MiniLM-L6-v2",  # 默认 embedding 模型
            "embedding_model_name": self.local_embedding_path,  # 先使用本地部署的模型，线上太卡
            "embedding_api_key": "embedding_api_key",  # 默认无 embedding API key
            "embedding_base_url": "embedding_base_url",  # 默认无 embedding base url
            "llm_provider": "deepseek",  # 默认 LLM provider
            "llm_model_name": Config.DEEPSEEK_CHAT_MODEL,  # 默认 LLM 模型
            "llm_api_key": Config.DEEPSEEK_API_KEY,  # 配置里的默认 LLM API key
            "llm_base_url": Config.DEEPSEEK_BASE_URL,  # 配置里的默认 LLM base url
            "llm_temperature": 0.8,  # 默认温度
            "chat_system_prompt": "你是一个专业的AI助手。请友好、准确地回答用户的问题。",  # 聊天系统默认提示词
            "rag_system_prompt": "你是一个专业的AI助手。请基于文档内容回答问题。",  # RAG系统提示词
            "rag_query_prompt": "文档内容：\n{context}\n\n问题：{question}\n\n请基于文档内容回答问题。如果文档中没有相关信息，请明确说明。",  # RAG查询提示词
            "retrieval_mode": "vector",  # 默认检索模式
            "vector_threshold": 0.2,  # 向量检索阈值
            "keyword_threshold": 0.2,  # 关键词检索阈值
            "vector_weight": 0.75,  # 检索混合权重
            "top_k": 15,  # 返回结果数量
            "created_at": None,  # 创建时间
            "updated_at": None,  # 更新时间
        }

    def update(self, json_data):
        self.logger.info(f"保存设置传递过来的值{json_data}")

        with self.create_db_transaction() as session:
            setting_model = session.query(Settings).filter_by(id="global").first()
            if not setting_model:
                setting_model = Settings(id="global")
                session.add(setting_model)
            for key, value in json_data.items():
                setattr(setting_model, key, value)
            session.flush()
            session.refresh(setting_model)
            return setting_model.to_dict()


settings_service = SettingsService()
