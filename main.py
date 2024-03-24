import asyncio
from bot import DiscordBot
from utils import BOT_TOKEN

bot = DiscordBot(BOT_TOKEN)

if __name__ == '__main__':
    print("Connecting to Discord...")
    asyncio.run(bot.run())