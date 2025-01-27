from flask import Flask, request, jsonify, redirect, url_for, send_file
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from user_management import User
import yt_dlp
import os
import re
import logging
import boto3
from botocore.exceptions import ClientError
import tempfile
import time
import subprocess

application = Flask(__name__, static_folder='static')
application.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key')  # Change this!
CORS(application)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(application)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@application.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect('/login')
    return send_file('index.html')

@application.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Missing username or password'}), 400
    
    user = User.create(username, password)
    if user:
        login_user(user)
        return jsonify({'message': 'Registration successful', 'username': username})
    else:
        return jsonify({'error': 'Username already exists'}), 400

@application.route('/login.html')
@application.route('/login')
def serve_login():
    return send_file('login.html')

@application.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logout successful'})

@application.route('/api/check-auth', methods=['GET'])
def check_auth():
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'username': current_user.username})
    return jsonify({'authenticated': False})

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Configure AWS S3
try:
    # Log environment variables (without sensitive data)
    application.logger.info(f"AWS Region: {os.environ.get('AWS_REGION')}")
    application.logger.info(f"AWS Bucket: {os.environ.get('AWS_BUCKET_NAME')}")
    application.logger.info("AWS Access Key ID exists: {}".format(bool(os.environ.get('AWS_ACCESS_KEY_ID'))))
    application.logger.info("AWS Secret Access Key exists: {}".format(bool(os.environ.get('AWS_SECRET_ACCESS_KEY'))))

    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name='eu-north-1'
    )
    
    BUCKET_NAME = os.environ.get('AWS_BUCKET_NAME')
    if not BUCKET_NAME:
        raise ValueError("AWS_BUCKET_NAME not set")
    
    # Test the connection
    s3_client.list_buckets()
    application.logger.info(f"Successfully connected to S3")
    
    def configure_s3_lifecycle():
        """Configure S3 bucket lifecycle rule to delete objects older than 1 hour"""
        try:
            s3_client.put_bucket_lifecycle_configuration(
                Bucket=BUCKET_NAME,
                LifecycleConfiguration={
                    'Rules': [
                        {
                            'ID': 'DeleteOldFiles',
                            'Status': 'Enabled',
                            'Filter': {
                                'Prefix': 'videos/'
                            },
                            'Expiration': {
                                'Days': 1
                            }
                        }
                    ]
                }
            )
            application.logger.info("Successfully configured S3 lifecycle rule")
        except Exception as e:
            application.logger.error(f"Failed to configure S3 lifecycle: {e}")
    
    # After successful S3 connection
    if s3_client and BUCKET_NAME:
        configure_s3_lifecycle()
    
except Exception as e:
    application.logger.error(f"AWS Configuration Error: {e}")
    s3_client = None
    BUCKET_NAME = None

# Check if ffmpeg is available
try:
    subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    application.logger.info("ffmpeg is available")
except (subprocess.SubprocessError, FileNotFoundError):
    application.logger.warning("ffmpeg is not available, some videos may not process correctly")

def sanitize_filename(filename):
    # Replace invalid characters with underscores
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)  # Replace invalid file characters
    filename = re.sub(r'[^\x00-\x7F]+', '_', filename)  # Replace non-ASCII characters
    filename = filename.replace(' ', '_')  # Replace spaces with underscores
    return filename

def upload_to_s3(file_path, object_name):
    """Upload a file to S3 bucket"""
    try:
        if not s3_client or not BUCKET_NAME:
            application.logger.error("S3 client or bucket name not properly initialized")
            return None

        application.logger.info(f"Attempting to upload {file_path} to {BUCKET_NAME}/{object_name}")
        
        # Upload file without ACL
        s3_client.upload_file(
            file_path, 
            BUCKET_NAME, 
            object_name
        )
        application.logger.info("File uploaded successfully")

        # Generate direct URL
        url = f"https://{BUCKET_NAME}.s3.eu-north-1.amazonaws.com/{object_name}"
        
        application.logger.info(f"Generated URL: {url}")
        return url
    except Exception as e:
        application.logger.error(f"S3 upload error: {e}")
        application.logger.error("Full error details:", exc_info=True)
        return None

def check_file_size(file_path, max_size_mb=50):
    """Check if file size is within Vercel's limit"""
    max_size_bytes = max_size_mb * 1024 * 1024
    file_size = os.path.getsize(file_path)
    return file_size <= max_size_bytes

def get_mime_type(file_ext):
    mime_types = {
        'mp4': 'video/mp4',
        'webm': 'video/webm',
        'mkv': 'video/x-matroska',
        'mp3': 'audio/mpeg',
        'm4a': 'audio/mp4',
    }
    return mime_types.get(file_ext.lower(), 'application/octet-stream')

def check_video_size(url):
    """Check video size before downloading"""
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            filesize = info.get('filesize', 0)
            if filesize and filesize > 500000000:  # 500MB
                return False
            return True
    except:
        return True  # If we can't check size, proceed with download

def cleanup_old_files():
    """Delete files older than 1 hour"""
    try:
        one_hour_ago = int(time.time() - 3600)
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix='videos/')
        
        if 'Contents' in response:
            for obj in response['Contents']:
                # Extract timestamp from filename (format: videos/timestamp_filename)
                try:
                    timestamp = int(obj['Key'].split('/')[1].split('_')[0])
                    if timestamp < one_hour_ago:
                        s3_client.delete_object(Bucket=BUCKET_NAME, Key=obj['Key'])
                        application.logger.info(f"Deleted old file: {obj['Key']}")
                except (IndexError, ValueError):
                    continue
                    
    except Exception as e:
        application.logger.error(f"Cleanup error: {e}")

@application.route('/download', methods=['POST'])
@login_required
def download_video():
    # Run cleanup before processing new download
    cleanup_old_files()
    video_url = request.json.get('url')

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        # Check video size first
        if not check_video_size(video_url):
            return jsonify({"error": "Video file is too large (max 500MB)"}), 413

        # Create a temporary directory for downloads
        with tempfile.TemporaryDirectory() as temp_dir:
            # Configure yt-dlp options
            ydl_opts = {
                'format': 'best[ext=mp4]/best',  # Prefer MP4 format
                'outtmpl': f'{temp_dir}/%(title)s.%(ext)s',
                'quiet': True,
                'restrictfilenames': True,
                'progress_hooks': [lambda d: None],
                'no_warnings': True,
                'extract_flat': False,
                'format_sort': ['res:1080', 'ext:mp4:m4a']
            }

            # Create a yt-dlp object
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video info
                info = ydl.extract_info(video_url, download=True)
                video_title = info.get('title', 'video')
                video_ext = info.get('ext', 'mp4')
                video_filename = sanitize_filename(f"{video_title}.{video_ext}")
                full_path = os.path.join(temp_dir, video_filename)

                # Log the downloaded file
                application.logger.debug(f"Downloaded file: {full_path}")

                # Check if the file exists
                if not os.path.exists(full_path):
                    application.logger.error(f"File not found: {full_path}")
                    return jsonify({"error": "File not found on server."}), 404

                # Generate a unique S3 object name using timestamp
                timestamp = int(time.time())
                s3_object_name = f"videos/{timestamp}_{video_filename}"

                # Add to download_video function before the S3 upload (around line 109):
                if not s3_client or not BUCKET_NAME:
                    return jsonify({"error": "AWS S3 is not properly configured"}), 503

                # Upload to S3 and get presigned URL
                download_url = upload_to_s3(full_path, s3_object_name)
                
                if not download_url:
                    return jsonify({"error": "Failed to upload to S3"}), 500

                return jsonify({
                    "download_url": download_url,
                    "title": video_title
                })

    except yt_dlp.utils.DownloadError as e:
        application.logger.error(f"DownloadError: {e}")
        return jsonify({"error": "The file wasn't available on the site."}), 400
    except Exception as e:
        application.logger.error(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500

# Add security headers (before app = app.wsgi_app)
@application.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

app = application.wsgi_app

if __name__ == '__main__':
    application.run(debug=True)