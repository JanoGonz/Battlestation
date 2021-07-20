from flask.helpers import url_for
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import ForeignKey
from app import db, login, scheduler
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from hashlib import md5
from time import time
import jwt
from app.search import add_to_index, remove_from_index, query_index
from flask import current_app
import json

#search class
class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


#llamar a los eventos
db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index = True, unique = True)
    email = db.Column(db.String(120), index = True, unique = True)
    password_hash = db.Column(db.String(128))
    register_date = db.Column(db.Date, default=datetime.utcnow) #default?
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    about_me = db.Column(db.String(120), default="")
    memberships = db.relationship('Membership', foreign_keys='Membership.user_id', backref='participant', lazy='dynamic') 
    messages_sent = db.relationship('Message',foreign_keys='Message.sender_id',
                                    backref='author', lazy='dynamic')
    messages_received = db.relationship('Message',
                                    foreign_keys='Message.recipient_id', backref='recipient', lazy='dynamic')
    last_message_read_time = db.Column(db.DateTime)
    last_notification_read_time = db.Column(db.DateTime)
    profile_pic = db.Column(db.String(20), default='')
    notifications = db.relationship('Notification', backref='user',
                                    lazy='dynamic')
    tournament_alerts = db.relationship('TournamentAlert',
                                    foreign_keys='TournamentAlert.user_id', backref='alertee', lazy='dynamic')
    pairing_1 = db.relationship('Pairing', foreign_keys='Pairing.user_1', backref='user_1_i',
                                    lazy='dynamic')
    pairing_2 = db.relationship('Pairing', foreign_keys='Pairing.user_2', backref='user_2_i',
                                    lazy='dynamic')
    organizer = db.relationship('Organizer', foreign_keys="Organizer.user_id", backref="organizer_name",
                                    lazy="dynamic")
    organization_message_sender = db.relationship('OrganizationMessage', foreign_keys="OrganizationMessage.sender_id", backref="author_org_message", lazy="dynamic")
    organization_reply_user = db.relationship('OrganizationMessageReply', foreign_keys="OrganizationMessageReply.sender_id", backref="reply_author_org_message", lazy="dynamic")
    organization_invite_requester = db.relationship('OrganizationInvitationRequest', foreign_keys="OrganizationInvitationRequest.user_id", 
                                    backref="requester", lazy='dynamic')
    #u.memberships devuelve todas las membership del usuario // representa "One" en "one to many"
    #organizes = db.relationship('Tournament', backref='organizes_as_user', lazy='dynamic')
    #pairings = db.relationship('Pairing', backref='pairings', lazy='dynamic')
    #records = db.relationship('Record', backref='records', lazy='dynamic')

    def __repr__(self):
        return 'User: {}'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        if self.profile_pic == None or self.profile_pic == '':
            digest = md5(self.email.lower().encode('utf-8')).hexdigest()
            return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, size)
        else:
            return url_for('static', filename='profile_pics/' + str(self.profile_pic))

    def signedIn(self):
        return Tournament.query.join(
            Membership, (Membership.user_id == User.id).filter(User.id == self.id).order_by(Tournament.starts_at.desc())
        )
    
    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256')
    
    def new_messages(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        unread_msgs = Message.query.filter_by(recipient=self).filter(
            Message.timestamp > last_read_time).count() + \
            OrganizationMessageReply.query.filter(OrganizationMessageReply.sender_id==self.id).\
                filter(OrganizationMessageReply.sent_by_org==True).filter(OrganizationMessageReply.timestamp > last_read_time).count()
        return unread_msgs

    def add_notification(self, name, type, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, type=type, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n
    
    def new_alerts(self):
        last_read_time = self.last_notification_read_time or datetime(1900, 1, 1)
        return TournamentAlert.query.filter_by(alertee=self).filter(
            TournamentAlert.timestamp > last_read_time).count()

    def organizes(self, org_id):
        check_org = Organizer.query.filter(Organizer.user_id==self.id).filter(Organizer.organization_id==org_id).count()
        if check_org==1:
            return True
        else:
            return False
    
    def new_org_alerts(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        if OrganizationMessageReply.query.filter(OrganizationMessageReply.sender_id==self.id).\
                filter(OrganizationMessageReply.sent_by_org==True).filter(OrganizationMessageReply.timestamp > last_read_time).count() > 0:
            return True
        else:
            return False
        


    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Tournament(SearchableMixin, db.Model):
    __searchable__ = ['name', 'game']
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), index = True)
    organizer_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    game = db.Column(db.String(255), index = True)
    created_at = db.Column(db.DateTime, index = True, default=datetime.utcnow) #default?
    starts_at = db.Column(db.DateTime, index = True)
    type_pairing = db.Column(db.Integer)
    type_registration = db.Column(db.Integer)
    min_participants = db.Column(db.Integer, default=0)
    max_participants = db.Column(db.Integer, default=0)
    organizer_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    in_progress = db.Column(db.Boolean, default=False)
    visible = db.Column(db.Boolean, default=False)
    between_rounds = db.Column(db.Integer, default=0)
    active_round = db.Column(db.Integer, default = 0)
    max_rounds = db.Column(db.Integer, default=1)
    #0 Swiss, #1 liga, #2 single elimination, #3 double elimination
    type = db.Column(db.Integer, default=0)
    participants = db.relationship('Membership', backref='participants', lazy='dynamic')
    info = db.relationship('Tournament_Info', backref='info', lazy='dynamic') # 1:1?
    tournament_pairing = db.relationship('Pairing', backref='tournament_data', lazy='dynamic')

    def __repr__(self):
        return '<Tournament {}>'.format(self.name)

    def get_next_trigger(self):
        if self.in_progress==True and self.active_round < self.max_rounds:
            return scheduler.get_job('schedule_tournament_' + self.id + '_round_' + self.active_round + 1).next_run_time()
        elif self.in_progress==True and self.active_round == self.max_rounds:
            return scheduler.get_job('end_tournament' + self.id ).next_run_time()


class Membership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id')) #many side
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))
    wins = db.Column(db.Integer, default=0)
    loses = db.Column(db.Integer, default=0)
    ties = db.Column(db.Integer, default=0)
    result = db.Column(db.Text, default='-')
    ready = db.Column(db.Boolean, default=False)
    banned = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<User: {} participates in {}>'.format(self.user_id, self.tournament_id)

class Tournament_Info(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_tournament = db.Column(db.Integer, db.ForeignKey('tournament.id'))
    description = db.Column(db.Text)
    location = db.Column(db.Text)
    rules = db.Column(db.Text)
    schedule = db.Column(db.Text)
    prizes = db.Column(db.Text)
    contact = db.Column(db.Text)
    img_url = db.Column(db.Text, default='')

    def avatar(self, size):
        if self.img_url != None or self.img_url != '':
            return url_for('static', filename='profile_pics/' + str(self.img_url))

    def __repr__(self):
        #pillar el nombre la foreign key?
        return '<Tournament info: {} for tournament {}>'.format(self.user_id, self.tournament_id)


class Pairing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_tournament = db.Column(db.Integer, db.ForeignKey('tournament.id'))
    user_1 = db.Column(db.Integer, db.ForeignKey('user.id'))
    user_2 = db.Column(db.Integer, db.ForeignKey('user.id'))
    result_1 = db.Column(db.Integer)
    result_2 = db.Column(db.Integer)
    ready_1 = db.Column(db.Boolean, default = False)
    ready_2 = db.Column(db.Boolean, default = False)
    round = db.Column(db.Integer, default = 0)
    pairings = db.relationship('User', backref='user_1', uselist=False, foreign_keys=[user_1])
    rivals = db.relationship('User', backref='user_2', uselist=False, foreign_keys=[user_2])
    user_1_r = db.relationship(User, foreign_keys=[user_1], back_populates='user_1')
    user_2_r = db.relationship(User, foreign_keys=[user_2], back_populates='user_2')


    def __repr__(self):
        return '<User: {} participates in {} against {}>'.format(self.user_1, self.id_tournament, self.user_2)
    

class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    location = db.Column(db.Text)
    website = db.Column(db.Text)
    contact = db.Column(db.Text)
    profile_pic = db.Column(db.String(20), default='')
    last_message_read_time = db.Column(db.DateTime)
    organizers = db.relationship('Organizer', backref='organizers', lazy='dynamic')
    organizes = db.relationship('Tournament', backref='organizes', lazy='dynamic')
    org_poster = db.relationship('OrganizationPost', backref='poster', lazy='dynamic')
    receiver = db.relationship('OrganizationMessage', foreign_keys='OrganizationMessage.org_id', backref='receiver', lazy='dynamic')
    
    def __repr__(self):
        return 'Organization: {}'.format(self.name)
    
    def avatar(self, size):
        if self.profile_pic == None or self.profile_pic == '':
            digest = md5(self.name.lower().encode('utf-8')).hexdigest()
            return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, size)
        else:
            return url_for('static', filename='profile_pics/' + str(self.profile_pic))

    def add_notification(self, name, type, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, type=type, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n
    
    def new_messages(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        if OrganizationMessageReply.query.filter(OrganizationMessageReply.organization_id==self.id).\
                filter(OrganizationMessageReply.sent_by_org==False).filter(OrganizationMessageReply.timestamp > last_read_time).count() > 0 or\
                OrganizationMessage.query.filter(OrganizationMessage.org_id==self.id).filter(OrganizationMessage.timestamp > last_read_time).count() > 0:
            return True
        else:
            return False

    def new_requests(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        if OrganizationInvitationRequest.query.filter(OrganizationInvitationRequest.organization_id==self.id).\
                filter(OrganizationInvitationRequest.timestamp > last_read_time).count() > 0:
            return True
        else:
            return False

class Organizer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    edit = db.Column(db.Boolean)
    create = db.Column(db.Boolean)
    delete = db.Column(db.Boolean)

    def __repr__(self):
        return '<User: {} organizes in {}>'.format(self.user_id, self.tournament_id)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.String(10000))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Message {}>'.format(self.body)
    

class TournamentAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    round = db.Column(db.Integer, default = 0)
    #0 new round, #1 todos los pairings completos, #2 error en results, #3 resultado cambiado, #4 banned lol
    type= db.Column(db.Integer, default=0)
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    #0 mensajes, 1 notificaciones de eventos, #2 Mensaje organización
    type = db.Column(db.Integer)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))

class OrganizationInvitationRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    #-1 rechazado, 0 pendiente, 1 aceptado
    status = db.Column(db.Integer, default=1)
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

class OrganizationMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    original_message = db.relationship('OrganizationMessageReply', foreign_keys="OrganizationMessageReply.message_id", 
        backref="original_message", lazy="dynamic")

    def __repr__(self):
        return '<Message {}>'.format(self.message)

class OrganizationMessageReply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('organization_message.id'))
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    sent_by_org = db.Column(db.Boolean, default=False)
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

class OrganizationPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    
    
