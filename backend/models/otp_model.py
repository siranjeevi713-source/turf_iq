from config.db import db
import datetime
import random

class OtpModel:
    collection = db["otp_sessions"] if db is not None else None

    @classmethod
    def generate_otp(cls, phone):
        """Generate a 6-digit OTP, store in DB with 5-min expiry"""
        otp = str(random.randint(100000, 999999))
        doc = {
            "phone": phone,
            "otp": otp,
            "expires_at": datetime.datetime.utcnow() + datetime.timedelta(minutes=5),
            "verified": False,
            "created_at": datetime.datetime.utcnow()
        }
        # Remove any old OTP for this phone
        cls.collection.delete_many({"phone": phone})
        cls.collection.insert_one(doc)
        return otp

    @classmethod
    def verify_otp(cls, phone, otp):
        """Validate OTP. Returns True if correct and not expired."""
        record = cls.collection.find_one({
            "phone": phone,
            "otp": otp,
            "verified": False
        })
        if not record:
            return False
        if record["expires_at"] < datetime.datetime.utcnow():
            return False
        # Mark as verified
        cls.collection.update_one(
            {"_id": record["_id"]},
            {"$set": {"verified": True}}
        )
        return True

    @classmethod
    def is_verified(cls, phone):
        """Check if phone has a verified OTP session"""
        record = cls.collection.find_one({
            "phone": phone,
            "verified": True
        })
        if not record:
            return False
        # Still within expiry window (extra safety)
        if record["expires_at"] < datetime.datetime.utcnow():
            return False
        return True

    @classmethod
    def clear(cls, phone):
        """Clean up OTP sessions for a phone"""
        cls.collection.delete_many({"phone": phone})
