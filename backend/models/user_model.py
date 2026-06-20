from config.db import db
from bson import ObjectId

class UserModel:
    collection = db["users"] if db is not None else None

    @classmethod
    def create_user(cls, user_data):
        return cls.collection.insert_one(user_data)

    @classmethod
    def find_by_phone(cls, phone):
        return cls.collection.find_one({"phone": phone})

    @classmethod
    def find_by_id(cls, user_id):
        return cls.collection.find_one({"_id": ObjectId(user_id)})
        
    @classmethod
    def update_user(cls, user_id, update_data):
        return cls.collection.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
