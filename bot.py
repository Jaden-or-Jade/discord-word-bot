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

TOKEN = os.getenv("DISCORD_TOKEN")

USAGE_FILE = "insult_usage.json"
ARCHETYPE_FILE = "user_archetypes.json"

# ---------------------------
# FILE HELPERS
# ---------------------------
def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

insult_usage = load_json(USAGE_FILE)
user_archetypes = load_json(ARCHETYPE_FILE)

# ---------------------------
# ROAST DATA
# ---------------------------
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

ARCHETYPES = {
    "spammer": 0,
    "essay_machine": 0,
    "ghost": 0,
    "meme_gremlin": 0,
    "repeater": 0,
    "dry_texter": 0
}

TRAIT_TO_ARCHETYPE = {
    "lol_spammer": "meme_gremlin",
    "short_texter": "dry_texter",
    "essay_writer": "essay_machine",
    "chronically_online": "spammer",
    "repetitive_vocabulary": "repeater"
}

ARCHETYPE_BIASES = {
    "meme_gremlin": {"lol_spammer": 1.5},
    "essay_machine": {"essay_writer": 1.5},
    "dry_texter": {"short_texter": 1.5},
    "repeater": {"repetitive_vocabulary": 1.5},
    "spammer": {"chronically_online": 1.5}
}

# ---------------------------
# BOT SETUP
# ---------------------------
intents = discord.Intents.default()
intents.message_content = True

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        synced = await self.tree.sync()
        print(f"Synced {len(synced)} commands")
        for cmd in synced:
            print(f"- {cmd.name}")

client = MyClient()

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

# ---------------------------
# HELPER: SMART PICK
# ---------------------------
def pick_least_used(options):
    for o in options:
        if o not in insult_usage:
            insult_usage[o] = 0

    min_count = min(insult_usage[o] for o in options)
    choices = [o for o in options if insult_usage[o] == min_count]
    return random.choice(choices)

# ---------------------------
# /TOPWORDS
# ---------------------------
@client.tree.command(name="topwords", description="Get most used words")
@app_commands.describe(user="Optional user", range="100, 7d, 30d")
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

    counter = Counter()

    async for message in interaction.channel.history(limit=1000):
        if message.author.bot or not message.content:
            continue
        if user and message.author != user:
            continue
        if cutoff and message.created_at < cutoff:
            continue

        words = re.findall(r'\b\w+\b', message.content.lower())
        counter.update(words)

    stopwords = {"b","c","d","e","f","g","h","j","k","m","n","o","p","q","r","s","t","u","v","w","x","y","z","the","and","is","to","a","of","in","it","for","on","you","i","my","that","like","so","was","me","have"}
    filtered = Counter({w: c for w, c in counter.items() if w not in stopwords})

    result = "\n".join(f"{w}: {c}" for w, c in filtered.most_common(10)) or "No data"

    await interaction.followup.send(result)

# ---------------------------
# /ROAST
# ---------------------------
@client.tree.command(name="roast", description="Roast a user")
async def roast(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(thinking=True)

    user_msgs = []
    server_msgs = []

    async for m in interaction.channel.history(limit=1000):
        if m.author.bot or not m.content:
            continue
        text = m.content.lower()
        server_msgs.append(text)
        if m.author == user:
            user_msgs.append(text)

    if not user_msgs:
        await interaction.followup.send("No data to roast 😭")
        return

    flat = " ".join(user_msgs)

    user_avg = sum(len(m.split()) for m in user_msgs) / len(user_msgs)
    server_avg = sum(len(m.split()) for m in server_msgs) / len(server_msgs)

    # --- trait scoring ---
    trait_scores = {
        "lol_spammer": int("lol" in flat),
        "short_texter": int(user_avg < server_avg * 0.6),
        "essay_writer": int(user_avg > server_avg * 1.5),
        "chronically_online": int(len(user_msgs) > len(server_msgs) * 0.3),
        "repetitive_vocabulary": int(len(set(flat.split())) < 20)
    }

    user_id = str(user.id)

    if user_id not in user_archetypes:
        user_archetypes[user_id] = {k: 0 for k in ARCHETYPES}

    dominant = max(user_archetypes[user_id], key=user_archetypes[user_id].get)

    # apply bias
    if dominant in ARCHETYPE_BIASES:
        for t, mult in ARCHETYPE_BIASES[dominant].items():
            trait_scores[t] *= mult

    traits = [t for t, s in trait_scores.items() if s >= 1]

    # update archetypes
    for t in traits:
        if t in TRAIT_TO_ARCHETYPE:
            arch = TRAIT_TO_ARCHETYPE[t]
            user_archetypes[user_id][arch] += 1

    save_json(ARCHETYPE_FILE, user_archetypes)

    # generate roasts
    roasts = []
    for t in traits:
        setup = pick_least_used(SETUPS)
        trait = pick_least_used(TRAITS[t])
        closer = pick_least_used(CLOSERS)

        insult_usage[setup] += 1
        insult_usage[trait] += 1
        insult_usage[closer] += 1

        roasts.append(f"{setup} {trait} {closer}")

    save_json(USAGE_FILE, insult_usage)

    if not roasts:
        roasts = ["You are aggressively normal."]

    msg = "\n".join(f"🔥 {r}" for r in roasts)
    msg += f"\n\nDominant archetype: {dominant}"

    await interaction.followup.send(msg)

# ---------------------------
# /SERVERPERSONALITY
# ---------------------------
@client.tree.command(name="serverpersonality", description="Analyze server vibe")
async def serverpersonality(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    msgs = []

    async for m in interaction.channel.history(limit=1000):
        if m.author.bot or not m.content:
            continue
        msgs.append(m.content.lower())

    if not msgs:
        await interaction.followup.send("Not enough data 😭")
        return

    text = " ".join(msgs)
    avg = sum(len(m.split()) for m in msgs) / len(msgs)

    lol = text.count("lol") + text.count("lmao")
    emoji = len(re.findall(r'[^\w\s]', text))

    chaos = avg < 6 or emoji > len(msgs)
    meme = lol > len(msgs) * 0.2
    chill = avg > 12

    if chaos:
        vibe = "🔥 CHAOTIC"
    elif meme:
        vibe = "😂 MEME"
    elif chill:
        vibe = "😌 CHILL"
    else:
        vibe = "⚖️ BALANCED"

    await interaction.followup.send(f"{vibe}\nAvg length: {avg:.1f}")

# ---------------------------
# RUN
# ---------------------------
client.run(TOKEN)