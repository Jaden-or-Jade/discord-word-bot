import discord
from discord import app_commands
from collections import Counter
from datetime import datetime, timedelta, timezone
import re
import os
from dotenv import load_dotenv
import json
import random

load_dotenv()

USAGE_FILE = "insult_usage.json"


def load_usage():
    if not os.path.exists(USAGE_FILE):
        return {}
    with open(USAGE_FILE, "r") as f:
        return json.load(f)


def save_usage(data):
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f)

SETUPS = [
    "You communicate like",
    "Your texting style is basically",
    "The way you talk is equivalent to",
    "If messaging had a difficulty setting, yours would be"
]

TRAITS = {
    "lol_spammer": [
        "a laugh track that never ends",
        "a sitcom audience that forgot the joke",
        "someone trying to survive with 'lol' as oxygen"
    ],
    "short_texter": [
        "a dying battery trying to save power",
        "a Morse code operator on break",
        "a minimalist who took it personally"
    ],
    "essay_writer": [
        "a Wikipedia article nobody asked for",
        "a courtroom closing statement in Discord form",
        "a novelist trapped in a group chat"
    ],
    "chronically_online": [
        "a notification that never sleeps",
        "a background app that refuses to close",
        "someone permanently logged into existence"
    ],
    "repetitive_vocabulary": [
        "a broken record with WiFi",
        "a looped voice memo",
        "a dictionary stuck on 12 words"
    ]
}

CLOSERS = [
    "and honestly it shows.",
    "respectfully, it’s concerning.",
    "I say this with love (I don’t).",
    "anyway… moving on."
]

insult_usage = load_usage()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

client = MyClient()

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


# ---------------------------
# TOP WORDS COMMAND
# ---------------------------
@client.tree.command(name="topwords", description="Get most used words (optional user + time range)")
@app_commands.describe(
    user="Optional user to analyze",
    range="Time range: 100, 1000, 7d, 30d"
)
async def topwords(interaction: discord.Interaction, user: discord.Member = None, range: str = "1000"):
    await interaction.response.defer(thinking=True)

    now = datetime.now(timezone.utc)

    if range == "100":
        cutoff = now - timedelta(hours=1)
    elif range == "7d":
        cutoff = now - timedelta(days=7)
    elif range == "30d":
        cutoff = now - timedelta(days=30)
    else:
        cutoff = None

    word_counter = Counter()

    async for message in interaction.channel.history(limit=1000):
        if message.author.bot or not message.content:
            continue

        if user and message.author != user:
            continue

        if cutoff and message.created_at < cutoff:
            continue

        words = re.findall(r'\b\w+\b', message.content.lower())
        word_counter.update(words)

    stopwords = {
        "the","and","is","to","a","of","in","it","for","on","you",
        "i","that","this","with","was","but","are","be","as","at"
    }

    filtered = Counter({w: c for w, c in word_counter.items() if w not in stopwords})
    top = filtered.most_common(10)

    if not top:
        result = "No usable words found."
    else:
        result = "\n".join([f"{w}: {c}" for w, c in top])

    title = "📊 Top words"
    if user:
        title += f" for {user.display_name}"
    if range:
        title += f" ({range})"

    await interaction.followup.send(f"{title}\n\n{result}")


# ---------------------------
# ROAST COMMAND
# ---------------------------
@client.tree.command(name="roast", description="Roast a user based on their message habits")
@app_commands.describe(user="The user to roast")
async def roast(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(thinking=True)

    user_messages = []
    server_messages = []

    async for message in interaction.channel.history(limit=1000):
        if message.author.bot or not message.content:
            continue

        content = message.content.lower()
        server_messages.append(content)

        if message.author == user:
            user_messages.append(content)

    if len(user_messages) == 0:
        await interaction.followup.send(f"{user.display_name} is too mysterious to roast 😭")
        return

    user_word_count = sum(len(m.split()) for m in user_messages)
    server_word_count = sum(len(m.split()) for m in server_messages)

    user_avg_len = user_word_count / max(len(user_messages), 1)
    server_avg_len = server_word_count / max(len(server_messages), 1)

    flat_text = " ".join(user_messages)

    traits = []

    if "lol" in flat_text:
        traits.append("lol_spammer")

    if user_avg_len < server_avg_len * 0.6:
        traits.append("short_texter")

    if user_avg_len > server_avg_len * 1.5:
        traits.append("essay_writer")

    if len(user_messages) > len(server_messages) * 0.3:
        traits.append("chronically_online")

    if len(set(flat_text.split())) < 20:
        traits.append("repetitive_vocabulary")

def pick_least_used(options):
    for o in options:
        if o not in insult_usage:
            insult_usage[o] = 0

    min_count = min(insult_usage[o] for o in options)
    candidates = [o for o in options if insult_usage[o] == min_count]

    return random.choice(candidates)


roasts = []

for t in traits:
    if t in TRAITS:
        setup = pick_least_used(SETUPS)
        trait = pick_least_used(TRAITS[t])
        closer = pick_least_used(CLOSERS)

        insult_usage[setup] += 1
        insult_usage[trait] += 1
        insult_usage[closer] += 1

        roast = f"{setup} {trait} {closer}"
        roasts.append(roast)

save_usage(insult_usage)

    if not roasts:
        roasts.append("You are so normal it’s actually suspicious.")

    result = "\n".join(f"🔥 {r}" for r in roasts)
    result += f"\n\nVerdict: {user.display_name} is statistically questionable."

    await interaction.followup.send(result)

# ---------------------------
# SERVER PERSONALITY COMMAND
# ---------------------------
@client.tree.command(name="serverpersonality", description="Analyze the personality of this server")
async def serverpersonality(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    messages = []

    async for message in interaction.channel.history(limit=1000):
        if message.author.bot or not message.content:
            continue
        messages.append(message.content.lower())

    text = " ".join(messages)

    total_messages = len(messages)
    if total_messages == 0:
        await interaction.followup.send("Not enough data to analyze 😭")
        return

    word_count = sum(len(m.split()) for m in messages)
    avg_length = word_count / total_messages

    lol_count = text.count("lol") + text.count("lmao") + text.count("haha") +text.count("lmfao")
    emoji_count = len(re.findall(r'[^\w\s,]', text))
    caps_messages = sum(1 for m in messages if m.isupper() and len(m) > 3)

    # --- scoring system ---
    chaos = 0
    chill = 0
    meme = 0

    # chaos signals
    if avg_length < 6:
        chaos += 2
    if caps_messages > total_messages * 0.1:
        chaos += 2
    if emoji_count > total_messages:
        chaos += 1

    # chill signals
    if avg_length > 12:
        chill += 2
    if lol_count < total_messages * 0.1:
        chill += 1

    # meme signals
    if lol_count > total_messages * 0.2:
        meme += 2
    if emoji_count > total_messages * 1.5:
        meme += 2

    # --- classification ---
    if chaos >= 3:
        personality = "🔥 CHAOTIC GROUP CHAT ENERGY"
    elif meme >= 3:
        personality = "😂 MEME-FIRST COMMUNITY"
    elif chill >= 3:
        personality = "😌 CHILL & CONVERSATIONAL SERVER"
    else:
        personality = "⚖️ BALANCED / SLIGHTLY CONFUSED ENERGY"

    # --- extra flavor ---
    details = [
        f"Messages scanned: {total_messages}",
        f"Average message length: {avg_length:.1f} words",
        f"LOL/laugh count: {lol_count}",
        f"Emoji density: {emoji_count}"
    ]

    await interaction.followup.send(
        f"🧠 **Server Personality Report**\n\n"
        f"{personality}\n\n"
        + "\n".join(details)
    )

# ---------------------------
# RUN BOT
# ---------------------------
client.run(TOKEN)