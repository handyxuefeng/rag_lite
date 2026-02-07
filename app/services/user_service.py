import hashlib
from app.services.base_service import BaseService
from app.models.user import User


class UserService(BaseService[User]):

    def hash_pwd(self, pwd):
        """
        对密码进行hash
        :param self: 说明
        :param pwd: 说明
        """
        return hashlib.sha256(pwd.encode("utf-8")).hexdigest()

    def register(self, username, password, email):

        print("传递到service的参数==", username, "pwd=", password, "email=", email)

        if not username or not password:
            # 抛出异常给control层，也就是定义好的蓝图
            raise ValueError("用户名和密码不能为空")
        if len(username) < 3:
            # 抛出异常给control层，也就是定义好的蓝图
            raise ValueError("用户名至少需要3个字符")

        if len(password) < 6:
            # 抛出异常给control层，也就是定义好的蓝图
            raise ValueError("密码至少需要6个字符")

        with self.create_db_transaction() as db_transaction_session:
            # 检查用户名是否存在
            exists_user = (
                db_transaction_session.query(User).filter_by(username=username).first()
            )
            if exists_user:
                raise ValueError(f"该用户名:{username}已经被注册了")

            if email:
                exists_email = (
                    db_transaction_session.query(User).filter_by(email=email).first()
                )
                if exists_email:
                    raise ValueError(f"该邮箱{email}已经被注册了")

            password_hash = self.hash_pwd(password)

            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                is_active=True,
            )
            # print("1.创建用户实列,id=", user.id)
            db_transaction_session.add(user)
            # print("2.把用户添加到到表中,id=", user.id)
            db_transaction_session.flush()
            # print("3.数据保存成功,id=", user.id)
            self.logger.info(f"{username}注册成功")

            return user.to_dict()

    def login(self, username, password):
        if not username or not password:
            raise ValueError("用户名和密码不能为空")
        else:
            with self.create_db_session() as db_session:
                exists_user = (
                    db_session.query(User).filter_by(username=username).first()
                )
                if not exists_user:
                    raise ValueError(f"用户{username}不存在")
                if not exists_user.is_active:
                    raise ValueError(f"用户{username}已经被封禁")

                if exists_user.password_hash != self.hash_pwd(password):
                    raise ValueError("密码错误")

                self.logger.info(f"用户{username}登录成功")
                return exists_user.to_dict()

    def get_user_by_id(self, user_id):
        # print("get_user_by_id=====", user_id)
        with self.create_db_session() as db_session:
            exists_user = db_session.query(User).filter(User.id == user_id).first()
        if exists_user:
            # print(f"查询到了用户{exists_user.to_dict()}")
            return exists_user.to_dict()
        return None


# 向外暴露实列
user_service = UserService()
