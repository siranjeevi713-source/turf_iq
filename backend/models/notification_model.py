from config.db import db
from bson import ObjectId
import datetime

class NotificationModel:
    collection = db["notifications"] if db is not None else None

    @classmethod
    def create(cls, user_id, notif_type, payload):
        doc = {
            "user_id": user_id,
            "type": notif_type,
            "payload": payload,
            "read": False,
            "created_at": datetime.datetime.utcnow()
        }
        result = cls.collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return doc

    @classmethod
    def get_user_notifications(cls, user_id):
        notifs = list(cls.collection.find({"user_id": user_id}).sort("created_at", -1).limit(50))
        for n in notifs:
            n["_id"] = str(n["_id"])
            n["created_at"] = n["created_at"].isoformat()
        return notifs

    @classmethod
    def mark_read(cls, notif_id):
        cls.collection.update_one({"_id": ObjectId(notif_id)}, {"$set": {"read": True}})

    @classmethod
    def mark_all_read(cls, user_id):
        cls.collection.update_many({"user_id": user_id}, {"$set": {"read": True}})
