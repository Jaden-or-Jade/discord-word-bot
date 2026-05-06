import discord
from discord import app_commands
from collections import Counter, defaultdict
from datetime import datetime, timezone
import re
import os
from dotenv import load_dotenv
import json
import random

load_dotenv()

# ---------------------------
# FILES
# ---------------------------
USAGE_FILE = "insult_usage.json"
ARCHETYPE_FILE = "user_archetypes.json"
PROFILE_FILE = "user_profiles.json"

# ---------------------------
# LOAD / SAVE
# ---------------------------
def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


insult_usage = load_json(USAGE_FILE)
user_archetypes = load_json(ARCHETYPE_FILE)
user_profiles = load_json(PROFILE_FILE)

# ---------------------------
# ROAST BANK
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
        "someone surviving purely on 'lol'"
    ],
    "short_texter": [
        "a dying battery conserving every character",
        "a Morse code operator on break",
        "minimalism taken personally"
    ],
    "essay_writer": [
        "a Wikipedia article nobody asked for",
        "a courtroom closing statement in Discord form",
        "a novelist trapped in a group chat"
    ],
    "chronically_online": [
        "a notification that never sleeps",
        "a background app refusing to close",
        "someone permanently logged in"
    ],
    "repetitive_vocabulary": [
        "a broken record with WiFi",
        "a looped voice memo",
        "a 12-word vocabulary prison"
    ]
}

CLOSERS = [
    "and honestly it shows.",
    "respectfully, it's concerning.",
    "I say this with love (I don't).",
    "anyway... moving on."
]

# ---------------------------
# ARCHETYPES
# ---------------------------
ARCHETYPES = {
    "meme_gremlin": ["lol_spammer"],
    "dry_texter": ["short_texter"],
    "essay_machine": ["essay_writer"],
    "spammer": ["chronically_online"],
    "repeater": ["repetitive_vocabulary"]
}

ARCHETYPE_DECAY = 0.98

TRAIT_TO_ARCHETYPE = {
    "lol_spammer": "meme_gremlin",
    "short_texter": "dry_texter",
    "essay_writer": "essay_machine",
    "chronically_online": "spammer",
    "repetitive_vocabulary": "repeater"
}

ARCHETYPE_BIASES = {
    "meme_gremlin": {"lol_spammer": 1.4},
    "essay_machine": {"essay_writer": 1.5},
    "dry_texter": {"short_texter": 1.6},
    "repeater": {"repetitive_vocabulary": 1.8},
    "spammer": {"chronically_online": 1.2}
}

# ---------------------------
# DISCORD SETUP
# ---------------------------
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
# PROFILE SYSTEM
# ---------------------------
def update_profile(user_id, messages, traits):

    if user_id not in user_profiles:
        user_profiles[user_id] = {
            "verbosity": 0,
            "chaos": 0,
            "repetition": 0,
            "emotion": 0,
            "predictability": 1.0
        }

    p = user_profiles[user_id]

    msg_count = len(messages)
    avg_len = sum(len(m.split()) for m in messages) / max(msg_count, 1)

    flat = " ".join(messages)

    p["verbosity"] = (p["verbosity"] * 0.9) + (avg_len * 0.1)
    p["chaos"] += flat.count("lol") + flat.count("!") * 0.5

    words = flat.split()
    p["repetition"] = 1 - (len(set(words)) / max(len(words), 1))

    p["emotion"] = sum(1 for m in messages if m.isupper()) / max(msg_count, 1)

    p["predictability"] = max(0.1, 1 - p["chaos"] / 50)

    user_profiles[user_id] = p
    save_json(PROFILE_FILE, user_profiles)


# ---------------------------
# ARCHETYPE SYSTEM
# ---------------------------
def update_archetype(user_id, traits):

    if user_id not in user_archetypes:
        user_archetypes[user_id] = defaultdict(float)

    profile = user_archetypes[user_id]

    # decay old identity
    for k in list(profile.keys()):
        profile[k] *= ARCHETYPE_DECAY

    # grow new identity
    for t in traits:
        for arch, mapped in ARCHETYPES.items():
            if t in mapped:
                profile[arch] += 1

    user_archetypes[user_id] = dict(profile)
    save_json(ARCHETYPE_FILE, user_archetypes)


def get_dominant(user_id):
    profile = user_archetypes.get(user_id, {})
    if not profile:
        return []
    top = max(profile.values())
    return [k for k, v in profile.items() if v >= top * 0.7]


# ---------------------------
# ANTI-REPEAT
# ---------------------------
def pick_least_used(options):
    for o in options:
        insult_usage.setdefault(o, 0)

    min_v = min(insult_usage[o] for o in options)
    pool = [o for o in options if insult_usage[o] == min_v]
    return random.choice(pool)


# ---------------------------
# ROAST COMMAND
# ---------------------------
@client.tree.command(name="roast", description="Roast a user based on behavior patterns")
async def roast(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(thinking=True)

    user_messages = []
    server_messages = []

    async for msg in interaction.channel.history(limit=1000):
        if msg.author.bot or not msg.content:
            continue

        text = msg.content.lower()
        server_messages.append(text)

        if msg.author == user:
            user_messages.append(text)

    if not user_messages:
        await interaction.followup.send("Too little data 😭")
        return

    user_words = sum(len(m.split()) for m in user_messages)
    server_words = sum(len(m.split()) for m in server_messages)

    user_avg = user_words / max(len(user_messages), 1)
    server_avg = server_words / max(len(server_messages), 1)

    flat = " ".join(user_messages)

    # ---------------------------
    # TRAITS
    # ---------------------------
    traits = []

    if "lol" in flat:
        traits.append("lol_spammer")

    if user_avg < server_avg * 0.6:
        traits.append("short_texter")

    if user_avg > server_avg * 1.5:
        traits.append("essay_writer")

    if len(user_messages) > len(server_messages) * 0.3:
        traits.append("chronically_online")

    if len(set(flat.split())) < 20:
        traits.append("repetitive_vocabulary")

    # ---------------------------
    # EVOLUTION
    # ---------------------------
    update_archetype(str(user.id), traits)
    update_profile(str(user.id), user_messages, traits)

    dominant = get_dominant(str(user.id))

    # ---------------------------
    # ROAST GENERATION
    # ---------------------------
    roasts = []

    for t in traits:
        if t in TRAITS:
            setup = pick_least_used(SETUPS)
            trait = pick_least_used(TRAITS[t])
            closer = pick_least_used(CLOSERS)

            insult_usage[setup] += 1
            insult_usage[trait] += 1
            insult_usage[closer] += 1

            roasts.append(f"{setup} {trait} {closer}")

    save_json(USAGE_FILE, insult_usage)

    if not roasts:
        roasts.append("You are so normal it's actually suspicious.")

    profile = user_profiles.get(str(user.id), {})

    if profile:
        roasts.append(
            f"\n🧠 Profile: chaos={profile['chaos']:.1f}, "
            f"predictability={profile['predictability']:.2f}"
        )

    if dominant:
        roasts.append(f"\n🎭 Archetype: {' + '.join(dominant)}")

    result = "\n".join(f"🔥 {r}" for r in roasts)
    result += f"\n\nVerdict: {user.display_name} is statistically unstable."

    await interaction.followup.send(result)


# ---------------------------
# RUN
# ---------------------------
client.run(TOKEN)