from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, \
    jsonify, current_app
from flask_login import current_user, login_required
from flask_babel import _, get_locale
from sqlalchemy.sql.expression import null
from app import db
from app.main.forms import EmptyForm, MessageForm, SearchForm, SubmitResults
from app.models import Membership, Message, Notification, OrganizationMessage, OrganizationMessageReply, Tournament, User, Organization, Organizer, Tournament_Info, Pairing, TournamentAlert
from app.main import bp
from app.jobs import *
from sqlalchemy import func
from sqlalchemy.orm import aliased, joinedload
from itertools import groupby
from operator import attrgetter
from sqlalchemy import or_, distinct
from collections import defaultdict

@bp.route('/')

@bp.route('/index')
@login_required
def index():
    return render_template('index.html', title=_('Home'))

#actualizar ultimo login cada vez que realiza una acción
@bp.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_login = datetime.utcnow()
        db.session.commit()

    g.locale = str(get_locale())
    #configurar los parametros de moment cada vez que se realiza una acción


@bp.route('/join/<tournament>', methods=['GET', 'POST'])
@login_required
def join(tournament):
    tournament = Tournament.query.filter_by(id=tournament).first()
    if tournament is None:
        flash(_('Tournament {} not found'.format(tournament)))
        return redirect(url_for('main.home'))
    if tournament.starts_at > datetime.utcnow():   
        membership = Membership(user_id = current_user.id, tournament_id=tournament.id, name = current_user.username)
        db.session.add(membership)
        db.session.commit()
        flash(_('Joined succesfuly'))
        return redirect(url_for('auth.user', username=current_user.username))
    else:
        flash(_('Tournament has already started'))
        return redirect(url_for('main.home'))

@bp.route('/leave/<tournament>', methods=['GET', 'POST'])
@login_required
def leave(tournament):
    tournament = Tournament.query.filter_by(id=tournament).first()
    if tournament is None:
        flash(_('Tournament {} not found'.format(tournament)))
        return redirect(url_for('main.home'))
    membership = Membership.query.filter(Membership.user_id==current_user.id).filter(Membership.tournament_id==tournament.id).first()
    db.session.delete(membership)
    db.session.commit()
    flash(_('Left succesfuly'))
    return redirect(url_for('auth.user', username=current_user.username))

@bp.route('/tournament_list')
def tournament_list():
    page = request.args.get('page', 1, type=int)
    past_page = request.args.get('past_page', 1, type=int)
    tournaments = Tournament.query.filter(Tournament.visible==True).filter(Tournament.starts_at > datetime.utcnow()).order_by(Tournament.starts_at.asc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False
    )

    past_tournaments = Tournament.query.filter(Tournament.visible==True).filter(Tournament.starts_at < datetime.utcnow()).order_by(Tournament.starts_at.desc()).paginate(
        past_page, current_app.config['POSTS_PER_PAGE'], False
    )
    next_url = url_for('main.tournament_list', page=tournaments.next_num, past_page=past_page) \
        if tournaments.has_next else None
    prev_url = url_for('main.tournament_list', page=tournaments.prev_num, past_page=past_page) \
        if tournaments.has_prev else None
    past_next_url = url_for('main.tournament_list', page=page, past_page=past_tournaments.next_num) \
        if past_tournaments.has_next else None
    past_prev_url = url_for('main.tournament_list', page=page, past_page=past_tournaments.prev_num) \
        if past_tournaments.has_prev else None
    form = EmptyForm()
    return render_template('tournament_list.html', title=_('Tournament list'), 
    form=form, tournaments=tournaments.items, past_tournaments=past_tournaments.items,
    next_url=next_url, prev_url=prev_url, past_next_url=past_next_url, past_prev_url=past_prev_url)

@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.lass_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()
    #g mantiene información después de una request(variable temporal)
    g.locale =str(get_locale())

@bp.route('/search')
@login_required
def search():
    form = EmptyForm()
    if not g.search_form.validate():
        return redirect(url_for('main.home'))
    page = request.args.get('page', 1, type=int)
    tournaments, total = Tournament.search(g.search_form.q.data, page, current_app.config['POSTS_PER_PAGE'])
    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * current_app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('search.html', title=_('Search'), tournaments=tournaments,
                           next_url=next_url, prev_url=prev_url, form=form)

# @bp.route('/user/<username>/popup')
# @login_required
# def user_popup(username):
#     user = User.query.filter_by(username=username).first_or_404()
#     form = EmptyForm()
#     return render_template('user_popup.html', user=user, form=form)


@bp.route('/tournament_details/<tourney>', methods=['GET','POST'])
@login_required
def tournament_details(tourney):
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
        
    created_by = User.query.filter(User.id==t.organizer_user_id).first()
    
    
    memberships = Membership.query.filter(Membership.tournament_id == t.id).filter(Membership.banned==False).order_by(Membership.wins.desc(), Membership.ties.desc(), Membership.loses.desc(), Membership.name)
    
    list_en = enumerate(memberships)
    
    details = Tournament_Info.query.filter(Tournament_Info.id_tournament==t.id).first()
    form = EmptyForm()
    joined = False
    banned = False
    if Membership.query.filter(Membership.user_id==current_user.id).filter(Membership.tournament_id==t.id).count() > 0:
        joined = True
        if Membership.query.filter(Membership.user_id==current_user.id).filter(Membership.tournament_id==t.id).filter(Membership.banned==True).count() > 0:
            banned = True
    
    user_a = aliased(User)
    user_b = aliased(User)

    pairings = db.session.query(Pairing.id_tournament, Pairing.ready_1, Pairing.ready_2, Pairing.user_1, Pairing.user_2, Pairing.result_1, Pairing.result_2, Pairing.round, user_a.username.label('username_1'), \
        user_b.username.label('username_2')).\
        join(Pairing.user_2_r).\
        distinct(user_a.username).\
        distinct(user_b.username).\
        filter(Pairing.user_1==user_a.id).\
        filter(Pairing.user_2==user_b.id).\
        filter(user_a.id is not user_b.id).\
        filter(Pairing.id_tournament==tourney).order_by(Pairing.round).all()
    # pairings = current_user.pairings()
    #pairings = db.session.query(Pairing.id_tournament, Pairing.result_1, Pairing.result_2, Pairing.round, user_a.username.label('user_1'), user_b.username.label('user_2')).join(Pairing.user_1_r).distinct(user_a.username).filter(Pairing.user_1==user_a.id).filter(Pairing.user_2==user_b.id).filter(user_a.id is not user_b.id).filter(Pairing.id_tournament==tourney).all()
    # for x in pairings:
    #     pairings_curated[x.round].append(x)
    pairings = [list(g) for k, g in groupby(pairings, attrgetter('round'))]
    started = False
    if t.starts_at < datetime.utcnow():
        started = True
    return render_template(
        'tournament_details.html',
        title = t.name,
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
        banned=banned
        )

@bp.route('/home')
@login_required
def home():
    return render_template('home.html', title=_('Home'))

@bp.route('/organizations')
@login_required
def organizations():
    page = request.args.get('page', 1, type=int)
    organizations = Organization.query.order_by(Organization.name.asc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False
    )
    my_org = Organization.query.join(Organizer).filter(current_user.id==Organizer.user_id).filter(Organizer.organization_id==Organization.id).all()
    next_url = url_for('main.organizations', page=organizations.next_num) \
        if organizations.has_next else None
    prev_url = url_for('main.organizations', page=organizations.prev_num) \
        if organizations.has_prev else None
    return render_template('organizations.html', title=_('Organizations'), my_org=my_org, organizations=organizations.items,
    next_url=next_url, prev_url=prev_url)

@bp.route('/my_tournaments')
@login_required
def my_tournaments():
    page = request.args.get('page', 1, type=int)
    page_j = request.args.get('page_j', 1, type=int)
    tournaments = Tournament.query.join(Membership, Membership.tournament_id==Tournament.id).filter(Membership.user_id==current_user.id).add_columns(
        Tournament.id, Tournament.name, Tournament.starts_at, Tournament.game, Tournament.in_progress, Membership.result).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False
    )
    past_t = tournaments.query.filter(Tournament.starts_at<datetime.now()).order_by(Tournament.starts_at.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False
    )
    joined_t = tournaments.query.filter(Tournament.starts_at>datetime.now()).order_by(Tournament.starts_at.asc()).paginate(
        page_j, current_app.config['POSTS_PER_PAGE'], False
    )

    next_url_old = url_for('main.my_tournaments', page=past_t.next_num, page_j=page_j) \
        if past_t.has_next else None
    prev_url_old = url_for('main.my_tournaments', page=past_t.prev_num, page_j=page_j) \
        if past_t.has_prev else None
    next_url_joined = url_for('main.my_tournaments', page=page, page_j=joined_t.next_num) \
        if joined_t.has_next else None
    prev_url_joined = url_for('main.my_tournaments', page=page, page_j=joined_t.prev_num) \
        if joined_t.has_prev else None
    return render_template('my_tournaments.html', title = _('My tournaments'), joined_t=joined_t.items, past_t=past_t.items, next_url_old=next_url_old, prev_url_old=prev_url_old, next_url_joined=next_url_joined, prev_url_joined=prev_url_joined)

@bp.route('/activity', methods=['GET', 'POST'])
@login_required
def activity():
    current_user.last_notification_read_time = datetime.utcnow()
    current_user.add_notification('tournament_alert_count', 0, 0)
    db.session.commit()
    user_a = aliased(User)
    user_b = aliased(User)
    active_t = db.session.query(Pairing.ready_1, Pairing.ready_2, Pairing.id.label('pairing_id'), Pairing.user_1, Pairing.user_2,Tournament.name, Pairing.round, Tournament.id, Tournament.starts_at, Pairing.round, user_a.username.label('user_1_name'), user_b.username.label('user_2_name')).\
        join(Membership, Membership.tournament_id==Tournament.id).join(Pairing, Pairing.round==Tournament.active_round).\
        join(Pairing.user_2_r).\
        filter(or_(Pairing.user_1==current_user.id, Pairing.user_2==current_user.id)).\
        filter(Pairing.id_tournament==Tournament.id).\
        filter(Tournament.in_progress==True).\
        distinct(user_a.username).\
        filter(Pairing.user_1==user_a.id).\
        filter(Pairing.user_2==user_b.id).\
        filter(user_a.id != user_b.id).\
        order_by(Tournament.starts_at.desc()).all()
    
    
    form = SubmitResults()

    if form.validate_on_submit():
        pairing = Pairing.query.filter(Pairing.id==form.pairing_id.data).first()
        t = Tournament.query.filter(Tournament.id==pairing.id_tournament).first()
        if t.active_round == pairing.round:
            if pairing.user_1 == current_user.id and not pairing.ready_2:
                pairing.ready_1 = True
                pairing.result_1 = form.result_1.data
                pairing.result_2 = form.result_2.data
                db.session.commit()
                return redirect(url_for('main.activity'))
            elif pairing.user_2 == current_user.id and not pairing.ready_1:
                pairing.result_1 = form.result_1.data
                pairing.result_2 = form.result_2.data
                pairing.ready_2 = True
                db.session.commit()
                return redirect(url_for('main.activity'))
            elif pairing.user_2 == current_user.id and pairing.ready_1:
                if form.result_2.data == pairing.result_2 and form.result_1.data == pairing.result_1:
                    pairing.ready_2 = True
                    db.session.commit()
                    flash(_('Result confirmed'))
                    return redirect(url_for('main.activity'))
                else:
                    pairing.ready_1 = False
                    user_1 = User.query.filter(User.id==pairing.user_1).first()
                    user_2 = User.query.filter(User.id==pairing.user_2).first()
                    t_alert = TournamentAlert(tournament_id = pairing.id_tournament, type=2, user_id = current_user.id, round = pairing.round, message = pairing.tournament_data.name + " - El resultado que ha enviado tu oponente no coincide con el tuyo. Actualiza tu resultado o contacta un organizador.")
                    t_alert_2 = TournamentAlert(tournament_id = pairing.id_tournament, type=2, user_id = pairing.user_1, round = pairing.round, message = pairing.tournament_data.name + " - El resultado que ha enviado tu oponente no coincide con el tuyo. Actualiza tu resultado o contacta un organizador.")
                    db.session.add(t_alert)
                    db.session.add(t_alert_2)
                    user_1.add_notification('tournament_alert_count', 0, user_1.new_alerts())
                    user_2.add_notification('tournament_alert_count', 0, user_2.new_alerts())
                    db.session.commit()
                    flash(_("Error submitting result. Your result and your opponent's don't match"))
                    return redirect(url_for('main.activity'))
            elif pairing.user_1 == current_user.id and pairing.ready_2:
                if form.result_2.data == pairing.result_2 and form.result_1.data == pairing.result_1:
                    pairing.ready_1 = True
                    db.session.commit()
                    flash(_('Result confirmed'))
                    return redirect(url_for('main.activity'))
                else:
                    pairing.ready_2 = False
                    user_1 = User.query.filter(User.id==pairing.user_1).first()
                    user_2 = User.query.filter(User.id==pairing.user_2).first()
                    t_alert = TournamentAlert(tournament_id = pairing.id_tournament, type=2, user_id = current_user.id, round = pairing.round, message = pairing.tournament_data.name + " - El resultado que ha enviado tu oponente no coincide con el tuyo. Actualiza tu resultado o contacta un organizador.")
                    t_alert_2 = TournamentAlert(tournament_id = pairing.id_tournament, type=2, user_id = pairing.user_2, round = pairing.round, message = pairing.tournament_data.name + " - El resultado que ha enviado tu oponente no coincide con el tuyo. Actualiza tu resultado o contacta un organizador.")
                    db.session.add(t_alert)
                    db.session.add(t_alert_2)
                    user_1.add_notification('tournament_alert_count', 0, user_1.new_alerts())
                    user_2.add_notification('tournament_alert_count', 0, user_2.new_alerts())
                    db.session.commit()
                    flash(_("Error submitting result. Your result and your opponent's don't match"))
                    return redirect(url_for('main.activity'))
            else:
                return redirect(url_for('main.activity'))
                #flash('Result for {} submitted'.format(active_t.name))
        else:
            flash(_('The round has ended before you submitted the result'))
            return redirect(url_for('main.home'))
    

    return render_template('activity.html', title = _('Activity'), form=form, active_t=active_t, scheduler=scheduler)

@bp.route('/send_message_org/<org>', methods=['GET', 'POST'])
@login_required
def send_message_org(org):
    organization = Organization.query.filter(Organization.id==org).first()
    form = MessageForm()
    if form.validate_on_submit():
        msg = OrganizationMessage(sender_id= current_user.id, org_id=organization.id, message=form.message.data)
        db.session.add(msg)
        db.session.commit()
        flash(_('Message sent'))
        return redirect(url_for('auth.organization', org=organization.name))
    return render_template('send_message_org.html', title=_('Send message to ') + str(organization.name), org = organization.name, form=form)

@bp.route('/reply_message_org/<message>', methods=['GET', 'POST'])
@login_required
def reply_message_org(message):
    original_msg = OrganizationMessage.query.filter(OrganizationMessage.id==message).first()
    if current_user.organizes(original_msg.receiver.id) or original_msg.sender_id==current_user.id:
        form = MessageForm()
        replies = OrganizationMessageReply.query.filter(OrganizationMessageReply.message_id==message).order_by(OrganizationMessageReply.timestamp).all()
        if form.validate_on_submit():
            if original_msg.sender_id==current_user.id:
                msg_r = OrganizationMessageReply(message_id=message, sender_id=original_msg.sender_id, sent_by_org=False, message = form.message.data, organization_id=original_msg.org_id)
                db.session.add(msg_r)
                db.session.commit()
            else:
                msg_r = OrganizationMessageReply(message_id=message, sender_id=original_msg.sender_id, sent_by_org=True, message = form.message.data, organization_id=original_msg.org_id)
                db.session.add(msg_r)
                db.session.commit()
                original_msg.author_org_message.add_notification('unread_message_count', 0, original_msg.author_org_message.new_messages())
                db.session.commit()
            flash(_('Reply sent succesfully'))
            return redirect(url_for('auth.organization', org=original_msg.receiver.name))
        return render_template('reply_message_org.html', title=_('Reply'), replies=replies, original_msg=original_msg, form=form)
    else:
        return redirect(url_for('main.home'))


@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data)
        db.session.add(msg)
        user.add_notification('unread_message_count', 0, user.new_messages())
        db.session.commit()
        flash(_('Your message has been sent.'))
        return redirect(url_for('auth.user', username=recipient))
    return render_template('send_message.html', title=_('Send Message'),
                           form=form, recipient=recipient)

@bp.route('/messages')
@login_required
def messages():
    org_alerts = current_user.new_org_alerts()
    current_user.last_message_read_time = datetime.utcnow()
    current_user.add_notification('unread_message_count', 0, 0)
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    page_s = request.args.get('page_s', 1 , type=int)
    messages = current_user.messages_received.order_by(
        Message.timestamp.desc()).paginate(
            page, current_app.config['POSTS_PER_PAGE'], False)

    next_url = url_for('main.messages', page=messages.next_num, page_s=page_s, _anchor="pills-received") \
        if messages.has_next else None
    prev_url = url_for('main.messages', page=messages.prev_num, page_s=page_s, _anchor="pills-received") \
        if messages.has_prev else None
    messages_sent = current_user.messages_sent.order_by(
        Message.timestamp.desc()).paginate(
            page_s, current_app.config['POSTS_PER_PAGE'], False)

    sent_next_url = url_for('main.messages', page=page, page_s=messages_sent.next_num, _anchor="pills-sent") \
        if messages_sent.has_next else None
    sent_prev_url = url_for('main.messages', page=page, page_s=messages_sent.prev_num, _anchor="pills-sent") \
        if messages_sent.has_prev else None

    org_messages = OrganizationMessage.query.filter(OrganizationMessage.sender_id==current_user.id).order_by(OrganizationMessage.timestamp.desc()).all()
    replies = []
    for m in org_messages:
        reply = OrganizationMessageReply.query.filter(OrganizationMessageReply.message_id==m.id).order_by(OrganizationMessageReply.timestamp).all()
        replies.append(reply)
    org_message_list = itertools.zip_longest(org_messages, replies, fillvalue=None)

    return render_template('messages.html', title=_('Inbox'), 
                        org_alerts = org_alerts,
                        messages=messages.items,
                        messages_sent=messages_sent.items,
                        next_url=next_url, prev_url=prev_url,
                        sent_next_url=sent_next_url, sent_prev_url=sent_prev_url,
                        org_message_list=org_message_list)
                        

@bp.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    notifications = current_user.notifications.filter(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications])


@bp.route('/tournament_alerts_popup')
@login_required
def tournament_alerts_popup():
    current_user.last_notification_read_time = datetime.utcnow()
    current_user.add_notification('tournament_alert_count', 0, 0)
    db.session.commit()
    t_alerts = current_user.tournament_alerts.order_by(TournamentAlert.timestamp.desc()).limit(10).all()
    return render_template('tournament_alerts_popup.html', t_alerts=t_alerts)

@bp.route('/delete_message/<id>')
@login_required
def delete_message(id):
    msg = Message.query.filter(Message.id==id).filter(or_(Message.recipient_id==current_user.id, Message.sender_id==current_user.id)).first()
    if msg is not None:
        db.session.delete(msg)
        db.session.commit()
        flash(_('Deleted message'))
        return redirect(url_for('main.messages'))
    else:
        flash(_('error'))
        return redirect(url_for('main.home'))
    
@bp.route('/notifications_list')
@login_required
def notification_list():
    current_user.last_notification_read_time = datetime.utcnow()
    current_user.add_notification('tournament_alert_count', 0, 0)
    t_alerts = current_user.tournament_alerts.order_by(TournamentAlert.timestamp.desc()).limit(30).all()
    return render_template('notifications.html', title = _('Notifications'), t_alerts=t_alerts)

@bp.route('/licenses')
def licenses():
    return render_template('licenses.html', title=_('Licenses'))
