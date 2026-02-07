from app.config import Config
from app.utils.logger import get_logger
from app.services.settings_service import settings_service

logger = get_logger(__name__)


class LLMFactory:
    _provider = {}

    @classmethod
    def register_provider(cls, provider_name, llm_provider_factory):
        cls._provider[provider_name.lower()] = llm_provider_factory
        logger.info(f"已经创建好{provider_name}的大模型")

    @classmethod
    def create_llm(
        cls, settings=None, temperature=0.7, max_tokens=1024, streaming=True
    ):
        if settings is None:
            settings = settings_service.get_user_settings()

        provider = settings.get("llm_provider", "deepseek").lower()
        provider_factory = cls._provider[provider]

        if provider_factory:
            return provider_factory(settings, temperature, max_tokens, streaming)
        else:
            raise ValueError(f"不支持的LLM提供商{provider}")

    @classmethod
    def _create_deepseek(cls, settings, temperature, max_tokens, streaming):
        from langchain_deepseek import ChatDeepSeek

        model_name = settings.get("llm_model_name", Config.DEEPSEEK_CHAT_MODEL)
        api_key = settings.get("llm_api_key", Config.DEEPSEEK_API_KEY)
        base_url = settings.get("llm_base_url", Config.DEEPSEEK_BASE_URL)

        llm = ChatDeepSeek(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
        )

        return llm

    @classmethod
    def _create_openai(cls, settings, temperature, max_tokens, streaming):
        from langchain_openai import OpenAI

        model_name = settings.get("llm_model_name", Config.OPENAI_CHAT_MODEL)
        api_key = settings.get("llm_api_key", Config.OPENAI_API_KEY)
        base_url = settings.get("llm_base_url", Config.OPENAI_BASE_URL)

        llm = OpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
        )
        return llm

    @classmethod
    def _create_ollama(cls, settings, temperature, max_tokens, streaming):
        from langchain_community.chat_models import ChatOllama

        model_name = settings.get("llm_model_name", Config.OLLAMA_CHAT_MODEL)
        api_key = settings.get("llm_api_key", Config.OLLAMA_API_KEY)
        base_url = settings.get("llm_base_url", Config.OLLAMA_BASE_URL)

        llm = ChatOllama(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
        )
        return llm


LLMFactory.register_provider("deepseek", LLMFactory._create_deepseek)
LLMFactory.register_provider("openai", LLMFactory._create_deepseek)
LLMFactory.register_provider("ollama", LLMFactory._create_deepseek)
