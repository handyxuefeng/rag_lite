from pymilvus import MilvusClient
from app.config import Config

print(f"连接到 Milvus: {Config.MILVUS_HOST}:{Config.MILVUS_PORT}")

client = MilvusClient(
    uri=f"http://{Config.MILVUS_HOST}:{Config.MILVUS_PORT}"
)

print("✓ Milvus 连接成功\n")

collections = client.list_collections()
print(f"当前存在的集合数量: {len(collections)}")
if collections:
    print("所有集合列表:")
    for col in collections:
        print(f"  - {col}")
else:
    print("  没有找到任何集合")

print(f"\n检查 langchain_milvus 创建的集合...")
langchain_collections = [col for col in collections if 'langchain' in col.lower()]
print(f"langchain 相关的集合数量: {len(langchain_collections)}")
for col in langchain_collections:
    print(f"  - {col}")
    try:
        count = client.query(
            collection_name=col,
            filter="",
            limit=10,
            output_fields=["text"]
        )
        print(f"    数据: {count['data']}")
    except Exception as e:
        print(f"    查询数据失败: {e}")
