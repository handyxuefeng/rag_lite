# 导入数据库创建引擎
from sqlalchemy import create_engine

# 导入数据库连接池
from sqlalchemy.pool import QueuePool

# 导入 sessionmaker，用于创建数据库会话工厂
from sqlalchemy.orm import sessionmaker

# 导入上下文管理器
from contextlib import contextmanager

# 导入sql异常类
from sqlalchemy.exc import SQLAlchemyError

from app.config import Config

from app.models import Base

# 导入日志获取方法（日志系统会在首次使用时自动从 Config 获取配置并初始化）
from app.utils.logger import get_logger

# 获取当前模块日志记录器（会自动初始化日志系统）
logger = get_logger(__name__)


def get_database_url():
    """
    获取数据库的连接地址
    url = mysql+pymysql://root:admin123@127.0.0.1:3306/rag?charset=utf8mb4
    """
    return (
        f"mysql+pymysql://{Config.DB_USER}:{Config.DB_PASSWORD}"
        f"@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}?charset={Config.DB_CHARSET}"
    )


# 创建数据库引擎，指定连接池、大小、回收等参数
engine = create_engine(
    # 数据库连接地址
    get_database_url(),
    # 数据库连接池
    poolclass=QueuePool,
    # 数据库连接池中最大连接数
    pool_size=10,
    # 允许最大溢出连接数 为 20
    max_overflow=20,
    # 3600秒如果不使用，回收连接池
    pool_recycle=3600,
    # 不输出sql日志
    echo=False,
)

# 创建 SQLAlchemy 会话工厂，用于生成 session 对象
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    # 尝试创建所有基于 Base 的表结构
    try:
        # 使用引擎来创建数据库的表结构
        Base.metadata.create_all(engine)
        # 记录数据库表结构初始化完成
        logger.info("数据库表结构初始化完成")
    except Exception as e:
        # 初始化出错时记录错误信息
        logger.error(f"数据库初始化失败: {e}")
        # 重新抛出异常
        raise


@contextmanager
def db_session():
    # 创建会话实列
    session = SessionLocal()

    try:
        yield session
    except Exception as e:
        logger.info(f"数据库会话错误{e}")
        raise
    finally:
        session.close()


@contextmanager
def db_transaction():
    """
    数据库事务上下文管理器（显式事务，自动提交，出错自动回滚）

    使用示例：
        >>> from app.utils.db import db_transaction
        >>> with db_transaction() as db:
        ...     user = User(name="test")
        ...     db.add(user)
        ...     # 自动提交，异常时自动回滚

    返回：
        SQLAlchemy Session 对象
    """

    # 创建会话实列
    session = SessionLocal()

    try:
        yield session
        # 事务正常结束可以自动提交
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.info(f"数据库事务错误{e}")
        raise
    except Exception as e:
        session.rollback()
        logger.info(f"数据库会话错误{e}")
        raise
    finally:
        session.close()
