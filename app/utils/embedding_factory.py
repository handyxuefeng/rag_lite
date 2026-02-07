from app.services.settings_service import settings_service
from app.utils.logger import get_logger

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import OllamaEmbeddings


logger = get_logger(__name__)


class EmbeddingFactory:

    @staticmethod
    def create_embeddings():
        embeddings = None
        settings = settings_service._get_default_settings()
        embedding_provider = settings.get("embedding_provider")
        embedding_model_name = settings.get("embedding_model_name")
        embedding_api_key = settings.get("embedding_api_key")
        embedding_base_url = settings.get("embedding_base_url")

        logger.info(
            f"开始创建嵌入向量embeddings,embedding_provider={embedding_provider},embedding_model_name={embedding_model_name},"
        )

        if embedding_provider == "huggingface":
            embeddings = HuggingFaceEmbeddings(
                model_name=embedding_model_name,
                model_kwargs={"device": "cpu"},
                # normalize_embeddings指的就是将向量归一化，长度为1，方向不变
                encode_kwargs={"normalize_embeddings": True},
            )
        elif embedding_provider == "openai":
            # 不需要baseUrl,但需要apikey
            embeddings = OpenAIEmbeddings(
                model_name=embedding_model_name, openai_api_key=embedding_api_key
            )
            logger.info("创建HuggingFaceEmbeddings的嵌入向量成功")

        elif embedding_provider == "ollma":
            embeddings = OllamaEmbeddings(
                model_name=embedding_model_name, base_url=embedding_base_url
            )
            logger.info("创建OpenAIEmbeddings的嵌入向量成功")
        else:
            # 没有，默认走本地模型
            embeddings = HuggingFaceEmbeddings(
                model_name=embedding_model_name,
                model_kwargs={"device": "cpu"},
                # normalize_embeddings指的就是将向量归一化，长度为1，方向不变
                encode_kwargs={"normalize_embeddings": True},
            )
            logger.info("创建OllamaEmbeddings的嵌入向量成功")

        if not embeddings:
            raise ValueError("未知的嵌入向量提供商,创建嵌入向量失败")

        return embeddings
