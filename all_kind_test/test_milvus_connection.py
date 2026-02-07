from pymilvus import MilvusClient
from app.config import Config
from app.utils.embedding_factory import EmbeddingFactory

print(f"连接到 Milvus: {Config.MILVUS_HOST}:{Config.MILVUS_PORT}")

try:
    client = MilvusClient(
        uri=f"http://{Config.MILVUS_HOST}:{Config.MILVUS_PORT}"
    )
    print("✓ Milvus 连接成功")
except Exception as e:
    print(f"✗ Milvus 连接失败: {e}")
    exit(1)

try:
    collections = client.list_collections()
    print(f"\n当前存在的集合数量: {len(collections)}")
    if collections:
        print("集合列表:")
        for col in collections:
            print(f"  - {col}")
    else:
        print("  没有找到任何集合")
except Exception as e:
    print(f"✗ 获取集合列表失败: {e}")

test_collection_name = "test_collection_456"
print(f"\n尝试创建测试集合: {test_collection_name}")

try:
    embeddings = EmbeddingFactory.create_embeddings()
    test_text = "这是一个测试文本"
    test_vector = embeddings.embed_query(test_text)
    print(f"✓ 嵌入向量生成成功，维度: {len(test_vector)}")

    client.create_collection(
        collection_name=test_collection_name,
        dimension=len(test_vector),
        metric_type="IP",
        consistency_level="Strong"
    )
    print(f"✓ 集合 {test_collection_name} 创建成功")

    data = [{
        "id": 1,
        "vector": test_vector,
        "text": test_text
    }]

    client.insert(
        collection_name=test_collection_name,
        data=data
    )
    print(f"✓ 成功向集合中插入 1 条数据")

    print(f"\n检查集合是否存在...")
    exists = client.has_collection(test_collection_name)
    print(f"✓ 集合 {test_collection_name} 是否存在: {exists}")

    print(f"\n再次检查集合列表:")
    collections = client.list_collections()
    print(f"集合数量: {len(collections)}")
    for col in collections:
        print(f"  - {col}")
        if col == test_collection_name:
            count = client.query(
                collection_name=col,
                filter="id == 1",
                output_fields=["text"]
            )
            print(f"    数据: {count}")

except Exception as e:
    print(f"✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n测试完成")
print(f"请在 Attu 界面 http://{Config.MILVUS_HOST}:8000/ 查看集合: {test_collection_name}")
