from flask import Flask, redirect, request, session, url_for, render_template
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

DISCORD_API = "https://discord.com/api"

def bot_in_guild(guild_id):
    url = f"{DISCORD_API}/guilds/{guild_id}/members/@me"
    headers = {"Authorization": f"Bot {BOT_TOKEN}"}
    r = requests.get(url, headers=headers)
    return r.status_code == 200

def load_data():
    try:
        with open("dashboard/data.json") as f:
            return json.load(f)
    except:
        return {}

def save_prefix(guild_id, prefix):
    data = load_data()
    data[guild_id] = prefix
    with open("dashboard/data.json", "w") as f:
        json.dump(data, f)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login")
def login():
    return redirect(
        f"{DISCORD_API}/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds"
    )

@app.route("/callback")
def callback():
    code = request.args.get("code")

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify guilds",
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(f"{DISCORD_API}/oauth2/token", data=data, headers=headers)

    token = r.json().get("access_token")
    session["token"] = token

    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    token = session.get("token")
    if not token:
        return redirect(url_for("login"))

    headers = {"Authorization": f"Bearer {token}"}

    user = requests.get(f"{DISCORD_API}/users/@me", headers=headers).json()
    guilds = requests.get(f"{DISCORD_API}/users/@me/guilds", headers=headers).json()

    managed = []
    invite = []

    for g in guilds:
        if bot_in_guild(g["id"]):
            managed.append(g)
        else:
            invite.append(g)

    return render_template("dashboard.html", user=user, managed=managed, invite=invite)

@app.route("/server/<guild_id>", methods=["GET", "POST"])
def server_panel(guild_id):
    if request.method == "POST":
        prefix = request.form.get("prefix")
        save_prefix(guild_id, prefix)

    data = load_data()
    current_prefix = data.get(guild_id, "!")

    return render_template("server.html", guild_id=guild_id, prefix=current_prefix)