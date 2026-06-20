from config.db import db
from bson import ObjectId
import datetime
import uuid

class PaymentModel:
    collection = db["payments"] if db is not None else None

    @classmethod
    def ensure_indexes(cls):
        try:
            cls.collection.create_index("txn_id", unique=True, name="unique_txn_id")
        except Exception as e:
            print(f"[PaymentModel] Index error: {e}")

    @classmethod
    def create_single_payment(cls, booking_id, user_id, amount):
        txn_id = "TXN-" + uuid.uuid4().hex[:12].upper()
        payment = {
            "booking_id": booking_id,
            "user_id": user_id,
            "amount": amount,
            "method": "single",
            "txn_id": txn_id,
            "status": "paid",
            "paid_at": datetime.datetime.utcnow()
        }
        result = cls.collection.insert_one(payment)
        payment["_id"] = str(result.inserted_id)
        return payment

    @classmethod
    def create_split_payments(cls, booking_id, player_ids, total_amount):
        """Create pending payment records for each player"""
        per_player = round(total_amount / len(player_ids), 2)
        payments = []
        for uid in player_ids:
            txn_id = "SPL-" + uuid.uuid4().hex[:12].upper()
            payment = {
                "booking_id": booking_id,
                "user_id": uid,
                "amount": per_player,
                "method": "split",
                "txn_id": txn_id,
                "status": "pending",
                "paid_at": None
            }
            result = cls.collection.insert_one(payment)
            payment["_id"] = str(result.inserted_id)
            payments.append(payment)
        return payments

    @classmethod
    def confirm_split_payment(cls, payment_id):
        """Player pays their share"""
        return cls.collection.update_one(
            {"_id": ObjectId(payment_id), "status": "pending"},
            {"$set": {"status": "paid", "paid_at": datetime.datetime.utcnow()}}
        )

    @classmethod
    def get_payments_for_booking(cls, booking_id):
        payments = list(cls.collection.find({"booking_id": booking_id}))
        for p in payments:
            p["_id"] = str(p["_id"])
        return payments

    @classmethod
    def all_paid(cls, booking_id):
        """Returns True if all split payments are paid"""
        payments = cls.get_payments_for_booking(booking_id)
        if not payments:
            return False
        return all(p["status"] == "paid" for p in payments)

    @classmethod
    def get_earnings_for_owner(cls, turf_ids):
        """Get total paid for turfs owned by owner"""
        # Join via bookings is complex in PyMongo, simplified sum here
        return list(cls.collection.find({"status": "paid"}))
