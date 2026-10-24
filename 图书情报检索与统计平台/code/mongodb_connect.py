from pymongo import MongoClient

# 统一连接参数，所有模块复用
CONN_STR = "mongodb://localhost:27017"
DB_NAME = "library"


def get_db():
    """返回 (数据库对象, 客户端对象)，调用方负责关闭 client"""
    client = MongoClient(CONN_STR, serverSelectionTimeoutMS=5000)
    return client[DB_NAME], client
