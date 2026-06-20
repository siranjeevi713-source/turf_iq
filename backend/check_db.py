import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config.db import db
from bson import ObjectId

def check_db():
    print('Turfs:', db.turfs.count_documents({}))
    # Find test owner
    owner = db.users.find_one({"phone": "8888888888"})
    if not owner:
        print("Owner not found!")
    else:
        owner_id = str(owner["_id"])
        print('Owner ID:', owner_id)
        turfs = list(db.turfs.find({"owner_id": owner_id}))
        print('Owner Turfs count:', len(turfs))
        if turfs:
            print("First turf ID:", turfs[0]["_id"])
        else:
            print("No turfs for this owner.")
            
    print('Bookings:', db.bookings.count_documents({}))
    print('Reviews:', db.reviews.count_documents({}))
    print('Notifs:', db.notifications.count_documents({}))

if __name__ == "__main__":
    check_db()
