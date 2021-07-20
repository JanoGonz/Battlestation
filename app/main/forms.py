from flask import request
from flask.app import Flask
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, DateField
from wtforms.fields.core import IntegerField, SelectField
from wtforms.fields.simple import HiddenField
from wtforms.validators import ValidationError, DataRequired, Length
from flask_babel import _, lazy_gettext as _l
from wtforms.widgets.core import HiddenInput
from app.models import User
from flask_login import current_user




class EmptyForm(FlaskForm):
    submit = SubmitField(_l('Submit'),render_kw={'class': 'btn btn-danger'})

class SearchForm(FlaskForm):
    q = StringField(_l('Search'), validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchForm, self).__init__(*args, **kwargs)

class SubmitResults(FlaskForm):
    result_1 = IntegerField(_l('Result'))
    result_2 = IntegerField(_l('Result'))
    pairing_id = IntegerField(widget=HiddenInput())
    submit = SubmitField(_l('Submit'),render_kw={'class': 'btn btn-danger'})

    # def __init__(self, *args, **kwargs):
    #     super(SubmitResults, self).__init__()
    #     self.result_L.choices = [
    #         (0, 0),
    #         (1, 1),
    #         (2, 2)
    #     ]
    #     self.result_2.choices = [
    #         (0, 0),
    #         (1, 1),
    #         (2, 2)
    #     ]

class MessageForm(FlaskForm):
    message = TextAreaField(_l('Message'), validators=[Length(min=0, max=10000), DataRequired()], render_kw={'class': 'form-control', 'rows': 10, 'columns': 9})
    submit = SubmitField(_l('Submit'))

class DeleteMessageForm(FlaskForm):
    message_id = IntegerField(widget=HiddenInput())
    submit = SubmitField(_l('Submit'),render_kw={'class': 'btn btn-danger'})