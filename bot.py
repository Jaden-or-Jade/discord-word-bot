import discord
from discord import app_commands
from collections import Counter
import re

TOKEN = "MTUwMTMyNjY0NDY4ODcxNTk4OA.GnwpBX.blBl1Az3jD3k7jnqtYHkl0bdwMjFRQJ9NorAjE"

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

@client.tree.command(name="topwords", description="Get most used words in this channel")
async def topwords(interaction: discord.Interaction):
    await interaction.response.send_message("Scanning messages... ⏳")

    word_counter = Counter()

    async for message in interaction.channel.history(limit=None):
        if message.author.bot:
            continue

        words = re.findall(r'\b\w+\b', message.content.lower())
        word_counter.update(words)

    stopwords = {"the", "and", "is", "to", "a", "of", "in", "it", "for", "on", "you"}
    for word in list(word_counter):
        if word in stopwords:
            del word_counter[word]

    top = word_counter.most_common(10)
    result = "\n".join([f"{w}: {c}" for w, c in top])

    await interaction.followup.send(result)

client.run(TOKEN)
