import os

from app.config import Config


def get_file_extension(file_name):
    """
    根据文件名称，得到文件的扩展名
    """
    # 使用 os.path.splitext 分离文件名与扩展名，取扩展名并去掉开头的点
    _, ext = os.path.splitext(file_name)
    return ext.lstrip(".")


def get_file_name_and_extension(file_name):
    """
    根据文件名称，得到文件名（不含扩展名）和扩展名
    """
    # 使用 os.path.splitext 分离文件名与扩展名
    name_without_ext, ext = os.path.splitext(file_name)
    return name_without_ext, ext.lstrip(".")


def allowed_file(file_name):
    ext = get_file_extension(file_name)
    return ext in Config.ALLOWED_EXTENSIONS
