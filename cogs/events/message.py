import json
import time
import asyncio
import discord
from discord.ext import commands
from typing import List, Dict
from collections import deque
from dateutil import tz
from datetime import datetime
from colorama import Fore, Style
import colorama
from pydantic import BaseModel

from shuttleai import ShuttleAsyncClient
from shuttleai.schemas import ChatChunk, Chat, ShuttleError

from utils import SHUTTLEAI_API_KEY, STREAM_COMPLETIONS

MAX_MESSAGE_HISTORY_LENGTH: int = 5

WAKE_PHRASES: List[str] = ["shuttle", "shuttleai", 'gemini', 'gpt', 'claude']
PHRASE_TO_MODEL: Dict[str, str] = {
    'gpt': 'gpt-3.5-turbo',
    'gemini': 'gemini-pro',
    'claude': 'claude-3-haiku',
    'shuttle': 'shuttle-turbo',
    'shuttleai': 'shuttle-turbo'
}

class Message(BaseModel):
    role: str
    content: str

class UserMessageHistory:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.messages: deque = deque(maxlen=MAX_MESSAGE_HISTORY_LENGTH)

    def add_message(self, role: str, content: str):
        self.messages.append(Message(role=role, content=content))

    def get_openai_messages(self):
        return [msg.dict() for msg in self.messages]

class RateLimiter:
    def __init__(self, max_messages: int, reset_time: int):
        self.max_messages = max_messages
        self.reset_time = reset_time
        self.user_msgs: Dict[int, tuple[int, float]] = {}

    def is_rate_limited(self, user_id: int) -> bool:
        now = time.time()
        msgs, last_reset = self.user_msgs.get(user_id, (0, 0))
        if now - last_reset >= self.reset_time:
            self.user_msgs[user_id] = (1, now)
            return False
        if msgs >= self.max_messages:
            return True
        self.user_msgs[user_id] = (msgs + 1, last_reset)
        return False

class MessageCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.message_history: Dict[int, UserMessageHistory] = {}
        self.rate_limiter = RateLimiter(5, 60)  # 5/min
        colorama.init()

    async def process_request(self, message: discord.Message, start_time, options, log_prefix, model, user_history):
        async with ShuttleAsyncClient(SHUTTLEAI_API_KEY, 120) as shuttle:
            response = await shuttle.chat_completion(**options)

            if STREAM_COMPLETIONS:
                chunks = []
                sent_message = None
                message_content = ""
                try:
                    async for chunk in response:
                        try:
                            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                                chunk = chunk.choices[0].delta.content
                                
                                print(chunk)
                                chunks.append(chunk)

                                message_content += chunk

                                if len(message_content) > 2000:
                                    if not sent_message:
                                        sent_message = await message.channel.send(message_content[:2000], allowed_mentions=discord.AllowedMentions.none())
                                    else:
                                        await sent_message.edit(content=sent_message.content + message_content[:2000], allowed_mentions=discord.AllowedMentions.none())
                                        sent_message = await message.channel.fetch_message(sent_message.id)

                                    message_content = message_content[2000:]

                                if "\n" in chunk:
                                    if not sent_message:
                                        sent_message = await message.channel.send(message_content, allowed_mentions=discord.AllowedMentions.none())
                                    else:
                                        await sent_message.edit(content=sent_message.content + message_content, allowed_mentions=discord.AllowedMentions.none())
                                        sent_message = await message.channel.fetch_message(sent_message.id)
                                    message_content = ""
                                else:
                                    pass
                        except Exception as e:
                            print(e)
                            if "Must be" in str(e):
                                sent_message = None
                            if "rate limit" in str(e):
                                await asyncio.sleep(1)
                            pass

                    while len(message_content) > 0:
                        if not sent_message:
                            sent_message = await message.channel.send(message_content[:2000], allowed_mentions=discord.AllowedMentions.none())
                        else:
                            await sent_message.edit(content=sent_message.content + message_content[:2000], allowed_mentions=discord.AllowedMentions.none())
                        message_content = message_content[2000:]
                except Exception as e:
                    print(e)
                    if "Must be" in str(e):
                        sent_message = None
                    if "rate limit" in str(e):
                        await asyncio.sleep(1)
                    pass
                finally:
                    response.aclose()

                end_time = time.time()
                duration = end_time - start_time

                assistant_response = "".join(chunks)
                print(f"{log_prefix} | {Fore.YELLOW}Response {Style.RESET_ALL}| {assistant_response} {Fore.LIGHTMAGENTA_EX}[{duration:.3f}s]{Style.RESET_ALL}")
            else:
                end_time = time.time()
                duration = end_time - start_time

                if isinstance(response, ShuttleError):
                    embed = discord.Embed(
                        title="❌ Error",
                        description=f"```{json.dumps(response.model_dump(), indent=4)}```",
                    )
                    await message.channel.send(embed=embed)
                    return

                assistant_response = response.choices[0].message.content

                embed = discord.Embed(
                    title=f"🤖 {model}",
                    description=assistant_response,
                )
                embed.set_footer(text=f"Responded in {duration:.3f}s")
                await message.channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
                print(f"{log_prefix} | {Fore.YELLOW}Response {Style.RESET_ALL}| {assistant_response} {Fore.LIGHTMAGENTA_EX}[{duration:.3f}s]{Style.RESET_ALL}")

            user_history.add_message("assistant", assistant_response)

            print(f"Current History for {message.author}:")
            for msg in user_history.messages:
                print(f"{msg.role}: {msg.content}")
            print("")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return

        wake_phrase_detected = any(phrase in message.content.lower() for phrase in WAKE_PHRASES)
        if self.bot.user in message.mentions or wake_phrase_detected:
            if self.rate_limiter.is_rate_limited(message.author.id):
                user_msgs, last_reset = self.rate_limiter.user_msgs.get(message.author.id, (0, 0))
                time_left = self.rate_limiter.reset_time - (time.time() - last_reset)
                rate_limit_end = int(time.time() + time_left)
                embed = discord.Embed(
                    title="⏱ Rate Limited",
                    description=f"You can send another message <t:{rate_limit_end}:R>.",
                    color=0xFF0000
                )
                await message.channel.send(embed=embed)
                return
            
            try:
                async with message.channel.typing():
                    user_history = self.message_history.get(message.author.id, UserMessageHistory(message.author.id))
                    user_history.add_message("user", message.content)
                    self.message_history[message.author.id] = user_history

                    openai_messages = user_history.get_openai_messages()

                    wake_phrase = next((phrase for phrase in WAKE_PHRASES if phrase in message.content.lower()), "shuttle")
                    model = PHRASE_TO_MODEL.get(wake_phrase, PHRASE_TO_MODEL["shuttle"])

                    start_time = time.time()
                    log_prefix = f"{Fore.LIGHTBLACK_EX}{datetime.now(tz=tz.tzlocal()).strftime('%I:%M:%S')}{Style.RESET_ALL} | {Fore.GREEN}[{message.author}]{Style.RESET_ALL} | {Fore.CYAN}[{model}]{Style.RESET_ALL}"
                    print(f"{log_prefix} | {Fore.YELLOW}Request {Style.RESET_ALL} | {message.content}")

                    options = {
                        'model': model,
                        'messages': openai_messages,
                    }

                    if STREAM_COMPLETIONS:
                        options['stream'] = True

                    try:
                        asyncio.create_task(self.process_request(message, start_time, options, log_prefix, model, user_history))
                    except Exception as e:
                        print(f"{log_prefix} | {Fore.RED}Error {Style.RESET_ALL} | {e}")

            except Exception as e:
                print(f"{log_prefix} | {Fore.RED}Error {Style.RESET_ALL} | {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(MessageCog(bot))