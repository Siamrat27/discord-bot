import discord
import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# ==== Get the API keys from .env file ====
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# ==== Configure Gemini ====
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-001')

# ==== Set up Discord Bot ====
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user} (ID: {client.user.id})')

@client.event
async def on_message(message):
    # Prevent the bot from responding to itself
    if message.author == client.user:
        return

    content = message.content.strip()

    # !test command
    if content == "!test":
        await message.channel.send("✅ Test successful! I'm alive and listening.")
        return

    # !ask command
    if content.startswith("!ask"):
        user_input = content[4:].strip()
        if not user_input:
            await message.channel.send("❗ Please ask a question after `!ask`.")
            return

        await message.channel.typing()
        try:
            response = model.generate_content(user_input)
            await message.channel.send(response.text)
        except Exception as e:
            print("Gemini API error:", e)
            await message.channel.send("❌ Error getting response from Gemini.")

# ==== Start the bot ====
client.run(DISCORD_BOT_TOKEN)
