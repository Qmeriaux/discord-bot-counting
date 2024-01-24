from datetime import datetime

import discord
import os
import mysql.connector
from discord.ext import commands
from dotenv import load_dotenv

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
load_dotenv()

count = 0
msg_author = None

# MySQL connection
mydb = mysql.connector.connect(
  host=os.getenv('DB_HOST'),
  user=os.getenv('DB_USER'),
  password=os.getenv('DB_PASSWORD'),
  database=os.getenv('DB_NAME')
)
print("Successfully connected to database")
mycursor = mydb.cursor()

def create_new_run():
    global count
    global starting_date
    global end_date
    global status
    global users
    count = 0
    starting_date = datetime.now()
    end_date = None
    status = 'running'
    users = ''
    mycursor.execute("INSERT INTO scores (score, starting_date, users, end_date, status) VALUES (%s, %s, %s, %s, %s)",
                     (count, starting_date, users, end_date, status))
    mydb.commit()

# Attempt to continue an existing run
mycursor.execute("SELECT * FROM scores WHERE status != 'finished' LIMIT 1")
result = mycursor.fetchone()
if result is not None:
    print("Continuing existing run...")
    count = result[0]
    starting_date = result[1]
    end_date = result[2]
    status = result[3]
    users = result[4]
else:
    print("Creating a new run...")
    create_new_run()

@bot.event
async def on_message(message):
    global count
    global msg_author
    global channel_id
    global users
    channel_id = os.getenv('CHANNEL_ID')
    if str(message.channel.id) == channel_id:  # replace with your specific channel id
        try:
            user_count = int(message.content)
            if user_count == count + 1 and msg_author != message.author:
                count += 1
                msg_author = message.author
                if str(msg_author) not in users:
                    users += ', ' + str(msg_author)  # Update the users list
                await message.add_reaction('\u2705')  # Checkmark reaction represents validation
                print("Count " + str(count) + " reached by " + str(msg_author))

                mycursor.execute("UPDATE scores SET score = %s, users = %s WHERE status = 'running'", (count, users))
                mydb.commit()

            else:
                if msg_author == message.author:
                    embed = discord.Embed(title="**Error!**", colour=0xFF0000)
                    embed.set_image(url="https://media1.tenor.com/m/ormtsnMh2RgAAAAC/you-youre.gif")
                    embed.add_field(name="Reason", value=f"Count reset to 0 due multiple tries in a row by {str(message.author)}", inline=False)
                    await message.channel.send(embed=embed)
                    print("Count reseted by " + str(message.author) + " due to multiple tries in a row.")
                else:
                    embed = discord.Embed(title="**Error!**", colour=0xFF0000)
                    embed.set_image(url="https://media1.tenor.com/m/ormtsnMh2RgAAAAC/you-youre.gif")
                    embed.add_field(name="Reason", value=f"Count reset to 0 due to incorrect sequence by {str(message.author)}", inline=False)
                    await message.channel.send(embed=embed)
                    print("Count reseted by " + str(message.author) + " due to incorrect sequence.")
                end_date = datetime.now()

                # Updated line to set end_date to current time when run is finished
                mycursor.execute("UPDATE scores SET status = %s, end_date = %s, shame = %s WHERE status = 'running'", ('finished', end_date, str(message.author)))
                mydb.commit()
                print("Run finished, creating a new run...")
                create_new_run()

                msg_author = None
                count = 0
        except ValueError:
            pass
    await bot.process_commands(message)

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    mycursor.execute("SELECT * FROM scores WHERE status = 'finished' ORDER BY score DESC LIMIT 5")
    top_scores = mycursor.fetchall()
    embed = discord.Embed(title="Top 5 leaderboard", description="Top 5 best runs:", color=0x0080ff)
    for i, score in enumerate(top_scores, start=1):
        embed.add_field(name=f"Top {i} : {score[0]}", value=f"Scored `{score[0]}` points starting on `{score[1]}` and ended on `{score[2]}`, participants were `{score[4][2:]}`, failed by `{score[5]}`.", inline=False)
        embed.set_field_at(i-1, name=f"Top {i} : {score[0]}", value=f"Scored **{score[0]}** points starting on `{score[1]}` and ended on `{score[2]}`, participants were `{score[4][2:]}`, failed by `{score[5]}`.", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='hallofshame')
async def hallofshame(ctx):
    mycursor.execute("SELECT shame, COUNT(*) as Count FROM scores WHERE status = 'finished' GROUP BY shame ORDER BY Count DESC LIMIT 5")
    shame_list = mycursor.fetchall()
    embed = discord.Embed(title="Hall of Shame", description="Top 5 with most fails:", color=0xFF0000)
    for i, shame in enumerate(shame_list, start=1):
        embed.add_field(name=f"Top {i} : {shame[0]}", value=f"Failed `{shame[1]}` times.", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='changelog')
async def changelog(ctx):
    embed = discord.Embed(title="Changelog", description="Changes made in this version:", color=0x0080ff)
    embed.add_field(name="Version 2.3", value="- Added Hall of Shame", inline=False)
    embed.add_field(name="Version 2.2", value="- Changed errors messages", inline=False)
    embed.add_field(name="Version 2.1", value="- Bug fixes", inline=False)
    embed.add_field(name="Version 2.0", value="- Added database connection\n- Added leaderboard", inline=False)
    embed.add_field(name="Version 1.0", value="- Initial release\n- Basic counting system", inline=False)
    await ctx.send(embed=embed)

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