from app.config import Config
from app.services.vector_db.chroma_db import ChromaVectorDB
from app.services.vector_db.milvus_db import MilvusVectorDB


class VectorDBFactory:
    _instance = None

    @classmethod
    def create_vector_db(cls):
        vector_db_type = Config.VECTOR_DB_TYPE

        if vector_db_type == "chroma":
            return ChromaVectorDB()
        elif vector_db_type == "milvus":
            return MilvusVectorDB()
        else:
            raise ValueError(f"不支持的向量数据类型{vector_db_type}")

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls.create_vector_db()

        return cls._instance


vector_db_service = VectorDBFactory.get_instance()
