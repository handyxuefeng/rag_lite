from langchain_milvus import Milvus
from app.config import Config
from app.utils.embedding_factory import EmbeddingFactory
from langchain_core.documents import Document

print(f"连接到 Milvus: {Config.MILVUS_HOST}:{Config.MILVUS_PORT}")

embeddings = EmbeddingFactory.create_embeddings()

connection_args = {
    "uri": f"http://{Config.MILVUS_HOST}:{Config.MILVUS_PORT}"
}
print(f"连接参数: {connection_args}")

test_collection_name = "kb_test_uri_collection"
print(f"\n尝试使用 langchain_milvus 创建集合: {test_collection_name}")

try:
    vector_store = Milvus(
        collection_name=test_collection_name,
        embedding_function=embeddings,
        connection_args=connection_args,
    )
    print(f"✓ langchain_milvus 集合初始化成功")

    test_doc = Document(
        page_content="这是一个测试文档",
        metadata={"id": "test_1", "source": "test"}
    )

    result = vector_store.add_documents([test_doc], ids=["test_1"])
    print(f"✓ 成功添加文档到集合")
    print(f"  结果: {result}")

    print(f"\n尝试查询文档...")
    search_results = vector_store.similarity_search("测试", k=1)
    print(f"✓ 查询成功，找到 {len(search_results)} 条结果")
    for res in search_results:
        print(f"  - {res.page_content}")

except Exception as e:
    print(f"✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("检查集合是否在 Milvus 中...")
from pymilvus import MilvusClient

client = MilvusClient(
    uri=f"http://{Config.MILVUS_HOST}:{Config.MILVUS_PORT}"
)

collections = client.list_collections()
print(f"当前存在的集合数量: {len(collections)}")
for col in collections:
    print(f"  - {col}")

if test_collection_name in collections:
    print(f"\n✓ 集合 {test_collection_name} 存在于 Milvus 中")
else:
    print(f"\n✗ 集合 {test_collection_name} 不存在于 Milvus 中")

print(f"\n测试完成")
