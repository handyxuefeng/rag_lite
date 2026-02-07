
"""
自动导入blueprints目录下所有蓝图模块
from app.blueprints import auth
from app.blueprints import knowledgebase
__all__ = ["auth", "knowledgebase"]
上面是之前的写法，当新增一个蓝图模块时，需要手动添加到__all__中，比较麻烦
现在改为自动导入所有蓝图模块
"""

import os
import importlib

# 自动导入blueprints目录下所有蓝图模块
__all__ = []

def auto_import_blueprints():
    """
    自动导入blueprints目录下所有蓝图模块
    """
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))

    #获取当前目录下所有.py文件，包含__init__.py
    all_py_files = os.listdir(current_dir)

    #print("all_py_files=", all_py_files)

    # 遍历目录下所有.py文件
    for filename in all_py_files:
        # 排除__init__.py和非.py文件
        if filename.endswith('.py') and (filename != '__init__.py' and filename != 'utils.py' and filename != '__pycache__'):
            # 获取模块名（去掉.py后缀）
            module_name = filename[:-3]
            
            try:
                # 动态导入模块
                module = importlib.import_module(f'.{module_name}', package='app.blueprints')
                # 将模块添加到全局命名空间
                globals()[module_name] = module
                # 如果模块有bp属性（蓝图实例），则添加到__all__
                if hasattr(module, 'bp'):
                    __all__.append(module_name)
            except ImportError as e:
                print(f"导入蓝图模块 {module_name} 失败: {e}")

# 收集所有蓝图实例
def get_all_blueprints():
    blueprints = []
    for module_name in __all__:
        module = globals()[module_name]
        if hasattr(module, 'bp'):
            blueprints.append(module.bp)
    return blueprints


# 自动导入所有蓝图模块
auto_import_blueprints()
