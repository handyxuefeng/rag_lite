from app.config import Config
from app.services.storage.local_storage import LocalStorage

from app.utils.logger import get_logger


logger = get_logger(__name__)


class StorageFactory:
    """
    用单类模式实现存储工厂
    负责创建和管理存储相关的实例
    """

    _instance = None

    @classmethod
    def create_storage(cls, storage_type: str, **kwargs):
        """
        根据存储类型创建存储实例
        :param storage_type: 存储类型，例如 'local', 'minio' 等
        :param kwargs: 其他参数
        :return: 存储实例
        """
        if storage_type is None:
            storage_type = Config.STORAGE_TYPE.lower()

        logger.info(f"创建存储实例, storage_type={storage_type}")

        # 根据存储类型创建相应的存储实例，local 或 minio
        if storage_type == "local":
            return LocalStorage(**kwargs)
        elif storage_type == "minio":

            from app.services.storage.minio_storage import MinioStorage

            logger.info("开始创建minio实列：MinioStorage")
            return MinioStorage()

        else:
            raise ValueError(f"未知的存储类型: {storage_type}")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls.create_storage(storage_type=None)
        return cls._instance
