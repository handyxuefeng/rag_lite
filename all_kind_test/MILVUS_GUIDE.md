# Milvus 本地访问指南

## 🎉 Milvus 已成功安装并运行！

### 📊 服务状态

所有容器已成功启动：
- ✅ **milvus-standalone** - Milvus主服务
- ✅ **milvus-etcd** - 元数据存储
- ✅ **milvus-minio** - 对象存储

### 🔗 访问地址

#### Milvus 数据库
- **地址**: `localhost:19530`
- **协议**: gRPC
- **Python客户端**: 已安装 `pymilvus`

#### Milvus 管理界面 (Attu)
- **地址**: http://localhost:9091
- **说明**: 可视化管理界面（如果已安装Attu）

#### MinIO 对象存储
- **API地址**: http://localhost:9000
- **控制台地址**: http://localhost:9001
- **用户名**: `minioadmin`
- **密码**: `minioadmin`

### 🚀 快速开始

#### 1. 运行示例代码
```bash
python milvus_example.py
```

#### 2. Python 代码连接示例

```python
from pymilvus import connections

# 连接到Milvus
connections.connect(
    alias="default",
    host="localhost",
    port="19530"
)

# 检查连接
from pymilvus import utility
print(f"集合列表: {utility.list_collections()}")

# 断开连接
connections.disconnect("default")
```

#### 3. 使用LangChain集成

```python
from langchain_community.vectorstores import Milvus
from langchain.embeddings import HuggingFaceEmbeddings

# 创建嵌入模型
embeddings = HuggingFaceEmbeddings()

# 连接到Milvus
vector_store = Milvus(
    embedding_function=embeddings,
    connection_args={"host": "localhost", "port": "19530"},
    collection_name="my_collection"
)
```

### 📝 常用命令

#### 查看容器状态
```bash
docker ps
```

#### 查看Milvus日志
```bash
docker logs milvus-standalone
```

#### 重启Milvus
```bash
docker-compose restart
```

#### 停止Milvus
```bash
docker-compose down
```

#### 启动Milvus
```bash
docker-compose up -d
```

### 🛠️ 管理界面

#### 使用Attu（推荐）
Attu是Milvus的官方可视化界面，可以：
- 查看集合和数据
- 执行搜索查询
- 监控系统状态
- 管理索引

如果需要安装Attu，可以修改docker-compose.yml添加：

```yaml
attu:
  container_name: milvus-attu
  image: zilliz/attu:v2.4.15
  environment:
    MILVUS_URL: milvus-standalone:19530
  ports:
    - "3000:3000"
  depends_on:
    - "standalone"
  networks:
    - milvus
```

### 📚 更多资源

- [Milvus官方文档](https://milvus.io/docs)
- [PyMilvus API文档](https://milvus.io/api-reference/pymilvus/v2.4.x/About.md)
- [LangChain Milvus集成](https://python.langchain.com/docs/integrations/vectorstores/milvus)

### ⚠️ 注意事项

1. **端口占用**: 确保19530、9091、9000、9001端口未被占用
2. **内存要求**: Milvus至少需要4GB内存
3. **数据持久化**: 数据存储在 `./volumes/` 目录下
4. **备份**: 定期备份 `./volumes/milvus` 目录

### 🐛 故障排查

#### 无法连接到Milvus
```bash
# 检查容器状态
docker ps

# 查看日志
docker logs milvus-standalone

# 检查端口
netstat -an | findstr 19530
```

#### 容器启动失败
```bash
# 查看详细日志
docker-compose logs

# 重启服务
docker-compose down
docker-compose up -d
```

### 💡 下一步

1. 运行示例代码测试连接
2. 集成到您的RAG项目中
3. 根据需求调整索引参数
4. 配置数据备份策略
