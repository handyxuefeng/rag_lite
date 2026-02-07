import os
from pathlib import Path
from .base import BaseStorage

# 导入Minio类和异常
from minio import Minio

# 导入Minio异常
from minio.error import S3Error

from io import BytesIO
from app.utils.logger import get_logger
from app.config import Config


class MinioStorage(BaseStorage):

    def __init__(
        self,
        # endpoint: str,  # MinIO服务器地址
        # access_key: str,  # 访问密钥
        # secret_key: str,
        # bucket_name: str,  # 存储桶名称
        # secure: bool = False,  # 是否使用https安全连接
        # region: str = None,  # 区域名称
    ):
        """
        初始化MinIO存储服务
        @param endpoint: MinIO服务器地址 127.0.0.1:9000
        @param access_key: 访问密钥 minioadmin
        @param secret_key: 密钥 minioadmin
        @param bucket_name: 存储桶名称 rag-lite
        @param secure: 是否使用https安全连接
        @param region: 区域名称
        """

        self.logger = get_logger(self.__class__.__name__)

        self.endpoint = Config.MINIO_ENDPOINT
        self.access_key = Config.MINIO_ACCESS_KEY
        self.secret_key = Config.MINIO_SECRET_KEY
        self.bucket_name = Config.MINIO_BUCKET_NAME
        self.secure = Config.MINIO_SECURE or False
        self.region = Config.MINIO_REGION or None

        self.logger.info(f"endpoint: {self.endpoint}")

        # 创建minio的客户端
        self.client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
            region=self.region,
        )
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)
            self.logger.info(f"创建MinIO存储桶: {self.bucket_name}")
        else:
            self.logger.info(f"MinIO存储桶已存在: {self.bucket_name}")

    def _get_full_path(self, file_path: str) -> str:
        return os.path.join(self.storage_dir, file_path)

    # 本地文件存储服务实现实现父类的上传文件方法
    def upload_file(
        self, file_path: str, file_data: bytes, content_type: str = None
    ) -> str:
        try:
            self.logger.info(f"上传文件到MinIO存储: {file_path}")

            # 创建一个字节流对象

            data_stream = BytesIO(file_data)  # 创建一个字节流对象

            # 通过minio客户端上传文件
            self.client.put_object(
                self.bucket_name,
                file_path,
                data_stream,
                length=len(file_data),
                content_type=content_type,
            )
        except S3Error as e:
            self.logger.error(f"上传文件到MinIO时出错: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"上传文件到MinIO时出错: {str(e)}")
            return None

    def download_file(self, file_path: str) -> bytes:
        """
        下载文件
        @param file_path: 文件的存储路径
        @return: 返回文件的二进制数据"""
        self.logger.info(f"从MinIO下载文件: {file_path}")
        try:
            # 获取对象句柄
            response = self.client.get_object(self.bucket_name, file_path)
            # 读取数据
            file_data = response.read()
            self.logger.info(f"从minio成功下载文件: {file_path}")
            # 关闭响应
            response.close()  #
            response.release_conn()  # 释放连接
            return file_data
        except FileNotFoundError as e:
            self.logger.error(f"文件未找到: {e}")
            return None
        except Exception as e:
            self.logger.error(f"下载文件时出错: {str(e)}")
            return None

    def delete_file(self, file_url: str) -> bool:
        """
        删除文件
        @param file_url: 文件的存储URL
        @return: 返回删除是否成功
        """

        try:
            self.client.remove_object(self.bucket_name, file_url)
            self.logger.info(f"从minoo成功删除文件: {file_url}")
            return True
        except Exception as e:
            self.logger.error(f"删除文件时出错: {str(e)}")
            return False
        pass

    def file_exists(self, file_url: str) -> bool:

        pass

    def get_file_url(self, filename: str) -> str:

        pass
