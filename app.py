#!/usr/bin/env python3
'''
HeyHeyBot 

Small bot for Discord that will announce when a user joins voice chat to other users in the same channel.
Greeting message is customizable and depends on user (one user - one audio file).
Audio files are stored in the ./data/greetings folder.
Also people can play audio files from the ./data/audio folder by typing !play <filename> in chat.

All audio played by the bot joining the voice channel.
We will store user-audio pairs in the JSON. It will be loaded on bot start.
'''
# necessary imports
import os
try:
    import discord
    from discord.ext import commands
except ImportError:
    print("discord.py module not found. Please install it with 'pip install discord.py'")
    exit(1)
import asyncio

# Audio processing
import wave
import contextlib

# bot settings stored in .env
from dotenv import load_dotenv
load_dotenv()

def check_val(value, default=True):
    if value is not None:
        if type(value) == bool:
            return value
        if value.lower() == 'true':
            value = True
        else:
            value = False
    else:
        value = default
    return value

# bot settings
token = os.getenv('DISCORD_TOKEN')
continue_presence = check_val(os.getenv('DISCORD_CONTINUE_PRESENCE'), default=False)
arrivial_announce = check_val(os.getenv('DISCORD_ARRIVAL_ANNOUNCE'))
muting_announce = check_val(os.getenv('DISCORD_MUTING_ANNOUNCE'))
leaving_announce = check_val(os.getenv('DISCORD_LEAVING_ANNOUNCE'))
loglevel = os.getenv('DISCORD_LOGLEVEL')
if loglevel is not None:
    loglevel = loglevel.upper()
    if loglevel not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        loglevel = 'INFO'
else:
    loglevel = 'WARNING'

stop_button = '⏹️ Stop '

# logging (rotate log every 1 MB, keep 5 old logs)
import logging
from logging.handlers import RotatingFileHandler
logger = logging.getLogger('HeyHeyBot')
loglevel = getattr(logging, loglevel)
logger.setLevel(loglevel)
handler = RotatingFileHandler('logs/heyheybot.log', maxBytes=1000000, backupCount=5, encoding='utf-8')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
logger.addHandler(handler)

# Start webpage in separate thread
if os.getenv('WEBPAGE_USERNAME') and os.getenv('WEBPAGE_PASSWORD'):
    from webserver import WebApp
    import threading
    webapp = WebApp()
    webapp_thread = threading.Thread(target=webapp.run)
    webapp_thread.start()
    logger.info(f'Webpage started')

# start bot
intents = discord.Intents.default()
intents.all()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.presences = True
intents.guilds = True

client = commands.Bot(
    command_prefix=commands.when_mentioned_or('!'),
    description='HeyHeyBot',
    intents=intents
)

@client.event
async def on_ready():
    logger.info('======')
    logger.info(f'Bot logged in as {client.user.name} (ID: {client.user.id})')
    logger.info(f'Connected to {len(client.guilds)} servers: {", ".join([guild.name for guild in client.guilds])}')
    logger.info(f'Bot is ready. Rich presence: {continue_presence}, arrival announce: {arrivial_announce}, muting announce: {muting_announce}, leaving announce: {leaving_announce}')
    logger.info('======')

# Play audio file from ./data/audio folder
sounds = {} # {filename: {'source': <discord.PCMVolumeTransformer>, 'duration': <int>}}
async def wav_length(audio_file):
    with contextlib.closing(wave.open(audio_file,'r')) as f:
        frames = f.getnframes()
        rate = f.getframerate()
        audiolen = frames / float(rate)
    return audiolen

# returns BufferedIOBase from given sound path
async def get_buffered_io(file):
    return open(file, 'rb')

# We are storing audio files in the dictionary to avoid opening the same file multiple times
async def cached_sounds(audio_file):
    if audio_file not in sounds:
        sounds[audio_file] = {
            'source': audio_file,
            'duration': await wav_length(audio_file)
        }
        logger.debug(f'Playing {audio_file}')
    else:
        logger.debug(f'Playing {audio_file} from cache')
    return sounds[audio_file]['source'], sounds[audio_file]['duration']

@client.command()
async def play(client, audio_file, audiolen=5, default='./data/greetings/hello.wav'):
    try:
        # Play audio file
        if not os.path.isfile(audio_file):
            audio_file = default
        sound, audiolen = await cached_sounds(audio_file)
        sound = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(sound), volume=1)
        client.voice_clients[0].play(sound, after=lambda e: logger.exception(f'Player error') if e else None)
        # wait until audio is played
        await asyncio.sleep(audiolen + 1)
    except discord.errors.ClientException as e:
        # if bot is already playing audio file
        if 'Already playing audio' in str(e):
            # stop playing
            client.voice_clients[0].stop()
            # play audio file
            await play(client, audio_file, audiolen, default)
        else:
            logger.error(f'Error playing audio file (ClientException): {e}')
            return
    except Exception as e:
        logger.error(f'Error playing audio file: {e}')
        return

# List all audio files in ./data/audio folder
async def list_audio_files(sort=True):
    audio_files = []
    for file in os.listdir('./data/audio'):
        if file.endswith('.wav'):
            file = file[:-4]
            audio_files.append(file)
    if sort:
        audio_files.sort()
    return audio_files

# Disconnect from voice channel
@client.command()
async def vc_disconnect(client, force=False):
    try:
        if continue_presence and not force:
            # check if any user is in a current voice channel
            current_voice_channel = client.voice_clients[0].channel
            if len(current_voice_channel.members) == 1:
                # if no users in a current voice channel, disconnect
                logger.info(f'No users in {current_voice_channel.name}, disconnecting')
                await client.voice_clients[0].disconnect()
            else:
                # if users in a current voice channel, do nothing
                return
        await client.voice_clients[0].disconnect()
    except Exception as e:
        logger.warning(f'Error disconnecting from voice channel: {e}')

async def is_same_channel(client, channel):
    # Check if user joins same voice channel as bot currently in
    # We don't want to play audio if person joins another voice channel
    bot_current_vc = client.voice_clients[0].channel if client.voice_clients else None
    logger.info(f'User joined {channel}, bot in {bot_current_vc}')
    if bot_current_vc is None:
        print('bot_current_vc is None')
        return True
    if bot_current_vc != channel:
        print('not same channel')
        return False
    print('same channel')
    return True

# logger.info username and channel name when user joins voice channel
@client.event
async def on_voice_state_update(member, before, after):
    # If bot ignore
    if member.id == client.user.id:
        return
    # If other bot ignore
    if member.bot:
        return
    if before.channel is None and after.channel is not None:
        if arrivial_announce:
            # When user joins voice channel (user was not in voice channel before)
            logger.info(f'{member.name} joined {after.channel.name}')
            # Join the same voice channel
            channel = after.channel
            try:
                await channel.connect()
            except:
                pass
            if continue_presence and not await is_same_channel(client, channel):
                return
            # Play audio file
            await play(client, f'./data/greetings/{member.name}.wav', default='./data/greetings/hello.wav')
            # Disconnect from the voice channel
            await vc_disconnect(client)
    elif before.channel is not None and after.channel is None:
        if leaving_announce:
            # When user leaves voice channel (user was in voice channel before)
            logger.info(f'{member.name} left {before.channel.name}')
            # Leave the voice channel announce
            channel = before.channel
            try:
                await channel.connect()
            except:
                pass
            if continue_presence and not await is_same_channel(client, channel):
                return
            # Play audio file
            await play(client, f'./data/leavings/{member.name}.wav', audiolen=1, default='./data/leavings/bye.wav')
            # Disconnect from the voice channel
            await vc_disconnect(client) 
    elif before.channel != after.channel:
        if arrivial_announce:
            # When user moves from one voice channel to another
            logger.info(f'{member.name} moved from {before.channel.name} to {after.channel.name}')
            # Disconnect from the previous voice channel
            await vc_disconnect(client, force=True)
            # Join the new voice channel
            try:
                await after.channel.connect()
            except Exception as e:
                logger.error(f'Error joining {after.channel.name}: {e}')
            if continue_presence and not await is_same_channel(client, after.channel):
                return
            # Play audio file
            await play(client, f'./data/greetings/{member.name}.wav', default='./data/greetings/hello.wav')
            # Disconnect from the voice channel
            await vc_disconnect(client)
    else:
        if muting_announce:
            # When user mutes/unmutes
            logger.info(f'{member.name} muted/unmuted')
            # Join the voice channel
            channel = after.channel
            try:
                await channel.connect()
            except:
                pass
            if continue_presence and not await is_same_channel(client, channel):
                return
            # Play audio file
            await play(client, f'./data/mutings/{member.name}.wav', default='./data/mutings/muted.wav')
            # Disconnect from the voice channel
            await vc_disconnect(client)

# Process button press
@client.event
async def on_interaction(interaction):
    # Get audio file name
    audio_file = interaction.data['custom_id']
    if audio_file == stop_button:
        client.voice_clients[0].stop()
        await interaction.response.send_message(f'⏹️ Stopped', ephemeral=True, silent=True, delete_after=1)
    try:
        audiolen = sounds[f'./data/audio/{audio_file}.wav']['duration'] # audio length from cache
    except:
        audiolen = 1 # default audio length
    await interaction.response.send_message(f'▶️ Playing: {audio_file}', ephemeral=True, silent=True, delete_after=audiolen)
    # Join the voice channel
    if interaction.user.voice is None:
        await interaction.response.send_message(f'⭕ You are not in voice channel', ephemeral=True, delete_after=3)
        return
    channel = interaction.user.voice.channel
    try:
        await channel.connect()
    except:
        pass
    # Play audio file
    await play(client, f'./data/audio/{audio_file}.wav')
    # # Delete message
    # await interaction.message.delete()
    # Disconnect from the voice channel
    await vc_disconnect(client)

# Display buttons with audio files when user types !playsound
@client.event
async def on_message(message):
    if message.content.startswith('!playsound'):
        # Get list of audio files
        audio_files = await list_audio_files()
        # Append stop button
        audio_files.append(stop_button)
        # Split to 25 files per button
        buttons_groups = [audio_files[i:i + 25] for i in range(0, len(audio_files), 25)]
        for group in buttons_groups:
            # Create buttons
            buttons = []
            for file in group:
                buttons.append(discord.ui.Button(label=file, custom_id=file))
            # Create view
            view = discord.ui.View()
            for button in buttons:
                view.add_item(button)
            # Send message
            await message.channel.send('', view=view)
    await client.process_commands(message)

# Run bot
client.run(token)
