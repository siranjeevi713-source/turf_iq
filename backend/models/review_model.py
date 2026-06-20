from config.db import db
from bson import ObjectId
import datetime

class ReviewModel:
    collection = db["reviews"] if db is not None else None

    @classmethod
    def create(cls, turf_id, user_id, user_name, rating, comment):
        doc = {
            "turf_id": turf_id,
            "user_id": user_id,
            "user_name": user_name,
            "rating": rating,
            "comment": comment,
            "created_at": datetime.datetime.utcnow()
        }
        result = cls.collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return doc

    @classmethod
    def get_for_turf(cls, turf_id):
        reviews = list(cls.collection.find({"turf_id": turf_id}).sort("created_at", -1))
        for r in reviews:
            r["_id"] = str(r["_id"])
            r["created_at"] = r["created_at"].isoformat()
        return reviews

    @classmethod
    def get_average_rating(cls, turf_id):
        reviews = cls.get_for_turf(turf_id)
        if not reviews:
            return 0
        return round(sum(r["rating"] for r in reviews) / len(reviews), 1)
