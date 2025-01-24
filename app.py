from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import os
import re
import logging
import boto3
from botocore.exceptions import ClientError
import tempfile
import time

application = Flask(__name__, static_folder='static')
CORS(application)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Configure AWS S3
try:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name=os.environ.get('AWS_REGION', 'us-east-1')
    )
    # Test the connection
    s3_client.list_buckets()
    BUCKET_NAME = os.environ.get('AWS_BUCKET_NAME')
    if not BUCKET_NAME:
        raise ValueError("AWS_BUCKET_NAME not set")
    
    # Verify bucket exists
    s3_client.head_bucket(Bucket=BUCKET_NAME)
    
except Exception as e:
    application.logger.error(f"AWS Configuration Error: {e}")
    s3_client = None
    BUCKET_NAME = None

def sanitize_filename(filename):
    # Replace invalid characters with underscores
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)  # Replace invalid file characters
    filename = re.sub(r'[^\x00-\x7F]+', '_', filename)  # Replace non-ASCII characters
    filename = filename.replace(' ', '_')  # Replace spaces with underscores
    return filename

def upload_to_s3(file_path, object_name):
    """Upload a file to S3 bucket"""
    try:
        s3_client.upload_file(file_path, BUCKET_NAME, object_name)
        # Generate a presigned URL that expires in 1 hour
        url = s3_client.generate_presigned_url('get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': object_name},
            ExpiresIn=3600)
        return url
    except ClientError as e:
        application.logger.error(f"S3 upload error: {e}")
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

@application.route('/download', methods=['POST'])
def download_video():
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
                'format': 'best',  # Get best quality
                'outtmpl': f'{temp_dir}/%(title)s.%(ext)s',
                'quiet': True,
                'restrictfilenames': True,
                'progress_hooks': [lambda d: None],  # Disable progress output
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