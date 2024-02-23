import asyncio
import os
import time
from datetime import datetime
from threading import Thread

import discord
import mysql.connector
from discord.ext import commands
from dotenv import load_dotenv

from flask import Flask
from flask import request, jsonify
from flask_cors import CORS

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
load_dotenv()

count = 0
msg_author = None

# MySQL connection
def connect_to_db():
    connection_attempts = 0
    while True:
        try:
            mydb = mysql.connector.connect(
              host=os.getenv('DB_HOST'),
              user=os.getenv('DB_USER'),
              password=os.getenv('DB_PASSWORD'),
              database=os.getenv('DB_NAME'),
              port=os.getenv('DB_PORT')  # handling DB_PORT from .env
            )
            print("Successfully connected to database")
            return mydb
        except mysql.connector.Error as err:
            connection_attempts += 1
            print(f"Attempt {connection_attempts}: Failed to connect to database. Error - {str(err)}")
            time.sleep(5)  # wait for 5 seconds before trying to connect again

mydb = connect_to_db()
mycursor = mydb.cursor()

# Function to check and re-establish database connection
async def check_db_connection(mydb):
    while True:
        try:
            mydb.ping()  # checks if the db connection is alive
        except Exception as e:
            print(f"Lost connection to database due to {str(e)}, reconnecting...")
            mydb = connect_to_db()
        await asyncio.sleep(5)  # the check is performed every 5 seconds

# Schedule the check_db_connection task after the bot is ready
@bot.event
async def on_ready():
    bot.loop.create_task(check_db_connection(mydb))


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

    mydb.ping(reconnect=True)  # NEW LINE ADDED
    mycursor.execute("INSERT INTO scores (score, starting_date, users, end_date, status) VALUES (%s, %s, %s, %s, %s)", (count, starting_date, users, end_date, status))
    mydb.commit()

# Attempt to continue an existing run
mydb.ping(reconnect=True)  # NEW LINE ADDED
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
    global msg_author
    global channel_id
    global users
    global count
    channel_id = os.getenv('CHANNEL_ID')
    if str(message.channel.id) == channel_id:  # replace with your specific channel id
        try:
            mydb.ping(reconnect=True)  # reconnect to DB if connection was lost
            mycursor.execute("SELECT score FROM scores WHERE status = 'running'")  # get the count from the DB
            count = mycursor.fetchone()[0]
            mydb.commit()

            user_count = int(message.content)
            print("count = ", count, " - usercount = ", user_count)
            if user_count == count + 1 and msg_author != message.author:
                count += 1
                msg_author = message.author
                if str(msg_author) not in users:
                    users += ', ' + str(msg_author)  # Update the users list
                await message.add_reaction('\u2705')  # Checkmark reaction represents validation
                print(f"Count {str(count)} reached by {str(msg_author)}")

                mydb.ping(reconnect=True)  # NEW LINE ADDED
                mycursor.execute("UPDATE scores SET score = %s, users = %s WHERE status = 'running'", (count, users))
                mycursor.execute("SELECT * FROM users WHERE username = %s", (str(msg_author),))
                user = mycursor.fetchone()

                # If the user exists, increment the money count
                if user is not None:
                    mycursor.execute("UPDATE users SET money = money + 1 WHERE username = %s", (str(msg_author),))
                else:
                    mycursor.execute("INSERT INTO users (username, money) VALUES (%s, 1)", (str(msg_author),))
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

                mydb.ping(reconnect=True)  # NEW LINE ADDED
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
    mydb.ping(reconnect=True)  # NEW LINE ADDED
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
    embed.add_field(name="Version 2.4", value="- Added automatic database reconnection", inline=False)
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


app = Flask(__name__)

CORS(app)  # Enable CORS on the Flask app


@app.route("/send", methods=["POST"])
def send_message():
    jsonPayload = request.get_json()
    message_to_send = jsonPayload.get('message')
    channel_id = os.getenv('CHANNEL_ID')  # replace with your channel id

    if message_to_send is None:
        return jsonify({'status': 'error', 'message': 'No message provided'}), 400

    # get the channel to send message
    target_channel = bot.get_channel(int(channel_id))

    if target_channel is None:
        return jsonify({'status': 'error', 'message': 'Invalid Channel ID'}), 400

    # use the bot to send the message to discord channel
    # we must run message sending in bot.loop
    future = asyncio.run_coroutine_threadsafe(target_channel.send(message_to_send), bot.loop)
    try:
        # Wait for the result with a timeout
        future.result(timeout=5)
    except asyncio.TimeoutError:
        return jsonify({'status': 'error', 'message': 'TimeOut Error in sending message'}), 500
    except Exception as e:
        # general exception, can use specific discord exception
        return jsonify({'status': 'error', 'message': str(e)}), 500
    return jsonify({'status': 'success', 'message': 'message sent'}), 200

# main function to execute the program
def main():
    # Create threads for both Flask app and the bot
    thread1 = Thread(target=app.run, kwargs={'host':'0.0.0.0', 'port':5100})
    thread2 = Thread(target=start_bot)

    # Start both threads
    thread1.start()
    thread2.start()

    # Join both threads to the main thread
    thread1.join()
    thread2.join()


if __name__ == "__main__":
    main()