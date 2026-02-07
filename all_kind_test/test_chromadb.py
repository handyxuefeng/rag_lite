"""
测试Chroma数据库查询功能
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_chroma import Chroma
from app.utils.embedding_factory import EmbeddingFactory
from app.config import Config


def test_chroma_query():
    """
    测试查询Chroma数据库
    """
    print("=" * 60)
    print("开始测试Chroma数据库查询")
    print("=" * 60)
    
    # 初始化嵌入模型
    print("\n1. 初始化嵌入模型...")
    embeddings = EmbeddingFactory.create_embeddings()
    print(f"   嵌入模型: {type(embeddings).__name__}")
    
    # 获取Chroma持久化目录
    persist_directory = Config.CHROMA_PERSIST_DIRECTORY
    print(f"\n2. Chroma数据库持久化目录: {persist_directory}")
    
    # 检查目录是否存在
    if not os.path.exists(persist_directory):
        print(f"   警告: 持久化目录不存在!")
        return
    
    # 列出所有collection
    print("\n3. 列出所有collection...")
    try:
        from chromadb import PersistentClient
        client = PersistentClient(path=persist_directory)
        collections = client.list_collections()
        
        if not collections:
            print("   没有找到任何collection!")
            return
        
        print(f"   找到 {len(collections)} 个collection:")
        for col in collections:
            print(f"   - {col.name}: {col.count()} 条记录")
    except Exception as e:
        print(f"   获取collection列表失败: {e}")
        return
    
    # 对每个collection进行查询测试
    for collection in collections:
        collection_name = collection.name
        print(f"\n{'=' * 60}")
        print(f"4. 测试查询collection: {collection_name}")
        print(f"{'=' * 60}")
        
        try:
            # 创建Chroma向量存储
            vector_store = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=persist_directory,
            )
            
            # 获取collection中的所有文档
            print(f"\n   获取collection中的文档...")
            all_docs = vector_store.get()
            print(f"   总文档数: {len(all_docs['ids'])}")
            
            if all_docs['ids']:
                print(f"\n   前3条文档示例:")
                for i in range(min(3, len(all_docs['ids']))):
                    doc_id = all_docs['ids'][i]
                    doc_content = all_docs['documents'][i]
                    metadata = all_docs['metadatas'][i] if all_docs['metadatas'] else {}
                    
                    print(f"\n   文档 {i+1}:")
                    print(f"   - ID: {doc_id}")
                    print(f"   - 内容: {doc_content[:100]}..." if len(doc_content) > 100 else f"   - 内容: {doc_content}")
                    print(f"   - 元数据: {metadata}")
            
            # 相似度搜索测试
            print(f"\n   测试相似度搜索...")
            test_queries = [
                "什么是机器学习",
                "Python编程",
                "数据库"
            ]
            
            for query in test_queries:
                print(f"\n   查询: '{query}'")
                results = vector_store.similarity_search_with_score(query, k=3)
                
                if results:
                    print(f"   找到 {len(results)} 条相关结果:")
                    for idx, (doc, score) in enumerate(results, 1):
                        print(f"   {idx}. 相似度: {score:.4f}")
                        print(f"      内容: {doc.page_content[:80]}..." if len(doc.page_content) > 80 else f"      内容: {doc.page_content}")
                        print(f"      元数据: {doc.metadata}")
                else:
                    print("   没有找到相关结果")
            
            # 带过滤条件的查询测试
            print(f"\n   测试带过滤条件的查询...")
            if all_docs['metadatas'] and any(all_docs['metadatas']):
                # 获取第一个文档的元数据作为过滤示例
                sample_metadata = all_docs['metadatas'][0]
                if sample_metadata:
                    filter_key = list(sample_metadata.keys())[0]
                    filter_value = sample_metadata[filter_key]
                    
                    print(f"   使用过滤条件: {filter_key}={filter_value}")
                    
                    try:
                        filtered_results = vector_store.similarity_search_with_score(
                            "test",
                            k=3,
                            filter={filter_key: filter_value}
                        )
                        print(f"   过滤后找到 {len(filtered_results)} 条结果")
                    except Exception as e:
                        print(f"   过滤查询失败: {e}")
            
        except Exception as e:
            print(f"   查询collection {collection_name} 失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 60}")
    print("测试完成!")
    print(f"{'=' * 60}")


def test_chroma_direct():
    """
    直接使用Chroma客户端进行测试
    """
    print("\n" + "=" * 60)
    print("直接使用Chroma客户端测试")
    print("=" * 60)
    
    persist_directory = Config.CHROMA_PERSIST_DIRECTORY
    
    try:
        from chromadb import PersistentClient
        
        client = PersistentClient(path=persist_directory)
        
        # 列出所有collection
        collections = client.list_collections()
        print(f"\n找到 {len(collections)} 个collection:")
        
        for collection in collections:
            print(f"\nCollection: {collection.name}")
            print(f"  - ID: {collection.id}")
            print(f"  - 文档数: {collection.count()}")
            
            # 获取前5条记录
            results = collection.get(limit=5)
            print(f"  - 前5条记录:")
            
            for i in range(len(results['ids'])):
                print(f"\n    记录 {i+1}:")
                print(f"      ID: {results['ids'][i]}")
                if results['documents']:
                    content = results['documents'][i]
                    print(f"      内容: {content[:80]}..." if len(content) > 80 else f"      内容: {content}")
                if results['metadatas']:
                    print(f"      元数据: {results['metadatas'][i]}")
    
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 测试1: 使用LangChain的Chroma接口
    test_chroma_query()
    
    # 测试2: 直接使用Chroma客户端
    test_chroma_direct()