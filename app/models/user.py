# 导入字段类型类型
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.sql import func

import uuid
from app.models.base import BaseModel


class User(BaseModel):
    # 指定数据库表名为User
    __tablename__ = "user"

    # 指定__repr__显示的字段
    __repr_fields__ = ["id", "username"]

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:32])

    username = Column(String(64), nullable=False, unique=True, index=True)

    email = Column(String(64), nullable=False, unique=True, index=True)

    password_hash = Column(String(255), nullable=False)

    # 是否激活，默认为激活，不可为空
    is_active = Column(Boolean, nullable=False)

    # 创建时间，默认为当前时间
    created_at = Column(DateTime, default=func.now())

    # 更新时间，默认为当前时间
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 将当前用户对象转换为字典
    def to_dict(self, include_password=False, **kwargs):
        # 转换为字典，如果未包含密码，排除 password_hash 字段
        """转换为字典"""
        if not include_password:
            exclude = ["password_hash"]
        else:
            exclude = []
        # 调用父类的 to_dict 方法，传入要排除的字段
        return super().to_dict(exclude=exclude, **kwargs)
