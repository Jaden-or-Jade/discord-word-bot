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

    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}

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
    "If messaging had a difficulty setting, yours would be",
    "You're like",
    "When you talk, it's essentially like"
]

TRAITS = {
    "lol_spammer": [
        "a laugh track that never ends.",
        "a sitcom audience that forgot the joke.",
        "someone trying to survive with 'lol' as oxygen."
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
        "a dictionary stuck on 12 words.",
        "a broken NPC."
    ]
}

CLOSERS = [
    "It honestly shows.",
    "Respectfully, it’s concerning.",
    "I say this with love (I don’t).",
    "Anyway… moving on.",
    "You need help."
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
    "meme_gremlin": {
        "lol_spammer": 1.5
    },

    "essay_machine": {
        "essay_writer": 1.5
    },

    "dry_texter": {
        "short_texter": 1.5
    },

    "repeater": {
        "repetitive_vocabulary": 1.5
    },

    "spammer": {
        "chronically_online": 1.5
    }
}

ARCHETYPE_STYLES = {

    "meme_gremlin": {
        "emoji": ["💀", "😂", "😭", "💀💀"],
        "prefix": "",
        "suffix": " (bro said that unironically 💀)"
    },

    "essay_machine": {
        "emoji": ["📚", "🧠", "📝"],
        "prefix": "⚠️ ANALYSIS: ",
        "suffix": ""
    },

    "dry_texter": {
        "emoji": ["."],
        "prefix": "",
        "suffix": "."
    },

    "repeater": {
        "emoji": ["🔁"],
        "prefix": "",
        "suffix": " (this is literally all you do)"
    },

    "spammer": {
        "emoji": ["📢", "🚨"],
        "prefix": "🚨 ",
        "suffix": " — anyway."
    }
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

    choices = [
        o for o in options
        if insult_usage[o] == min_count
    ]

    return random.choice(choices)

def apply_archetype_style(text, archetype):

    style = ARCHETYPE_STYLES.get(archetype)

    if not style:
        return f"🔥 {text}"

    emoji = random.choice(style["emoji"])
    prefix = style["prefix"]
    suffix = style["suffix"]

    return f"{prefix}{emoji} {text}{suffix}"

# ---------------------------
# /TOPWORDS
# ---------------------------
@client.tree.command(
    name="topwords",
    description="Get most used words"
)

@app_commands.describe(
    user="Optional user",
    range="100, 7d, 30d"
)

async def topwords(
    interaction: discord.Interaction,
    user: discord.Member = None,
    range: str = "1000"
):

    await interaction.response.defer(thinking=True)

    now = datetime.now(timezone.utc)

    cutoff = None

    if range == "100":
        cutoff = now - timedelta(hours=1)

    elif range == "7d":
        cutoff = now - timedelta(days=7)

    elif range == "30d":
        cutoff = now - timedelta(days=30)

    counter = Counter()

    limit = 3000 if user else 1000

    async for message in interaction.channel.history(limit=limit):

        if message.author.bot or not message.content:
            continue

        if user is not None and message.author.id != user.id:
            continue

        if cutoff and message.created_at < cutoff:
            continue

        words = re.findall(
            r'\b\w+\b',
            message.content.lower()
        )

        counter.update(words)

    stopwords = {
        "the","and","is","to","a","of","in","it","for",
        "on","you","i","my","that","like","so","was",
        "me","have"
    }

    filtered = Counter({
        w: c for w, c in counter.items()
        if w not in stopwords
    })

    result = "\n".join(
        f"{w}: {c}"
        for w, c in filtered.most_common(10)
    )

    if not result:
        result = "No data"

    if user:
        result = f"{user.mention}\n\n{result}"

    await interaction.followup.send(result)

# ---------------------------
# /ROAST
# ---------------------------
@client.tree.command(
    name="roast",
    description="Roast a user"
)

@app_commands.describe(
    user="User to roast"
)

async def roast(
    interaction: discord.Interaction,
    user: discord.Member
):

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
        await interaction.followup.send(
            f"{user.mention} has no roastable data 😭"
        )
        return

    flat = " ".join(user_msgs)

    user_avg = (
        sum(len(m.split()) for m in user_msgs)
        / len(user_msgs)
    )

    server_avg = (
        sum(len(m.split()) for m in server_msgs)
        / len(server_msgs)
    )

    # ---------------------------
    # TRAIT SCORING
    # ---------------------------
    trait_scores = {

        "lol_spammer":
            int("lol" in flat),

        "short_texter":
            int(user_avg < server_avg * 0.6),

        "essay_writer":
            int(user_avg > server_avg * 1.5),

        "chronically_online":
            int(len(user_msgs) > len(server_msgs) * 0.3),

        "repetitive_vocabulary":
            int(len(set(flat.split())) < 20)
    }

    user_id = str(user.id)

    # ---------------------------
    # ENSURE PROFILE EXISTS
    # ---------------------------
    if user_id not in user_archetypes:
        user_archetypes[user_id] = {
            k: 0 for k in ARCHETYPES
        }

    profile = user_archetypes[user_id]

    if not profile:
        profile = {
            k: 0 for k in ARCHETYPES
        }

        user_archetypes[user_id] = profile

    # ---------------------------
    # CURRENT DOMINANT
    # ---------------------------
    dominant = max(
        profile,
        key=profile.get
    )

    # ---------------------------
    # APPLY ARCHETYPE BIAS
    # ---------------------------
    if dominant in ARCHETYPE_BIASES:

        for t, mult in ARCHETYPE_BIASES[dominant].items():

            if t in trait_scores:
                trait_scores[t] *= mult

    traits = [
        t for t, s in trait_scores.items()
        if s >= 1
    ]

    # ---------------------------
    # UPDATE ARCHETYPES
    # ---------------------------
    for t in traits:

        arch = TRAIT_TO_ARCHETYPE.get(t)

        if arch:
            user_archetypes[user_id][arch] += 1

    save_json(
        ARCHETYPE_FILE,
        user_archetypes
    )

    # ---------------------------
    # RECALCULATE DOMINANT
    # ---------------------------
    dominant = max(
        user_archetypes[user_id],
        key=user_archetypes[user_id].get
    )

    # ---------------------------
    # GENERATE ROASTS
    # ---------------------------
    best_trait = max(
    trait_scores,
    key=trait_scores.get
)

setup = pick_least_used(SETUPS)
trait = pick_least_used(TRAITS[best_trait])
closer = pick_least_used(CLOSERS)

insult_usage[setup] += 1
insult_usage[trait] += 1
insult_usage[closer] += 1

raw_roast = (
    f"{setup} "
    f"{trait} "
    f"{closer}"
)

styled = apply_archetype_style(
    raw_roast,
    dominant
)

roasts = [
    f"{user.mention} {styled}"
]

    save_json(
        USAGE_FILE,
        insult_usage
    )

    if not roasts:
        roasts = [
            f"{user.mention} You are aggressively normal."
        ]

    msg = "\n".join(roasts)

    msg += (
        f"\n\n🧬 Dominant archetype: "
        f"**{dominant}**"
    )

    await interaction.followup.send(msg)

# ---------------------------
# /SERVERPERSONALITY
# ---------------------------
@client.tree.command(
    name="serverpersonality",
    description="Analyze server vibe"
)

async def serverpersonality(
    interaction: discord.Interaction
):

    await interaction.response.defer(thinking=True)

    msgs = []

    async for m in interaction.channel.history(limit=1000):

        if m.author.bot or not m.content:
            continue

        msgs.append(m.content.lower())

    if not msgs:
        await interaction.followup.send(
            "Not enough data 😭"
        )
        return

    text = " ".join(msgs)

    avg = (
        sum(len(m.split()) for m in msgs)
        / len(msgs)
    )

    lol = (
        text.count("lol")
        + text.count("lmao")
    )

    emoji = len(
        re.findall(r'[^\w\s]', text)
    )

    if avg < 6 or emoji > len(msgs):
        vibe = "🔥 CHAOTIC"

    elif lol > len(msgs) * 0.2:
        vibe = "😂 MEME"

    elif avg > 12:
        vibe = "😌 CHILL"

    else:
        vibe = "⚖️ BALANCED"

    await interaction.followup.send(
        f"{vibe}\nAvg length: {avg:.1f}"
    )

# ---------------------------
# RUN
# ---------------------------
client.run(TOKEN)