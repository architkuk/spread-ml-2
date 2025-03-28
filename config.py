import os
from pathlib import Path

basedir = Path(__file__).parent
instance_dir = basedir / 'instance'
instance_dir.mkdir(exist_ok=True)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-testing'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{instance_dir}/spreadml.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False 