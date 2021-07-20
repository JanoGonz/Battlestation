from itertools import zip_longest
from flask import Flask, request, current_app
import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_babel import Babel, _, lazy_gettext as _l
from elasticsearch import Elasticsearch
from config import Config
from flask_apscheduler import APScheduler
import pytz
from pytz import utc


from apscheduler.schedulers.background import BackgroundScheduler
from flask_apscheduler import APScheduler

#db = SQLAlchemy()
db = SQLAlchemy(session_options={

    'expire_on_commit': False

})
migrate = Migrate()

babel = Babel()
login = LoginManager()
#indica a flask_login cual es la página de login, hay que usar el nombre de url_for
login.login_view = 'auth.login'
login.login_message = _l('Please log in to access this page.')
mail = Mail()
bootstrap = Bootstrap()
moment = Moment()

scheduler = BackgroundScheduler(daemon=False)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)
    babel.init_app(app)

    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
        if app.config['ELASTICSEARCH_URL'] else None

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    if not app.debug:
        if app.config['MAIL_SERVER']:
            #log correo
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                toaddrs=app.config['ADMINS'], subject='Battlestation Failure',
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR)

            #log a file
            app.logger.addHandler(mail_handler)
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler('logs/proyecto.log', maxBytes=10240,
                                            backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
            #debug, info, warning, error and critical
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

            app.logger.setLevel(logging.INFO)
            app.logger.info('Battlestation startup')


    scheduler.configure(jobstores=app.config['SCHEDULER_JOBSTORES'], executors=app.config['SCHEDULER_EXECUTORS'], job_defaults=app.config['SCHEDULER_JOB_DEFAULTS'], timezone=utc)
    scheduler.start()

    # from app.jobs import start_tasks
    # start_tasks()
    return app
    



@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])

from app import models
