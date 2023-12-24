import discord
import os
from discord.ext import commands
from dotenv import load_dotenv

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
load_dotenv()

count = 0
msg_author = None


@bot.event
async def on_message(message):
    global count
    global msg_author
    global channel_id
    channel_id = os.getenv('CHANNEL_ID')
    if str(message.channel.id) == channel_id:  # replace with your specific channel id
        try:
            user_count = int(message.content)
            if user_count == count + 1 and msg_author != message.author:
                count += 1
                msg_author = message.author
                await message.add_reaction('\u2705')  # Checkmark reaction represents validation
                print("Count " + str(count) + " reached by " + str(msg_author))
            else:
                if msg_author == message.author:
                    await message.channel.send('Count reset to 0 due multiple tries in a row.')
                    print("Count reseted by " + str(msg_author) + " due to multiple tries in a row.")
                else:
                    await message.channel.send('Count reset to 0 due to incorrect sequence.')
                    print("Count reseted by " + str(msg_author) + " due to incorrect sequence.")
                count = 0
                msg_author = None
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
