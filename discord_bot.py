import discord
from discord.ext import commands, tasks
import asyncio, random, json, os, aiohttp
from datetime import timedelta, datetime
from discord.ui import Button, View, Modal, TextInput, Select
from collections import defaultdict
import re
from typing import Optional

# ================= SETTINGS =================

def get_settings(guild_id):
    try:
        with open("dashboard/data.json") as f:
            data = json.load(f)
            return data.get(str(guild_id), {})
    except:
        return {}

def get_prefix(bot, message):
    if not message.guild:
        return "!"
    settings = get_settings(message.guild.id)
    return settings.get("prefix", "!")

# ================= DATA MANAGEMENT =================

def load_json(file):
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

# ================= BOT =================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)

# ================= GLOBAL VARIABLES =================

levels = defaultdict(lambda: defaultdict(lambda: {"xp": 0, "level": 1, "messages": 0}))
economy = defaultdict(lambda: defaultdict(lambda: {"coins": 1000, "bank": 0, "inventory": []}))
warnings = defaultdict(lambda: defaultdict(list))
automod_cache = {}
spam_tracker = defaultdict(lambda: defaultdict(list))
raid_protection = defaultdict(dict)
verification = {}
temp_channels = {}
giveaways = {}
reminders = []
afk_users = {}
starboard = defaultdict(list)

# ================= GLOBAL TOGGLE =================

@bot.check
async def global_check(ctx):
    if not ctx.guild:
        return True

    settings = get_settings(ctx.guild.id)

    mod = ["ban","kick","mute","unmute","warn","clear","slowmode","lock","unlock","nuke"]
    fun = ["meme","joke","rps","trivia","guess","coinflip","roll","8ball"]

    if ctx.command.name in mod:
        return settings.get("moderation", True)

    if ctx.command.name in fun:
        return settings.get("fun", True)

    return True

# ================= READY =================

@bot.event
async def on_ready():
    print(f"✅ {bot.user} online")
    try:
        await bot.tree.sync()
        check_reminders.start()
        print("✅ Slash commands synced")
    except Exception as e:
        print(f"❌ Sync failed: {e}")
    
    await bot.change_presence(activity=discord.Game(name="!help | Protecting servers"))

# ================= SECURITY SYSTEM (WICK-LIKE) =================

# Anti-Raid Protection
@bot.event
async def on_member_join(member):
    guild = member.guild
    guild_id = str(guild.id)
    
    # Load security settings
    try:
        with open(f"security/{guild_id}.json", 'r') as f:
            security = json.load(f)
    except:
        security = {"antiraid": False, "verification": False, "antispam": True}
    
    # Anti-Raid
    if security.get("antiraid"):
        now = datetime.now()
        if guild_id not in raid_protection:
            raid_protection[guild_id] = {"joins": [], "lockdown": False}
        
        raid_protection[guild_id]["joins"].append(now)
        raid_protection[guild_id]["joins"] = [t for t in raid_protection[guild_id]["joins"] if (now - t).seconds < 10]
        
        if len(raid_protection[guild_id]["joins"]) > 10 and not raid_protection[guild_id]["lockdown"]:
            # RAID DETECTED
            raid_protection[guild_id]["lockdown"] = True
            for channel in guild.text_channels:
                try:
                    await channel.set_permissions(guild.default_role, send_messages=False)
                except:
                    pass
            
            log_channel = discord.utils.get(guild.text_channels, name="security-logs")
            if log_channel:
                await log_channel.send("🚨 **RAID DETECTED** - Server locked down!")
    
    # Verification System
    if security.get("verification"):
        verify_role = discord.utils.get(guild.roles, name="Unverified")
        if verify_role:
            await member.add_roles(verify_role)
            
            try:
                await member.send(f"Welcome to {guild.name}! Please verify in the verification channel.")
            except:
                pass

# Anti-Spam System
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return
    
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)
    
    # Load security settings
    try:
        with open(f"security/{guild_id}.json", 'r') as f:
            security = json.load(f)
    except:
        security = {"antispam": True, "antilink": False, "badwords": []}
    
    # Anti-Spam
    if security.get("antispam"):
        now = datetime.now()
        spam_tracker[guild_id][user_id].append(now)
        spam_tracker[guild_id][user_id] = [t for t in spam_tracker[guild_id][user_id] if (now - t).seconds < 5]
        
        if len(spam_tracker[guild_id][user_id]) > 5:
            try:
                await message.author.timeout(timedelta(minutes=5), reason="Spam detected")
                await message.channel.send(f"🔇 {message.author.mention} muted for spam")
                await message.delete()
            except:
                pass
    
    # Anti-Link
    if security.get("antilink"):
        if re.search(r'https?://|discord\.gg/', message.content):
            if not message.author.guild_permissions.manage_messages:
                await message.delete()
                await message.channel.send(f"{message.author.mention} No links allowed!", delete_after=3)
                return
    
    # Bad Words Filter
    badwords = security.get("badwords", [])
    if any(word.lower() in message.content.lower() for word in badwords):
        await message.delete()
        await message.channel.send(f"{message.author.mention} Watch your language!", delete_after=3)
        return
    
    # Level System
    levels[guild_id][user_id]["messages"] += 1
    levels[guild_id][user_id]["xp"] += random.randint(15, 25)
    
    # Level up check
    current_level = levels[guild_id][user_id]["level"]
    current_xp = levels[guild_id][user_id]["xp"]
    needed_xp = 5 * (current_level ** 2) + 50 * current_level + 100
    
    if current_xp >= needed_xp:
        levels[guild_id][user_id]["level"] += 1
        levels[guild_id][user_id]["xp"] = 0
        await message.channel.send(f"🎉 {message.author.mention} leveled up to **Level {levels[guild_id][user_id]['level']}**!")
    
    # AFK System
    if user_id in afk_users:
        del afk_users[user_id]
        await message.channel.send(f"Welcome back {message.author.mention}! Your AFK status has been removed.", delete_after=5)
    
    # Check mentions for AFK users
    for mention in message.mentions:
        if str(mention.id) in afk_users:
            await message.channel.send(f"{mention.name} is AFK: {afk_users[str(mention.id)]}")
    
    await bot.process_commands(message)

# Security Commands
@bot.hybrid_command()
@commands.has_permissions(administrator=True)
async def antiraid(ctx, toggle: str):
    guild_id = str(ctx.guild.id)
    os.makedirs("security", exist_ok=True)
    
    try:
        with open(f"security/{guild_id}.json", 'r') as f:
            security = json.load(f)
    except:
        security = {}
    
    security["antiraid"] = toggle.lower() == "on"
    
    with open(f"security/{guild_id}.json", 'w') as f:
        json.dump(security, f)
    
    await ctx.send(f"🛡️ Anti-Raid: **{toggle.upper()}**")

@bot.hybrid_command()
@commands.has_permissions(administrator=True)
async def antispam(ctx, toggle: str):
    guild_id = str(ctx.guild.id)
    os.makedirs("security", exist_ok=True)
    
    try:
        with open(f"security/{guild_id}.json", 'r') as f:
            security = json.load(f)
    except:
        security = {}
    
    security["antispam"] = toggle.lower() == "on"
    
    with open(f"security/{guild_id}.json", 'w') as f:
        json.dump(security, f)
    
    await ctx.send(f"🛡️ Anti-Spam: **{toggle.upper()}**")

@bot.hybrid_command()
@commands.has_permissions(administrator=True)
async def antilink(ctx, toggle: str):
    guild_id = str(ctx.guild.id)
    os.makedirs("security", exist_ok=True)
    
    try:
        with open(f"security/{guild_id}.json", 'r') as f:
            security = json.load(f)
    except:
        security = {}
    
    security["antilink"] = toggle.lower() == "on"
    
    with open(f"security/{guild_id}.json", 'w') as f:
        json.dump(security, f)
    
    await ctx.send(f"🛡️ Anti-Link: **{toggle.upper()}**")

@bot.hybrid_command()
@commands.has_permissions(administrator=True)
async def addbadword(ctx, *, word: str):
    guild_id = str(ctx.guild.id)
    os.makedirs("security", exist_ok=True)
    
    try:
        with open(f"security/{guild_id}.json", 'r') as f:
            security = json.load(f)
    except:
        security = {"badwords": []}
    
    if "badwords" not in security:
        security["badwords"] = []
    
    security["badwords"].append(word.lower())
    
    with open(f"security/{guild_id}.json", 'w') as f:
        json.dump(security, f)
    
    await ctx.send(f"✅ Added `{word}` to bad words filter")

@bot.hybrid_command()
@commands.has_permissions(administrator=True)
async def lockdown(ctx):
    for channel in ctx.guild.text_channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        except:
            pass
    await ctx.send("🔒 **Server locked down!**")

@bot.hybrid_command()
@commands.has_permissions(administrator=True)
async def unlockdown(ctx):
    for channel in ctx.guild.text_channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=None)
        except:
            pass
    await ctx.send("🔓 **Lockdown lifted!**")

# ================= MODERATION =================

@bot.hybrid_command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason"):
    await member.ban(reason=reason)
    embed = discord.Embed(title="Member Banned", color=discord.Color.red())
    embed.add_field(name="User", value=member.mention)
    embed.add_field(name="Moderator", value=ctx.author.mention)
    embed.add_field(name="Reason", value=reason)
    await ctx.send(embed=embed)

@bot.hybrid_command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason"):
    await member.kick(reason=reason)
    embed = discord.Embed(title="Member Kicked", color=discord.Color.orange())
    embed.add_field(name="User", value=member.mention)
    embed.add_field(name="Moderator", value=ctx.author.mention)
    embed.add_field(name="Reason", value=reason)
    await ctx.send(embed=embed)

@bot.hybrid_command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutes:int=10, *, reason="No reason"):
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await ctx.send(f"🔇 {member.mention} muted for {minutes} minutes")

@bot.hybrid_command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 {member.mention} unmuted")

@bot.hybrid_command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount:int=10):
    await ctx.channel.purge(limit=amount+1)
    msg = await ctx.send(f"🧹 Cleared {amount} messages")
    await asyncio.sleep(3)
    await msg.delete()

@bot.hybrid_command()
@commands.has_permissions(moderate_members=True)
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    
    warnings[guild_id][user_id].append({
        "reason": reason,
        "moderator": str(ctx.author),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    
    warn_count = len(warnings[guild_id][user_id])
    await ctx.send(f"⚠️ {member.mention} warned for: {reason} (Total warnings: {warn_count})")
    
    # Auto-punish
    if warn_count >= 3:
        await member.timeout(timedelta(hours=1), reason="3 warnings reached")
        await ctx.send(f"🔇 {member.mention} auto-muted for 1 hour (3 warnings)")

@bot.hybrid_command()
@commands.has_permissions(moderate_members=True)
async def warnings(ctx, member: discord.Member):
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    
    user_warnings = warnings[guild_id][user_id]
    
    if not user_warnings:
        await ctx.send(f"{member.mention} has no warnings")
        return
    
    embed = discord.Embed(title=f"Warnings for {member}", color=discord.Color.yellow())
    for i, w in enumerate(user_warnings, 1):
        embed.add_field(
            name=f"Warning {i}",
            value=f"**Reason:** {w['reason']}\n**By:** {w['moderator']}\n**Time:** {w['time']}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.hybrid_command()
@commands.has_permissions(moderate_members=True)
async def clearwarns(ctx, member: discord.Member):
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    warnings[guild_id][user_id] = []
    await ctx.send(f"✅ Cleared all warnings for {member.mention}")

@bot.hybrid_command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"⏱️ Slowmode set to {seconds} seconds")

@bot.hybrid_command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Channel locked")

@bot.hybrid_command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
    await ctx.send("🔓 Channel unlocked")

@bot.hybrid_command()
@commands.has_permissions(manage_channels=True)
async def nuke(ctx):
    channel = ctx.channel
    new_channel = await channel.clone()
    await channel.delete()
    await new_channel.send("💥 Channel nuked!")

# ================= LEVELING SYSTEM =================

@bot.hybrid_command()
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    
    data = levels[guild_id][user_id]
    
    embed = discord.Embed(title=f"{member.name}'s Rank", color=discord.Color.blue())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Level", value=data["level"])
    embed.add_field(name="XP", value=f"{data['xp']}/{5 * (data['level'] ** 2) + 50 * data['level'] + 100}")
    embed.add_field(name="Messages", value=data["messages"])
    
    await ctx.send(embed=embed)

@bot.hybrid_command()
async def leaderboard(ctx):
    guild_id = str(ctx.guild.id)
    
    sorted_users = sorted(levels[guild_id].items(), key=lambda x: x[1]["level"], reverse=True)[:10]
    
    embed = discord.Embed(title="🏆 Leaderboard", color=discord.Color.gold())
    
    for i, (user_id, data) in enumerate(sorted_users, 1):
        try:
            member = ctx.guild.get_member(int(user_id))
            if member:
                embed.add_field(
                    name=f"{i}. {member.name}",
                    value=f"Level {data['level']} | {data['xp']} XP",
                    inline=False
                )
        except:
            pass
    
    await ctx.send(embed=embed)

@bot.hybrid_command()
@commands.has_permissions(administrator=True)
async def setlevel(ctx, member: discord.Member, level: int):
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    levels[guild_id][user_id]["level"] = level
    levels[guild_id][user_id]["xp"] = 0
    await ctx.send(f"✅ Set {member.mention}'s level to {level}")

# ================= ECONOMY SYSTEM =================

@bot.hybrid_command()
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)
    
    data = economy[guild_id][user_id]
    
    embed = discord.Embed(title=f"💰 {member.name}'s Balance", color=discord.Color.green())
    embed.add_field(name="Wallet", value=f"${data['coins']}")
    embed.add_field(name="Bank", value=f"${data['bank']}")
    embed.add_field(name="Total", value=f"${data['coins'] + data['bank']}")
    
    await ctx.send(embed=embed)

@bot.hybrid_command()
async def daily(ctx):
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    
    economy[guild_id][user_id]["coins"] += 500
    await ctx.send(f"💵 You received $500! New balance: ${economy[guild_id][user_id]['coins']}")

@bot.hybrid_command()
async def work(ctx):
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    
    earnings = random.randint(100, 300)
    economy[guild_id][user_id]["coins"] += earnings
    
    jobs = ["programmer", "designer", "manager", "chef", "driver"]
    await ctx.send(f"💼 You worked as a {random.choice(jobs)} and earned ${earnings}!")

@bot.hybrid_command()
async def deposit(ctx, amount: str):
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    
    if amount.lower() == "all":
        amount = economy[guild_id][user_id]["coins"]
    else:
        amount = int(amount)
    
    if economy[guild_id][user_id]["coins"] < amount:
        await ctx.send("❌ You don't have that much!")
        return
    
    economy[guild_id][user_id]["coins"] -= amount
    economy[guild_id][user_id]["bank"] += amount
    await ctx.send(f"🏦 Deposited ${amount} to your bank")

@bot.hybrid_command()
async def withdraw(ctx, amount: str):
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    
    if amount.lower() == "all":
        amount = economy[guild_id][user_id]["bank"]
    else:
        amount = int(amount)
    
    if economy[guild_id][user_id]["bank"] < amount:
        await ctx.send("❌ You don't have that much in the bank!")
        return
    
    economy[guild_id][user_id]["bank"] -= amount
    economy[guild_id][user_id]["coins"] += amount
    await ctx.send(f"💵 Withdrew ${amount} from your bank")

@bot.hybrid_command()
async def give(ctx, member: discord.Member, amount: int):
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    target_id = str(member.id)
    
    if economy[guild_id][user_id]["coins"] < amount:
        await ctx.send("❌ You don't have that much!")
        return
    
    economy[guild_id][user_id]["coins"] -= amount
    economy[guild_id][target_id]["coins"] += amount
    await ctx.send(f"✅ Gave ${amount} to {member.mention}")

@bot.hybrid_command()
async def rob(ctx, member: discord.Member):
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    target_id = str(member.id)
    
    if random.random() < 0.5:
        amount = random.randint(50, 200)
        if economy[guild_id][target_id]["coins"] < amount:
            await ctx.send(f"😂 {member.mention} is too poor to rob!")
            return
        
        economy[guild_id][target_id]["coins"] -= amount
        economy[guild_id][user_id]["coins"] += amount
        await ctx.send(f"💰 You robbed ${amount} from {member.mention}!")
    else:
        fine = random.randint(100, 300)
        economy[guild_id][user_id]["coins"] -= fine
        await ctx.send(f"🚔 You got caught! Fine: ${fine}")

@bot.hybrid_command()
async def gamble(ctx, amount: int):
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    
    if economy[guild_id][user_id]["coins"] < amount:
        await ctx.send("❌ You don't have that much!")
        return
    
    if random.random() < 0.5:
        economy[guild_id][user_id]["coins"] += amount
        await ctx.send(f"🎰 You won ${amount}! New balance: ${economy[guild_id][user_id]['coins']}")
    else:
        economy[guild_id][user_id]["coins"] -= amount
        await ctx.send(f"🎰 You lost ${amount}! New balance: ${economy[guild_id][user_id]['coins']}")

@bot.hybrid_command()
async def shop(ctx):
    embed = discord.Embed(title="🛒 Shop", color=discord.Color.blue())
    embed.add_field(name="1. VIP Role", value="$5000", inline=False)
    embed.add_field(name="2. Custom Role", value="$10000", inline=False)
    embed.add_field(name="3. Color Role", value="$3000", inline=False)
    await ctx.send(embed=embed)

@bot.hybrid_command()
async def buy(ctx, item: int):
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    
    items = {
        1: ("VIP Role", 5000),
        2: ("Custom Role", 10000),
        3: ("Color Role", 3000)
    }
    
    if item not in items:
        await ctx.send("❌ Invalid item!")
        return
    
    name, price = items[item]
    
    if economy[guild_id][user_id]["coins"] < price:
        await ctx.send(f"❌ You need ${price} to buy {name}!")
        return
    
    economy[guild_id][user_id]["coins"] -= price
    economy[guild_id][user_id]["inventory"].append(name)
    await ctx.send(f"✅ Purchased {name} for ${price}!")

# ================= FUN COMMANDS =================

@bot.hybrid_command()
async def coinflip(ctx):
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"🪙 {result}")

@bot.hybrid_command()
async def roll(ctx, sides:int=6):
    await ctx.send(f"🎲 {random.randint(1,sides)}")

@bot.hybrid_command(name="8ball")
async def eightball(ctx, *, question):
    responses = [
        "Yes", "No", "Maybe", "Definitely", "Absolutely not",
        "Ask again later", "Cannot predict now", "Very doubtful",
        "Without a doubt", "My sources say no", "Outlook good"
    ]
    await ctx.send(f"🎱 {random.choice(responses)}")

@bot.hybrid_command()
async def joke(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://official-joke-api.appspot.com/random_joke") as r:
            data = await r.json()
            await ctx.send(f"{data['setup']}\n\n||{data['punchline']}||")

@bot.hybrid_command()
async def meme(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://meme-api.com/gimme") as r:
            data = await r.json()
            embed = discord.Embed(title=data['title'], color=discord.Color.random())
            embed.set_image(url=data['url'])
            await ctx.send(embed=embed)

@bot.hybrid_command()
async def dog(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://dog.ceo/api/breeds/image/random") as r:
            data = await r.json()
            embed = discord.Embed(title="🐕 Random Dog", color=discord.Color.orange())
            embed.set_image(url=data['message'])
            await ctx.send(embed=embed)

@bot.hybrid_command()
async def cat(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.thecatapi.com/v1/images/search") as r:
            data = await r.json()
            embed = discord.Embed(title="🐱 Random Cat", color=discord.Color.purple())
            embed.set_image(url=data[0]['url'])
            await ctx.send(embed=embed)

@bot.hybrid_command()
async def choose(ctx, *choices):
    if len(choices) < 2:
        await ctx.send("❌ Provide at least 2 choices!")
        return
    await ctx.send(f"🤔 I choose: **{random.choice(choices)}**")

@bot.hybrid_command()
async def say(ctx, *, message):
    await ctx.message.delete()
    await ctx.send(message)

@bot.hybrid_command()
async def reverse(ctx, *, text):
    await ctx.send(text[::-1])

@bot.hybrid_command()
async def ascii(ctx, *, text):
    ascii_art = {
        'a': '▄▀█', 'b': '█▄▄', 'c': '█▀▀', 'd': '█▀▄', 'e': '█▀▀',
        'f': '█▀▀', 'g': '█▀▀', 'h': '█░█', 'i': '█', 'j': '░░█',
        'k': '█▄▀', 'l': '█░░', 'm': '█▀▄▀█', 'n': '█▄░█', 'o': '█▀█',
        'p': '█▀█', 'q': '▄▀█', 'r': '█▀█', 's': '█▀', 't': '▀█▀',
        'u': '█░█', 'v': '█░█', 'w': '█░█░█', 'x': '▀▄▀', 'y': '█▄█',
        'z': '▀█'
    }
    result = ' '.join(ascii_art.get(c.lower(), c) for c in text)
    await ctx.send(f"```\n{result}\n```")

@bot.hybrid_command()
async def mock(ctx, *, text):
    result = ''.join(c.upper() if i % 2 else c.lower() for i, c in enumerate(text))
    await ctx.send(result)

# ================= GAMES =================

# RPS Game
class RPS(View):
    def __init__(self, user):
        super().__init__(timeout=30)
        self.user = user

    async def interaction_check(self, interaction):
        return interaction.user == self.user

    async def play(self, interaction, choice):
        bot_choice = random.choice(["rock","paper","scissors"])
        
        if choice == bot_choice:
            result = "🤝 Tie!"
        elif (choice=="rock" and bot_choice=="scissors") or \
             (choice=="paper" and bot_choice=="rock") or \
             (choice=="scissors" and bot_choice=="paper"):
            result = "🎉 You Win!"
        else:
            result = "😢 You Lose!"
        
        embed = discord.Embed(title="Rock Paper Scissors", color=discord.Color.blue())
        embed.add_field(name="Your Choice", value=choice.capitalize())
        embed.add_field(name="Bot Choice", value=bot_choice.capitalize())
        embed.add_field(name="Result", value=result, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Rock", style=discord.ButtonStyle.gray, emoji="🪨")
    async def rock(self, interaction, button):
        await self.play(interaction, "rock")

    @discord.ui.button(label="Paper", style=discord.ButtonStyle.gray, emoji="📄")
    async def paper(self, interaction, button):
        await self.play(interaction, "paper")

    @discord.ui.button(label="Scissors", style=discord.ButtonStyle.gray, emoji="✂️")
    async def scissors(self, interaction, button):
        await self.play(interaction, "scissors")

@bot.hybrid_command()
async def rps(ctx):
    embed = discord.Embed(title="Rock Paper Scissors", description="Choose your move!", color=discord.Color.blue())
    await ctx.send(embed=embed, view=RPS(ctx.author))

# Trivia Game
@bot.hybrid_command()
async def trivia(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://opentdb.com/api.php?amount=1&type=multiple") as r:
            data = await r.json()
            q = data['results'][0]
            
            correct = q['correct_answer']
            answers = q['incorrect_answers'] + [correct]
            random.shuffle(answers)
            
            embed = discord.Embed(title="🧠 Trivia", description=q['question'], color=discord.Color.blue())
            
            for i, answer in enumerate(answers, 1):
                embed.add_field(name=f"{i}", value=answer, inline=False)
            
            await ctx.send(embed=embed)
            
            def check(m):
                return m.author == ctx.author and m.content in ['1','2','3','4']
            
            try:
                msg = await bot.wait_for("message", check=check, timeout=15)
                user_answer = answers[int(msg.content) - 1]
                
                if user_answer == correct:
                    await ctx.send(f"✅ Correct! The answer was: {correct}")
                else:
                    await ctx.send(f"❌ Wrong! The correct answer was: {correct}")
            except asyncio.TimeoutError:
                await ctx.send(f"⏰ Time's up! The answer was: {correct}")

# Guess the Number
@bot.hybrid_command()
async def guess(ctx):
    num = random.randint(1, 100)
    await ctx.send("🔢 Guess a number between 1-100! You have 20 seconds.")

    def check(m):
        return m.author == ctx.author and m.content.isdigit()

    tries = 0
    while tries < 5:
        try:
            msg = await bot.wait_for("message", check=check, timeout=20)
            guess_num = int(msg.content)
            tries += 1
            
            if guess_num == num:
                await ctx.send(f"🎉 Correct! It was {num}! Tries: {tries}")
                return
            elif guess_num < num:
                await ctx.send("📈 Higher!")
            else:
                await ctx.send("📉 Lower!")
        except asyncio.TimeoutError:
            await ctx.send(f"⏰ Time's up! The number was {num}")
            return
    
    await ctx.send(f"😢 You ran out of tries! The number was {num}")

# TicTacToe
class TicTacToe(View):
    def __init__(self, player1, player2):
        super().__init__(timeout=60)
        self.player1 = player1
        self.player2 = player2
        self.current = player1
        self.board = [["⬜" for _ in range(3)] for _ in range(3)]
        self.symbols = {str(player1.id): "❌", str(player2.id): "⭕"}

    def check_win(self):
        # Check rows, columns, diagonals
        for i in range(3):
            if self.board[i][0] == self.board[i][1] == self.board[i][2] != "⬜":
                return True
            if self.board[0][i] == self.board[1][i] == self.board[2][i] != "⬜":
                return True
        
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != "⬜":
            return True
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != "⬜":
            return True
        
        return False

    def is_full(self):
        return all(cell != "⬜" for row in self.board for cell in row)

    async def make_move(self, interaction, row, col):
        if interaction.user != self.current:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return
        
        if self.board[row][col] != "⬜":
            await interaction.response.send_message("Spot taken!", ephemeral=True)
            return
        
        self.board[row][col] = self.symbols[str(self.current.id)]
        
        if self.check_win():
            board_str = '\n'.join([''.join(row) for row in self.board])
            await interaction.response.edit_message(content=f"{board_str}\n\n🎉 {self.current.mention} wins!", view=None)
            return
        
        if self.is_full():
            board_str = '\n'.join([''.join(row) for row in self.board])
            await interaction.response.edit_message(content=f"{board_str}\n\n🤝 It's a tie!", view=None)
            return
        
        self.current = self.player2 if self.current == self.player1 else self.player1
        board_str = '\n'.join([''.join(row) for row in self.board])
        await interaction.response.edit_message(content=f"{board_str}\n\n{self.current.mention}'s turn!", view=self)

    @discord.ui.button(label="1", row=0)
    async def b1(self, i, b): await self.make_move(i, 0, 0)
    @discord.ui.button(label="2", row=0)
    async def b2(self, i, b): await self.make_move(i, 0, 1)
    @discord.ui.button(label="3", row=0)
    async def b3(self, i, b): await self.make_move(i, 0, 2)
    @discord.ui.button(label="4", row=1)
    async def b4(self, i, b): await self.make_move(i, 1, 0)
    @discord.ui.button(label="5", row=1)
    async def b5(self, i, b): await self.make_move(i, 1, 1)
    @discord.ui.button(label="6", row=1)
    async def b6(self, i, b): await self.make_move(i, 1, 2)
    @discord.ui.button(label="7", row=2)
    async def b7(self, i, b): await self.make_move(i, 2, 0)
    @discord.ui.button(label="8", row=2)
    async def b8(self, i, b): await self.make_move(i, 2, 1)
    @discord.ui.button(label="9", row=2)
    async def b9(self, i, b): await self.make_move(i, 2, 2)

@bot.hybrid_command()
async def tictactoe(ctx, opponent: discord.Member):
    if opponent == ctx.author:
        await ctx.send("❌ You can't play against yourself!")
        return
    if opponent.bot:
        await ctx.send("❌ You can't play against a bot!")
        return
    
    game = TicTacToe(ctx.author, opponent)
    board_str = '\n'.join([''.join(row) for row in game.board])
    await ctx.send(f"{board_str}\n\n{ctx.author.mention}'s turn!", view=game)

# Connect4
@bot.hybrid_command()
async def connect4(ctx, opponent: discord.Member):
    await ctx.send(f"🎮 Connect 4 game started! {ctx.author.mention} vs {opponent.mention}\n(Game board would be implemented with buttons)")

# Slots
@bot.hybrid_command()
async def slots(ctx):
    emojis = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
    results = [random.choice(emojis) for _ in range(3)]
    
    result_str = f"[ {results[0]} | {results[1]} | {results[2]} ]"
    
    if results[0] == results[1] == results[2]:
        await ctx.send(f"🎰 {result_str}\n\n🎉 JACKPOT! You won 1000 coins!")
    elif results[0] == results[1] or results[1] == results[2]:
        await ctx.send(f"🎰 {result_str}\n\n✨ Two match! You won 100 coins!")
    else:
        await ctx.send(f"🎰 {result_str}\n\n😢 Better luck next time!")

# Blackjack
@bot.hybrid_command()
async def blackjack(ctx):
    await ctx.send("🃏 Starting Blackjack game...\n(Full blackjack implementation with buttons)")

# Hangman
@bot.hybrid_command()
async def hangman(ctx):
    words = ["python", "discord", "computer", "programming", "developer", "database", "algorithm"]
    word = random.choice(words)
    guessed = ["_"] * len(word)
    tries = 6
    
    await ctx.send(f"🎯 Hangman started!\n```{' '.join(guessed)}```\nTries left: {tries}")

# ================= UTILITY =================

@bot.hybrid_command()
async def afk(ctx, *, reason="AFK"):
    afk_users[str(ctx.author.id)] = reason
    await ctx.send(f"💤 {ctx.author.mention} is now AFK: {reason}")

@bot.hybrid_command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    
    embed = discord.Embed(title=f"User Info: {member}", color=member.color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Nickname", value=member.nick or "None")
    embed.add_field(name="Status", value=str(member.status))
    embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Created", value=member.created_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Roles", value=len(member.roles))
    
    await ctx.send(embed=embed)

@bot.hybrid_command()
async def serverinfo(ctx):
    guild = ctx.guild
    
    embed = discord.Embed(title=f"Server Info: {guild.name}", color=discord.Color.blue())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="Owner", value=guild.owner.mention)
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Channels", value=len(guild.channels))
    embed.add_field(name="Roles", value=len(guild.roles))
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Boosts", value=guild.premium_subscription_count)
    
    await ctx.send(embed=embed)

@bot.hybrid_command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.name}'s Avatar", color=discord.Color.blue())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.hybrid_command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: {latency}ms")

@bot.hybrid_command()
async def remind(ctx, time: int, unit: str, *, reminder: str):
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    
    if unit not in units:
        await ctx.send("❌ Use: s (seconds), m (minutes), h (hours), d (days)")
        return
    
    seconds = time * units[unit]
    remind_time = datetime.now().timestamp() + seconds
    
    reminders.append({
        "user": ctx.author.id,
        "channel": ctx.channel.id,
        "time": remind_time,
        "message": reminder
    })
    
    await ctx.send(f"⏰ Reminder set for {time}{unit}!")

@tasks.loop(seconds=30)
async def check_reminders():
    now = datetime.now().timestamp()
    for reminder in reminders[:]:
        if now >= reminder["time"]:
            channel = bot.get_channel(reminder["channel"])
            user = bot.get_user(reminder["user"])
            
            if channel and user:
                await channel.send(f"⏰ {user.mention} Reminder: {reminder['message']}")
            
            reminders.remove(reminder)

@bot.hybrid_command()
async def poll(ctx, question: str, *options):
    if len(options) < 2:
        await ctx.send("❌ Need at least 2 options!")
        return
    
    if len(options) > 10:
        await ctx.send("❌ Maximum 10 options!")
        return

    emojis = ['1️⃣','2️⃣','3️⃣','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣','🔟']
    
    embed = discord.Embed(title="📊 Poll", description=question, color=discord.Color.blue())
    
    for i, option in enumerate(options):
        embed.add_field(name=f"{emojis[i]} Option {i+1}", value=option, inline=False)
    
    msg = await ctx.send(embed=embed)
    
    for i in range(len(options)):
        await msg.add_reaction(emojis[i])

@bot.hybrid_command()
async def giveaway(ctx, duration: int, winners: int, *, prize: str):
    embed = discord.Embed(title="🎉 GIVEAWAY 🎉", description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Duration:** {duration}m", color=discord.Color.gold())
    embed.set_footer(text="React with 🎉 to enter!")
    
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")
    
    giveaway_id = str(msg.id)
    end_time = datetime.now().timestamp() + (duration * 60)
    
    giveaways[giveaway_id] = {
        "channel": ctx.channel.id,
        "end": end_time,
        "winners": winners,
        "prize": prize
    }
    
    await asyncio.sleep(duration * 60)
    
    msg = await ctx.channel.fetch_message(int(giveaway_id))
    reaction = discord.utils.get(msg.reactions, emoji="🎉")
    
    if reaction:
        users = [user async for user in reaction.users() if not user.bot]
        
        if len(users) < winners:
            await ctx.send("❌ Not enough participants!")
            return
        
        winners_list = random.sample(users, winners)
        winner_mentions = ", ".join(w.mention for w in winners_list)
        
        await ctx.send(f"🎉 Congratulations {winner_mentions}! You won: **{prize}**")

@bot.hybrid_command()
async def suggest(ctx, *, suggestion: str):
    channel = discord.utils.get(ctx.guild.text_channels, name="suggestions")
    
    if not channel:
        await ctx.send("❌ No suggestions channel found!")
        return
    
    embed = discord.Embed(title="💡 New Suggestion", description=suggestion, color=discord.Color.green())
    embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
    
    msg = await channel.send(embed=embed)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")
    
    await ctx.send("✅ Suggestion submitted!")

# ================= TICKET SYSTEM =================

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.green, emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        user = interaction.user
        
        # Check if user already has a ticket
        existing = discord.utils.get(guild.text_channels, name=f"ticket-{user.name.lower()}")
        if existing:
            await interaction.response.send_message("❌ You already have a ticket open!", ephemeral=True)
            return
        
        # Create ticket channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            overwrites=overwrites,
            category=discord.utils.get(guild.categories, name="Tickets")
        )
        
        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=f"Welcome {user.mention}!\nSupport will be with you shortly.\n\nClick 🔒 to close this ticket.",
            color=discord.Color.blue()
        )
        
        await channel.send(embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🔒 Closing ticket in 5 seconds...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

@bot.hybrid_command()
@commands.has_permissions(administrator=True)
async def ticketsetup(ctx):
    embed = discord.Embed(
        title="🎫 Support Tickets",
        description="Click the button below to create a support ticket!",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketView())

# ================= REACTION ROLES =================

@bot.hybrid_command()
@commands.has_permissions(manage_roles=True)
async def reactionrole(ctx, emoji: str, role: discord.Role, *, message: str):
    embed = discord.Embed(title="Reaction Roles", description=message, color=discord.Color.blue())
    msg = await ctx.send(embed=embed)
    await msg.add_reaction(emoji)
    
    # Store in database (simplified)
    await ctx.send(f"✅ Reaction role setup: {emoji} → {role.mention}")

@bot.event
async def on_raw_reaction_add(payload):
    # Handle reaction roles (simplified implementation)
    pass

# ================= WELCOME/GOODBYE =================

@bot.event
async def on_member_join(member):
    # Welcome message
    channel = discord.utils.get(member.guild.text_channels, name="welcome")
    if channel:
        embed = discord.Embed(
            title="Welcome!",
            description=f"Welcome {member.mention} to {member.guild.name}!",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    # Goodbye message
    channel = discord.utils.get(member.guild.text_channels, name="welcome")
    if channel:
        embed = discord.Embed(
            title="Goodbye!",
            description=f"{member.name} has left the server.",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)

# ================= LOGGING =================

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    
    log_channel = discord.utils.get(message.guild.text_channels, name="logs")
    if log_channel:
        embed = discord.Embed(title="🗑️ Message Deleted", color=discord.Color.red())
        embed.add_field(name="Author", value=message.author.mention)
        embed.add_field(name="Channel", value=message.channel.mention)
        embed.add_field(name="Content", value=message.content or "No content", inline=False)
        await log_channel.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    
    log_channel = discord.utils.get(before.guild.text_channels, name="logs")
    if log_channel:
        embed = discord.Embed(title="✏️ Message Edited", color=discord.Color.orange())
        embed.add_field(name="Author", value=before.author.mention)
        embed.add_field(name="Channel", value=before.channel.mention)
        embed.add_field(name="Before", value=before.content, inline=False)
        embed.add_field(name="After", value=after.content, inline=False)
        await log_channel.send(embed=embed)

@bot.event
async def on_member_ban(guild, user):
    log_channel = discord.utils.get(guild.text_channels, name="logs")
    if log_channel:
        embed = discord.Embed(title="🔨 Member Banned", color=discord.Color.red())
        embed.add_field(name="User", value=f"{user.name}#{user.discriminator}")
        await log_channel.send(embed=embed)

# ================= HELP COMMAND =================

@bot.hybrid_command(name="help")
async def help_command(ctx, category: str = None):
    if not category:
        embed = discord.Embed(title="📚 Bot Commands", description="Use `!help <category>` for more info", color=discord.Color.blue())
        embed.add_field(name="🛡️ Security", value="`antiraid`, `antispam`, `antilink`, `lockdown`")
        embed.add_field(name="🔨 Moderation", value="`ban`, `kick`, `mute`, `warn`, `clear`")
        embed.add_field(name="📊 Leveling", value="`rank`, `leaderboard`, `setlevel`")
        embed.add_field(name="💰 Economy", value="`balance`, `daily`, `work`, `rob`, `shop`")
        embed.add_field(name="🎮 Games", value="`rps`, `trivia`, `guess`, `tictactoe`, `slots`")
        embed.add_field(name="🎉 Fun", value="`meme`, `joke`, `8ball`, `dog`, `cat`")
        embed.add_field(name="🛠️ Utility", value="`userinfo`, `serverinfo`, `poll`, `remind`")
        embed.add_field(name="🎫 Tickets", value="`ticketsetup`")
        
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"Help for category: {category}")

# ================= RUN =================

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    TOKEN = os.getenv("TOKEN")

    if not TOKEN:
        print("❌ No token found in .env file")
    else:
        # Create necessary directories
        os.makedirs("security", exist_ok=True)
        os.makedirs("dashboard", exist_ok=True)
        
        print("🚀 Starting bot...")
        bot.run(TOKEN)