"""
配置管理模块
"""

# 导入操作系统相关模块
import os

# 导入路径处理模块path
from pathlib import Path

# 导入dotenv，用来读取.env文件配置的环境变量
from dotenv import load_dotenv

load_dotenv()


class Config:
    """应用配置类"""

    # 基础配置
    # 项目根目录
    BASE_DIR = Path(__file__).parent.parent

    # 加载环境变量SECRET_KEY
    SECRET_KEY = os.getenv("SECRET_KEY") or "dev-secret-key-change-in-production"

    # 应用配置
    # 读取应用监听的主机地址，默认为本地所有地址
    APP_HOST = os.environ.get("APP_HOST", "0.0.0.0")
    # 读取应用监听的端口，默认为 5000，类型为 int
    APP_PORT = int(os.environ.get("APP_PORT", 5000))
    # 读取 debug 模式配置，字符串转小写等于 'true' 则为 True（开启调试）
    APP_DEBUG = os.environ.get("APP_DEBUG", "false").lower() == "true"

    # 读取允许上传的最大文件大小，默认为 100MB，类型为 int
    MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 104857600))  # 100MB

    # 允许上传的文件扩展名集合
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}

    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}

    MAX_IMAGE_SIZE = int(os.environ.get("MAX_IMAGE_SIZE", 5242880))  # 5MB

    # 日志配置
    # 日志目录，默认./logs
    LOG_DIR = os.getenv("LOG_DIR") or "./logs"

    # 日志文件名
    LOG_FILE = os.getenv("LOG_FILE") or "rag_lite.log"

    # 日志等级
    LOG_LEVEL = os.getenv("LOG_LEVEL") or "INFO"

    # 是否启用控制台日志
    LOG_ENABLE_CONSOLE = os.environ.get("LOG_ENABLE_CONSOLE", "true").lower() == "true"

    # 是否启用文件日志，默认 True
    LOG_ENABLE_FILE = os.environ.get("LOG_ENABLE_FILE", "true").lower() == "true"

    # 无序鉴权的接口URL配置
    # ["/login", "/register"]  # 无需鉴权的白名单路径
    NO_AUTH_URLS = ["/login", "/register", "/static"]

    # mysql数据库连接配置
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", 3306)
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "aUdio_0609")
    DB_NAME = os.environ.get("DB_NAME", "rag")
    DB_CHARSET = os.environ.get("DB_CHARSET", "utf8mb4")

    # 本地文件存储配置
    STORAGE_DIR = os.environ.get("TORAGE_DIR", "./file_storage")

    # 文件存储的地方，可以存储在本地，也可以存储在云盘上，如minio，s3等
    STORAGE_TYPE = os.environ.get("STORAGE_TYPE", "local")

    # MinIO 配置（当 STORAGE_TYPE='minio' 时使用）
    MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "")
    MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "")
    MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "")
    MINIO_BUCKET_NAME = os.environ.get("MINIO_BUCKET_NAME", "rag-lite")
    MINIO_SECURE = os.environ.get("MINIO_SECURE", "false").lower() == "true"
    MINIO_REGION = os.environ.get("MINIO_REGION", None)

    # 配置模型、提示词和检索参数
    DEEPSEEK_CHAT_MODEL = os.environ.get("DEEPSEEK_CHAT_MODEL", "deepseek-chat")
    DEEPSEEK_API_KEY = os.environ.get(
        "DEEPSEEK_API_KEY", "sk-df48a127025c47eda18521abeb515757"
    )
    DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    OPENAI_CHAT_MODEL = os.environ.get("DEEPSEEK_CHAT_MODEL", "deepseek-chat")
    OPENAI_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    OPENAI_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    OLLAMA_CHAT_MODEL = os.environ.get("DEEPSEEK_CHAT_MODEL", "deepseek-chat")
    OLLAMA_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    OLLAMA_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    # 指定向量数据库的类型
    VECTOR_DB_TYPE = os.environ.get("VECTOR_DB_TYPE", "milvus")  # chroma 或 milvus
    # 指定 chroma向量数据库的本地存储目录
    CHROMA_PERSIST_DIRECTORY = os.environ.get("CHROMA_PERSIST_DIRECTORY", "./chroma_db")

    # 配置Milvus向量数据库的连接参数
    MILVUS_HOST = os.environ.get("MILVUS_HOST", "localhost")  # 这个是本地的ip地址

    # MILVUS_HOST = os.environ.get("MILVUS_HOST", "124.220.1.72") #这个是服务器的ip地址

    MILVUS_PORT = os.environ.get("MILVUS_PORT", "19530")


# config = Config()
# print("config.LOG_DIR=", config.LOG_DIR)
