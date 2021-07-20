import itertools
from app import db, scheduler
from datetime import datetime
from operator import attrgetter
import secrets
import os
from PIL import Image
from itertools import groupby, zip_longest
from logging import log
from re import T
from flask import render_template, flash, redirect, url_for, request, g, current_app
from flask_login.utils import login_required, logout_user
from sqlalchemy.orm.util import aliased
from tzlocal import get_localzone
from app.auth import bp
from app.auth.forms import CreateTournamentForm, EditProfileForm, EditTournamentForm, EmptyForm, NewTournamentAdv, OrganizationEditForm, OrganizationInvitationRequestForm, OrganizationPostForm, RegistrationForm, LoginForm, ResetPasswordRequestForm, ResetPasswordForm, CreateOrganizationForm, SubmitResults
from flask_login import current_user, login_user
from werkzeug.urls import url_parse
from app.models import Message, OrganizationInvitationRequest, OrganizationMessage, OrganizationMessageReply, TournamentAlert, Tournament_Info, User, Tournament, Membership, Organization, Organizer, Pairing, OrganizationPost
from app.auth.email import send_password_reset_email
from flask_babel import _, lazy_gettext as _l, get_locale
import pytz
from tzlocal import get_localzone
from sqlalchemy.sql.expression import func
from sqlalchemy import or_
from app.jobs import *

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)
    
    output_size = (128, 128)
    i = Image.open(form_picture)
    i.thumbnail(output_size)

    i.save(picture_path)

    return picture_fn

def save_picture_tournament(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)
    
    output_size = (512, 256)
    i = Image.open(form_picture)
    i.thumbnail(output_size)

    i.save(picture_path)

    return picture_fn

def delete_picture(old_picture):
    os.remove(os.path.join(current_app.root_path, 'static/profile_pics', old_picture))

@bp.route('/login', methods=['GET', 'POST'])
def login():

    #si está logueado y accede a la url, redirije a index
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        #existe el usuario y la contraseña coincide?
        if user is None or not user.check_password(form.password.data):
            flash(_('Invalid username or password'))
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        #snippet para buscar la siguiente página a la que redirigir
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.home')
        return redirect(next_page)
    return render_template('auth/login.html', title=_('Login'), form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.home'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(_('You have been registered succesfully'))
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title=_('Sign up'), form = form)

@bp.route('/user/<username>')
@login_required
def user(username):
    page = request.args.get('page', 1, type=int)
    page_o = request.args.get('page_o', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    #contenido del perfil
    joined_tournaments = db.session.query(Tournament.id, Tournament.name, Tournament.game, Tournament.starts_at, Membership.result).join(Membership).filter(
        Tournament.id == Membership.tournament_id
    ).filter(
        Membership.user_id == user.id
    ).order_by(Tournament.starts_at.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False
    )
    # if len(joined_tournaments) < 1:
    #     joined_tournaments = False
    organized_tournaments = Tournament.query.filter(Tournament.organizer_user_id==user.id).order_by(Tournament.starts_at.desc()).paginate(
        page_o, current_app.config['POSTS_PER_PAGE'], False
    )
    # if len(organized_tournaments) < 1:
    #     organized_tournaments = False
    #joined_tournaments = Tournament.query.filter_by(user_id = user.id).join('participants').all()
    next_url_joined = url_for('auth.user', username=username, page=joined_tournaments.next_num, page_o=page_o) \
        if joined_tournaments.has_next else None
    prev_url_joined = url_for('auth.user', username=username, page=joined_tournaments.prev_num, page_o=page_o) \
        if joined_tournaments.has_prev else None
    next_url_organized = url_for('auth.user', username=username, page=page, page_o=organized_tournaments.next_num) \
        if organized_tournaments.has_next else None
    prev_url_organized = url_for('auth.user', username=username, page=page, page_o=organized_tournaments.prev_num) \
        if organized_tournaments.has_prev else None
    return render_template('user.html', title=_("User") + ' ' + user.username ,user=user, organized_tournaments=organized_tournaments.items, joined_tournaments = joined_tournaments.items, next_url_joined=next_url_joined, prev_url_joined= prev_url_joined,
    next_url_organized=next_url_organized, prev_url_organized=prev_url_organized #,variable=variable
    )



@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            if current_user.profile_pic != "":
                delete_picture(current_user.profile_pic)
            current_user.profile_pic = picture_file
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Changes saved'))
        return redirect(url_for('auth.user', username=current_user.username))
    #recibe get en vez de post
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    
    return render_template('edit_profile.html', title=_('Edit profile'), form=form)


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        #no está dentro del if para no usar esta función para saber si un usuario está registrado o no
        flash(_('Check your email for instructions to reset your password'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', title=_('Reset password'), form=form)
        
@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.home'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(_('Your password has been reseted.'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', title= _('Reset password'), form=form)

@bp.route('/create_org', methods=['GET', 'POST'])
@login_required
def create_org():
    form = CreateOrganizationForm()
    if form.validate_on_submit():
        organization = Organization(name=form.name.data, location=form.location.data, website=form.website.data, contact = form.contact.data)
        db.session.add(organization)
        db.session.commit()
        organizer = Organizer(user_id=current_user.id, organization_id=organization.id, edit=True, create=True, delete=True)
        db.session.add(organizer)
        db.session.commit()
        flash(_('Organization created'))
        return redirect(url_for('main.home'))
    return render_template('auth/create_org.html', form=form, title=_('New organization'))

@bp.route('/organization/<org>', methods=['GET', 'POST'])
@login_required
def organization(org):
    page = request.args.get('page', 1, type=int)
    page_p = request.args.get('page_p', 1, type=int)
    page_post = request.args.get('post_page', 1, type=int)
    organization = Organization.query.filter(Organization.name==org).first_or_404()
    if current_user.organizes(organization.id):
        new_messages = organization.new_messages()
        new_requests = organization.new_requests()
        organization.last_message_read_time = datetime.utcnow()
        db.session.commit()
        organizes = True
    else:
        organizes = False
        new_requests = False
        new_messages = False

    if organization is None:
        flash(_('Organization {} not found'.format(org)))
        return redirect(url_for('main.home'))
    form = OrganizationPostForm()
    ##################
    messages = OrganizationMessage.query.filter(OrganizationMessage.org_id==organization.id).order_by(OrganizationMessage.timestamp.desc()).all()
    replies = []
    for m in messages:
        reply = OrganizationMessageReply.query.filter(OrganizationMessageReply.message_id==m.id).order_by(OrganizationMessageReply.timestamp).all()
        replies.append(reply)
    message_list = itertools.zip_longest(messages, replies, fillvalue=None)
    ####################
    members = Organizer.query.filter(Organizer.organization_id==organization.id).all()
    pending_invitations = OrganizationInvitationRequest.query.filter(OrganizationInvitationRequest.organization_id==organization.id).filter(OrganizationInvitationRequest.status==1).order_by(OrganizationInvitationRequest.timestamp).all()
    denied_invitations = OrganizationInvitationRequest.query.filter(OrganizationInvitationRequest.organization_id==organization.id).filter(OrganizationInvitationRequest.status==0).order_by(OrganizationInvitationRequest.timestamp).all()
    accepted_invitations = OrganizationInvitationRequest.query.filter(OrganizationInvitationRequest.organization_id==organization.id).filter(OrganizationInvitationRequest.status==2).order_by(OrganizationInvitationRequest.timestamp).all()
    posts = OrganizationPost.query.filter(OrganizationPost.organization_id==organization.id).order_by(OrganizationPost.timestamp.desc()).paginate(
        page_post, current_app.config['POSTS_PER_PAGE'], False
    )
    past_tournaments = Tournament.query.filter(Tournament.organizer_id==organization.id).filter(Tournament.starts_at<datetime.now()).paginate(
        page_p, current_app.config['POSTS_PER_PAGE'], False
    )
    future_tournaments = Tournament.query.filter(Tournament.organizer_id==organization.id).filter(Tournament.starts_at>datetime.now()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False
    )

    next_url = url_for('auth.organization', org=org, page=future_tournaments.next_num, page_p=page_p, _anchor="pills-tournaments") \
        if future_tournaments.has_next else None
    prev_url = url_for('auth.organization', org=org, page=future_tournaments.prev_num, page_p=page_p, _anchor="pills-tournaments") \
        if future_tournaments.has_prev else None

    past_next_url = url_for('auth.organization', org=org, page=page, page_p=past_tournaments.next_num, _anchor="pills-tournaments") \
        if past_tournaments.has_next else None
    past_prev_url = url_for('auth.organization', org=org, page=page, page_p=past_tournaments.prev_num, _anchor="pills-tournaments") \
        if past_tournaments.has_prev else None

    post_next_url = url_for('auth.organization', org=org, page_post=posts.next_num, _anchor="pills-posts") \
        if posts.has_next else None
    post_prev_url = url_for('auth.organization', org=org, page_post=posts.prev_num, _anchor="pills-posts") \
        if posts.has_prev else None

    if request.method == 'POST' and form.validate_on_submit():
        post = OrganizationPost(post_author_id=current_user.id, organization_id=organization.id, body=form.post.data)
        db.session.add(post)
        db.session.commit()
        form.post.data = ''
        flash(_('Added the new post'))
        return redirect(url_for('auth.organization', org=org))

    return render_template('organization.html', 
    organization=organization, 
    title = organization.name,
    future_tournaments=future_tournaments.items, 
    past_tournaments = past_tournaments.items,
    members = members, 
    organizes = organizes,
    form=form,
    posts=posts.items,
    pending_invitations=pending_invitations,
    denied_invitations=denied_invitations,
    accepted_invitations=accepted_invitations,
    message_list = message_list,
    new_messages = new_messages,
    new_requests = new_requests,
    next_url = next_url, prev_url=prev_url, 
    past_next_url=past_next_url, past_prev_url=past_prev_url, 
    post_next_url=post_next_url, post_prev_url=post_prev_url
    )

@bp.route('/edit_org/<organization>', methods=['GET', 'POST'])
@login_required
def edit_org(organization):
    if current_user.organizes(organization):
        org = Organization.query.filter(Organization.id==organization).first()
        form = OrganizationEditForm(org.name)
        if request.method== 'POST' and form.validate_on_submit():
            org.name = form.name.data
            org.contact = form.contact.data
            org.website = form.website.data
            org.location = form.location.data
            if form.picture.data:
                picture_file = save_picture(form.picture.data)
                if org.profile_pic != "":
                    delete_picture(org.profile_pic)
                org.profile_pic = picture_file
                db.session.commit()
            db.session.commit()
            flash('Changes applied succesfully')
            return redirect(url_for('auth.organization', org=org.name))
        else:
            form.name.data = org.name
            form.website.data = org.website
            form.contact.data = org.contact
            form.location.data = org.location
            return render_template('auth/edit_org.html', title=_('Edit organization') + ' ' + org.name, form=form, org=org)
    else:
        return redirect(url_for('main.home'))

@bp.route('/edit_post/<organization>/<post>', methods=['GET', 'POST'])
@login_required
def edit_post(post, organization):
    if current_user.organizes(organization):
        org = Organization.query.filter(Organization.id==organization).first()
        p = OrganizationPost.query.filter(OrganizationPost.id==post).first()
        form = OrganizationPostForm()
        if request.method== 'POST' and form.validate_on_submit():
            p.body = form.post.data
            db.session.commit()
            flash(_('Organization succesfully edited'))
            return redirect(url_for('auth.organization', org=org.name))
        else:
            form.post.data = p.body
            return render_template('edit_post.html', title=_('Edit post'), form=form)
    else:
        return redirect(url_for('main.home'))
    

@bp.route('/delete_post/<organization>/<post>')
@login_required
def delete_post(post, organization):
    if current_user.organizes(organization):
        org = Organization.query.filter(Organization.id==organization).first()
        p = OrganizationPost.query.filter(OrganizationPost.id==post).first()
        db.session.delete(p)
        db.session.commit()
        flash(_('Post deleted'))
        return redirect(url_for('auth.organization', org=org.name))
    else:
        return redirect(url_for('main.home'))

@bp.route('/new_tournament', methods=['GET', 'POST'])
@login_required
def new_tournament():
    form = CreateTournamentForm()
    if form.validate_on_submit():
        time = form.starts_at.data.astimezone(pytz.utc)
        if form.organizer.data == -1:
            tournament = Tournament(organizer_user_id=current_user.id, type=0, visible=form.visible.data, name=form.name.data, game=form.game.data, starts_at=time, max_rounds = form.number_of_rounds.data, between_rounds=form.time_between_rounds.data)
        else:
            tournament = Tournament(organizer_id=form.organizer.data, type= 0, visible=form.visible.data, organizer_user_id=current_user.id, name=form.name.data, game=form.game.data, starts_at=time, max_rounds = form.number_of_rounds.data, between_rounds=form.time_between_rounds.data)
        db.session.add(tournament)
        db.session.commit()
        t_info = Tournament_Info(id_tournament=tournament.id, description="")
        job_id = 'schedule_tournament_' + str(tournament.id)
        db.session.add(t_info)
        db.session.commit()
        scheduler.add_job(
            schedule_tournament, 
            run_date=time, 
            id=job_id,
            args=[tournament.id], 
            jobstore='default')
        
        # scheduler.add_job(
        #     func=schedule_tournament,
        #     trigger= 'date',
        #     run_date=time,
        #     args=[current_app._get_current_object(), tournament.id], 
        #     id = job_id,
        #     name = job_id,
        #     replace_existing = True
        # )



        flash(_('Tournament registered correctly'))
        return redirect(url_for('main.tournament_details', tourney=tournament.id))
    return render_template('auth/new_tournament.html', title=_('New Tournament'), form=form)

@bp.route('/new_tournament_adv', methods=['GET', 'POST'])
@login_required
def new_tournament_adv():
    form = NewTournamentAdv()
    if form.validate_on_submit():
        db.session.commit()
        time = form.starts_at.data.astimezone(pytz.utc)
        if form.organizer.data == -1:
            tournament = Tournament(organizer_user_id=current_user.id, type=form.type.data, visible=form.visible.data, name=form.name.data, game=form.game.data, starts_at=time, max_rounds = form.number_of_rounds.data, between_rounds=form.time_between_rounds.data)
        else:
            tournament = Tournament(organizer_id=form.organizer.data, type=form.type.data, visible=form.visible.data, organizer_user_id=current_user.id, name=form.name.data, game=form.game.data, starts_at=time, max_rounds = form.number_of_rounds.data, between_rounds=form.time_between_rounds.data)
        db.session.add(tournament)
        db.session.commit()
        if form.picture.data:
            picture_file = save_picture_tournament(form.picture.data)
            t_info = Tournament_Info(id_tournament=tournament.id, \
                description=form.description.data,\
                rules=form.rules.data,\
                schedule=form.schedule.data,\
                prizes=form.prizes.data,\
                contact=form.contact.data,\
                img_url=picture_file)
            db.session.add(t_info)
            db.session.commit()
        else:
            t_info = Tournament_Info(id_tournament=tournament.id, \
                description=form.description.data,\
                rules=form.rules.data,\
                schedule=form.schedule.data,\
                prizes=form.prizes.data,\
                contact=form.contact.data)
            db.session.add(t_info)
            db.session.commit()

        scheduler.add_job(
            schedule_tournament, 
            run_date=time, 
            args=[tournament.id], 
            id='schedule_tournament_' + str(tournament.id))
        flash(_('Tournament registered correctly'))
        return redirect(url_for('main.tournament_details', tourney=tournament.id))
    
    return render_template('auth/new_tournament_adv.html',title=_('New tournament Advanced'), form=form)

@bp.route('/edit_tournament/<t>', methods=['GET', 'POST'])
@login_required
def edit_tournament(t):
    form = EditTournamentForm()
    form_delete = EmptyForm()
    tournament = Tournament.query.filter(Tournament.id==t).first_or_404()
    t_info = Tournament_Info.query.filter(Tournament_Info.id_tournament==tournament.id).first()
    if t_info is None:
        t_info = Tournament_Info(id_tournament=tournament.id, description="")
        db.session.add(t_info)
        db.session.commit()
    #checks if user can edit the tournament or not
    if  Tournament.query.filter(Tournament.id==tournament.id).join(Organization).filter(Organization.id==Tournament.organizer_id).join(Organizer).filter(Organizer.organization_id==Organization.id).filter(Organizer.user_id==current_user.id).count() < 1 and tournament.organizer_user_id is not current_user.id:
        return redirect(url_for('main.home'))
    else:
        if form.validate_on_submit():
            if form.picture.data:
                picture_file = save_picture_tournament(form.picture.data)
                if t_info.img_url != "":
                    delete_picture(t_info.img_url)
                t_info.img_url = picture_file
                db.session.commit()
            tournament.name = form.name.data
            tournament.visible = form.visible.data
            tournament.game = form.game.data
            tournament.starts_at = form.starts_at.data.astimezone(pytz.utc)
            if form.organizer.data == -1:
                tournament.organizer_user_id=current_user.id
                tournament.organizer_id=None
            else:
                tournament.organizer_user_id=current_user.id
                tournament.organizer_id=form.organizer.data
            tournament.max_rounds = form.number_of_rounds.data
            tournament.between_rounds=form.time_between_rounds.data
            tournament.type=form.type.data
            t_info.description = form.description.data
            t_info.rules = form.rules.data
            t_info.schedule = form.schedule.data
            t_info.prizes = form.prizes.data
            t_info.contact = form.contact.data
            db.session.commit()
            scheduler.reschedule_job('schedule_tournament_' + str(t), run_date=form.starts_at.data.astimezone(pytz.utc))
            return redirect(url_for('main.tournament_details', tourney=t))

        elif request.method == 'GET':
            form.name.default = tournament.name
            form.game.default = tournament.game
            localtimezone = get_localzone()
            t_starts_at = pytz.utc.localize(tournament.starts_at, is_dst=None).astimezone(localtimezone)
            form.time_between_rounds.default = tournament.between_rounds
            form.number_of_rounds.default = tournament.max_rounds
            if tournament.organizer_id is None:
                form.organizer.default = -1
            else:
                form.organizer.default = tournament.organizer_id
            form.starts_at.default = t_starts_at
            form.type.default = tournament.type
            form.visible.default = tournament.visible
            form.description.default = t_info.description
            form.rules.default = t_info.rules
            form.schedule.default = t_info.schedule
            form.prizes.default = t_info.prizes
            form.contact.default = t_info.contact
            form.process()
    return render_template('auth/edit_tournament.html',title=_('Edit tournament'), form=form, form_delete=form_delete, t=tournament)

@bp.route('/delete/<tournament>', methods=['POST'])
@login_required
def delete_tournament(tournament):
    t = Tournament.query.filter(Tournament.id==tournament).first_or_404()
    form = EmptyForm()
    if form.validate_on_submit():
        if t.organizer_user_id==current_user.id or Tournament.query.filter(Tournament.id==t.id).join(Organization).filter(Organization.id==Tournament.organizer_id).join(Organizer).filter(Organizer.organization_id==Organization.id).filter(Organizer.user_id==current_user.id).count() > 0:
            t_info = Tournament_Info.query.filter(Tournament_Info.id_tournament==tournament).first()
            db.session.delete(t_info)
            db.session.commit()
            memberships = Membership.query.filter(Membership.tournament_id==tournament)
            for m in memberships:
                db.session.delete(m)
                db.session.commit()
            db.session.delete(t)
            db.session.commit()
            flash(_('Tournament deleted'))
            return redirect(url_for('main.home'))
    else:
        return redirect(url_for('main.home'))


@bp.route('/request_invitation/<organization>', methods=['GET', 'POST'])
@login_required
def request_invitation(organization):
    form = OrganizationInvitationRequestForm()
    org = Organization.query.filter(Organization.id==organization).first()
    condition = Organizer.query.filter(Organizer.user_id==current_user.id).filter(Organizer.organization_id==organization).count()
    condition_2 = OrganizationInvitationRequest.query.filter(OrganizationInvitationRequest.user_id==current_user.id).filter(OrganizationInvitationRequest.organization_id==organization).count()
    if condition < 1 and condition_2 < 1:
        if form.validate_on_submit():
            invitation = OrganizationInvitationRequest(user_id=current_user.id, organization_id=organization, message=form.body.data)
            db.session.add(invitation)
            db.session.commit()
            flash(_('Request submitted'))
            return redirect(url_for('main.home'))
        return render_template('auth/request_invitation.html', title=_('Request invitation') + ' ' + org.name, form=form, org=org.name)
    else:
        
        flash(_('You have already submitted a invitation request'))
        return redirect(url_for('auth.organization', org=org.name))


@bp.route('/deny_inv/<inv>')
@login_required
def deny_inv(inv):
    invitation = OrganizationInvitationRequest.query.filter(OrganizationInvitationRequest.id==inv).first()
    organization = Organization.query.filter(Organization.id==invitation.organization_id).first()
    if current_user.organizes(organization.id):
        invitation.status = 0
        db.session.commit()
        flash(_('Invitation denied'))
        return redirect(url_for('auth.organization', org=organization.name))
    else:
        return redirect(url_for('main.home'))

@bp.route('/accept_inv/<inv>')
@login_required
def accept_inv(inv):
    invitation = OrganizationInvitationRequest.query.filter(OrganizationInvitationRequest.id==inv).first()
    organization = Organization.query.filter(Organization.id==invitation.organization_id).first()
    if current_user.organizes(organization.id):
        invitation.status = 2
        new_organizer = Organizer(user_id=invitation.user_id, organization_id=organization.id, edit=True, create=True, delete=True)
        db.session.add(new_organizer)
        db.session.commit()
        inv_accepted = Message(sender_id=current_user.id, recipient_id=invitation.user_id, body='<p>Your request to join ' + organization.name +' has been accepted!</p>')
        db.session.add(inv_accepted)
        db.session.commit()
        invitation.requester.add_notification('unread_message_count', 0, invitation.requester.new_messages())
        db.session.commit()
        flash(_('Invitation accepted'))
        return redirect(url_for('auth.organization', org=organization.name))
    else:
        return redirect(url_for('main.home'))


@bp.route('/delete_inv/<inv>')
@login_required
def delete_inv(inv):
    invitation = OrganizationInvitationRequest.query.filter(OrganizationInvitationRequest.id==inv).first()
    organization = Organization.query.filter(Organization.id==invitation.organization_id).first()
    if current_user.organizes(organization.id):
        db.session.delete(invitation)
        db.session.commit()
        flash(_('Invitation deleted, the user can reapply now.'))
        return redirect(url_for('auth.organization', org=organization.name))
    else:
        return redirect(url_for('main.home'))

@bp.route('/leave_organization/<org>')
@login_required
def leave_organization(org):
    if current_user.organizes(org):
        organizer = Organizer.query.filter(Organizer.organization_id==org).filter(Organizer.user_id==current_user.id).first()
        db.session.delete(organizer)
        db.session.commit()
        invitation = OrganizationInvitationRequest.query.filter(OrganizationInvitationRequest.user_id==current_user.id).filter(OrganizationInvitationRequest.organization_id==org).first()
        if invitation is not None:
            db.session.delete(invitation)
            db.session.commit()
        flash(_('You have left the organization'))
        return redirect(url_for('main.home'))
    else:
        return redirect(url_for('main.home'))

@bp.route('/console/<tourney>', methods=['GET','POST'])
@login_required
def console(tourney):
    t = Tournament.query.filter(Tournament.id==tourney).first()
    if t is None:
        flash(_('Tournament not found'))
        return redirect(url_for('main.home'))
    organizer = Organization.query.filter(Organization.id==t.organizer_id).first()
    organizes = False
    if t.organizer_user_id==current_user.id:
        organizes = True
    elif  current_user.organizes(t.organizer_id):
        organizes = True
    else:
        return redirect(url_for('main.home'))
        

    created_by = User.query.filter(User.id==t.organizer_user_id).first()

    memberships = Membership.query.filter(Membership.tournament_id == t.id).order_by(Membership.wins.desc(), Membership.ties.desc(), Membership.loses.desc(), Membership.name)
    
    list_en = enumerate(memberships)
    
    details = Tournament_Info.query.filter(Tournament_Info.id_tournament==t.id).first()
    form = EmptyForm()
    joined = False
    if Membership.query.filter(Membership.user_id==current_user.id).filter(Membership.tournament_id==t.id).count() > 0:
        joined = True
    
    user_a = aliased(User)
    user_b = aliased(User)

    pairings = db.session.query(Pairing.id_tournament, Pairing.ready_1, Pairing.ready_2, Pairing.id, Pairing.user_1, Pairing.user_2, Pairing.result_1, Pairing.result_2, Pairing.round, user_a.username.label('username_1'), user_b.username.label('username_2')).\
        join(Pairing.user_2_r).\
        distinct(user_a.username).\
        distinct(user_b.username).\
        filter(Pairing.user_1==user_a.id).\
        filter(Pairing.user_2==user_b.id).\
        filter(user_a.id is not user_b.id).\
        filter(Pairing.id_tournament==tourney).order_by(Pairing.round).all()
    
    pairings = [list(g) for k, g in groupby(pairings, attrgetter('round'))]
    started = False
    if t.starts_at < datetime.utcnow():
        started = True
    form_submit = SubmitResults()
    if request.method == 'POST' and form_submit.validate_on_submit():
        pairing = Pairing.query.filter(Pairing.id==form_submit.pairing_id.data).first()
            #active round -> Sin cambios en los resultados
        if pairing.round == t.active_round and t.in_progress == True:
            form_submit.result_1.default = pairing.result_2
            form_submit.result_2.default = pairing.result_2
            db.session.commit()
        #ha sido de una ronda en la que se han cambiado resultados
        elif pairing.round < t.active_round or t.in_progress == False:
            if pairing.result_1 is not None and pairing.result_2 is not None:
                #cambiamos que ha ganado 1 a que ha ganado 2
                if pairing.result_1 > pairing.result_2:
                    if form_submit.result_1.data < form_submit.result_2.data:
                        m1 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_1).first()
                        m2 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_2).first()
                        m1.wins = m1.wins - 1
                        m2.wins = m2.wins + 1
                        m1.loses = m1.loses + 1
                        m2.loses = m2.loses - 1
                        db.session.commit()
                    elif form_submit.result_1.data == form_submit.result_2.data:
                        m1 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_1).first()
                        m2 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_2).first()
                        m1.ties = m1.ties + 1
                        m2.ties = m2.ties + 1
                        m2.loses = m2.loses - 1
                        m1.wins = m1.wins - 1
                        db.session.commit()
                #cambiamos que ha ganado 2 a que ha ganado 1
                elif pairing.result_1 < pairing.result_2:
                    if form_submit.result_1.data > form_submit.result_2.data:
                        m1 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_1).first()
                        m2 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_2).first()
                        m1.wins = m1.wins + 1
                        m2.wins = m2.wins - 1
                        m1.loses = m1.loses - 1
                        m2.loses = m2.loses + 1
                        db.session.commit()
                    elif form_submit.result_1.data == form_submit.result_2.data:
                        m1 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_1).first()
                        m2 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_2).first()
                        m1.ties = m1.ties + 1
                        m2.ties = m2.ties + 1
                        m1.loses = m1.loses - 1
                        m2.wins = m2.wins - 1
                        db.session.commit()
                elif pairing.result_1 == pairing.result_2:
                    if form_submit.result_1.data > form_submit.result_2.data:
                        m1 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_1).first()
                        m2 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_2).first()
                        m1.ties = m1.ties - 1
                        m2.ties = m2.ties - 1
                        m1.wins = m1.wins + 1
                        m2.loses = m2.loses + 1
                        db.session.commit()
                    elif form_submit.result_1.data < form_submit.result_2.data:
                        m1 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_1).first()
                        m2 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_2).first()
                        m1.ties = m1.ties - 1
                        m2.ties = m2.ties - 1
                        m1.loses = m1.loses + 1
                        m2.wins = m2.wins + 1
                        db.session.commit()
            #no hay resultados
            else:
                if form_submit.result_1.data < form_submit.result_2.data:
                    m1 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_1).first()
                    m2 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_2).first()
                    m1.loses = m1.loses +1
                    m2.wins = m2.wins + 1
                    db.session.commit()

                elif form_submit.result_1.data > form_submit.result_2.data:
                    m1 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_1).first()
                    m2 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_2).first()
                    m1.wins = m1.wins + 1
                    m2.loses = m2.loses +1
                    db.session.commit()

                elif form_submit.result_1.data == form_submit.result_2.data:
                    m1 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_1).first()
                    m2 = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.user_id==pairing.user_2).first()
                    m1.ties = m1.ties + 1
                    m2.ties = m2.ties +1
                    db.session.commit()

        
        pairing.result_1 = form_submit.result_1.data
        pairing.result_2 = form_submit.result_2.data
        pairing.ready_1 = True
        pairing.ready_2 = True
        db.session.commit()
        #cambiar resultados después de que el torneo haya terminado
        if t.in_progress is False:
            membership_results = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.banned==False).order_by(Membership.wins.desc()).order_by(Membership.loses).order_by(Membership.ties).order_by(Membership.name)
            for index, m in enumerate(membership_results):
                m.result = index+1
                m.participant.add_notification('tournament_alert_count', 0, m.participant.new_alerts())
                t_alert = TournamentAlert(tournament_id = t.id, type=3, user_id = m.user_id, round = 0, message ="Los resultados de " + t.name + " han cambiado.")
                db.session.add(t_alert)
                db.session.commit()
        else:
            user_1 = User.query.filter(User.id==pairing.user_1).first()
            t_alert = TournamentAlert(tournament_id = t.id, type=3, user_id = user_1.id, round = pairing.round, message = t.name + " - Los resultados de la ronda " + str(pairing.round) + " han sido cambiados. Contacta un organizador para obtener más información")
            db.session.add(t_alert)
            user_1.add_notification('tournament_alert_count', 0, user_1.new_alerts())
            db.session.commit()
            user_2 = User.query.filter(User.id==pairing.user_2).first()
            t_alert_2 = TournamentAlert(tournament_id = t.id, type=3, user_id = user_2.id, round = pairing.round, message = t.name + " - Los resultados de la ronda " + str(pairing.round) + " han sido cambiados. Contacta un organizador para obtener más información")
            db.session.add(t_alert_2)
            user_2.add_notification('tournament_alert_count', 0, user_2.new_alerts())
            db.session.commit()

        flash(_('Result updated'))
        return redirect(url_for('auth.console', tourney=tourney))

    return render_template(
        'console.html',
        title = _('Console') + ' ' +  t.name,
        joined=joined, 
        form=form, 
        t=t, 
        details=details, 
        organizer=organizer, 
        memberships=memberships,
        list_en=list_en, 
        created_by=created_by, 
        organizes=organizes,
        pairings = pairings,
        started = started,
        form_submit=form_submit
        )

@bp.route('/switch_membership/<membership>/<tourney>')
@login_required
def switch_membership(membership, tourney):
    t = Tournament.query.filter(Tournament.id == tourney).first()
    
    organizes = False
    if t.organizer_user_id==current_user.id:
        organizes = True
    elif  current_user.organizes(t.organizer_id):
        organizes = True
    if organizes:
        m = Membership.query.filter(Membership.id==membership).filter(Membership.tournament_id==t.id).first()
        if m is None:
            return redirect(url_for('main.home'))
        else:
            if m.banned == True:
                m.banned = False
                user = User.query.filter(User.id==m.user_id).first()
                t_alert = TournamentAlert(tournament_id = t.id, type=4, user_id = user.id, round = 0, message = t.name + " - Tu participación ha sido reactivada. Contacta un organizador para obtener más información.")
                db.session.add(t_alert)
                user.add_notification('tournament_alert_count', 0, user.new_alerts())
                db.session.commit()
                flash(_('Member unbanned from the tournament'))
            else:
                m.banned = True
                user = User.query.filter(User.id==m.user_id).first()
                t_alert = TournamentAlert(tournament_id = t.id, type=4, user_id = user.id, round = 0, message = t.name + " - Tu participación ha sido revocada. Contacta un organizador para obtener más información.")
                user = User.query.filter(User.id==m.user_id).first()
                db.session.add(t_alert)
                user.add_notification('tournament_alert_count', 0, user.new_alerts())
                db.session.commit()
                flash(_('Member banned from the tournament'))
        
        if t.in_progress is False and t.active_round == t.max_rounds:
            membership_results = Membership.query.filter(Membership.tournament_id==t.id).filter(Membership.banned==False).order_by(Membership.wins.desc()).order_by(Membership.loses).order_by(Membership.ties).order_by(Membership.name)
            for index, m in enumerate(membership_results):
                m.result = index+1
                m.participant.add_notification('tournament_alert_count', 0, m.participant.new_alerts())
                t_alert = TournamentAlert(tournament_id = t.id, type=3, user_id = m.user_id, round = 0, message = "Los resultados de " + t.name + " han cambiado.")
                db.session.add(t_alert)
                db.session.commit()
    else:
        return redirect(url_for('main.home'))
    return redirect(url_for('auth.console', tourney = tourney))
