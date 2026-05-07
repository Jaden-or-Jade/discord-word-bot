import discord
from discord import app_commands
from collections import Counter
from datetime import datetime, timedelta, timezone
import re
import os
from dotenv import load_dotenv
import json
import random
import string

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

USAGE_FILE = "insult_usage.json"
ARCHETYPE_FILE = "user_archetypes.json"
STOPWORDS_FILE = "stopwords.txt"

# ---------------------------
# FILE HELPERS
# ---------------------------
def load_json(file):
    if not os.path.exists(file):
        return {}
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def load_stopwords():
    if not os.path.exists(STOPWORDS_FILE):
        return set()

    with open(STOPWORDS_FILE, "r") as f:
        return {line.strip().lower() for line in f if line.strip()}

STOPWORDS = load_stopwords()
STOPWORDS.update(set(string.ascii_letters))
insult_usage = load_json(USAGE_FILE)
user_archetypes = load_json(ARCHETYPE_FILE)

# ---------------------------
# ROAST DATA
# ---------------------------
SETUPS = [
    "You communicate like",
    "Your texting style is basically",
    "The way you talk is equivalent to",
    "If messaging had a difficulty setting, yours would be",
    "You're like",
]

TRAITS = {
    "lol_spammer": [
        "a laugh track that never ends.",
        "a sitcom audience that forgot the joke.",
        "someone surviving on 'lol' like oxygen."
    ],
    "short_texter": [
        "a dying battery trying to save power.",
        "a Morse code operator on break.",
        "a minimalist who took it personally."
    ],
    "essay_writer": [
        "a Wikipedia article nobody asked for.",
        "a courtroom closing statement in Discord form.",
        "a novelist trapped in a group chat."
    ],
    "chronically_online": [
        "a notification that never sleeps.",
        "a background app that refuses to close.",
        "someone permanently logged into existence."
    ],
    "repetitive_vocabulary": [
        "a broken record with WiFi.",
        "a looped voice memo.",
        "a dictionary stuck on 12 words."
    ]
}

CLOSERS = [
    "It shows.",
    "Respectfully, concerning.",
    "I say this with love (I don’t).",
    "Anyway… moving on.",
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

ARCHETYPE_STYLES = {
    "meme_gremlin": {"emoji": ["💀", "😂", "😭"], "prefix": "", "suffix": " 💀"},
    "essay_machine": {"emoji": ["📚", "🧠"], "prefix": "⚠️ ", "suffix": ""},
    "dry_texter": {"emoji": ["."], "prefix": "", "suffix": "."},
    "repeater": {"emoji": ["🔁"], "prefix": "", "suffix": " (repeat behavior detected)"},
    "spammer": {"emoji": ["📢", "🚨"], "prefix": "🚨 ", "suffix": " — anyway."}
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
        await self.tree.sync()

client = MyClient()

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

# ---------------------------
# HELPERS
# ---------------------------
def pick_least_used(options):
    for o in options:
        if o not in insult_usage:
            insult_usage[o] = 0

    min_count = min(insult_usage[o] for o in options)
    candidates = [o for o in options if insult_usage[o] == min_count]
    return random.choice(candidates)

def style(text, archetype):
    s = ARCHETYPE_STYLES.get(archetype)
    if not s:
        return f"🔥 {text}"
    return f"{s['prefix']}{random.choice(s['emoji'])} {text}{s['suffix']}"

# ---------------------------
# TOPWORDS
# ---------------------------
@client.tree.command(name="topwords", description="Get most used words")
async def topwords(interaction: discord.Interaction, user: discord.Member = None):
    await interaction.response.defer(thinking=True)

    counter = Counter()

    async for m in interaction.channel.history(limit=1500):
        if m.author.bot or not m.content:
            continue
        if user and m.author.id != user.id:
            continue

        words = re.findall(r"\b\w+\b", m.content.lower())

        filtered_words = [
            w for w in words
            if w.isalpha() and w not in STOPWORDS
        ]

        counter.update(filtered_words)

    result = "\n".join(
        f"{w}: {c}" for w, c in counter.most_common(10)
    ) or "No data"

    if user:
        await interaction.followup.send(
            f"📊 Top words for {user.mention}\n\n{result}"
        )
    else:
        await interaction.followup.send(
            f"📊 Top server words\n\n{result}"
        )

# ---------------------------
# ROAST (FIXED: SINGLE ROAST ONLY)
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

        if m.author.id == user.id:
            user_msgs.append(text)

    if not user_msgs:
        await interaction.followup.send(f"{user.mention} has no data 😭")
        return

    flat = " ".join(user_msgs)

    user_avg = sum(len(m.split()) for m in user_msgs) / len(user_msgs)
    server_avg = sum(len(m.split()) for m in server_msgs) / len(server_msgs)

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

    profile = user_archetypes[user_id]

    dominant = max(profile, key=profile.get)

    if dominant in ARCHETYPE_BIASES:
        for t, mult in ARCHETYPE_BIASES[dominant].items():
            trait_scores[t] *= mult

    best_trait = max(trait_scores, key=trait_scores.get)

    arch = TRAIT_TO_ARCHETYPE.get(best_trait)
    if arch:
        user_archetypes[user_id][arch] += 1

    save_json(ARCHETYPE_FILE, user_archetypes)

    setup = pick_least_used(SETUPS)
    trait = random.choice(TRAITS[best_trait])
    closer = pick_least_used(CLOSERS)

    insult_usage[setup] = insult_usage.get(setup, 0) + 1
    insult_usage[trait] = insult_usage.get(trait, 0) + 1
    insult_usage[closer] = insult_usage.get(closer, 0) + 1

    save_json(USAGE_FILE, insult_usage)

    raw = f"{setup} {trait} {closer}"
    final = style(raw, dominant)

    msg = f"{user.mention} {final}\n\n🧬 {dominant}"

    await interaction.followup.send(msg)

# ---------------------------
# RUN
# ---------------------------
client.run(TOKEN)