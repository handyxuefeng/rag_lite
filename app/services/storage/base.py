from abc import ABC, abstractmethod

from typing import Optional


class BaseStorage(ABC):
    @abstractmethod
    def upload_file(self, filename: str, file_data: bytes, content_type: str) -> str:
        """
        上传文件并返回其存储URL。

        @param filename: 文件名
        @param file_data: 文件的二进制数据
        @param content_type: 文件的内容类型（MIME类型）
        @return: 文件的存储URL
        """

        pass

    @abstractmethod
    def download_file(self, file_url: str) -> Optional[bytes]:
        """
        文件下载服务
        @param file_url: 文件的存储URL
        @return: 返回文件的二进制数据，如果文件不存在则返回None
        """
        pass

    @abstractmethod
    def delete_file(self, file_url: str) -> bool:
        """
        删除文件
        @param file_url: 文件的存储URL
        @return: 返回删除是否成功
        """
        pass

    @abstractmethod
    def file_exists(self, file_url: str) -> bool:
        """
        判断文件是否存在
        @param file_url: 文件的存储URL
        @return: 返回文件是否存在
        """
        pass

    @abstractmethod
    def get_file_url(self, filename: str) -> str:
        """
        获取文件下载地址
        @param filename: 文件名
        @return: 文件的下载地址
        """
        pass

    def get_file_mime_type(self, filename: str) -> Optional[str]:
        """
        获取文件的MIME类型
        @param filename: 文件名
        @return: 返回文件的MIME类型，如果无法确定则返回None
        """
        import mimetypes

        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type

    def get_file_name(self, file_url: str) -> str:
        """
        从文件URL中提取文件名
        @param file_url: 文件的存储URL
        @return: 返回文件名
        """
        import os

        return os.path.basename(file_url)

    def get_file_extension(self, filename: str) -> str:
        """
        获取文件的扩展名
        @param filename: 文件名
        @return: 返回文件的扩展名
        """
        import os

        return os.path.splitext(filename)[1].lower()  # 包括点号的扩展名
