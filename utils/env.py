import os
from dotenv import load_dotenv

load_dotenv()

valid_bool_options = ["true", "1", "yes", "y", "t"]

SHUTTLEAI_API_KEY: str = os.getenv('SHUTTLEAI_API_KEY')
BOT_TOKEN: str = os.getenv('BOT_TOKEN')
STREAM_COMPLETIONS: bool = bool(os.getenv("STREAM_COMPLETIONS", "False").lower() in valid_bool_options)