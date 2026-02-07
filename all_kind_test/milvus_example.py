from pymilvus import connections, utility, Collection, FieldSchema, CollectionSchema, DataType
import numpy as np

def connect_to_milvus():
    """
    连接到本地Milvus数据库
    """
    try:
        connections.connect(
            alias="default",
            host="localhost",
            port="19530"
        )
        print("✅ 成功连接到Milvus数据库")
        return True
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def check_connection():
    """
    检查连接状态
    """
    try:
        status = connections.get_connection_status("default")
        print(f"连接状态: {status}")
        
        list_collections = utility.list_collections()
        print(f"当前集合数量: {len(list_collections)}")
        print(f"集合列表: {list_collections}")
        
        return True
    except Exception as e:
        print(f"❌ 检查连接失败: {e}")
        return False

def create_sample_collection():
    """
    创建示例集合
    """
    collection_name = "demo_collection"
    
    if utility.has_collection(collection_name):
        print(f"集合 {collection_name} 已存在")
        return Collection(collection_name)
    
    dim = 128
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=False),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim)
    ]
    
    schema = CollectionSchema(fields, description="示例集合")
    collection = Collection(name=collection_name, schema=schema)
    print(f"✅ 成功创建集合: {collection_name}")
    
    return collection

def insert_sample_data(collection):
    """
    插入示例数据
    """
    num_entities = 10
    entities = [
        [i for i in range(num_entities)],
        [np.random.rand(128).tolist() for _ in range(num_entities)]
    ]
    
    insert_result = collection.insert(entities)
    print(f"✅ 成功插入 {num_entities} 条数据")
    print(f"插入ID: {insert_result.primary_keys}")
    
    collection.flush()
    return insert_result

def create_index(collection):
    """
    创建索引
    """
    index_params = {
        "index_type": "IVF_FLAT",
        "metric_type": "L2",
        "params": {"nlist": 128}
    }
    
    collection.create_index(field_name="embedding", index_params=index_params)
    print("✅ 成功创建索引")

def search_data(collection):
    """
    搜索数据
    """
    collection.load()
    
    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
    
    query_vector = [np.random.rand(128).tolist()]
    results = collection.search(
        data=query_vector,
        anns_field="embedding",
        param=search_params,
        limit=3,
        expr=None
    )
    
    print(f"✅ 搜索完成，找到 {len(results[0])} 个结果")
    for i, result in enumerate(results[0]):
        print(f"  结果 {i+1}: ID={result.id}, 距离={result.distance}")

def main():
    """
    主函数
    """
    print("=" * 50)
    print("Milvus 数据库连接示例")
    print("=" * 50)
    
    if not connect_to_milvus():
        return
    
    print("\n检查连接状态...")
    check_connection()
    
    print("\n创建示例集合...")
    collection = create_sample_collection()
    
    print("\n插入示例数据...")
    insert_sample_data(collection)
    
    print("\n创建索引...")
    create_index(collection)
    
    print("\n搜索数据...")
    search_data(collection)
    
    print("\n" + "=" * 50)
    print("示例运行完成！")
    print("=" * 50)
    
    connections.disconnect("default")
    print("已断开连接")

if __name__ == "__main__":
    main()
