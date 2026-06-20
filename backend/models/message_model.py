from config.db import db
from bson import ObjectId
import datetime

class MessageModel:
    collection = db["messages"] if db is not None else None

    @classmethod
    def save_message(cls, room_id, sender_id, sender_name, message_text):
        doc = {
            "room_id": room_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "text": message_text,
            "timestamp": datetime.datetime.utcnow()
        }
        return cls.collection.insert_one(doc)

    @classmethod
    def get_room_messages(cls, room_id):
        raw = list(cls.collection.find({"room_id": room_id}).sort("timestamp", 1))
        for msg in raw:
            msg["_id"] = str(msg["_id"])
            msg["timestamp"] = msg["timestamp"].isoformat()
        return raw
