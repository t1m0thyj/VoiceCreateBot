import os
import sys
import traceback

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

initial_extensions = ['cogs.voice']

class MyBot(commands.Bot):
    async def setup_hook(self):
        for extension in initial_extensions:
            try:
                await self.load_extension(extension)
            except Exception as e:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = MyBot(command_prefix=".", intents=intents)
bot.remove_command("help")

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

bot.run(os.environ['DISCORD_BOT_TOKEN'])
