from flask import Flask, redirect, request, session, url_for, render_template
import requests
import os
from dotenv import load_dotenv

# Load env (Render uses its own env system, this still works locally)
load_dotenv()

app = Flask(__name__, template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

DISCORD_API = "https://discord.com/api"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login")
def login():
    if not CLIENT_ID or not REDIRECT_URI:
        return "Missing CLIENT_ID or REDIRECT_URI", 500

    return redirect(
        f"{DISCORD_API}/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds"
    )

@app.route("/callback")
def callback():
    code = request.args.get("code")

    if not code:
        return "No code provided", 400

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

    if r.status_code != 200:
        return f"Token error: {r.text}", 500

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

    return render_template("dashboard.html", user=user, guilds=guilds)