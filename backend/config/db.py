import os

def get_db():
    try:
        from pymongo import MongoClient
        print("Attempting to connect to native MongoDB...")
        client = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/turffiq"), serverSelectionTimeoutMS=1000)
        client.server_info() # Force connection check
        print("MongoDB connected successfully")
        return client.get_default_database()
    except Exception as e:
        print(f"Failed to connect to local MongoDB: {e}")
        print("Falling back to local isolated Mongomock DB instance for seamless platform execution...")
        import mongomock
        mock_client = mongomock.MongoClient()
        return mock_client.turffiq

db = get_db()
