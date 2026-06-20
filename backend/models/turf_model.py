from config.db import db
from bson import ObjectId

class TurfModel:
    collection = db["turfs"] if db is not None else None

    @classmethod
    def create_turf(cls, turf_data):
        return cls.collection.insert_one(turf_data)

    @classmethod
    def get_all_turfs(cls):
        turfs = list(cls.collection.find())
        for turf in turfs:
            turf["_id"] = str(turf["_id"])
        return turfs

    @classmethod
    def get_turf_by_id(cls, turf_id):
        turf = cls.collection.find_one({"_id": ObjectId(turf_id)})
        if turf:
            turf["_id"] = str(turf["_id"])
        return turf
        
    @classmethod
    def update_turf(cls, turf_id, update_data):
        return cls.collection.update_one({"_id": ObjectId(turf_id)}, {"$set": update_data})

    @classmethod
    def get_turfs_by_location(cls, location):
        turfs = list(cls.collection.find({"location": {"$regex": location, "$options": "i"}}))
        for turf in turfs:
            turf["_id"] = str(turf["_id"])
        return turfs

    @classmethod
    def generate_virtual_turfs(cls, location):
        import random
        # Create virtual turfs assigned to the Super Owner (or random native owner)
        owner = db["users"].find_one({"role": "Turf Owner"})
        owner_id = str(owner["_id"]) if owner else "virtual_owner"
        
        virtual_names = [f"{location} Turf Arena", f"City Sports Ground {location}"]
        for name in virtual_names:
            turf_data = {
                "turf_name": name,
                "owner_id": owner_id,
                "location": f"Central {location}",
                "phone": "9999999999",
                "lat": str(random.uniform(10.0, 13.0)),
                "lng": str(random.uniform(77.0, 80.0)),
                "photos": [f"https://source.unsplash.com/800x600/?football,stadium,sports&sig={random.randint(1,1000)}"],
                "services": ["Parking", "Restroom", "Floodlights"],
                "price_per_hour": random.choice([500, 800, 1000]),
                "is_virtual": True
            }
            cls.create_turf(turf_data)
