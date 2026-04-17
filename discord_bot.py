import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import json
import os
from datetime import datetime, timedelta
import aiohttp

from discord.ui import Button, View

# ==================== GAME VIEWS ====================

class RPSView(View):
    def __init__(self, user):
        super().__init__()
        self.user = user

    async def interaction_check(self, interaction):
        return interaction.user == self.user

    async def play(self, interaction, choice):
        bot_choice = random.choice(["rock", "paper", "scissors"])

        if choice == bot_choice:
            result = "🤝 It's a tie!"
        elif (choice == "rock" and bot_choice == "scissors") or \
             (choice == "paper" and bot_choice == "rock") or \
             (choice == "scissors" and bot_choice == "paper"):
            result = "🎉 You win!"
        else:
            result = "💀 You lose!"

        await interaction.response.edit_message(
            content=f"You chose **{choice}**\nBot chose **{bot_choice}**\n{result}",
            view=None
        )

    @discord.ui.button(label="🪨 Rock", style=discord.ButtonStyle.primary)
    async def rock(self, interaction, button):
        await self.play(interaction, "rock")

    @discord.ui.button(label="📄 Paper", style=discord.ButtonStyle.success)
    async def paper(self, interaction, button):
        await self.play(interaction, "paper")

    @discord.ui.button(label="✂️ Scissors", style=discord.ButtonStyle.danger)
    async def scissors(self, interaction, button):
        await self.play(interaction, "scissors")


class TicTacToeButton(Button):
    def __init__(self, x, y):
        super().__init__(style=discord.ButtonStyle.secondary, label='\u200b', row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction):
        view: TicTacToeView = self.view
        
        if interaction.user != view.current_player:
            await interaction.response.send_message("❌ It's not your turn!", ephemeral=True)
            return

        if view.board[self.x][self.y] != 0:
            await interaction.response.send_message("❌ That spot is taken!", ephemeral=True)
            return

        view.board[self.x][self.y] = view.current_marker
        self.label = view.current_marker
        self.style = discord.ButtonStyle.success if view.current_marker == "X" else discord.ButtonStyle.danger
        self.disabled = True

        winner = view.check_winner()
        if winner:
            for child in view.children:
                child.disabled = True
            await interaction.response.edit_message(content=f"🎉 {view.current_player.mention} wins!", view=view)
            view.stop()
        elif view.is_board_full():
            for child in view.children:
                child.disabled = True
            await interaction.response.edit_message(content="🤝 It's a tie!", view=view)
            view.stop()
        else:
            view.current_player = view.player2 if view.current_player == view.player1 else view.player1
            view.current_marker = "O" if view.current_marker == "X" else "X"
            await interaction.response.edit_message(
                content=f"**Tic Tac Toe**\n{view.player1.mention} (X) vs {view.player2.mention} (O)\n\nCurrent turn: {view.current_player.mention}",
                view=view
            )


class TicTacToeView(View):
    def __init__(self, player1, player2):
        super().__init__()
        self.player1 = player1
        self.player2 = player2
        self.current_player = player1
        self.current_marker = "X"
        self.board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]

        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))

    def check_winner(self):
        # Check rows, columns, and diagonals
        for i in range(3):
            if self.board[i][0] == self.board[i][1] == self.board[i][2] != 0:
                return True
            if self.board[0][i] == self.board[1][i] == self.board[2][i] != 0:
                return True
        
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != 0:
            return True
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != 0:
            return True
        
        return False

    def is_board_full(self):
        for row in self.board:
            if 0 in row:
                return False
        return True


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
    embed = discord.Embed(title=f"📊 {guild.name}", color=discord.Color.blue())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    
    embed.add_field(name="Owner", value=guild.owner.mention)
    embed.add_field(name="Created", value=guild.created_at.strftime("%b %d, %Y"))
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Roles", value=len(guild.roles))
    embed.add_field(name="Channels", value=len(guild.channels))
    embed.add_field(name="Emojis", value=len(guild.emojis))
    
    await ctx.send(embed=embed)

@bot.hybrid_command(name="userinfo", description="Get user information")
async def userinfo(ctx, member: discord.Member = None):
    """Display user information"""
    member = member or ctx.author
    embed = discord.Embed(title=f"👤 {member}", color=member.color)
    embed.set_thumbnail(url=member.display_avatar.url)
    
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Nickname", value=member.nick or "None")
    embed.add_field(name="Status", value=str(member.status).title())
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%b %d, %Y"))
    embed.add_field(name="Account Created", value=member.created_at.strftime("%b %d, %Y"))
    embed.add_field(name="Roles", value=len(member.roles) - 1)
    
    await ctx.send(embed=embed)

@bot.hybrid_command(name="avatar", description="Get user's avatar")
async def avatar(ctx, member: discord.Member = None):
    """Display user's avatar"""
    member = member or ctx.author
    embed = discord.Embed(title=f"{member}'s Avatar", color=discord.Color.blue())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="membercount", description="Get server member count")
async def membercount(ctx):
    """Display member count"""
    await ctx.send(f"👥 This server has **{ctx.guild.member_count}** members!")

@bot.hybrid_command(name="ping", description="Check bot latency")
async def ping(ctx):
    """Check bot's latency"""
    await ctx.send(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

# ==================== FUN COMMANDS (ORIGINAL) ====================

@bot.hybrid_command(name="8ball", description="Ask the magic 8ball")
async def eightball(ctx, *, question: str):
    """Ask the magic 8ball a question"""
    responses = [
        "Yes", "No", "Maybe", "Definitely", "Absolutely not",
        "Ask again later", "Cannot predict now", "Don't count on it",
        "It is certain", "Without a doubt", "Outlook good"
    ]
    await ctx.send(f"🎱 {random.choice(responses)}")

@bot.hybrid_command(name="roll", description="Roll a dice")
async def roll(ctx, sides: int = 6):
    """Roll a dice with specified sides"""
    await ctx.send(f"🎲 You rolled a **{random.randint(1, sides)}**!")

@bot.hybrid_command(name="coinflip", description="Flip a coin")
async def coinflip(ctx):
    """Flip a coin"""
    await ctx.send(f"🪙 {random.choice(['Heads', 'Tails'])}!")

@bot.hybrid_command(name="meme", description="Get a random meme")
async def meme(ctx):
    """Fetch a random meme"""
    async with aiohttp.ClientSession() as session:
        async with session.get('https://meme-api.com/gimme') as resp:
            if resp.status == 200:
                data = await resp.json()
                embed = discord.Embed(title=data['title'], color=discord.Color.random())
                embed.set_image(url=data['url'])
                embed.set_footer(text=f"👍 {data['ups']} upvotes")
                await ctx.send(embed=embed)

@bot.hybrid_command(name="joke", description="Get a random joke")
async def joke(ctx):
    """Fetch a random joke"""
    async with aiohttp.ClientSession() as session:
        async with session.get('https://official-joke-api.appspot.com/random_joke') as resp:
            if resp.status == 200:
                data = await resp.json()
                await ctx.send(f"😂 {data['setup']}\n||{data['punchline']}||")

@bot.hybrid_command(name="poll", description="Create a poll")
async def poll(
    ctx,
    question: str,
    option1: str,
    option2: str,
    option3: str = None,
    option4: str = None,
    option5: str = None,
    option6: str = None,
    option7: str = None,
    option8: str = None,
    option9: str = None,
    option10: str = None
):
    """Create a poll with reactions"""

    options = [
        option1, option2, option3, option4, option5,
        option6, option7, option8, option9, option10
    ]

    # remove None values
    options = [opt for opt in options if opt is not None]

    if len(options) < 2:
        await ctx.send("❌ Please provide at least 2 options!")
        return

    embed = discord.Embed(
        title="📊 Poll",
        description=question,
        color=discord.Color.blue()
    )

    reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

    for i, option in enumerate(options):
        embed.add_field(
            name=f"{reactions[i]} Option {i+1}",
            value=option,
            inline=False
        )

    message = await ctx.send(embed=embed)

    for i in range(len(options)):
        await message.add_reaction(reactions[i])

@bot.hybrid_command(name="rps", description="Play Rock Paper Scissors")
async def rps(ctx):
    """Play Rock Paper Scissors with the bot"""
    view = RPSView(ctx.author)
    await ctx.send("🎮 **Rock Paper Scissors!** Choose your move:", view=view)

# ==================== NEW FUN GAMES ====================

@bot.hybrid_command(name="trivia", description="Play a trivia quiz game")
async def trivia(ctx):
    """Play trivia quiz"""
    async with aiohttp.ClientSession() as session:
        async with session.get('https://opentdb.com/api.php?amount=1&type=multiple') as resp:
            if resp.status == 200:
                data = await resp.json()
                question_data = data['results'][0]
                
                question = question_data['question'].replace('&quot;', '"').replace('&#039;', "'")
                correct = question_data['correct_answer'].replace('&quot;', '"').replace('&#039;', "'")
                incorrect = [ans.replace('&quot;', '"').replace('&#039;', "'") for ans in question_data['incorrect_answers']]
                
                all_answers = incorrect + [correct]
                random.shuffle(all_answers)
                
                embed = discord.Embed(
                    title="🧠 Trivia Time!",
                    description=question,
                    color=discord.Color.purple()
                )
                embed.add_field(name="Category", value=question_data['category'])
                embed.add_field(name="Difficulty", value=question_data['difficulty'].title())
                
                for i, answer in enumerate(all_answers, 1):
                    embed.add_field(name=f"Option {i}", value=answer, inline=False)
                
                await ctx.send(embed=embed)
                await ctx.send(f"💡 Type the number (1-4) of your answer! You have 15 seconds.")
                
                def check(m):
                    return m.author == ctx.author and m.content.isdigit() and 1 <= int(m.content) <= 4
                
                try:
                    msg = await bot.wait_for('message', check=check, timeout=15.0)
                    user_answer = all_answers[int(msg.content) - 1]
                    
                    if user_answer == correct:
                        await ctx.send(f"✅ **Correct!** The answer was: {correct}")
                    else:
                        await ctx.send(f"❌ **Wrong!** The correct answer was: {correct}")
                except asyncio.TimeoutError:
                    await ctx.send(f"⏰ **Time's up!** The correct answer was: {correct}")

@bot.hybrid_command(name="guess", description="Guess the number game")
async def guess(ctx, max_number: int = 100):
    """Guess a number between 1 and max_number"""
    number = random.randint(1, max_number)
    attempts = 0
    
    await ctx.send(f"🎯 I'm thinking of a number between 1 and {max_number}. You have 5 attempts!")
    
    def check(m):
        return m.author == ctx.author and m.content.isdigit()
    
    while attempts < 5:
        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            guess = int(msg.content)
            attempts += 1
            
            if guess == number:
                await ctx.send(f"🎉 **Correct!** You guessed it in {attempts} attempt(s)!")
                return
            elif guess < number:
                await ctx.send(f"📈 Higher! ({5 - attempts} attempts left)")
            else:
                await ctx.send(f"📉 Lower! ({5 - attempts} attempts left)")
        except asyncio.TimeoutError:
            await ctx.send(f"⏰ Time's up! The number was {number}")
            return
    
    await ctx.send(f"💀 Game over! The number was {number}")

@bot.hybrid_command(name="scramble", description="Word scramble game")
async def scramble(ctx):
    """Unscramble the word"""
    words = [
        "python", "discord", "computer", "keyboard", "monitor", "internet",
        "programming", "developer", "algorithm", "database", "network", "server"
    ]
    
    word = random.choice(words)
    scrambled = ''.join(random.sample(word, len(word)))
    
    await ctx.send(f"🔤 **Unscramble this word:** `{scrambled}`\n⏰ You have 20 seconds!")
    
    def check(m):
        return m.author == ctx.author
    
    try:
        msg = await bot.wait_for('message', check=check, timeout=20.0)
        
        if msg.content.lower() == word:
            await ctx.send(f"✅ **Correct!** The word was `{word}`")
        else:
            await ctx.send(f"❌ **Wrong!** The word was `{word}`")
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ **Time's up!** The word was `{word}`")

@bot.hybrid_command(name="truthordare", description="Play Truth or Dare")
async def truthordare(ctx, choice: str = None):
    """Play Truth or Dare"""
    truths = [
        "What's the most embarrassing thing you've done?",
        "What's your biggest fear?",
        "What's a secret you've never told anyone?",
        "Who was your first crush?",
        "What's the worst lie you've ever told?",
        "What's your most embarrassing childhood memory?",
    ]
    
    dares = [
        "Send a funny selfie",
        "Do 20 pushups and post a video",
        "Change your nickname to 'Chicken Nugget' for 1 hour",
        "Send a voice message singing your favorite song",
        "Post an embarrassing photo from your camera roll",
        "Do a handstand (or try to) and post a pic",
    ]
    
    if choice and choice.lower() == "truth":
        await ctx.send(f"🤔 **Truth:** {random.choice(truths)}")
    elif choice and choice.lower() == "dare":
        await ctx.send(f"🎯 **Dare:** {random.choice(dares)}")
    else:
        await ctx.send("❌ Please choose 'truth' or 'dare'! Example: `/truthordare truth`")

@bot.hybrid_command(name="wouldyourather", description="Would You Rather game")
async def wouldyourather(ctx):
    """Play Would You Rather"""
    questions = [
        ("have the ability to fly", "be invisible"),
        ("live in the past", "live in the future"),
        ("have unlimited money", "have unlimited time"),
        ("never use social media again", "never watch another movie/TV show"),
        ("be able to talk to animals", "be able to speak all languages"),
        ("have superhuman strength", "have superhuman intelligence"),
        ("explore space", "explore the ocean"),
        ("always be 10 minutes late", "always be 20 minutes early"),
    ]
    
    option1, option2 = random.choice(questions)
    
    embed = discord.Embed(
        title="🤔 Would You Rather...",
        description=f"**A)** {option1}\n\n**B)** {option2}",
        color=discord.Color.gold()
    )
    
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🇦")
    await msg.add_reaction("🇧")

@bot.hybrid_command(name="tictactoe", description="Play Tic Tac Toe")
async def tictactoe(ctx, opponent: discord.Member):
    """Play Tic Tac Toe with another member"""
    if opponent.bot:
        await ctx.send("❌ You can't play with a bot!")
        return
    
    if opponent == ctx.author:
        await ctx.send("❌ You can't play with yourself!")
        return
    
    view = TicTacToeView(ctx.author, opponent)
    await ctx.send(
        f"**Tic Tac Toe**\n{ctx.author.mention} (X) vs {opponent.mention} (O)\n\nCurrent turn: {ctx.author.mention}",
        view=view
    )

@bot.hybrid_command(name="blackjack", description="Play Blackjack")
async def blackjack(ctx):
    """Play a simple game of Blackjack"""
    def card_value(card):
        if card in ['J', 'Q', 'K']:
            return 10
        elif card == 'A':
            return 11
        else:
            return int(card)
    
    def hand_value(hand):
        value = sum(card_value(card) for card in hand)
        # Adjust for Aces
        aces = hand.count('A')
        while value > 21 and aces:
            value -= 10
            aces -= 1
        return value
    
    deck = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'] * 4
    random.shuffle(deck)
    
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]
    
    embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.green())
    embed.add_field(name="Your Hand", value=f"{' '.join(player_hand)} (Value: {hand_value(player_hand)})")
    embed.add_field(name="Dealer's Hand", value=f"{dealer_hand[0]} 🎴")
    
    await ctx.send(embed=embed)
    await ctx.send("Type `hit` to draw a card or `stand` to stop!")
    
    def check(m):
        return m.author == ctx.author and m.content.lower() in ['hit', 'stand']
    
    while hand_value(player_hand) < 21:
        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            
            if msg.content.lower() == 'stand':
                break
            
            player_hand.append(deck.pop())
            player_val = hand_value(player_hand)
            
            embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.green())
            embed.add_field(name="Your Hand", value=f"{' '.join(player_hand)} (Value: {player_val})")
            embed.add_field(name="Dealer's Hand", value=f"{dealer_hand[0]} 🎴")
            
            await ctx.send(embed=embed)
            
            if player_val > 21:
                await ctx.send("💀 **BUST!** You went over 21. Dealer wins!")
                return
        except asyncio.TimeoutError:
            await ctx.send("⏰ Time's up! Dealer wins by default.")
            return
    
    # Dealer's turn
    while hand_value(dealer_hand) < 17:
        dealer_hand.append(deck.pop())
    
    player_val = hand_value(player_hand)
    dealer_val = hand_value(dealer_hand)
    
    final_embed = discord.Embed(title="🃏 Final Results", color=discord.Color.gold())
    final_embed.add_field(name="Your Hand", value=f"{' '.join(player_hand)} (Value: {player_val})")
    final_embed.add_field(name="Dealer's Hand", value=f"{' '.join(dealer_hand)} (Value: {dealer_val})")
    
    if dealer_val > 21:
        final_embed.add_field(name="Result", value="🎉 **YOU WIN!** Dealer busted!", inline=False)
    elif player_val > dealer_val:
        final_embed.add_field(name="Result", value="🎉 **YOU WIN!**", inline=False)
    elif player_val == dealer_val:
        final_embed.add_field(name="Result", value="🤝 **TIE!**", inline=False)
    else:
        final_embed.add_field(name="Result", value="💀 **DEALER WINS!**", inline=False)
    
    await ctx.send(embed=final_embed)

# ==================== UTILITY COMMANDS ====================

@bot.hybrid_command(name="announce", description="Make an announcement")
@commands.has_permissions(administrator=True)
async def announce(ctx, channel: discord.TextChannel, *, message: str):
    """Send an announcement to a channel"""
    embed = discord.Embed(
        title="📢 Announcement",
        description=message,
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Announced by {ctx.author}")
    await channel.send(embed=embed)
    await ctx.send("✅ Announcement sent!")

@bot.hybrid_command(name="say", description="Make the bot say something")
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, message: str):
    """Make the bot repeat a message"""
    await ctx.message.delete()
    await ctx.send(message)

@bot.hybrid_command(name="embed", description="Create a custom embed")
@commands.has_permissions(manage_messages=True)
async def embed_command(ctx, title: str, *, description: str):
    """Create a custom embed message"""
    embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
    await ctx.send(embed=embed)

@bot.hybrid_command(name="remind", description="Set a reminder")
async def remind(ctx, time: int, *, reminder: str):
    """Set a reminder in minutes"""
    await ctx.send(f"⏰ I'll remind you in {time} minute(s)!")
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
        name="🎮 Fun & Games",
        value="`8ball`, `roll`, `coinflip`, `meme`, `joke`, `poll`, `rps`, `trivia`, `guess`, `scramble`, `truthordare`, `wouldyourather`, `tictactoe`, `blackjack`",
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
    try:
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("❌ You don't have permission!", ephemeral=True)
        elif isinstance(error, commands.MemberNotFound):
            await ctx.reply("❌ Member not found!", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"❌ Missing argument: {error.param}", ephemeral=True)
        else:
            await ctx.reply(f"❌ Error: {error}", ephemeral=True)
    except:
        pass  # prevents crash if interaction expired

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