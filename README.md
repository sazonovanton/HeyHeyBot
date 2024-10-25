# HeyHeyBot 🎵
HeyHeyBot is a simple Discord bot with soundboard functionality that enhances your voice chat experience. Whenever a user joins a voice chat, the bot plays a customizable greeting audio for that user, announcing their arrival to others in the channel. 

## Features 🌟
- **Personalized Greetings**: Assign a unique audio file for each user. When they join the voice chat, their greeting is played.
- **Soundboard Functionality**: By sending `!playsound` to a chat on Discord server, you can request buttons with the names of available sounds. Clicking a button will play the corresponding sound in the voice chat.
- **Automatic Audio Playback**: The bot joins the voice channel to play audio, ensuring a seamless experience for users.
- **Webserver for Audio Uploads**: Application includes a webserver that allows users to upload their audio files with ease if enabled. 
- **User-Specific Greetings**: Through the web interface, you can:
  - Upload custom greeting sounds for specific Discord users
  - Set existing soundboard sounds as user greetings
  - View and manage greeting history with automatic versioning
- **HTTPS Support**: Secure your web interface with SSL/TLS encryption for added security.

## Setup & Configuration 🛠️
### Prerequisites
Get your Discord bot token from [Discord Developer Portal](https://discord.com/developers/applications). Token can be requested by creating a new application and clicking `Reset Token` button on a Bot page (link to this page looks like this: `https://discord.com/developers/applications/{APPLICATION_ID}/bot`).

Easiest way to run the bot is using Docker.  
Change `docker-compose.yml` file to match your settings (example below):
```yaml
version: "3"
services:
  heyheybot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: HeyHeyBot
    environment:
      - DISCORD_TOKEN=PLACE_YOUR_DISCORD_TOKEN_HERE
      - DISCORD_CONTINUE_PRESENCE=True
      - DISCORD_MUTING_ANNOUNCE=False
      # - WEBPAGE_USERNAME=YOUR_WEBPAGE_USERNAME
      # - WEBPAGE_PASSWORD=YOUR_WEBPAGE_PASSWORD
      # - WEBPAGE_HOST=localhost
      # - WEBPAGE_PORT=5100
      # - SSL_CERT=/path/to/cert.pem
      # - SSL_KEY=/path/to/key.pem
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      # For SSL certificates:
      # - ./certs:/app/certs
    # ports:
    #   - 5100:5100
    restart: unless-stopped
```  
Possible environment variables:
* `DISCORD_TOKEN` - Discord bot token (required)
* `DISCORD_CONTINUE_PRESENCE` - Whether bot will leave voice channel after playing audio (default: `False`)
* `DISCORD_MUTING_ANNOUNCE` - Whether to announce muting/unmuting (default: `True`)
* `DISCORD_ARRIVAL_ANNOUNCE` - Whether to announce user arrivals (default: `True`)
* `DISCORD_LEAVE_ANNOUNCE` - Whether to announce user departures (default: `True`)  
* `DISCORD_LOGLEVEL` - Logging level (default: `WARNING`)
* `WEBPAGE_USERNAME` - Username for a webpage where you can upload files (required for the webserver to start)
* `WEBPAGE_PASSWORD` - Password for this webpage (required for the webserver to start)
* `WEBPAGE_HOST` - Host for this webpage (default `localhost`, set to something like `0.0.0.0` if you want to access webpage from outside)
* `WEBPAGE_PORT` - Port for webserver to use (default `5100`, also uncomment `ports` section in `docker-compose.yml`)
* `SSL_CERT` - Path to SSL certificate file (optional, for HTTPS support)
* `SSL_KEY` - Path to SSL private key file (optional, for HTTPS support)

Then run the following command in the root directory of the project:
```bash
docker compose up -d
```

### Configuration
- **Soundboard**: Store greeting audios in the `./data/audio` directory. Only `.wav` files are supported.
- **Announcements**: Store announcement audios in the `./data/greetings`, `./data/leavings` and `./data/mutings` directories. Default files should be `hello.wav`, `bye.wav` and `muted.wav` respectively. Custom greeting files are automatically versioned and stored as `{discord_name}.wav` for current greetings and `{discord_name}.{version}.wav` for previous versions. Only `.wav` files are supported.  

Example directory structure:
```
data
├── audio
│   ├── fuze.wav
│   ├── amogus.wav
│   ├── pew.wav
│   └── ...
├── greetings
│   ├── hello.wav
│   ├── cooldiscordname.wav
│   ├── cooldiscordname.1.wav
│   ├── cooldiscordname.2.wav
│   └── ...
├── leavings
│   ├── bye.wav
│   ├── cooldiscordname.wav
│   └── ...
└── mutings
    ├── muted.wav
    ├── cooldiscordname.wav
    └── ...
```

### HTTPS Configuration
To enable HTTPS:

1. Prepare your SSL certificate and private key files (e.g., using Let's Encrypt)
2. Add the certificate files to your Docker volume by adding this to docker-compose.yml:
   ```yaml
   volumes:
     - ./certs:/app/certs
   ```
3. Set the SSL environment variables in docker-compose.yml:
   ```yaml
   environment:
     - SSL_CERT=/app/certs/cert.pem
     - SSL_KEY=/app/certs/key.pem
   ```
4. Restart the container for changes to take effect

### Adding a bot to your server
1. Go to [Discord Developer Portal](https://discord.com/developers/applications) and select your application.
2. Go to `OAuth2` tab and select `URL Generator`.
3. Select `bot` scope and set bot permissions. At least `Read Messages/View Channels`, `Send Messages in Threads`, `Connect`, `Speak`, `Use Voice Activity` and `Priority Speaker` permissions are required.
4. Copy the generated link and paste it in your browser. Select the server you want to add the bot to and click `Authorize`.
5. Bot should now be visible in the server's member list.

### Logs
Logs are stored in the `./logs` directory and rotated by size (1 MB). History of 5 logs is kept.

### Webserver
You can use web interface to manage audio files and user greetings. The interface provides:

1. **Soundboard Management**:
   - Upload new sounds to the soundboard
   - Play and delete existing sounds
   - Set any soundboard sound as a user's greeting

2. **User Greetings Management**:
   - Upload custom greeting sounds for specific Discord users
   - View all users' greeting sounds with version history
   - Play and delete greeting sounds
   - Automatic versioning of greeting sounds (old versions are preserved)

When file is uploaded it automatically converts to `.wav`. Use `!playsound` in Discord chat to request for a new updated soundboard buttons.  

`WEBPAGE_USERNAME` and `WEBPAGE_PASSWORD` is required for a webserver to start. When it starts you can access it via browser:
- HTTP: `http://{WEBPAGE_HOST}:{WEBPAGE_PORT}/`
- HTTPS (if configured): `https://{WEBPAGE_HOST}:{WEBPAGE_PORT}/`

Default location is [http://localhost:5100/](http://localhost:5100/) or [https://localhost:5100/](https://localhost:5100/) if HTTPS is enabled.

Uploaded files will be automatically converted to WAV and volume will be normalized to -16.

## Usage 🚀

1. Join a voice chat and experience personalized greetings!
2. Trigger the soundboard by typing !playsound and click on the displayed buttons to play the sounds from `./data/audio` directory. Soundboard will be send to chat as a message and will remain there. If you update the `./data/audio` directory, you need to request new soundboard by typing `!playsound` again.
3. Upload new audio to soundboard via webpage if you have set it up.
4. Set custom greeting sounds for specific users through the web interface:
   - Upload a new sound directly as a greeting
   - Set an existing soundboard sound as a greeting
   - View and manage greeting history for each user

Beware that there is no differentiating between servers yet. If you have multiple servers with the bot, announcements for users and soundboard will be the same on all of them.  

## Additional Information 📚

### Converting audio files to WAV
You can use [FFmpeg](https://ffmpeg.org/) to convert audio files to WAV format.  
Simpliest command:
```bash
ffmpeg -i "sound.mp3" "sound.wav"
```  
Changing volume to 70% of original:
```bash
ffmpeg -i "sound.mp3" -af "volume=0.7" "sound.wav"
```  
Trimming audio from 0 to 4 seconds:
```bash
ffmpeg -i "sound.mp3" -ss 0 -to 4 "sound.wav"
```
If we also want it to fading out at the end (fade out starts at 3 seconds and lasts 1 second):
```bash
ffmpeg -i "sound.mp3" -ss 0 -to 4 -af "afade=t=out:st=3:d=1" "sound.wav"
```  
Learn more about FFmpeg [here](https://ffmpeg.org/ffmpeg.html).

### Normalizing volume of audio files
It is possible that some of your audio files will be louder than others. You can use `volume_normalization.py` script to normalize volume of all audio files in a given directory. It uses `ffmpeg` to do it, so you need to have it installed. Just run the script, it will ask you for the directory with audio files and then it will normalize them.  
It works only with `.wav` files.
