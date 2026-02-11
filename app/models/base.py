from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.inspection import inspect
from typing import Dict, Any, Optional

# 创建统一的Base类，所有的ORM模型都应该继承此Base

Base = declarative_base()


# 定义所有模型的基类
class BaseModel(Base):
    # 把此类标记为抽象类，这样就不会创建表了
    __abstract__ = True

    # 把模型对象转换成字典
    def to_dict(self, exclude=[], **kwargs):
        # 要排除的字段列表，比如打印模型时，不能打印密码

        exclude_fields_list = exclude or []

        result = {}

        # 获取当前模型的所有列的定义,也就是通过inspect方法获取类上的所有属性
        mapper_columns = inspect(self.__class__)

        # 遍历模型中定义的所有列
        for column in mapper_columns.columns:
            # 获取列名
            col_name = column.name

            if col_name in exclude_fields_list:
                continue
            # 获取此字段名的值
            value = getattr(self, col_name, None)

            # 如果该字段的值是日期类型，调用isoformat方法转换为字符串
            if hasattr(value, "isoformat"):
                result[col_name] = value.isoformat() if value else None
            else:
                result[col_name] = value

        return result

    def __repr__(self):
        # 如果子类指定义__repr_fields__值，优先显示这些字段
        if hasattr(self, "__repr_fields__"):
            fields = getattr(self, "__repr_fields__")
            attrs = ", ".join(f"{field}={getattr(self,field,None)}" for field in fields)
        else:
            attrs = f"id={getattr(self,'id',None)}"
        return f"<{self.__class__.__name__}({attrs})>"
