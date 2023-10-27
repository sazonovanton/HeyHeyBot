'''
Flask webserver for uploading and deleting audio files.
User can upload audio files to the server and delete them. Auth is required.
Uploaded audio files are converted to .wav format and saved to the data/audio folder.
'''

from flask import Flask, request, Response, render_template, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename
import os
import subprocess
import secrets

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
        self.host = os.getenv('WEBPAGE_HOST') if os.getenv('WEBPAGE_HOST') else 'localhost'
        self.port = int(os.getenv('WEBPAGE_PORT')) if os.getenv('WEBPAGE_PORT') else 5100

        self.app = Flask(__name__)
        self.app.config['UPLOAD_FOLDER'] = self.upload_folder
        self.app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB

        self.app.add_url_rule('/', 'index', self.index, methods=['GET', 'POST'])
        self.app.add_url_rule('/upload', 'upload', self.upload, methods=['GET', 'POST'])
        self.app.add_url_rule('/delete', 'delete', self.delete, methods=['GET', 'POST'])
        self.app.add_url_rule('/login', 'login', self.login, methods=['GET', 'POST'])
        self.app.add_url_rule('/logout', 'logout', self.logout, methods=['GET', 'POST'])

        # set secret key
        self.app.secret_key = secrets.token_hex(16)

        # add template location
        self.app.template_folder = './templates'

    def run(self):
        '''
        Starts the webserver.
        '''
        self.app.run(host=self.host, port=self.port, debug=False, threaded=True)

    def filelist(self, filter=('wav')):
        '''
        Returns a list of all files in the upload folder, while filtering for the given file extension.
        '''
        files = []
        for file in os.listdir(self.app.config['UPLOAD_FOLDER']):
            if file.endswith(filter):
                files.append(file)
        files.sort()
        return files

    def index(self):
        '''
        Renders index.html with a list of all uploaded files.
        '''
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        else:
            return render_template('index.html', uploaded_files=self.filelist())
        
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
        Lets user upload audio files to the server.
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
                        return render_template('index.html', success='File uploaded.', uploaded_files=self.filelist())
                    else:
                        os.remove(os.path.join(self.app.config['UPLOAD_FOLDER'], filename))
                        return render_template('index.html', error='Something went wrong while converting the file.', uploaded_files=self.filelist())
                else:
                    return render_template('index.html', error='Invalid file extension.', uploaded_files=self.filelist())
            else:
                return render_template('index.html')
    
    def delete(self):
        '''
        Deletes audio file from server.
        Delete is called via <a href="/delete?filename={{ filename }}">Delete</a> in index.html.
        '''
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        else:
            if request.method == 'GET':
                filename = request.args.get('filename')
                if os.path.exists(os.path.join(self.app.config['UPLOAD_FOLDER'], filename)):
                    os.remove(os.path.join(self.app.config['UPLOAD_FOLDER'], filename))
                    return render_template('index.html', success='File deleted.', uploaded_files=self.filelist())
                else:
                    return render_template('index.html', error='File not found.', uploaded_files=self.filelist())
            else:
                return render_template('index.html')
            
    def allowed_file(self, filename):
        '''
        Checks if file extension is allowed.
        '''
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extentions
    
    def convert(self, filename, loudness=-16):
        '''
        Converts audio file to .wav format.
        Necessary for volume normalization and to avoid bitrate issues:
            -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json
            -ar 48000
            -ac 2
        '''
        if os.path.exists(os.path.join(self.app.config['UPLOAD_FOLDER'], filename)):
            subprocess.call(
                ['ffmpeg', '-i', os.path.join(self.app.config['UPLOAD_FOLDER'], filename), '-af', f'loudnorm=I={loudness}', '-ar', '48000', '-ac', '2', '-y', os.path.join(self.app.config['UPLOAD_FOLDER'], filename.replace('.mp3', '.wav'))]
            )
            os.remove(os.path.join(self.app.config['UPLOAD_FOLDER'], filename))
            return True
        else:
            return False
    
if __name__ == "__main__":
    WebApp()