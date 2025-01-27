from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import boto3
import json
import os

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name='eu-north-1'
        )
        
        try:
            response = s3_client.get_object(
                Bucket=os.environ.get('AWS_BUCKET_NAME'),
                Key='users/users.json'
            )
            users = json.loads(response['Body'].read().decode('utf-8'))
            user_data = users.get(str(user_id))
            
            if user_data:
                return User(
                    id=user_id,
                    username=user_data['username'],
                    password_hash=user_data['password_hash']
                )
        except:
            return None

    @staticmethod
    def get_by_username(username):
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name='eu-north-1'
        )
        
        try:
            response = s3_client.get_object(
                Bucket=os.environ.get('AWS_BUCKET_NAME'),
                Key='users/users.json'
            )
            users = json.loads(response['Body'].read().decode('utf-8'))
            
            for user_id, user_data in users.items():
                if user_data['username'] == username:
                    return User(
                        id=user_id,
                        username=user_data['username'],
                        password_hash=user_data['password_hash']
                    )
        except:
            return None

    @staticmethod
    def create(username, password):
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name='eu-north-1'
        )
        
        try:
            # Get existing users
            try:
                response = s3_client.get_object(
                    Bucket=os.environ.get('AWS_BUCKET_NAME'),
                    Key='users/users.json'
                )
                users = json.loads(response['Body'].read().decode('utf-8'))
            except:
                users = {}

            # Check if username already exists
            for user_data in users.values():
                if user_data['username'] == username:
                    return None

            # Create new user
            new_user_id = str(len(users) + 1)
            users[new_user_id] = {
                'username': username,
                'password_hash': generate_password_hash(password)
            }

            # Save updated users
            s3_client.put_object(
                Bucket=os.environ.get('AWS_BUCKET_NAME'),
                Key='users/users.json',
                Body=json.dumps(users)
            )

            return User(
                id=new_user_id,
                username=username,
                password_hash=users[new_user_id]['password_hash']
            )
        except:
            return None

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)