import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import json
import os
from datetime import datetime, timedelta
import aiohttp

# Bot setup with all intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ==================== MODERATION COMMANDS ====================

@bot.hybrid_command(name="ban", description="Ban a member from the server")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Ban a member from the server"""
    try:
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"{member.mention} has been banned.",
            color=discord.Color.red()
        )
        embed.add_field(name="Reason", value=reason)
        embed.set_footer(text=f"Banned by {ctx.author}")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Failed to ban member: {e}")

@bot.hybrid_command(name="unban", description="Unban a user from the server")
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: str):
    """Unban a user by their ID"""
    try:
        user = await bot.fetch_user(int(user_id))
        await ctx.guild.unban(user)
        await ctx.send(f"✅ {user.name} has been unbanned.")
    except Exception as e:
        await ctx.send(f"❌ Failed to unban user: {e}")

@bot.hybrid_command(name="kick", description="Kick a member from the server")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Kick a member from the server"""
    try:
        await member.kick(reason=reason)
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"{member.mention} has been kicked.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Reason", value=reason)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Failed to kick member: {e}")

@bot.hybrid_command(name="mute", description="Mute a member")
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, duration: int = 10, *, reason: str = "No reason provided"):
    """Timeout a member for specified minutes"""
    try:
        await member.timeout(timedelta(minutes=duration), reason=reason)
        await ctx.send(f"🔇 {member.mention} has been muted for {duration} minutes. Reason: {reason}")
    except Exception as e:
        await ctx.send(f"❌ Failed to mute member: {e}")

@bot.hybrid_command(name="unmute", description="Unmute a member")
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    """Remove timeout from a member"""
    try:
        await member.timeout(None)
        await ctx.send(f"🔊 {member.mention} has been unmuted.")
    except Exception as e:
        await ctx.send(f"❌ Failed to unmute member: {e}")

@bot.hybrid_command(name="warn", description="Warn a member")
@commands.has_permissions(moderate_members=True)
async def warn(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Warn a member"""
    embed = discord.Embed(
        title="⚠️ Warning Issued",
        description=f"{member.mention} has been warned.",
        color=discord.Color.yellow()
    )
    embed.add_field(name="Reason", value=reason)
    embed.set_footer(text=f"Warned by {ctx.author}")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="clear", description="Clear messages from the channel")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    """Delete messages from the channel"""
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"🗑️ Deleted {len(deleted) - 1} messages.")
        await asyncio.sleep(3)
        await msg.delete()
    except Exception as e:
        await ctx.send(f"❌ Failed to clear messages: {e}")

@bot.hybrid_command(name="slowmode", description="Set slowmode for the channel")
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int = 0):
    """Set slowmode delay in seconds"""
    try:
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await ctx.send("✅ Slowmode disabled.")
        else:
            await ctx.send(f"✅ Slowmode set to {seconds} seconds.")
    except Exception as e:
        await ctx.send(f"❌ Failed to set slowmode: {e}")

@bot.hybrid_command(name="lock", description="Lock the channel")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    """Lock the channel to prevent messages"""
    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send("🔒 Channel locked.")
    except Exception as e:
        await ctx.send(f"❌ Failed to lock channel: {e}")

@bot.hybrid_command(name="unlock", description="Unlock the channel")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    """Unlock the channel"""
    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send("🔓 Channel unlocked.")
    except Exception as e:
        await ctx.send(f"❌ Failed to unlock channel: {e}")

# ==================== SERVER MANAGEMENT ====================

@bot.hybrid_command(name="addrole", description="Add a role to a member")
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    """Add a role to a member"""
    try:
        await member.add_roles(role)
        await ctx.send(f"✅ Added {role.name} to {member.mention}")
    except Exception as e:
        await ctx.send(f"❌ Failed to add role: {e}")

@bot.hybrid_command(name="removerole", description="Remove a role from a member")
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    """Remove a role from a member"""
    try:
        await member.remove_roles(role)
        await ctx.send(f"✅ Removed {role.name} from {member.mention}")
    except Exception as e:
        await ctx.send(f"❌ Failed to remove role: {e}")

@bot.hybrid_command(name="createrole", description="Create a new role")
@commands.has_permissions(manage_roles=True)
async def createrole(ctx, name: str, color: str = "default"):
    """Create a new role"""
    try:
        color_value = discord.Color.default() if color == "default" else discord.Color(int(color.replace("#", ""), 16))
        role = await ctx.guild.create_role(name=name, color=color_value)
        await ctx.send(f"✅ Created role: {role.mention}")
    except Exception as e:
        await ctx.send(f"❌ Failed to create role: {e}")

@bot.hybrid_command(name="deleterole", description="Delete a role")
@commands.has_permissions(manage_roles=True)
async def deleterole(ctx, role: discord.Role):
    """Delete a role"""
    try:
        await role.delete()
        await ctx.send(f"✅ Deleted role: {role.name}")
    except Exception as e:
        await ctx.send(f"❌ Failed to delete role: {e}")

@bot.hybrid_command(name="setnick", description="Change a member's nickname")
@commands.has_permissions(manage_nicknames=True)
async def setnick(ctx, member: discord.Member, *, nickname: str):
    """Change a member's nickname"""
    try:
        await member.edit(nick=nickname)
        await ctx.send(f"✅ Changed {member.mention}'s nickname to {nickname}")
    except Exception as e:
        await ctx.send(f"❌ Failed to change nickname: {e}")

# ==================== INFORMATION COMMANDS ====================

@bot.hybrid_command(name="serverinfo", description="Get server information")
async def serverinfo(ctx):
    """Display server information"""
    guild = ctx.guild
    embed = discord.Embed(title=f"{guild.name} Info", color=discord.Color.blue())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="Owner", value=guild.owner.mention)
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Channels", value=len(guild.channels))
    embed.add_field(name="Roles", value=len(guild.roles))
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"))
    await ctx.send(embed=embed)

@bot.hybrid_command(name="userinfo", description="Get user information")
async def userinfo(ctx, member: discord.Member = None):
    """Display user information"""
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.name}'s Info", color=member.color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Nickname", value=member.nick or "None")
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Roles", value=", ".join([r.mention for r in member.roles[1:]]) or "None")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="avatar", description="Get user's avatar")
async def avatar(ctx, member: discord.Member = None):
    """Display user's avatar"""
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.name}'s Avatar", color=member.color)
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="membercount", description="Get server member count")
async def membercount(ctx):
    """Display member count statistics"""
    guild = ctx.guild
    total = guild.member_count
    bots = sum(1 for m in guild.members if m.bot)
    humans = total - bots
    
    embed = discord.Embed(title="Member Count", color=discord.Color.green())
    embed.add_field(name="Total", value=total)
    embed.add_field(name="Humans", value=humans)
    embed.add_field(name="Bots", value=bots)
    await ctx.send(embed=embed)

# ==================== FUN COMMANDS ====================

@bot.hybrid_command(name="8ball", description="Ask the magic 8ball")
async def eightball(ctx, *, question: str):
    """Ask a question to the magic 8ball"""
    responses = [
        "It is certain.", "It is decidedly so.", "Without a doubt.",
        "Yes definitely.", "You may rely on it.", "As I see it, yes.",
        "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
        "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
        "Cannot predict now.", "Concentrate and ask again.",
        "Don't count on it.", "My reply is no.", "My sources say no.",
        "Outlook not so good.", "Very doubtful."
    ]
    await ctx.send(f"🎱 {random.choice(responses)}")

@bot.hybrid_command(name="roll", description="Roll a dice")
async def roll(ctx, sides: int = 6):
    """Roll a dice with specified sides"""
    result = random.randint(1, sides)
    await ctx.send(f"🎲 You rolled a {result}!")

@bot.hybrid_command(name="coinflip", description="Flip a coin")
async def coinflip(ctx):
    """Flip a coin"""
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"🪙 {result}!")

@bot.hybrid_command(name="meme", description="Get a random meme")
async def meme(ctx):
    """Fetch a random meme from Reddit"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://meme-api.com/gimme') as response:
                data = await response.json()
                embed = discord.Embed(title=data['title'], color=discord.Color.random())
                embed.set_image(url=data['url'])
                embed.set_footer(text=f"👍 {data['ups']} | r/{data['subreddit']}")
                await ctx.send(embed=embed)
    except:
        await ctx.send("❌ Failed to fetch meme.")

@bot.hybrid_command(name="joke", description="Get a random joke")
async def joke(ctx):
    """Fetch a random joke"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://official-joke-api.appspot.com/random_joke') as response:
                data = await response.json()
                await ctx.send(f"😄 {data['setup']}\n\n||{data['punchline']}||")
    except:
        await ctx.send("❌ Failed to fetch joke.")

@bot.hybrid_command(name="poll", description="Create a poll")
async def poll(
    ctx,
    question: str,
    option1: str,
    option2: str,
    option3: str = None,
    option4: str = None,
    option5: str = None
):
    options = [option1, option2, option3, option4, option5]
    options = [opt for opt in options if opt is not None]

    embed = discord.Embed(title="📊 " + question, color=discord.Color.blue())

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    description = ""
    for i, option in enumerate(options):
        description += f"\n{emojis[i]} {option}"

    embed.description = description
    msg = await ctx.send(embed=embed)

    for i in range(len(options)):
        await msg.add_reaction(emojis[i])

# ==================== UTILITY COMMANDS ====================

@bot.hybrid_command(name="ping", description="Check bot latency")
async def ping(ctx):
    """Check the bot's latency"""
    await ctx.send(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

@bot.hybrid_command(name="announce", description="Make an announcement")
@commands.has_permissions(manage_messages=True)
async def announce(ctx, channel: discord.TextChannel, *, message: str):
    """Send an announcement to a channel"""
    embed = discord.Embed(
        title="📢 Announcement",
        description=message,
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Announced by {ctx.author}")
    await channel.send(embed=embed)
    await ctx.send(f"✅ Announcement sent to {channel.mention}")

@bot.hybrid_command(name="say", description="Make the bot say something")
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, message: str):
    """Make the bot repeat a message"""
    await ctx.message.delete()
    await ctx.send(message)

@bot.hybrid_command(name="embed", description="Create a custom embed")
@commands.has_permissions(manage_messages=True)
async def embed_create(ctx, title: str, *, description: str):
    """Create a custom embed"""
    embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
    await ctx.send(embed=embed)

@bot.hybrid_command(name="remind", description="Set a reminder")
async def remind(ctx, time: int, *, reminder: str):
    """Set a reminder (time in minutes)"""
    await ctx.send(f"⏰ I'll remind you in {time} minutes!")
    await asyncio.sleep(time * 60)
    await ctx.send(f"{ctx.author.mention} Reminder: {reminder}")

# ==================== WELCOME/GOODBYE SYSTEM ====================

@bot.event
async def on_member_join(member):
    """Welcome new members"""
    channel = discord.utils.get(member.guild.text_channels, name='welcome')
    if channel:
        embed = discord.Embed(
            title="👋 Welcome!",
            description=f"Welcome to {member.guild.name}, {member.mention}!",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Member Count", value=f"You are member #{member.guild.member_count}")
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    """Goodbye message"""
    channel = discord.utils.get(member.guild.text_channels, name='goodbye')
    if channel:
        embed = discord.Embed(
            title="👋 Goodbye",
            description=f"{member.name} has left the server.",
            color=discord.Color.red()
        )
        await channel.send(embed=embed)

# ==================== LEVELING SYSTEM ====================

@bot.event
async def on_message(message):
    """Award XP for messages"""
    if message.author.bot:
        return
    
    # Process commands first
    await bot.process_commands(message)

# ==================== TICKET SYSTEM ====================

@bot.hybrid_command(name="ticket", description="Create a support ticket")
async def ticket(ctx):
    """Create a support ticket channel"""
    category = discord.utils.get(ctx.guild.categories, name="Tickets")
    if not category:
        category = await ctx.guild.create_category("Tickets")
    
    ticket_channel = await ctx.guild.create_text_channel(
        f"ticket-{ctx.author.name}",
        category=category
    )
    
    await ticket_channel.set_permissions(ctx.guild.default_role, read_messages=False)
    await ticket_channel.set_permissions(ctx.author, read_messages=True, send_messages=True)
    
    embed = discord.Embed(
        title="🎫 Support Ticket",
        description=f"Hello {ctx.author.mention}! Support will be with you shortly.",
        color=discord.Color.blue()
    )
    await ticket_channel.send(embed=embed)
    await ctx.send(f"✅ Ticket created: {ticket_channel.mention}")

@bot.hybrid_command(name="closeticket", description="Close a ticket")
@commands.has_permissions(manage_channels=True)
async def closeticket(ctx):
    """Close the current ticket channel"""
    if "ticket" in ctx.channel.name:
        await ctx.send("🔒 Closing ticket in 5 seconds...")
        await asyncio.sleep(5)
        await ctx.channel.delete()

# ==================== AUTO-MODERATION ====================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # automod
    bad_words = []
    if any(word in message.content.lower() for word in bad_words):
        await message.delete()
        await message.channel.send(
            f"{message.author.mention} Watch your language!",
            delete_after=5
        )
        return

    await bot.process_commands(message)

# ==================== EVENT LOGGING ====================

@bot.event
async def on_message_delete(message):
    """Log deleted messages"""
    if message.author.bot:
        return
    
    log_channel = discord.utils.get(message.guild.text_channels, name='logs')
    if log_channel:
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            description=message.content,
            color=discord.Color.red()
        )
        embed.set_author(name=message.author, icon_url=message.author.display_avatar.url)
        embed.add_field(name="Channel", value=message.channel.mention)
        await log_channel.send(embed=embed)

@bot.event
async def on_message_edit(before, after):
    """Log edited messages"""
    if before.author.bot or before.content == after.content:
        return
    
    log_channel = discord.utils.get(before.guild.text_channels, name='logs')
    if log_channel:
        embed = discord.Embed(title="✏️ Message Edited", color=discord.Color.orange())
        embed.set_author(name=before.author, icon_url=before.author.display_avatar.url)
        embed.add_field(name="Before", value=before.content[:1024], inline=False)
        embed.add_field(name="After", value=after.content[:1024], inline=False)
        embed.add_field(name="Channel", value=before.channel.mention)
        await log_channel.send(embed=embed)

# ==================== HELP COMMAND ====================

@bot.hybrid_command(name="help", description="Show all commands")
async def help_command(ctx):
    """Display all available commands"""
    embed = discord.Embed(title="🤖 Bot Commands", color=discord.Color.blue())
    
    embed.add_field(
        name="🔨 Moderation",
        value="`ban`, `unban`, `kick`, `mute`, `unmute`, `warn`, `clear`, `slowmode`, `lock`, `unlock`",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Management",
        value="`addrole`, `removerole`, `createrole`, `deleterole`, `setnick`",
        inline=False
    )
    
    embed.add_field(
        name="ℹ️ Information",
        value="`serverinfo`, `userinfo`, `avatar`, `membercount`, `ping`",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Fun",
        value="`8ball`, `roll`, `coinflip`, `meme`, `joke`, `poll`",
        inline=False
    )
    
    embed.add_field(
        name="🛠️ Utility",
        value="`announce`, `say`, `embed`, `remind`, `ticket`, `closeticket`",
        inline=False
    )
    
    await ctx.send(embed=embed)

# ==================== BOT EVENTS ====================

@bot.event
async def on_ready():
    """Bot startup event"""
    print(f'✅ {bot.user} is online!')
    print(f'Connected to {len(bot.guilds)} servers')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="your server | !help"
        )
    )

# ==================== ERROR HANDLING ====================

@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command!")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param}")
    else:
        await ctx.send(f"❌ An error occurred: {error}")

# ==================== RUN BOT ====================

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    TOKEN = os.getenv('TOKEN')
    
    if TOKEN is None or TOKEN == "your_bot_token_here":
        print("❌ Please add your bot token to the script!")
        print("Get your token from: https://discord.com/developers/applications")
    else:
        bot.run(TOKEN)
