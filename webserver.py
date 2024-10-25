'''
Flask webserver for uploading and deleting audio files.
User can upload audio files to the server and delete them. Auth is required.
Uploaded audio files are converted to .wav format and saved to the data/audio folder.
'''

from flask import Flask, request, Response, render_template, redirect, url_for, session, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import os
import subprocess
import secrets
import glob
import shutil
from pydub import AudioSegment
from pydub.playback import play

from dotenv import load_dotenv
load_dotenv()

class WebApp:
    def __init__(self):
        self.credentials = {
            'username': os.getenv('WEBPAGE_USERNAME'),
            'password': os.getenv('WEBPAGE_PASSWORD')
        }
        self.allowed_extentions = {'mp3', 'wav'}
        self.upload_folder = os.getenv('UPLOAD_FOLDER') if os.getenv('UPLOAD_FOLDER') else './data/audio'
        self.greetings_folder = './data/greetings'
        self.host = os.getenv('WEBPAGE_HOST') if os.getenv('WEBPAGE_HOST') else 'localhost'
        self.port = int(os.getenv('WEBPAGE_PORT')) if os.getenv('WEBPAGE_PORT') else 5100
        self.ssl_context = None
        
        # Setup SSL if certificates are provided
        cert_path = os.getenv('SSL_CERT')
        key_path = os.getenv('SSL_KEY')
        if cert_path and key_path and os.path.exists(cert_path) and os.path.exists(key_path):
            self.ssl_context = (cert_path, key_path)

        self.app = Flask(__name__)
        self.app.config['UPLOAD_FOLDER'] = self.upload_folder
        self.app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB

        self.app.add_url_rule('/', 'index', self.index, methods=['GET', 'POST'])
        self.app.add_url_rule('/upload', 'upload', self.upload, methods=['GET', 'POST'])
        self.app.add_url_rule('/upload_greeting', 'upload_greeting', self.upload_greeting, methods=['POST'])
        self.app.add_url_rule('/set_greeting', 'set_greeting', self.set_greeting, methods=['POST'])
        self.app.add_url_rule('/set_version_as_current', 'set_version_as_current', self.set_version_as_current, methods=['POST'])
        self.app.add_url_rule('/delete', 'delete', self.delete, methods=['GET', 'POST'])
        self.app.add_url_rule('/login', 'login', self.login, methods=['GET', 'POST'])
        self.app.add_url_rule('/logout', 'logout', self.logout, methods=['GET', 'POST'])
        self.app.add_url_rule('/play', 'play_audio', self.play_audio, methods=['GET'])
        self.app.add_url_rule('/get_greetings', 'get_greetings', self.get_greetings, methods=['GET'])

        # set secret key
        self.app.secret_key = secrets.token_hex(16)

        # add template location
        self.app.template_folder = './templates'

        # Create necessary directories if they don't exist
        os.makedirs(self.upload_folder, exist_ok=True)
        os.makedirs(self.greetings_folder, exist_ok=True)

    def run(self):
        '''
        Starts the webserver with optional SSL support.
        '''
        self.app.run(
            host=self.host, 
            port=self.port, 
            debug=False, 
            threaded=True,
            ssl_context=self.ssl_context
        )

    def get_greeting_versions(self, username):
        '''
        Get all versions of greeting files for a username
        '''
        pattern = os.path.join(self.greetings_folder, f"{username}.*.wav")
        files = glob.glob(pattern)
        return sorted(files, key=lambda x: int(x.split('.')[-2]) if x.split('.')[-2].isdigit() else 0)

    def get_next_version(self, username):
        '''
        Get the next version number for a user's greeting file
        '''
        existing_versions = self.get_greeting_versions(username)
        if not existing_versions:
            return 1
        last_version = max([int(f.split('.')[-2]) for f in existing_versions if f.split('.')[-2].isdigit()])
        return last_version + 1

    def backup_existing_greeting(self, username):
        '''
        Backup existing greeting file with versioning
        '''
        current_file = os.path.join(self.greetings_folder, f"{username}.wav")
        if os.path.exists(current_file):
            next_version = self.get_next_version(username)
            backup_file = os.path.join(self.greetings_folder, f"{username}.{next_version}.wav")
            os.rename(current_file, backup_file)
            return True
        return False

    def set_version_as_current(self):
        '''
        Sets a specific version as the current greeting for a user
        '''
        if not session.get('logged_in'):
            return jsonify({'error': 'Not authorized'}), 401

        data = request.get_json()
        if not data or 'username' not in data or 'version' not in data:
            return jsonify({'error': 'Missing required fields'}), 400

        username = secure_filename(data['username'])
        version = data['version']

        # Source file is the versioned file
        source_file = os.path.join(self.greetings_folder, f"{username}.{version}.wav")
        if not os.path.exists(source_file):
            return jsonify({'error': 'Source version not found'}), 404

        # Backup current if it exists
        current_file = os.path.join(self.greetings_folder, f"{username}.wav")
        if os.path.exists(current_file):
            self.backup_existing_greeting(username)

        # Copy the versioned file as the new current
        try:
            shutil.copy2(source_file, current_file)
            return jsonify({'success': True, 'message': f'Version {version} set as current greeting for {username}'})
        except Exception as e:
            return jsonify({'error': f'Failed to set version as current: {str(e)}'}), 500

    def filelist(self, filter=('wav'), folder=None):
        '''
        Returns a list of all files in the specified folder, while filtering for the given file extension.
        '''
        target_folder = folder if folder else self.app.config['UPLOAD_FOLDER']
        files = []
        for file in os.listdir(target_folder):
            if file.endswith(filter):
                files.append(file)
        files.sort()
        return files

    def get_greetings(self):
        '''
        Returns a list of all greeting files with their associated usernames
        '''
        if not session.get('logged_in'):
            return jsonify({'error': 'Not authorized'}), 401

        greetings = []
        for file in os.listdir(self.greetings_folder):
            if file.endswith('.wav'):
                parts = file.rsplit('.', 2)
                if len(parts) == 2:  # Current greeting file
                    username = parts[0]
                    greetings.append({
                        'username': username,
                        'filename': file,
                        'is_current': True
                    })
                elif len(parts) == 3 and parts[1].isdigit():  # Versioned backup
                    username = parts[0]
                    version = parts[1]
                    greetings.append({
                        'username': username,
                        'filename': file,
                        'version': version,
                        'is_current': False
                    })

        return jsonify(greetings)

    def index(self):
        '''
        Renders index.html with a list of all uploaded files.
        '''
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        else:
            soundboard_files = self.filelist()
            greeting_files = self.filelist(folder=self.greetings_folder)
            return render_template('index.html', 
                                uploaded_files=soundboard_files,
                                greeting_files=greeting_files)
        
    def login(self):
        '''
        Displays login page when user is not logged in.
        '''
        if request.method == 'POST':
            if request.form['username'] == self.credentials['username'] and request.form['password'] == self.credentials['password']:
                session['logged_in'] = True
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error='Invalid credentials.')
        else:
            return render_template('login.html')
        
    def logout(self):
        '''
        Logs user out.
        '''
        session['logged_in'] = False
        return redirect(url_for('index'))
    
    def upload(self):
        '''
        Lets user upload audio files to the soundboard.
        '''
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        else:
            if request.method == 'POST':
                if 'file' not in request.files:
                    return render_template('index.html', error='No file selected.')
                file = request.files['file']
                if file.filename == '':
                    return render_template('index.html', error='No file selected.')
                if file and self.allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(self.app.config['UPLOAD_FOLDER'], filename))
                    success = self.convert(filename)
                    if success:
                        return render_template('index.html', 
                                            success='File uploaded.',
                                            uploaded_files=self.filelist(),
                                            greeting_files=self.filelist(folder=self.greetings_folder))
                    else:
                        os.remove(os.path.join(self.app.config['UPLOAD_FOLDER'], filename))
                        return render_template('index.html', 
                                            error='Something went wrong while converting the file.',
                                            uploaded_files=self.filelist(),
                                            greeting_files=self.filelist(folder=self.greetings_folder))
                else:
                    return render_template('index.html', 
                                        error='Invalid file extension.',
                                        uploaded_files=self.filelist(),
                                        greeting_files=self.filelist(folder=self.greetings_folder))
            else:
                return render_template('index.html')

    def set_greeting(self):
        '''
        Sets an existing sound as a user's greeting sound
        '''
        if not session.get('logged_in'):
            return jsonify({'error': 'Not authorized'}), 401

        data = request.get_json()
        if not data or 'username' not in data or 'filename' not in data:
            return jsonify({'error': 'Missing required fields'}), 400

        username = secure_filename(data['username'])
        source_file = os.path.join(self.upload_folder, data['filename'])
        
        if not os.path.exists(source_file):
            return jsonify({'error': 'Source file not found'}), 404

        # Backup existing greeting if it exists
        self.backup_existing_greeting(username)

        # Copy the selected sound as the new greeting
        target_file = os.path.join(self.greetings_folder, f"{username}.wav")
        try:
            shutil.copy2(source_file, target_file)
            return jsonify({'success': True, 'message': f'Greeting set for {username}'})
        except Exception as e:
            return jsonify({'error': f'Failed to set greeting: {str(e)}'}), 500

    def upload_greeting(self):
        '''
        Lets user upload greeting audio files for specific Discord users.
        '''
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            if 'file' not in request.files:
                return render_template('index.html', error='No file selected.')
            
            file = request.files['file']
            discord_username = request.form.get('discord_username', '').strip()
            
            if file.filename == '' or not discord_username:
                return render_template('index.html', error='Both file and Discord username are required.')
            
            if file and self.allowed_file(file.filename):
                # Backup existing greeting if it exists
                self.backup_existing_greeting(discord_username)

                # Save new greeting
                filename = secure_filename(f"{discord_username}.wav")
                file_path = os.path.join(self.greetings_folder, filename)
                file.save(file_path)
                success = self.convert(filename, folder=self.greetings_folder)
                
                if success:
                    return render_template('index.html',
                                        success=f'Greeting sound for {discord_username} uploaded successfully.',
                                        uploaded_files=self.filelist(),
                                        greeting_files=self.filelist(folder=self.greetings_folder))
                else:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return render_template('index.html',
                                        error='Something went wrong while converting the file.',
                                        uploaded_files=self.filelist(),
                                        greeting_files=self.filelist(folder=self.greetings_folder))
            else:
                return render_template('index.html',
                                    error='Invalid file extension.',
                                    uploaded_files=self.filelist(),
                                    greeting_files=self.filelist(folder=self.greetings_folder))

    def play_audio(self):
        '''
        Serves the audio file with the given filename.
        '''
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        else:
            if request.method == 'GET':
                filename = request.args.get('filename')
                folder = request.args.get('folder', 'soundboard')
                
                target_folder = self.greetings_folder if folder == 'greetings' else self.app.config['UPLOAD_FOLDER']
                
                if filename in self.filelist(folder=target_folder):
                    return send_from_directory(target_folder, filename)
                else:
                    return 'File not found', 404
            else:
                return 'Invalid request', 400
    
    def delete(self):
        '''
        Deletes audio file from server.
        '''
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        else:
            if request.method == 'GET':
                filename = request.args.get('filename')
                folder = request.args.get('folder', 'soundboard')
                
                target_folder = self.greetings_folder if folder == 'greetings' else self.app.config['UPLOAD_FOLDER']
                file_path = os.path.join(target_folder, filename)
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                    return render_template('index.html',
                                        success='File deleted.',
                                        uploaded_files=self.filelist(),
                                        greeting_files=self.filelist(folder=self.greetings_folder))
                else:
                    return render_template('index.html',
                                        error='File not found.',
                                        uploaded_files=self.filelist(),
                                        greeting_files=self.filelist(folder=self.greetings_folder))
            else:
                return render_template('index.html')
            
    def allowed_file(self, filename):
        '''
        Checks if file extension is allowed.
        '''
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extentions
    
    def convert(self, filename, folder=None, loudness=-16):
        '''
        Converts audio file to .wav format with volume normalization.
        '''
        target_folder = folder if folder else self.app.config['UPLOAD_FOLDER']
        file_path = os.path.join(target_folder, filename)
        
        if os.path.exists(file_path):
            output_path = os.path.join(target_folder, filename.replace('.mp3', '.wav'))
            subprocess.call(
                ['ffmpeg', '-i', file_path, '-af', f'loudnorm=I={loudness}', '-ar', '48000', '-ac', '2', '-y', output_path]
            )
            
            # Remove original file if it's different from the output
            if file_path != output_path:
                os.remove(file_path)
            return True
        else:
            return False
    
if __name__ == "__main__":
    WebApp()
