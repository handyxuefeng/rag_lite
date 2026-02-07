from abc import ABC, abstractmethod

from langchain_core.documents import Document


class VectorBaseService(ABC):
    """
    向量数据库基类，用来获取和创建集合
    向量数据库的增删
    """

    @abstractmethod
    def get_or_create_collection(self):
        pass

    @abstractmethod
    def add_documents(self, collection_name, documents, ids):
        """
        添加文档到向量数据库中的集合
        """
        pass

    @abstractmethod
    def delete_document_from_collection(self, collection_name, ids=None, filter=None):
        """
        删除集合中的文档
        """
        pass

    @abstractmethod
    def delete_collection(self, collection_name):
        """
        删除整个集合
        """
        pass
