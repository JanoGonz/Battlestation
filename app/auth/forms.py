from flask.app import Flask
from flask.templating import render_template
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import SelectField, StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.fields.core import IntegerField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo, Length, InputRequired
from wtforms.widgets.core import HiddenInput
from app.models import User, Organization, Organizer
from flask_babel import _, lazy_gettext as _l
from flask_login import current_user
from wtforms.fields.html5 import DateTimeField, DateTimeLocalField
from datetime import datetime
import pytz


class LoginForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    remember_me = BooleanField(_l('Remember Me'))
    submit = SubmitField(_l('Sign In'))

class RegistrationForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    password =PasswordField(_l('Password'), validators=[DataRequired()])
    password2 = PasswordField(
        _l('Repeat Password'), validators = [DataRequired(), EqualTo('password')]
    )
    submit = SubmitField(_l('Register'))

    def validate_username(self,username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError(_l('Username already in use'))
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError(_l('Email address already in use'))

#profile editor
class EditProfileForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    about_me = TextAreaField(_l('About me'), validators=[Length(min=0, max=120)])
    picture = FileField(_l('Profile pic'), render_kw={'class': 'form-control-file'}, validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField(_l('Submit'))

    def __init__(self, original_username, *args, **kwargs):
        #overload validation
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
    
    def validate_username(self, username):
        if username.data != self.original_username:
            #check si el nombre de usuario existe
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError(_l('Username already in use.'))

class EmptyForm(FlaskForm):
    submit = SubmitField(_l('Submit'),render_kw={'class': 'btn'})

class ResetPasswordRequestForm(FlaskForm):
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    submit = SubmitField(_l('Request Password Reset'))

class ResetPasswordForm(FlaskForm):
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    password2 = PasswordField(
        _l('Repeat Password'), validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(_l('Request Password Reset'))

class CreateOrganizationForm(FlaskForm):
    name = StringField(_l('Organization name'), validators=[Length(min=5, max=50)])
    location = StringField(_l('Location (optional)'))
    website = StringField(_l('Website (optional)'))
    contact = StringField(_l('Contact email (optional)'))
    submit = SubmitField(_l('Submit'))
    
    def validate_name(self, name):
            org = Organization.query.filter_by(name=name.data).first()
            if org is not None:
                raise ValidationError(_l('Organization name already in use.'))


class CreateTournamentForm(FlaskForm):
    name = StringField(_l('Name'), validators=[DataRequired()])
    game = StringField(_l('Game'), validators=[DataRequired()])
    starts_at = DateTimeLocalField(_l('Start Date'), format='%Y-%m-%dT%H:%M',validators=[InputRequired()], default= lambda: datetime.now(), id='datepick')
    organizer = SelectField(_l('Organizer'))
    time_between_rounds = SelectField(_l('Time between rounds'))
    number_of_rounds = SelectField(_l('Number of rounds'))
    visible = BooleanField(_l('Visible'))
    submit = SubmitField(_l('Submit'))

    def __init__(self):
        super(CreateTournamentForm, self).__init__()
        organizaciones = Organization.query.join(Organizer).filter(Organization.id == Organizer.organization_id).filter(Organizer.user_id==current_user.id)
        
        if organizaciones is not None:
            values =  [(-1, _l('As user'))] + [(c.id, c.name) for c in organizaciones] 
            self.organizer.choices = values
        else:
            self.organizer.choices = [(-1, _l('As user'))]

        self.time_between_rounds.choices = [
            (0, _l('1 hour')),
            (1, _l('1 week')),
            (2, _l('2 minutes :)'))
        ]

        self.number_of_rounds.choices = [
            (1, 1),
            (2, 2),
            (3, 3),
            (4, 4),
            (5, 5),
            (6, 6),
            (7, 7),
            (8, 8),
            (9, 9),
        ]

    def validate_starts_at(self,starts_at):
        if starts_at.data < datetime.now():
            raise ValidationError(_l('You cannot create a tournament that starts in the past'))

class NewTournamentAdv(FlaskForm):
    name = StringField(_l('Name'), validators=[DataRequired()], render_kw={'class': 'form-control'})
    game = StringField(_l('Game'), validators=[DataRequired()], render_kw={'class': 'form-control'})
    starts_at = DateTimeLocalField(_l('Start Date'), format='%Y-%m-%dT%H:%M',validators=[InputRequired()], default= lambda: datetime.now(), id='datepick', render_kw={'class': 'form-control'})
    description = TextAreaField(_l('Description'), validators=[Length(min=0, max=-1)], render_kw={'class': 'form-control description', 'rows': 3})
    rules = TextAreaField(_l('Rules'), validators=[Length(min=0, max=-1)], render_kw={'class': 'form-control', 'rows': 3})
    schedule = TextAreaField(_l('Schedule'), validators=[Length(min=0, max=-1)], render_kw={'class': 'form-control', 'rows': 3})
    prizes = TextAreaField(_l('Prizes'), validators=[Length(min=0, max=-1)], render_kw={'class': 'form-control', 'rows': 3})
    contact = TextAreaField(_l('Contact'),validators=[Length(min=0, max=-1)], render_kw={'class': 'form-control', 'rows': 3})
    organizer = SelectField(_l('Organizer'),render_kw={'class': 'form-control', 'rows': 3})
    type = SelectField(_l('Type'),render_kw={'class': 'form-control', 'rows': 3})
    time_between_rounds = SelectField(_l('Time between rounds'), render_kw={'class': 'form-control', 'rows': 3})
    number_of_rounds = SelectField(_l('Number of rounds'), render_kw={'class': 'form-control', 'rows': 3})
    picture = FileField(_l('Tournament Banner'), render_kw={'class': 'btn'}, validators=[FileAllowed(['jpg', 'png'])])
    visible = BooleanField(_l('Visible'))
    submit = SubmitField(_l('Submit'), render_kw={'class': 'btn'})

    def __init__(self):
        super(NewTournamentAdv, self).__init__()
        organizaciones = Organization.query.join(Organizer).filter(Organization.id == Organizer.organization_id).filter(Organizer.user_id==current_user.id)
        
        if organizaciones is not None:
            values =[(-1, _l('As user'))]+ [(c.id, c.name) for c in organizaciones]
            self.organizer.choices = values
        else:
            self.organizer.choices = [(-1, _l('As user'))]

        self.time_between_rounds.choices = [
            (0, _l('1 hour')),
            (1, _l('1 week')),
            (2, _l('2 minutes :)'))
        ]

        self.number_of_rounds.choices = [
            (1, 1),
            (2, 2),
            (3, 3),
            (4, 4),
            (5, 5),
            (6, 6),
            (7, 7),
            (8, 8),
            (9, 9),
        ]

        self.type.choices = [
            (0, _l('Swiss')),
            (1, _l('League')),
            (2, _l('Single elimination')),
            (3, _l('Double elimination'))
        ]

    def validate_starts_at(self,starts_at):
        if starts_at.data < datetime.now():
            raise ValidationError(_l('You cannot create a tournament that starts in the past'))
        
class EditTournamentForm(FlaskForm):
    name = StringField(_l('Name'), validators=[DataRequired()], render_kw={'class': 'form-control'})
    game = StringField(_l('Game'), validators=[DataRequired()], render_kw={'class': 'form-control'})
    starts_at = DateTimeLocalField(_l('Start Date'), format='%Y-%m-%dT%H:%M',validators=[InputRequired()], render_kw={'class': 'form-control'})
    description = TextAreaField(_l('Description'), validators=[Length(min=0, max=-1)], render_kw={'class': 'form-control description', 'rows': 3})
    rules = TextAreaField(_l('Rules'), validators=[Length(min=0, max=-1)], render_kw={'class': 'form-control', 'rows': 3})
    schedule = TextAreaField(_l('Schedule'), validators=[Length(min=0, max=-1)], render_kw={'class': 'form-control', 'rows': 3})
    prizes = TextAreaField(_l('Prizes'), validators=[Length(min=0, max=-1)], render_kw={'class': 'form-control', 'rows': 3})
    contact = TextAreaField(_l('Contact'),validators=[Length(min=0, max=-1)], render_kw={'class': 'form-control', 'rows': 3})
    organizer = SelectField(_l('Organizer'), render_kw={'class': 'form-control', 'rows': 3})
    type = SelectField(_l('Type'), render_kw={'class': 'form-control', 'rows': 3})
    time_between_rounds = SelectField(_l('Time between rounds'), render_kw={'class': 'form-control', 'rows': 3})
    number_of_rounds = SelectField(_l('Number of rounds'), render_kw={'class': 'form-control', 'rows': 3})
    picture = FileField(_l('Tournament Banner'), render_kw={'class': 'form-control-file'}, validators=[FileAllowed(['jpg', 'png'])])
    visible = BooleanField(_l('Visible'))
    submit = SubmitField(_l('Submit'), render_kw={'class': 'btn'})

    def __init__(self):
        super(EditTournamentForm, self).__init__()
        organizaciones = Organization.query.join(Organizer).filter(Organization.id == Organizer.organization_id).filter(Organizer.user_id==current_user.id)
        
        if organizaciones is not None:
            values = [(-1, _l('As user'))] +[(c.id, c.name) for c in organizaciones] 
            self.organizer.choices = values
        else:
            self.organizer.choices = [(-1, _l('As user'))]

        self.time_between_rounds.choices = [
            (0, _l('1 hour')),
            (1, _l('1 week')),
            (2, _l('2 minutes :)'))
        ]

        self.number_of_rounds.choices = [
            (1, 1),
            (2, 2),
            (3, 3),
            (4, 4),
            (5, 5),
            (6, 6),
            (7, 7),
            (8, 8),
            (9, 9),
        ]

        self.type.choices = [
            (0, _l('Swiss')),
            (1, _l('League')),
            (2, _l('Single elimination')),
            (3, _l('Double elimination'))
        ]
    def validate_starts_at(self,starts_at):
        if starts_at.data < datetime.now():
            raise ValidationError(_l('You cannot create a tournament that starts in the past'))

class OrganizationPostForm(FlaskForm):
    post = TextAreaField(_l('Post'), validators=[Length(min=10, max=-1)], render_kw={'class': 'form-control', 'rows': 3})
    submit = SubmitField(_l('Submit'), render_kw={'class': 'btn btn-danger'})

class OrganizationEditForm(FlaskForm):
    name = StringField(_l('Organization name'), validators=[Length(min=5, max=50)])
    website = StringField(_l('Website'), validators=[Length(min=0, max=50)])
    contact = StringField(_l('Contact address'), validators=[Length(min=0, max=50)])
    location = StringField(_l('Location'), validators=[Length(min=0, max=100)])
    picture = FileField(_l('Profile pic'), render_kw={'class': 'form-control-file'}, validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField(_l('Submit'), render_kw={'class': 'btn btn-danger'})

    def __init__(self, original_name, *args, **kwargs):
        #overload validation
        super(OrganizationEditForm, self).__init__(*args, **kwargs)
        self.original_name = original_name
        
    def validate_name(self, name):
        if name.data != self.original_name:
            org = Organization.query.filter_by(name=name.data).first()
            if org is not None:
                raise ValidationError(_l('Organization name already in use.'))

class OrganizationInvitationRequestForm(FlaskForm):
    body = TextAreaField(_l('Body of the request'), validators=[Length(min=10, max=-1)], render_kw={'class': 'form-control', 'rows': 3})
    submit = SubmitField(_l('Submit'), render_kw={'class': 'btn btn-danger'})


class SubmitResults(FlaskForm):
    result_1 = IntegerField(_l('Result'))
    result_2 = IntegerField(_l('Result'))
    pairing_id = IntegerField(widget=HiddenInput())
    pairing_test = StringField()
    submit = SubmitField(_l('Submit'),render_kw={'class': 'btn btn-danger'})
