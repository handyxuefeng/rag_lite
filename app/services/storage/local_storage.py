import os
from pathlib import Path
from .base import BaseStorage
from app.config import Config
from app.utils.logger import get_logger


class LocalStorage(BaseStorage):

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        storage_dir = Config.STORAGE_DIR
        # 判断STORAGE_DIR是否是绝对路径
        if os.path.isabs(storage_dir):
            self.storage_dir = Path(storage_dir)
        else:
            # 如果不是绝对路径，则相对于当前工作目录
            # self.storage_dir = / storage_dir
            self.logger.info(f"Path(os.getcwd()) =: {Path(os.getcwd()) }")

            self.storage_dir = Path(__file__).parent.parent.parent / storage_dir

        # 创建存储目录（如果不存在）
        os.makedirs(self.storage_dir, exist_ok=True)

        self.logger.info(f"本地存储初始化成功: {self.storage_dir}")

    def _get_full_path(self, file_path: str) -> str:
        return str(os.path.join(self.storage_dir, file_path))

    # 本地文件存储服务实现实现父类的上传文件方法
    def upload_file(
        self, file_path: str, file_data: bytes, content_type: str = None
    ) -> str:

        self.logger.info(f"上传文件到本地存储LocalStorage: {file_path}")

        full_path = self._get_full_path(file_path)

        # 确保目录存在
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(file_data)

        self.logger.info(f"文件已保存到本地: {full_path}")
        return full_path

    def download_file(self, file_path: str) -> bytes:
        try:
            full_path = self._get_full_path(file_path)
            with open(full_path, "rb") as f:
                return f.read()
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
        print("要删除文件的url= ", file_url)

        try:
            full_path = self._get_full_path(file_url)

            print("要删除文件的full_path= ", full_path)
            
            if full_path and os.path.exists(full_path):
                os.remove(full_path)

                self.logger.info(f"成功删除文件: {full_path}")

                try:
                    # 如果文件删除后，父目录为空的话，尝试删除父目录
                    parent_dir = os.path.dirname(full_path)
                    if os.path.exists(parent_dir) and not os.listdir(parent_dir):
                        os.rmdir(parent_dir)
                        self.logger.info(f"成功删除空的父目录: {parent_dir}")
                except Exception as e:
                    self.logger.warning(f"删除父目录时出错: {str(e)}")
            else:
                self.logger.warning(f"尝试删除的文件不存在: {full_path}")
                return False
        except Exception as e:
            self.logger.error(f"删除文件时出错: {str(e)}")
            return False
        

    def file_exists(self, file_url: str) -> bool:

        pass

    def get_file_url(self, filename: str) -> str:

        pass
