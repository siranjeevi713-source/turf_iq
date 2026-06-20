from config.db import db
from bson import ObjectId
import datetime
import random

class SlotModel:
    collection = db["slots"] if db is not None else None

    @classmethod
    def ensure_indexes(cls):
        try:
            cls.collection.create_index(
                [("turf_id", 1), ("date", 1), ("hour_slot", 1)],
                unique=True,
                name="unique_turf_date_slot"
            )
        except Exception as e:
            print(f"[SlotModel] Index error: {e}")

    @classmethod
    def create_slots_for_day(cls, turf_id, date, price_per_slot=500):
        """Generate 6AM-11PM hourly slots for a date (Demo Engine weights)"""
        created = []
        for hour in range(6, 23):
            if 18 <= hour <= 22:
                status = random.choices(["booked", "blocked", "available"], weights=[0.80, 0.10, 0.10])[0]
            else:
                status = random.choices(["booked", "blocked", "available"], weights=[0.40, 0.30, 0.30])[0]
                
            slot = {
                "turf_id": turf_id,
                "date": date,
                "hour_slot": hour,
                "label": f"{hour:02d}:00 - {hour+1:02d}:00",
                "status": status,
                "price": price_per_slot,
                "booked_by_team": None,
                "booked_by_booking": None,
                "created_at": datetime.datetime.utcnow()
            }
            try:
                result = cls.collection.insert_one(slot)
                slot["_id"] = str(result.inserted_id)
                created.append(slot)
            except Exception:
                pass  # Skip duplicates (unique index)
        return created

    @classmethod
    def get_available_slots(cls, turf_id, date, target_hour=None):
        now = datetime.datetime.now(datetime.UTC)
        
        # DEMO MODE: Check if slots physically exist for this query. If not, autospawn them!
        total_slots_for_day = cls.collection.count_documents({"turf_id": turf_id, "date": date})
        if total_slots_for_day == 0:
            cls.create_slots_for_day(turf_id, date)

        query = {
            "turf_id": turf_id,
            "date": date,
            "status": "available",
            "$or": [
                {"locked_until": {"$exists": False}},
                {"locked_until": {"$lt": now}}
            ]
        }


        slots = list(cls.collection.find(query).sort("hour_slot", 1))
        
        # DEMO GUARANTEE: Always ensure at least 2 slots are available
        if len(slots) < 2:
            # Find blocked/booked ones and flip a few to available
            all_day = list(cls.collection.find({"turf_id": turf_id, "date": date}))
            non_avail = [s for s in all_day if s["status"] != "available"]
            random.shuffle(non_avail)
            to_unlock = non_avail[:max(0, 2 - len(slots))]
            for s in to_unlock:
                cls.collection.update_one({"_id": s["_id"]}, {"$set": {"status": "available", "locked_until": None}})
            # Re-query slots after unlocking
            slots = list(cls.collection.find(query).sort("hour_slot", 1))

        # Scarcity + Nearest proximity Engine
        if len(slots) > 0:
            if target_hour is not None:
                # Prioritize those closest to target hour
                slots.sort(key=lambda x: abs(x["hour_slot"] - target_hour))
                num_to_show = min(len(slots), random.randint(2, 5))
                slots = slots[:num_to_show]
                # Sort chronologically again for final UI
                slots.sort(key=lambda x: x["hour_slot"])
                
                # Add label to the absolute closest one if it's within 2 hours
                for s in slots:
                    if abs(s["hour_slot"] - target_hour) <= 2:
                        s["proximity_label"] = "Best Match 🎯"
                        break
            else:
                random.shuffle(slots)
                num_to_show = min(len(slots), random.randint(2, 5))
                slots = sorted(slots[:num_to_show], key=lambda x: x["hour_slot"])
        else:
            return []
            
        for s in slots:
            s["_id"] = str(s["_id"])
        return slots

    @classmethod
    def get_fallback_suggestions(cls, turf_id, date, target_hour):
        """Cross-turf search when original turf is fully booked"""
        turf = db["turfs"].find_one({"_id": ObjectId(turf_id)})
        if not turf: return []
        
        city = turf.get("location", "").split()[-1] # Extract 'Chennai' from 'North Chennai'
        # Find other turfs in the same city
        other_turfs = list(db["turfs"].find({
            "_id": {"$ne": ObjectId(turf_id)},
            "location": {"$regex": city, "$options": "i"}
        }))
        if not other_turfs: return []
        
        other_turf_ids = [str(x["_id"]) for x in other_turfs]
        
        # Now find available slots in those turfs on the same date
        now = datetime.datetime.now(datetime.UTC)
        query = {
            "turf_id": {"$in": other_turf_ids},
            "date": date,
            "status": "available",
            "$or": [
                {"locked_until": {"$exists": False}}, {"locked_until": {"$lt": now}}
            ]
        }
        if date == now.strftime("%Y-%m-%d"):
            query["hour_slot"] = {"$gt": now.hour}
            
        # Get exactly matching or +-1 hour slots
        all_alts = list(cls.collection.find(query))
        alts = [s for s in all_alts if abs(s["hour_slot"] - target_hour) <= 1]
        
        # If none perfectly close, loosen bounds
        if not alts:
            alts = [s for s in all_alts if abs(s["hour_slot"] - target_hour) <= 3]
            
        # Format response natively for frontend
        alts.sort(key=lambda x: abs(x["hour_slot"] - target_hour))
        best_alts = alts[:3] # Show max 3 alternatives
        
        results = []
        for s in best_alts:
            t = next((turf for turf in other_turfs if str(turf["_id"]) == s["turf_id"]), None)
            if t:
                s["_id"] = str(s["_id"])
                s["turf_name"] = t["turf_name"]
                s["turf_location"] = t["location"]
                s["turf_lat"] = t.get("lat")
                s["turf_lng"] = t.get("lng")
                s["proximity_label"] = "Nearby Fallback 🔥"
                results.append(s)
        return results

    @classmethod
    def get_slots_by_turf_date(cls, turf_id, date):
        """Returns ALL slots (available, booked, blocked) for owner dashboard view.
        Auto-generates slots if none exist for the given date."""
        
        # Auto-generate if no slots exist for this turf+date
        total = cls.collection.count_documents({"turf_id": turf_id, "date": date})
        if total == 0:
            # Fetch turf price to use for slot generation
            turf = db["turfs"].find_one({"_id": ObjectId(turf_id)})
            price = turf.get("price_per_hour", 500) if turf else 500
            cls.create_slots_for_day(turf_id, date, price)
        
        slots = list(cls.collection.find({
            "turf_id": turf_id,
            "date": date
        }).sort("hour_slot", 1))
        
        now = datetime.datetime.now(datetime.UTC)
        for s in slots:
            s["_id"] = str(s["_id"])
            # If dynamically locked right now, show as locked for display
            if s.get("status") == "available" and s.get("locked_until") and s["locked_until"] > now:
                s["display_status"] = "locked"
                s["label"] += " (Locked)"
            else:
                s["display_status"] = s["status"]
                
        return slots

    @classmethod
    def lock_slot(cls, slot_id, minutes=3):
        now = datetime.datetime.now(datetime.UTC)
        expiry = now + datetime.timedelta(minutes=minutes)
        
        # Only allow locking if status is available and not currently locked
        result = cls.collection.update_one(
            {"_id": ObjectId(slot_id), "status": "available", 
             "$or": [{"locked_until": {"$exists": False}}, {"locked_until": {"$lt": now}}]},
            {"$set": {"locked_until": expiry}}
        )
        return result.modified_count > 0

    @classmethod
    def book_slot(cls, slot_id, team_id, booking_id):
        result = cls.collection.update_one(
            {"_id": ObjectId(slot_id), "status": "available"},
            {"$set": {
                "status": "booked",
                "booked_by_team": team_id,
                "booked_by_booking": booking_id
            }}
        )
        return result.modified_count > 0

    @classmethod
    def update_slot_status(cls, slot_id, status):
        return cls.collection.update_one(
            {"_id": ObjectId(slot_id)},
            {"$set": {"status": status}}
        )

    @classmethod
    def update_slot_price(cls, slot_id, price):
        return cls.collection.update_one(
            {"_id": ObjectId(slot_id)},
            {"$set": {"price": price}}
        )

    @classmethod
    def get_by_id(cls, slot_id):
        slot = cls.collection.find_one({"_id": ObjectId(slot_id)})
        if slot:
            slot["_id"] = str(slot["_id"])
        return slot
