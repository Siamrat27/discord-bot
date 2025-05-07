import discord
import google.generativeai as genai
from dotenv import load_dotenv
import os
from keep_alive import keep_alive  # Import keep_alive function

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
            your_name = "Ks"  # 🔒 Your hardcoded name
            await message.channel.send(f"{your_name}, here's my answer:\n{response.text}")
        except Exception as e:
            print("Gemini API error:", e)
            await message.channel.send("❌ Error getting response from Gemini.")

# ==== Keep the bot alive with a web service ====
keep_alive()  # Call the keep_alive function

# ==== Start the bot ====
client.run(DISCORD_BOT_TOKEN)
