import discord
import google.generativeai as genai
from dotenv import load_dotenv
import os
import asyncio
import datetime
import requests
from bs4 import BeautifulSoup
from keep_alive import keep_alive  # Optional for hosting platforms

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_BOT_CHANNEL = int(os.getenv("DISCORD_BOT_CHANNEL"))  # Make sure this is an int

# Setup Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-001')

# Discord client setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Store last user prompt
last_prompt = {}

# Function to scrape weather in Bangkok
def get_scraped_weather():
    try:
        url = "https://www.timeanddate.com/weather/thailand/bangkok"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.content, "html.parser")
        weather_data = {}

        qlook = soup.find("div", id="qlook")
        if qlook:
            temp = qlook.find("div", class_="h2")
            if temp:
                weather_data["Temperature"] = temp.text.strip()

            condition = qlook.find("p")
            if condition:
                weather_data["Condition"] = condition.text.strip()

            all_ps = qlook.find_all("p")
            if len(all_ps) >= 2:
                extra_info = all_ps[1].decode_contents().split("<br>")
                for info in extra_info:
                    soup_line = BeautifulSoup(info, "html.parser").text.strip()
                    if "Feels Like:" in soup_line:
                        weather_data["Feels Like"] = soup_line.replace("Feels Like:", "").strip()
                    elif "Forecast:" in soup_line:
                        weather_data["Forecast"] = soup_line.replace("Forecast:", "").strip()
                    elif "Wind:" in soup_line:
                        weather_data["Wind"] = soup_line.replace("Wind:", "").strip()
        return weather_data
    except Exception as e:
        print("Weather scraping error:", e)
        return "Couldn't fetch weather."

# Function to scrape PM2.5 in Bangkok
def get_scraped_pm25():
    try:
        url = "https://www.iqair.com/th/thailand/bangkok/pathum-wan?srsltid=AfmBOopw6UBDCgmFfDPkqpr1gJ1Cl3l-Cnth0mf4p6OOGOn6fhPdMvPI"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.content, "html.parser")
        pm25_element = soup.find("p", class_="aqi-value__estimated")

        if pm25_element:
            pm25_value = pm25_element.get_text(strip=True)
            return f"PM2.5: {pm25_value}"
        else:
            return "PM2.5 data not available."
    except Exception as e:
        print("PM2.5 scraping error:", e)
        return "Couldn't fetch PM2.5."

# Async task to send message every day at 5:00 AM
async def daily_message_task():
    await client.wait_until_ready()
    channel = client.get_channel(int(DISCORD_BOT_CHANNEL))  # Replace with your channel ID (as an int)

    while not client.is_closed():
        now = datetime.datetime.now()
        next_run = now.replace(hour=5, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run += datetime.timedelta(days=1)
        wait_time = (next_run - now).total_seconds()
        await asyncio.sleep(wait_time)

        try:
            weather_data = get_scraped_weather()
            pm25_data = get_scraped_pm25()

            # Build the weather and air quality summary
            weather_lines = [f"{k}: {v}" for k, v in weather_data.items()]
            weather_text = "\n".join(weather_lines)

            # Build the prompt with both weather and PM2.5 info
            prompt = (
                f"Good morning Kong! Here is the weather and air quality update for Bangkok:\n\n"
                f"Weather Info:\n{weather_text}\n\n"
                f"Air Quality Info:\n{pm25_data}\n\n"
                f"Give Kong a suggestion message based on the weather and air quality. Make it easy to read, not too long.(unit: temp:°C, pm2.5:µg/m³)"
            )

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

    # !test command
    if content == "!test":
        await message.channel.send("✅ Hi Kong, test successful! I'm alive and listening.")
        return

    # !now command for instant message
    if content == "!now":
        weather_data = get_scraped_weather()
        pm25_data = get_scraped_pm25()

        weather_lines = [f"{k}: {v}" for k, v in weather_data.items()]
        weather_text = "\n".join(weather_lines)

        prompt = (
            f"Here is the current weather and air quality update for Bangkok:\n\n"
            f"Weather Info:\n{weather_text}\n\n"
            f"Air Quality Info:\n{pm25_data}\n\n"
            f"Give Kong a suggestion message based on the weather and air quality. Make it easy to read, not too long.(unit: temp:°C, pm2.5:µg/m³)"
        )

        try:
            response = model.generate_content(prompt)
            await message.channel.send(response.text)
        except Exception as e:
            print("Gemini API error:", e)
            await message.channel.send("❌ Error getting response from Gemini. Try again later")
        return

    # !ask command
    if content.startswith("!ask"):
        user_input = content[4:].strip()
        if not user_input:
            await message.channel.send("❗ Please ask a question after `!ask`.")
            return

        last_prompt[user_id] = user_input
        await message.channel.typing()
        try:
            prompt = f"Please reply as if you're speaking directly to someone named Kong. {user_input}"
            response = model.generate_content(prompt)
            await message.channel.send(response.text)
        except Exception as e:
            print("Gemini API error:", e)
            await message.channel.send("❌ Error getting response from Gemini. Try again later")
        return

    # Follow-up continuation
    if content.lower() in ["yes", "no", "okay", "sure", "go on", "continue","next","ok"]:
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

# Keep-alive (optional for Replit or similar)
keep_alive()

# Run bot
client.run(DISCORD_BOT_TOKEN)
