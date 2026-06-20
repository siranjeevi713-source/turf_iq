from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
import os, datetime, atexit

from config.db import db

import os
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend'))
app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

if db is not None:
    print("Database is ready")
    try:
        from seed.seed_data import init_seed
        init_seed()
    except Exception as e:
        print(f"Error running seed data on startup: {e}")

@app.route("/", methods=["GET"])
def home():
    return send_from_directory(frontend_dir, "index.html")

@app.route("/<path:path>", methods=["GET"])
def serve_frontend(path):
    return send_from_directory(frontend_dir, path)

# ── Blueprints ──────────────────────────────────────────────────────────────
from routes.auth_routes import auth_bp
from routes.turf_routes import turf_bp
from controllers.booking_controller import booking_bp
from controllers.team_controller import team_bp
from controllers.slot_controller import slot_bp
from controllers.payment_controller import payment_bp
from controllers.notification_controller import notification_bp
from controllers.review_controller import review_bp
from controllers.message_controller import message_bp
from models.message_model import MessageModel
from models.notification_model import NotificationModel

app.register_blueprint(auth_bp,          url_prefix="/api/auth")
app.register_blueprint(turf_bp,          url_prefix="/api/turfs")
app.register_blueprint(booking_bp,       url_prefix="/api/bookings")
app.register_blueprint(team_bp,          url_prefix="/api/teams")
app.register_blueprint(slot_bp,          url_prefix="/api/slots")
app.register_blueprint(payment_bp,       url_prefix="/api/payments")
app.register_blueprint(notification_bp,  url_prefix="/api/notifications")
app.register_blueprint(review_bp,        url_prefix="/api/reviews")
app.register_blueprint(message_bp,       url_prefix="/api/messages")

# Ensure DB indexes
from models.slot_model import SlotModel
from models.payment_model import PaymentModel
SlotModel.ensure_indexes()
PaymentModel.ensure_indexes()

# ── Socket.io ───────────────────────────────────────────────────────────────
from flask_socketio import emit, join_room, leave_room

@socketio.on("join")
def on_join(data):
    """Join a generic or team room"""
    room = data.get("room")
    join_room(room)
    past = MessageModel.get_room_messages(room)
    emit("load_history", past)
    emit("message", {"text": f"{data.get('name')} joined.", "system": True}, to=room)

@socketio.on("join_team_room")
def join_team_room(data):
    """Player joins their team chat room – team_<id>"""
    team_id = data.get("team_id")
    user_id = data.get("user_id")
    user_name = data.get("name", "Player")
    room = f"team_{team_id}"
    join_room(room)
    # Load history and send only to this socket
    past = MessageModel.get_room_messages(room)
    emit("load_history", past)
    emit("message", {"text": f"{user_name} joined the chat.", "system": True}, to=room)

@socketio.on("sendMessage")
def handle_message(data):
    room     = data.get("room")
    user_id  = data.get("user_id")
    name     = data.get("name")
    msg_text = data.get("msg")
    MessageModel.save_message(room, user_id, name, msg_text)
    emit("message", {
        "text":      msg_text,
        "user":      name,
        "user_id":   user_id,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }, to=room)

@socketio.on("join_user_room")
def join_user_room(data):
    """Personal room for SocketIO push notifications"""
    join_room(f"user_{data.get('user_id')}")

@socketio.on("typing")
def handle_typing(data):
    room = data.get("room")
    emit("typing", {"name": data.get("name")}, to=room, include_self=False)

@socketio.on("stop_typing")
def handle_stop_typing(data):
    room = data.get("room")
    emit("stop_typing", {"name": data.get("name")}, to=room, include_self=False)

@socketio.on("payment_update")
def payment_update(data):
    """Broadcast payment status to team room"""
    team_id = data.get("team_id")
    if team_id:
        emit("payment_update", data, to=f"team_{team_id}")

# ── APScheduler: Match Reminders ────────────────────────────────────────────
from apscheduler.schedulers.background import BackgroundScheduler
import bson

def check_upcoming_matches():
    if db is None:
        return
    now = datetime.datetime.utcnow()
    thresholds = [
        (datetime.timedelta(days=1),     "1 day before",  "reminder_1d"),
        (datetime.timedelta(hours=2),    "2 hours before","reminder_2h"),
        (datetime.timedelta(minutes=30), "30 min before", "reminder_30m"),
    ]
    bookings = list(db["bookings"].find({"status": "Confirmed"}))
    for booking in bookings:
        date_str  = booking.get("date")
        slot_hour = 12
        if booking.get("slot_id"):
            try:
                slot = db["slots"].find_one({"_id": bson.ObjectId(booking["slot_id"])})
                if slot:
                    slot_hour = slot.get("hour_slot", 12)
            except Exception:
                pass
        if not date_str:
            continue
        try:
            match_dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(hour=slot_hour)
        except Exception:
            continue
        for delta, label, notif_type in thresholds:
            window_start = match_dt - delta
            window_end   = window_start + datetime.timedelta(minutes=1)
            if window_start <= now <= window_end:
                existing = db["notifications"].find_one({
                    "booking_id": str(booking["_id"]), "type": notif_type
                })
                if not existing:
                    user_id = booking.get("user_id")
                    payload = {
                        "message": f"⏰ Reminder ({label}): Your match is coming up!",
                        "booking_id": str(booking["_id"]),
                        "date": date_str, "slot_hour": slot_hour
                    }
                    notif = NotificationModel.create(user_id, notif_type, payload)
                    db["notifications"].update_one(
                        {"_id": bson.ObjectId(notif["_id"])},
                        {"$set": {"booking_id": str(booking["_id"])}}
                    )
                    socketio.emit("notification", notif, to=f"user_{user_id}")
                    print(f"[Scheduler] Sent {notif_type} to user {user_id}")

def simulate_platform_activity():
    if db is None: return
    try:
        import random
        # 1. Simulate players organically joining existing teams
        teams = list(db["teams"].find({"status": "Looking for players"}))
        if teams:
            team = random.choice(teams)
            users_list = list(db["users"].find({"role": "User", "_id": {"$nin": [bson.ObjectId(pid) for pid in team.get("players", [])]}}))
            if users_list:
                user_to_add = random.choice(users_list)
                db["teams"].update_one(
                    {"_id": team["_id"]},
                    {"$push": {"players": str(user_to_add["_id"])}, "$inc": {"current_players_count": 1}}
                )
                socketio.emit("team_update", {"message": "New player joined a team!"})

        # 2. Simulate random slots being booked or cancelled
        now = datetime.datetime.now(datetime.UTC)
        recent_slots = list(db["slots"].find({"date": {"$gt": now.strftime("%Y-%m-%d")}}).limit(100))
        if recent_slots:
            # Change 3-5 random slots
            for _ in range(random.randint(3, 5)):
                tgt = random.choice(recent_slots)
                new_status = "booked" if tgt["status"] == "available" else "available"
                db["slots"].update_one({"_id": tgt["_id"]}, {"$set": {"status": new_status, "locked_until": None}})
            socketio.emit("slot_update", {"message": "Slots shifting dynamically"})
            
        print("[Scheduler] Dynamic Platform Activity Simulated 🔥")
    except Exception as e:
        print(f"[Scheduler] Activity sim error: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(func=check_upcoming_matches, trigger="interval", minutes=1)
scheduler.add_job(func=simulate_platform_activity, trigger="interval", minutes=3)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    import webbrowser
    import threading
    port = int(os.environ.get("PORT", 5000))
    print("\n>>> TURFFIQ SERVER RUNNING <<<")
    print(f"URL: http://localhost:{port}\n")
    
    def open_browser():
        webbrowser.open(f"http://localhost:{port}")
    threading.Timer(1.5, open_browser).start()
    
    socketio.run(app, host="0.0.0.0", port=port, debug=True, allow_unsafe_werkzeug=True)
