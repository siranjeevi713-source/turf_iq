import datetime
import random
import bcrypt
import traceback
from bson import ObjectId
import json
import logging

try:
    from config.db import db
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.db import db
    
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SeedData")

# Constants
CITIES = ["Chennai", "Coimbatore", "Madurai", "Trichy", "Salem", "Erode", "Tirunelveli"]
SPORTS = ["Football", "Cricket", "Basketball", "Tennis", "Badminton"]
LEVELS = ["Beginner", "Intermediate", "Advanced"]
GENDERS = ["Male", "Female"]

TAMIL_NAMES_FIRST = ["Aarav", "Arjun", "Aditya", "Sai", "Krishna", "Karthik", "Ravi", "Surya", "Rahul", "Vijay", "Ajith", "Dhanush", "Sanjay", "Vikram", "Siva", "Ashwin", "Vishal", "Gautham", "Pooja", "Priya", "Sneha", "Divya", "Swathi", "Aishwarya", "Shruti", "Anjali", "Kavya", "Keerthi", "Nithya", "Ramya"]
TAMIL_NAMES_LAST = ["Kumar", "Raj", "Rao", "Prasad", "Swamy", "Nair", "Iyer", "Pillai", "Menon", "Reddy", "Krishnan", "Rajan", "Srinivasan", "Venkatesh", "Ram", "Subramaniam"]

def generate_phone():
    return str(random.randint(9000000000, 9999999999))

def hash_pw(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def generate_users(count=100):
    users = []
    default_pw = hash_pw("password123")
    
    for _ in range(count):
        fname = random.choice(TAMIL_NAMES_FIRST)
        lname = random.choice(TAMIL_NAMES_LAST)
        is_owner = random.random() < 0.1 
        role = "Turf Owner" if is_owner else "User"
        
        user = {
            "name": f"{fname} {lname}",
            "age": random.randint(18, 45),
            "gender": random.choice(GENDERS),
            "phone": generate_phone(),
            "password": default_pw,
            "role": role,
            "sports_interest": random.sample(SPORTS, k=random.randint(1, 3)) if role == "User" else [],
            "player_level": random.choice(LEVELS) if role == "User" else "Beginner",
            "location": random.choice(CITIES),
            "matches_played": random.randint(0, 50) if role == "User" else 0,
            "wins": random.randint(0, 20) if role == "User" else 0,
            "rating": round(random.uniform(3.5, 5.0), 1) if role == "User" else 0,
            "points": random.randint(0, 1000) if role == "User" else 0,
            "badges": []
        }
        users.append(user)
    return users

class SeedData:
    def __init__(self):
        pass
        
    def seed_all(self):
        try:
            if db.users.count_documents({}) > 0:
                logger.info("Database already seeded with users. Skipping.")
                return False
                
            logger.info("Initializing Seed Script for TURFFIQ...")
            
            # Create Users
            users_data = generate_users(200)
            # Add default accounts for testing:
            users_data.append({
                "name": "Admin Player", "age": 25, "gender": "Male", "phone": "9999999999", 
                "password": hash_pw("password123"), "role": "User", "sports_interest": ["Football"], 
                "player_level": "Advanced", "location": "Chennai", "matches_played": 10, "wins": 8, "rating": 4.8, "points": 500, "badges": []
            })
            users_data.append({
                "name": "Super Owner", "age": 40, "gender": "Male", "phone": "8888888888", 
                "password": hash_pw("password123"), "role": "Turf Owner", "sports_interest": [], 
                "player_level": "Beginner", "location": "Chennai", "matches_played": 0, "wins": 0, "rating": 0, "points": 0, "badges": []
            })
            
            inserted_users = db.users.insert_many(users_data)
            user_ids = [str(x) for x in inserted_users.inserted_ids]
            players = [u for u in db.users.find({"role": "User"})]
            owners = [o for o in db.users.find({"role": "Turf Owner"})]
            
            logger.info(f"Created {len(users_data)} users.")
            
            # Create Turfs
            cities_dist = {"Chennai": 15, "Coimbatore": 8, "Madurai": 6, "Trichy": 5, "Salem": 4, "Erode": 3, "Tirunelveli": 3} # ~44 Turfs
            turfs_data = []
            owner_index = 0
            
            TURF_NAMES = ["Arena", "Sports Hub", "Ground", "FC", "Kicks", "Field", "Court", "Turf", "Zone", "Park"]
            
            for city, num_turfs in cities_dist.items():
                for i in range(num_turfs):
                    owner = owners[owner_index % len(owners)]
                    owner_index += 1
                    t_name = f"{city} {random.choice(TAMIL_NAMES_FIRST)} {random.choice(TURF_NAMES)}"
                    
                    turf = {
                        "turf_name": t_name,
                        "owner_id": str(owner["_id"]),
                        "location": f"{random.choice(['North', 'South', 'East', 'West', 'Central'])} {city}",
                        "phone": owner["phone"],
                        "lat": str(random.uniform(10.0, 13.0)), 
                        "lng": str(random.uniform(77.0, 80.0)),
                        "photos": [f"https://source.unsplash.com/800x600/?football,stadium,sports&sig={random.randint(1,1000)}"],
                        "services": random.sample(["Parking", "Restroom", "Drinking Water", "Floodlights", "Equipment", "Cafeteria", "Locker Room"], k=random.randint(3, 7)),
                        "price_per_hour": random.choice([500, 600, 800, 1000, 1200, 1500])
                    }
                    turfs_data.append(turf)
                    
            inserted_turfs = db.turfs.insert_many(turfs_data)
            turf_ids = [str(x) for x in inserted_turfs.inserted_ids]
            
            logger.info(f"Created {len(turfs_data)} turfs.")
            
            # Create Slots for the next 7 days
            logger.info("Creating slots...")
            slots_data = []
            today = datetime.datetime.utcnow().date()
            
            for turf in db.turfs.find():
                for day_offset in range(7):
                    slot_date = (today + datetime.timedelta(days=day_offset)).strftime("%Y-%m-%d")
                    for hour in range(6, 23):
                        # Smart Scarcity: High demand at peak hours
                        # Peak hours: 6 PM (18) to 10 PM (22)
                        # Off-peak: 6 AM to 5 PM
                        if 18 <= hour <= 22:
                            # 80% booked, 10% blocked, 10% available
                            status = random.choices(["booked", "blocked", "available"], weights=[0.80, 0.10, 0.10])[0]
                        else:
                            # Day time: 40% booked, 30% blocked, 30% available
                            status = random.choices(["booked", "blocked", "available"], weights=[0.40, 0.30, 0.30])[0]

                        slots_data.append({
                            "turf_id": str(turf["_id"]),
                            "date": slot_date,
                            "hour_slot": hour,
                            "label": f"{hour:02d}:00 - {hour+1:02d}:00",
                            "status": status,
                            "price": turf["price_per_hour"],
                            "booked_by_team": None,
                            "booked_by_booking": None,
                            "created_at": datetime.datetime.utcnow()
                        })
            
            db.slots.insert_many(slots_data)
            logger.info(f"Created {len(slots_data)} slots.")
            
            # Create Teams
            logger.info("Creating teams...")
            teams_data = []
            # We want around 30 teams
            for _ in range(35):
                team_creator = random.choice(players)
                req_players = random.randint(5, 15)
                # Ensure the creator is in the team
                team_players = [str(team_creator["_id"])] 
                # Add random existing players (simulate joining)
                num_to_add = random.randint(0, req_players - 1)
                available_players = [str(p["_id"]) for p in players if str(p["_id"]) != str(team_creator["_id"])]
                random.shuffle(available_players)
                team_players.extend(available_players[:num_to_add])
                
                t_date = (today + datetime.timedelta(days=random.randint(0, 5))).strftime("%Y-%m-%d")
                t_time = f"{random.randint(6, 21):02d}:00"
                
                teams_data.append({
                    "team_name": f"{random.choice(TAMIL_NAMES_FIRST)} {random.choice(['Strikers', 'Riders', 'Blasters', 'Warriors', 'Knights', 'Kings'])}",
                    "sport": random.choice(SPORTS),
                    "location": random.choice(CITIES),
                    "date_time": f"{t_date}T{t_time}",
                    "required_players": req_players,
                    "current_players_count": len(team_players),
                    "players": team_players,
                    "creator_id": str(team_creator["_id"]),
                    "turf_id": None, 
                    "slot_id": None,
                    "status": "Looking for players" if len(team_players) < req_players else "Full"
                })
            
            inserted_teams = db.teams.insert_many(teams_data)
            logger.info(f"Created {len(teams_data)} teams.")
            
            # Create Bookings and Payments
            logger.info("Creating bookings and payments...")
            bookings_data = []
            payments_data = []
            messages_data = []
            notifications_data = []
            
            # Select some teams to have active bookings
            turf_docs = list(db.turfs.find())
            team_docs = list(db.teams.find({"current_players_count": {"$gt": 1}}))
            random.shuffle(team_docs)
            
            # 15 teams will have booked a turf
            for team in team_docs[:15]:
                turf = random.choice(turf_docs)
                
                # Extract date from team date_time
                date_str = team["date_time"].split("T")[0]
                hour_val = int(team["date_time"].split("T")[1].split(":")[0])
                
                # Find available slot
                slot = db.slots.find_one({"turf_id": str(turf["_id"]), "date": date_str, "hour_slot": hour_val, "status": "available"})
                if not slot:
                    # Just grab any available slot for this turf on this date
                    slot = db.slots.find_one({"turf_id": str(turf["_id"]), "date": date_str, "status": "available"})
                
                if slot:
                    services = random.sample(turf.get("services", []), k=random.randint(0, min(3, len(turf.get("services", [])))))
                    total_cost = slot["price"] + sum([20 for s in services]) # simplified service cost
                    
                    booking_id = ObjectId()
                    payment_method = random.choice(["single", "split"])
                    
                    bookings_data.append({
                        "_id": booking_id,
                        "user_id": str(team["creator_id"]),
                        "team_id": str(team["_id"]),
                        "turf_id": str(turf["_id"]),
                        "slot_id": str(slot["_id"]),
                        "date": slot["date"],
                        "services": services,
                        "total_cost": total_cost,
                        "payment_method": payment_method,
                        "payment_status": "paid",
                        "status": "Confirmed",
                        "owner_status": "accepted",
                        "created_at": datetime.datetime.utcnow() - datetime.timedelta(hours=random.randint(1, 48))
                    })
                    
                    # Update slot
                    db.slots.update_one({"_id": slot["_id"]}, {"$set": {"status": "booked", "booked_by_team": str(team["_id"]), "booked_by_booking": str(booking_id)}})
                    
                    # Create payments
                    if payment_method == "single":
                        payments_data.append({
                            "booking_id": str(booking_id),
                            "user_id": str(team["creator_id"]),
                            "amount": total_cost,
                            "method": "single",
                            "txn_id": f"TXN-{random.randint(10000, 99999)}",
                            "status": "paid",
                            "paid_at": datetime.datetime.utcnow()
                        })
                    else: # Split
                        per_player = round(total_cost / len(team["players"]), 2)
                        for pid in team["players"]:
                            payments_data.append({
                                "booking_id": str(booking_id),
                                "user_id": pid,
                                "amount": per_player,
                                "method": "split",
                                "txn_id": f"SPL-{random.randint(10000, 99999)}",
                                "status": "paid",
                                "paid_at": datetime.datetime.utcnow()
                            })
                            
                    # Add team messages
                    for pid in team["players"][:3]:
                        player = db.users.find_one({"_id": ObjectId(pid)})
                        messages_data.append({
                            "room_id": f"team_{str(team['_id'])}",
                            "sender_id": pid,
                            "sender_name": player["name"] if player else "Player",
                            "text": random.choice(["Hey guys! Ready for the match?", "Booked the turf, make sure to pay.", "I'll bring the water.", "Let's win this!", "See you all there."]),
                            "timestamp": datetime.datetime.utcnow() - datetime.timedelta(minutes=random.randint(1, 60))
                        })

            if bookings_data:
                db.bookings.insert_many(bookings_data)
                db.payments.insert_many(payments_data)
                
            if messages_data:
                db.messages.insert_many(messages_data)
             
            # Create some reviews
            logger.info("Creating reviews...")
            reviews_data = []
            for turf in db.turfs.find():
                for _ in range(random.randint(1, 5)):
                    reviewer = random.choice(players)
                    reviews_data.append({
                        "turf_id": str(turf["_id"]),
                        "user_id": str(reviewer["_id"]),
                        "user_name": reviewer["name"],
                        "rating": random.choice([4, 4.5, 5, 5, 5]),
                        "comment": random.choice(["Great turf!", "Loved the pitch.", "Nice floodlights.", "Good quality grass.", "Perfect location."]),
                        "created_at": datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(1, 30))
                    })
            if reviews_data:
                db.reviews.insert_many(reviews_data)
             
            logger.info("✅ Database seeded successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error during seeding: {e}")
            traceback.print_exc()
            return False

def init_seed():
    seeder = SeedData()
    return seeder.seed_all()

if __name__ == "__main__":
    init_seed()
