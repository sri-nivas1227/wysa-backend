# Start a Flask app

from flask import Flask, request, jsonify
from flask_pymongo import pymongo
from dotenv import load_dotenv
import os
from password import hash_password, verify_password
import jwt
from datetime import datetime, timedelta

load_dotenv()

uri = os.getenv("MONGO_CONNECTION_STRING")
# Create a new client and connect to the server
client = pymongo.MongoClient(uri)
# Send a ping to confirm a successful connection
try:
    client.admin.command("ping")
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

sleep_db = client.sleep_db
sleep_assessment_collection = sleep_db.sleep_assessment_collection
user_collection = sleep_db.user_collection
sleep_assessment_collection.create_index("username", unique=True)
user_collection.create_index("username", unique=True)
app = Flask(__name__)


@app.route("/")
def hello_world():
    return "Hello World!"


# Maintaining a Score field considering a scale of 10 and rating the health based on responses


@app.route("/api/v1/user/login", methods=["POST"])
def login():
    data = request.json
    username = data["username"].lower()
    password = data["password"]
    user = user_collection.find_one({"username": username})
    if user is not None:
        is_valid_password = verify_password(
            password, user["salt"], user["hashed_password"]
        )
        if is_valid_password:
            payload = {
                "username": username,
                # "exp" : 3600
            }
            token = jwt.encode(payload, os.getenv("SECRET_KEY"), algorithm="HS256")
            return jsonify({"status": "success", "token": token}), 200
        else:
            return jsonify({"status": "error", "message": "Invalid password"}), 401

    else:
        salt, hashed_password = hash_password(password)
        user_status = user_collection.insert_one(
            {"username": username, "salt": salt, "hashed_password": hashed_password}
        )
        if user_status.acknowledged:
            payload = {
                "username": username,
                # "exp" : 3600/
            }
            token = jwt.encode(payload, os.getenv("SECRET_KEY"), algorithm="HS256")
            return jsonify({"status": "success", "token": token}), 201


@app.route("/api/v1/sleep/assessment/struggle-period", methods=["POST"])
def struggle_period():
    auth_header = request.headers.get("Authorization")
    if auth_header:
        token = auth_header.split(" ")[1]
        try:
            try:
                payload = jwt.decode(
                    token, os.getenv("SECRET_KEY"), algorithms=["HS256"]
                )
            except Exception as e:
                return jsonify({"status": "error", "message": "Invalid token"}), 401
            print(payload)
            username = payload["username"]
            data = request.json
            sleep_struggle_period = data["sleep_struggle_period"]
            if sleep_struggle_period == "<2":
                score = 10
            elif sleep_struggle_period == "2-8":
                score = 6
            elif sleep_struggle_period == ">8":
                score = 2
            sleep_assessment_collection.insert_one(
                {
                    "username": username,
                    "sleep_struggle_period": sleep_struggle_period,
                    "score": score,
                }
            )
            return jsonify({"status": "success"}), 200
        except Exception as e:
            print(e)
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "An unexpected error occurred on the server side",
                    }
                ),
                500,
            )


@app.route("/api/v1/sleep/assessment/sleeping-time", methods=["POST"])
def handle_sleep_time():
    auth_header = request.headers.get("Authorization")
    if auth_header:
        token = auth_header.split(" ")[1]
        try:
            try:
                payload = jwt.decode(
                    token, os.getenv("SECRET_KEY"), algorithms=["HS256"]
                )
            except Exception as e:
                return jsonify({"message": "Invalid token", "status": "error"}), 401
            username = payload["username"]
            data = request.json
            sleeping_time = data["sleeping-time"]
            sleep_assessment_collection.update_one(
                {"username": username}, {"$set": {"sleeping_time": sleeping_time}}
            )
            # Let's consider the average sleeping hours of a person to be 7 hours
            # then we can send an estimated waking time
            sleeping_time_date_obj = datetime.strptime(sleeping_time, "%H:%M")
            waking_time_obj = sleeping_time_date_obj + timedelta(hours=7)
            waking_time = waking_time_obj.strftime("%H:%M")
            return (
                jsonify({"status": "success", "estimated_waking_time": waking_time}),
                200,
            )
        except Exception as e:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "An unexpected error occurred on the server side",
                    }
                ),
                500,
            )


@app.route("/api/v1/sleep/assessment/waking-time", methods=["POST"])
def handle_waking_time():
    auth_header = request.headers.get("Authorization")
    if auth_header:
        token = auth_header.split(" ")[1]
        try:
            try:
                payload = jwt.decode(
                    token, os.getenv("SECRET_KEY"), algorithms=["HS256"]
                )
            except Exception as e:
                return jsonify({"message": "Invalid token", "status": "error"}), 401
            username = payload["username"]
            data = request.json
            waking_time = data["waking-time"]
            # sleep_assessment_collection.insert_one({"username" : username, "waking_time" : waking_time})
            sleep_assessment_collection.update_one(
                {"username": username}, {"$set": {"waking_time": waking_time}}
            )
            user = sleep_assessment_collection.find_one({"username": username})
            sleeping_time = user["sleeping_time"]
            # estimating sleep hours
            sleeping_time_obj = datetime.strptime(sleeping_time, "%H:%M")
            waking_time_obj = datetime.strptime(waking_time, "%H:%M")
            sleep_hours = int((waking_time_obj - sleeping_time_obj).seconds / 3600)
            return (
                jsonify({"status": "success", "estimated_sleep_hours": sleep_hours}),
                200,
            )
        except Exception as e:
            print(e)
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "An unexpected error occurred on the server side",
                    }
                ),
                500,
            )


@app.route("/api/v1/sleep/assessment/sleep-hours", methods=["POST"])
def handle_sleep_hours():
    auth_header = request.headers.get("Authorization")
    if auth_header:
        token = auth_header.split(" ")[1]
        try:
            try:
                payload = jwt.decode(
                    token, os.getenv("SECRET_KEY"), algorithms=["HS256"]
                )
            except Exception as e:
                return jsonify({"message": "Invalid token", "status": "error"}), 401
            username = payload["username"]
            data = request.json
            sleep_hours = int(data["sleep-hours"])
            score = 0
            if sleep_hours < 6:
                score = 4
            elif sleep_hours < 8:
                score = 9
            elif sleep_hours > 8:
                score = 3
            db_score = sleep_assessment_collection.find_one({"username": username})[
                "score"
            ]
            avg_score = int((db_score + score) / 2)
            sleep_assessment_collection.update_one(
                {"username": username},
                {"$set": {"sleep_hours": sleep_hours, "score": avg_score}},
            )
            return jsonify({"status": "success", "score": avg_score}), 200
        except Exception as e:
            print(e)
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "An unexpected error occurred on the server side",
                    }
                ),
                500,
            )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
