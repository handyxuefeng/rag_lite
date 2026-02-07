from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class TextSplitter:
    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "，", "。", ",", ".", "？", "?", "!" ""],
        )

    def split_document(self, documents_list: list[Document], doc_id: str) -> list:
        """
        利用RecursiveCharacterTextSplitter分割分档列表
        返回chunk列表
        """
        chunks = self.splitter.split_documents(documents_list)

        split_result = []
        for idx, chunk in enumerate(chunks, 1):
            # 分块id = 'xxxxx_1,xxxx_2'
            chunk_id = f"{doc_id}_{idx}" if doc_id else idx
            split_result.append(
                {
                    "id": chunk_id,
                    "chunk_index": idx,
                    "text": chunk.page_content,
                    "metadata": chunk.metadata,
                }
            )

        return split_result
