import os
import sys
import discord
from discord.ext import commands

from typing import List

class DiscordBot:
    def __init__(self, BOT_TOKEN):
        self.BOT_TOKEN = BOT_TOKEN
        self.client = commands.Bot(command_prefix="/", intents=discord.Intents.all())
        self.setup()

    async def load_cogs(self):
        cog_dirs = self._get_cog_dirs('./cogs')
        for directory in cog_dirs:
            await self._load_cogs_from_dir(directory)

    def _get_cog_dirs(self, base_dir):
        cog_dirs = [root for root, _, files in os.walk(base_dir) if any(file.endswith('.py') for file in files)]
        return cog_dirs

    async def _load_cogs_from_dir(self, dir_path):
        for filename in os.listdir(dir_path):
            if filename.endswith('.py') and filename != '__init__.py':
                cog_path = os.path.join(dir_path, filename).replace('/', '.').replace('\\', '.').replace('..', '')[:-3]
                try:
                    await self.client.load_extension(cog_path)
                    print(f"Loaded {filename}.")
                except Exception as e:
                    print(f"Failed to load extension {filename}: {e}")

    async def run(self):
        async with self.client:
            try:
                await self.client.start(self.BOT_TOKEN)
            except KeyboardInterrupt:
                pass
            except Exception as e:
                print(f"ERROR -> {e}")
            finally:
                await self.client.close()
                sys.exit()

    def setup(self):
        @self.client.event
        async def on_ready():
            print('------')
            print('Logged in as')
            print(f'{self.client.user.name}#{self.client.user.discriminator} (ID: {self.client.user.id})')
            print('------')
            await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.custom, name="Custom ShuttleAI Status", state="https://shuttleai.app"))
            await self.load_cogs()
            await self.client.tree.sync()