import discord
import google.generativeai as genai
from dotenv import load_dotenv
import os
import asyncio
import datetime
import requests
from bs4 import BeautifulSoup
from keep_alive import keep_alive  # Make sure you have keep_alive.py

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_BOT_CHANNEL =  os.getenv("DISCORD_BOT_TOKEN")

# Setup Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-001')

# Discord client setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Store last user prompt
last_prompt = {}

# Function to scrape current date info (example: from timeanddate.com)
def get_scraped_date():
    try:
        response = requests.get("https://www.timeanddate.com/worldclock/thailand/bangkok")
        soup = BeautifulSoup(response.content, "html.parser")
        time_element = soup.find("span", id="ct")
        return time_element.text.strip() if time_element else "Time unavailable"
    except Exception as e:
        print("Scraping error:", e)
        return "Couldn't fetch date."

# Async task to send message every day at 5:00 AM
async def daily_message_task():
    await client.wait_until_ready()
    channel = client.get_channel(DISCORD_BOT_CHANNEL)  # Replace with your channel ID (as an int)

    while not client.is_closed():
        now = datetime.datetime.now()
        next_run = now.replace(hour=5, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run += datetime.timedelta(days=1)
        wait_time = (next_run - now).total_seconds()
        await asyncio.sleep(wait_time)

        try:
            date_info = get_scraped_date()
            prompt = f"Say something encouraging to Kong for the new day. The current Bangkok time is {date_info}."
            response = model.generate_content(prompt)
            await channel.send(response.text)
        except Exception as e:
            print("Scheduled message error:", e)

@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user} (ID: {client.user.id})')
    client.loop.create_task(daily_message_task())

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip()
    user_id = message.author.id

    # !test
    if content == "!test":
        await message.channel.send("✅ Hi Kong, test successful! I'm alive and listening.")
        return

    # !ask
    if content.startswith("!ask"):
        user_input = content[4:].strip()
        if not user_input:
            await message.channel.send("❗ Please ask a question after `!ask`.")
            return

        # Save prompt for continuity
        last_prompt[user_id] = user_input

        await message.channel.typing()
        try:
            prompt = f"Please reply as if you're speaking directly to someone named Kong. {user_input}"
            response = model.generate_content(prompt)
            await message.channel.send(response.text)
        except Exception as e:
            print("Gemini API error:", e)
            await message.channel.send("❌ Error getting response from Gemini.")
        return

    # Simple follow-up (one previous message context)
    if content.lower() in ["yes", "no", "okay", "sure", "go on", "continue"]:
        if user_id in last_prompt:
            await message.channel.typing()
            try:
                follow_up = f"Kong previously asked: {last_prompt[user_id]}\nNow they say: {content}\nContinue the conversation naturally."
                response = model.generate_content(follow_up)
                await message.channel.send(response.text)
            except Exception as e:
                print("Follow-up error:", e)
                await message.channel.send("❌ Error continuing the conversation.")
        else:
            await message.channel.send("ℹ️ No previous conversation to continue from.")

# Keep bot alive
keep_alive()

# Run the bot
client.run(DISCORD_BOT_TOKEN)
