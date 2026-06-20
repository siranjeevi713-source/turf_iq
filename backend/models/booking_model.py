from config.db import db
from bson import ObjectId

class BookingModel:
    collection = db["bookings"] if db is not None else None

    @classmethod
    def create_booking(cls, booking_data):
        return cls.collection.insert_one(booking_data)

    @classmethod
    def get_user_bookings(cls, user_id):
        return list(cls.collection.find({"user_id": user_id}))
