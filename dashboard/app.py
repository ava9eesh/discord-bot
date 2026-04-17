from flask import Flask, app, redirect, request, session, url_for, render_template
import requests
import os
from dotenv import load_dotenv

from pathlib import Path
load_dotenv(dotenv_path=Path("../.env"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
app.secret_key = "supersecretkey"

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

DISCORD_API = "https://discord.com/api"

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

    return render_template("dashboard.html", user=user, guilds=guilds)

if __name__ == "__main__":
    app.run(debug=True)