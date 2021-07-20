import os
from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
from dotenv import load_dotenv

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config(object):

    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
	'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')

    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL') is not None
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = ('Battlestation help', 'battlestation-help@gmail.com')
    ADMINS = ['battlestation.help@gmail.com']


    POSTS_PER_PAGE = 10
    LANGUAGES = ['en', 'es']

    """App configuration."""

    SCHEDULER_JOBSTORES = {
    'default': SQLAlchemyJobStore(
        url='sqlite:///' + os.path.join(basedir, 'app.db')
        )
    }

    SCHEDULER_EXECUTORS = {
        'default': ThreadPoolExecutor(20),
        'processpool': ProcessPoolExecutor(5)
    }

    SCHEDULER_JOB_DEFAULTS = {
        'coalesce': False,
        'max_instances': 3
    }
#     SCHEDULER_EXECUTORS = {"default": {"type": "threadpool", "max_workers": 20}}

#     SCHEDULER_JOB_DEFAULTS = {"coalesce": False, "max_instances": 3}
#     SCHEDULER_JOBSTORES = {"default": SQLAlchemyJobStore(url="sqlite:///jobs.sqlite")}
    SCHEDULER_API_ENABLED = True
