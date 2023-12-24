import discord
import os
from discord.ext import commands
from dotenv import load_dotenv

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
load_dotenv()

count = 0


@bot.event
async def on_message(message):
    global count
    print("message received : " + message.content)
    print("in channel : " + str(message.channel.id))
    if message.channel.id == 984489193457729548:  # replace with your specific channel id
        print("OUAIS")
        try:
            user_count = int(message.content)
            if user_count == count + 1:
                count += 1
                await message.channel.send('Count valid')  # message when count is valid
            else:
                count = 0
                await message.channel.send('Count reset to 0 due to incorrect sequence.')
        except ValueError:
            pass  # not a number
    await bot.process_commands(message)


# function to start the bot
def start_bot():
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        raise Exception("BOT_TOKEN is not set in environment variables")
    bot.run(bot_token)


# main function to execute the program
def main():
    start_bot()


if __name__ == "__main__":
    main()