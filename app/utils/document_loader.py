import os

# 核心，导入langchain
from langchain_community.document_loaders import (
    PyMuPDFLoader,
    Docx2txtLoader,
    TextLoader,
)


# 导入创建具有名称临时文件的工具，结合with可自动清理
from tempfile import NamedTemporaryFile

# 导入日志工具
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentLoader:

    @staticmethod
    def loader(file_data, file_type):
        """
        file_data:文件内容,是一个二进制文件
        file_type: [pdf,md,docs]
        """
        if file_type == "pdf":
            return DocumentLoader.load_pdf(file_data)
        elif file_type == "docx":
            return DocumentLoader.load_docx(file_data)
        elif file_type in ["txt", "md"]:
            return DocumentLoader.load_txt(file_data)
        else:
            raise ValueError(f"不能加载的文档的类型{file_type}")

    @staticmethod
    def load_pdf(file_data):
        try:
            # delete=False表示 创建不自动删除的临时文件，delete=True
            with NamedTemporaryFile(delete=False, suffix=".pdf") as tempfile:
                # 把file_data二进制文件写入到临时文件中
                tempfile.write(file_data)
                temp_path = tempfile.name

            """
            这里要在with NamedTemporaryFile的外面访问临时文件，如果delete=True，则表示离开
            后，就自动删除了临时文件，后面的语句块没法访问到临时文件了
            """

            try:
                pyMuPDFLoader = PyMuPDFLoader(temp_path)
                documents = pyMuPDFLoader.load()
                return documents
            except Exception as e:
                logger.error(f"通过PyMuPDFLoader工具load:{temp_path} 失败")
                raise ValueError(f"通过PyMuPDFLoader工具load {temp_path} 失败")
            finally:
                # 手动删除临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.info(f"加载pdf文档出错{str(e)}")
            raise ValueError(f"加载pdf文档出错{str(e)}")

    @staticmethod
    def load_docx(file_data):
        try:
            # delete=False表示 创建不自动删除的临时文件，delete=True
            with NamedTemporaryFile(delete=False, suffix=".docx") as tempfile:
                # 把file_data二进制文件写入到临时文件中
                tempfile.write(file_data)
                temp_path = tempfile.name

            """
            这里要在with NamedTemporaryFile的外面访问临时文件，如果delete=True，则表示离开
            后，就自动删除了临时文件，后面的语句块没法访问到临时文件了
            """

            try:
                docx2txtLoader = Docx2txtLoader(temp_path)
                documents = docx2txtLoader.load()
                return documents
            except Exception as e:
                logger.error(f"通过Docx2txtLoader工具load{temp_path}失败")
                raise ValueError(f"通过Docx2txtLoader工具load{temp_path}失败")
            finally:
                # 手动删除临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.info(f"加载docx文档出错{str(e)}")
            raise ValueError(f"加载docx文档出错{str(e)}")

    @staticmethod
    def load_txt(file_data):
        try:
            # delete=False表示 创建不自动删除的临时文件，delete=True
            with NamedTemporaryFile(delete=False, suffix=".docx") as tempfile:
                # 把file_data二进制文件写入到临时文件中
                tempfile.write(file_data)
                temp_path = tempfile.name

            """
            这里要在with NamedTemporaryFile的外面访问临时文件，如果delete=True，则表示离开
            后，就自动删除了临时文件，后面的语句块没法访问到临时文件了
            """

            try:
                textLoader = TextLoader(temp_path)
                documents = textLoader.load()
                return documents
            except Exception as e:
                logger.error(f"通过TextLoader工具load{temp_path}失败")
                raise ValueError(f"通过TextLoader工具load{temp_path}失败")
            finally:
                # 手动删除临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            logger.info(f"加载txt文档出错{str(e)}")
            raise ValueError(f"加载txt文档出错{str(e)}")
