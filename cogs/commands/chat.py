import json
import discord
from typing import List
from discord.ext import commands, tasks
from discord import app_commands

from shuttleai import ShuttleAsyncClient

from utils import SHUTTLEAI_API_KEY

CHAT_MODELS = []

async def cache_models():
    global CHAT_MODELS
    async with ShuttleAsyncClient(SHUTTLEAI_API_KEY) as client:
        chatModels = await client.get_models(endpoint='/v1/chat/completions')
        CHAT_MODELS = [model.id for model in chatModels.data]

@tasks.loop(hours=1)
async def refresh_models():
    await cache_models()

async def autocomplete_models(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=model, value=model)
        for model in CHAT_MODELS
        if current.lower() in model.lower()
    ]

class ChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        refresh_models.start()

    def cog_unload(self):
        refresh_models.cancel()

    @tasks.loop(count=1)
    async def cache_models_on_startup(self):
        await cache_models()
        self.cache_models_on_startup.stop()

    @commands.hybrid_group(name='chat', with_app_command=True)
    async def chat(self, ctx: commands.Context):
        await ctx.send("You need to specify a subcommand.")

    @chat.command(
        name='completions',
        description='Get chat completions from ShuttleAI.',
    )
    @app_commands.autocomplete(model=autocomplete_models)
    async def completions(self, ctx: commands.Context, model: str, messages: str):
        try:
            await ctx.defer(ephemeral=False)
            is_plain = True
            if messages.startswith('[{') and messages.endswith('}]'):
                messages = json.loads(messages)
                is_plain = False

            async with ShuttleAsyncClient(SHUTTLEAI_API_KEY, 230) as shuttle:
                response = await shuttle.chat_completion(
                    model=model,
                    messages=messages,
                    plain=is_plain
                )
                await ctx.send(f'```{json.dumps(response.model_dump(), indent=4)}```')

        except Exception as e:
            import traceback
            traceback.print_exc()
            await ctx.send(f"Error: {e}")

async def setup(bot):
    await bot.add_cog(ChatCog(bot))