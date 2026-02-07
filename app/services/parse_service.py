from app.utils.document_loader import DocumentLoader


class ParseService:
    """
    文件解析服务
    """

    def parse(self, file_data, file_type) -> list:
        file_type = file_type.lower()

        # 通过各种文档加载器，得到文本内容
        return DocumentLoader.loader(file_data, file_type)


parse_service = ParseService()
