from typing import Optional, TypeVar, Generic, Dict, Any

# 导入数据操作工具
from app.utils.db import db_session, db_transaction

# 导入日志获取方法（日志系统会在首次使用时自动从 Config 获取配置并初始化）
from app.utils.logger import get_logger

# 获取当前模块日志记录器（会自动初始化日志系统）
# logger = get_logger(__name__)

# 定义一个泛型
T = TypeVar("T")


class BaseService(Generic[T]):
    """
    定义基础服务类，支持泛型
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    # 得到数据库会话
    def create_db_session(self):
        return db_session()

    # 得到数据库操作事务
    def create_db_transaction(self):
        return db_transaction()

    def get_by_id(self, model_class: T, entity_id: str):
        with self.create_db_session() as db_session:
            try:
                return (
                    db_session.query(model_class)
                    .filter(model_class.id == entity_id)
                    .first()
                )
            except Exception as e:
                self.logger.error("获取ID对应的对象失败:{e}")
                return None

    def pagination_query(self, model_class_list, page, page_size, order_by):
        """
        在基类封装统一的分页查询方法
        """
        if order_by is not None:
            model_class_list = model_class_list.order_by(order_by)
        # 获取查询到记录的总条数
        total = model_class_list.count()

        # 计算偏移量,类似mysql的 limit 10
        offset = (page - 1) * page_size

        # 获取当前页的数据
        query_model_list = model_class_list.offset(offset).limit(page_size).all()

        model_dict = [
            model.to_dict() if hasattr(model, "to_dict") else model
            for model in query_model_list
        ]
        return {
            "items": model_dict,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
            },
        }
