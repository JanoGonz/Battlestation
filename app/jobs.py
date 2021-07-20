# from sqlalchemy.sql.expression import func, select
from datetime import datetime, timedelta
import itertools

from app.models import User, Tournament, Membership, TournamentAlert, Pairing
from app.jobs import *
from sqlalchemy import or_
from sqlalchemy.sql.expression import func
from app import db, scheduler

def pairs(list, n):
    zipped = itertools.izip_longest(*[iter(list)] * n, fillvalue=0)
    return zipped
        #return zip(*[iter(list)]*n)

#opciones de tiempo entre rondas
def time_between_rounds(i):
    switcher = {
        0: timedelta(hours=1),
        1: timedelta(days=7),
        2: timedelta(minutes=3)
    }
    return switcher.get(i, "Invalid")

def schedule_tournament(t):
    from battlestation import app
    with app.app_context():
        #need filter ready
        tournament = Tournament.query.filter(Tournament.id==t).first()
        #list_as_pairs = pairs(members, 2)
        #START CREATE PAIRINGS
        members = User.query.join(Membership, Membership.user_id==User.id).filter(Membership.tournament_id==t).filter(Membership.banned==False).order_by(func.random()).all()
        if len(members) > tournament.min_participants and len(members) > 1:
            for x in members:
                t_alert = TournamentAlert(tournament_id = t, user_id = x.id, round = 1, message =tournament.name + " - La ronda 1 ha comenzado")
                db.session.add(t_alert)
                x.add_notification('tournament_alert_count', 0, x.new_alerts())
                db.session.commit()
            #Start swiss
            if tournament.type == 0:
                for x, y in itertools.zip_longest(members[0::2], members[1::2], fillvalue=0):
                    if y == 0:
                        pairing = Pairing(id_tournament = t, user_1 = x.id, user_2 = 0, result_1 = 1, result_2 = 0, round = 1)
                        db.session.add(pairing)
                        db.session.commit()
                    else:
                        pairing = Pairing(id_tournament = t, user_1 = x.id, user_2 = y.id, round = 1)
                        db.session.add(pairing)
                        db.session.commit()
            #END CREATE PAIRINGS
            #START LEAGUE
            elif tournament.type == 1:
                combination_members = list(itertools.combinations(members, 2))
                for x, y in combination_members:
                        pairing = Pairing(id_tournament = t, user_1 = x.id, user_2 = y.id, round = 1)
                        db.session.add(pairing)
                        db.session.commit()
            #ENG LEAGUE
            #START SINGLE ELIMINATION
            elif tournament.type == 2:
                members_se = User.query.join(Membership, Membership.user_id==User.id).filter(Membership.tournament_id==t).filter(Membership.banned==False).filter(Membership.loses < 1).order_by(func.random()).all()
                for x, y in itertools.zip_longest(members_se[0::2], members_se[1::2], fillvalue=0):
                    if y == 0:
                        pairing = Pairing(id_tournament = t, user_1 = x.id, user_2 = 0, result_1 = 1, result_2 = 0, round = 1)
                        db.session.add(pairing)
                        db.session.commit()
                    else:
                        pairing = Pairing(id_tournament = t, user_1 = x.id, user_2 = y.id, round = 1)
                        db.session.add(pairing)
                        db.session.commit()
            #END SINGLE ELIMINATION
            #START DOUBLE ELIMINATION
            elif tournament.type == 3:
                    members_de = User.query.join(Membership, Membership.user_id==User.id).filter(Membership.tournament_id==t).filter(Membership.banned==False).filter(Membership.loses < 2).order_by(func.random()).all()
                    for x, y in itertools.zip_longest(members_de[0::2], members_de[1::2], fillvalue=0):
                        if y == 0:
                            pairing = Pairing(id_tournament = t, user_1 = x.id, user_2 = 0, result_1 = 1, result_2 = 0, round = 1)
                            db.session.add(pairing)
                            db.session.commit()
                        else:
                            pairing = Pairing(id_tournament = t, user_1 = x.id, user_2 = y.id, round = 1)
                            db.session.add(pairing)
                            db.session.commit()
            #END DOUBLE ELIMINATION

            tournament.active_round = 1
            tournament.in_progress = True
            db.session.commit()
            if tournament.max_rounds > 1:
                scheduler.add_job(
                    schedule_round, 
                    run_date=datetime.utcnow() + time_between_rounds(tournament.between_rounds), 
                    args=[t, 2], 
                    id='schedule_tournament_' + str(t) + '_round_' + str(tournament.active_round+1))
                return True
            else:
                scheduler.add_job(
                    end_tournament, 
                    run_date=datetime.utcnow() + time_between_rounds(tournament.between_rounds), 
                    args=[t], 
                    id='end_tournament' + str(t))
                return True
        else:
            for m in members:
                t_alert = TournamentAlert(tournament_id = t, type=2, user_id = m.id, round = 0, message =tournament.name + " - No hay participantes suficientes como para que el torneo tenga lugar.")
                m.add_notification('tournament_alert_count', 0, m.new_alerts())
                db.session.add(t_alert)
                db.session.commit()


def schedule_round(t, n_round):
    from battlestation import app
    with app.app_context():
        #need filter ready
        #resultados
        pairings_last_round = Pairing.query.filter(Pairing.id_tournament==t).filter(Pairing.round==n_round-1).filter(Pairing.user_1 != 0).filter(Pairing.user_2 != 0)
        for p in pairings_last_round:
            m = Membership.query.filter(Membership.tournament_id==t).filter(Membership.user_id==p.user_1).first()
            m2 = Membership.query.filter(Membership.tournament_id==t).filter(Membership.user_id==p.user_2).first()
            if p.result_1 is None or p.result_2 is None:
                p.result_1 = 0
                p.resutl_2 = 0
                m.ties = m.ties+1
                m2.ties = m2.ties+1
                db.session.commit()
            else:
                if p.result_1 > p.result_2:
                    m.wins = m.wins+1
                    m2.loses = m2.loses+1
                    db.session.commit()
                elif p.result_1 == p.result_2:
                    m.ties = m.ties+1
                    m2.ties = m2.ties+1
                    db.session.commit()
                else:
                    m2.wins = m2.wins+1
                    m.loses = m.loses+1
                    db.session.commit()

        byes = Pairing.query.filter(Pairing.id_tournament==t).filter(Pairing.round==n_round-1).filter(or_(Pairing.user_1==0, Pairing.user_2==0)).all()
        for b in byes:
            if b.user_1 != 0:
                m = Membership.query.filter(Membership.tournament_id==t).filter(Membership.user_id==b.user_1).first()
                m.wins = m.wins+1
                db.session.commit()
            else:
                m = Membership.query.filter(Membership.tournament_id==t).filter(Membership.user_id==b.user_2).first()
                m.wins = m.wins+1
                db.session.commit()

        tournament = Tournament.query.filter(Tournament.id==t).first()
        tournament.active_round = n_round
        db.session.commit()
        #START CREATE PAIRINGS
        members = User.query.join(Membership, Membership.user_id==User.id).filter(Membership.tournament_id==t).filter(Membership.banned==False).order_by(Membership.wins.desc(), func.random()).all()
        #list_as_pairs = pairs(members, 2)
        if tournament.type== 0:
            for x, y in itertools.zip_longest(members[0::2], members[1::2], fillvalue=0):
                if y == 0:
                    pairing = Pairing(id_tournament = t, user_1 = x.id, user_2 = 0, result_1 = 1, result_2 = 0, round = n_round)
                    db.session.add(pairing)
                    db.session.commit()
                else:
                    pairing = Pairing(id_tournament = t, user_1 = x.id, user_2 = y.id, round = n_round)
                    db.session.add(pairing)
                    db.session.commit()
        #START LEAGUE
        elif tournament.type==1:
                combination_members = list(itertools.combinations(members, 2))
                for x, y in combination_members:
                        pairing = Pairing(id_tournament = t, user_1 = x.id, user_2 = y.id, round = n_round)
                        db.session.add(pairing)
                        db.session.commit()
        #END LEAGUE
        #START SINGLE ELIMINATION
        elif tournament.type == 2:
            members_se = User.query.join(Membership, Membership.user_id==User.id).filter(Membership.tournament_id==t).filter(Membership.banned==False).filter(Membership.loses < 1).order_by(func.random()).all()
            if len(members_se) > 1:
                for x, y in itertools.zip_longest(members_se[0::2], members_se[1::2], fillvalue=0):
                    if y == 0:
                        pairing = Pairing(id_tournament = t, user_1 = x.id, user_2 = 0, result_1 = 1, result_2 = 0, round = n_round)
                        db.session.add(pairing)
                        db.session.commit()
                    else:
                        pairing = Pairing(id_tournament = t, user_1 = x.id, user_2 = y.id, round = n_round)
                        db.session.add(pairing)
                        db.session.commit()
            else:
                membership_results = Membership.query.filter(Membership.tournament_id==t).filter(Membership.banned==False).order_by(Membership.wins.desc()).order_by(Membership.loses).order_by(Membership.ties).order_by(Membership.name)
                for index, m in enumerate(membership_results):
                    m.result = index+1
                    t_alert = TournamentAlert(tournament_id = t, type=3, user_id = m.user_id, round = 0, message ="El torneo " + tournament.name + " - ha terminado")
                    db.session.add(t_alert)
                    m.participant.add_notification('tournament_alert_count', 0, m.participant.new_alerts())
                    db.session.commit()
                    tournament.in_progress = False
                    db.session.commit()
                return False
        #END SINGLE ELIMINATION

        #START DOUBLE ELIMINATION
        #No manda alerta si no hay pairing
        elif tournament.type == 3:
                members_de = User.query.join(Membership, Membership.user_id==User.id).filter(Membership.tournament_id==t).filter(Membership.banned==False).filter(Membership.loses < 2).order_by(func.random()).all()
                if len(members_de) > 1:
                    for x, y in itertools.zip_longest(members_de[0::2], members_de[1::2], fillvalue=0):
                        if y == 0:
                            pairing = Pairing(id_tournament = t, user_1 = x.id, user_2 = 0, result_1 = 1, result_2 = 0, round = n_round)
                            db.session.add(pairing)
                            db.session.commit()
                        else:
                            pairing = Pairing(id_tournament = t, user_1 = x.id, user_2 = y.id, round = n_round)
                            db.session.add(pairing)
                            db.session.commit()
                else:
                    membership_results = Membership.query.filter(Membership.tournament_id==t).filter(Membership.banned==False).order_by(Membership.wins.desc()).order_by(Membership.loses).order_by(Membership.ties).order_by(Membership.name)
                    for index, m in enumerate(membership_results):
                        m.result = index+1
                        t_alert = TournamentAlert(tournament_id = t, type=3, user_id = m.user_id, round = 0, message ="El torneo " + tournament.name + " - ha terminado")
                        db.session.add(t_alert)
                        m.participant.add_notification('tournament_alert_count', 0, m.participant.new_alerts())
                        db.session.commit()
                        tournament.in_progress = False
                        db.session.commit()
                    return False
        #END DOUBLE ELIMINATION
        for x in members:
            t_alert = TournamentAlert(tournament_id = t, user_id = x.id, round = 1, message =tournament.name + " - La ronda " + str(n_round) + " ha comenzado")
            db.session.add(t_alert)
            x.add_notification('tournament_alert_count', 0, x.new_alerts())
            db.session.commit()

        if tournament.max_rounds > n_round:
            scheduler.add_job(
                schedule_round, 
                run_date=datetime.utcnow() + time_between_rounds(tournament.between_rounds), 
                args=[t, n_round+1], 
                id='schedule_tournament_' + str(t) + '_round_' + str(n_round+1))
        else:
            scheduler.add_job(
                end_tournament, 
                run_date=datetime.utcnow() + time_between_rounds(tournament.between_rounds), 
                args=[t], 
                id='end_tournament' + str(t))

def end_tournament(t):
    from battlestation import app
    with app.app_context():
        tournament = Tournament.query.filter(Tournament.id==t).first()
        pairings_last_round = Pairing.query.filter(Pairing.id_tournament==t).filter(Pairing.round==tournament.max_rounds).filter(Pairing.user_1!=0).filter(Pairing.user_2!=0).all()
        for p in pairings_last_round:
            m = Membership.query.filter(Membership.tournament_id==t).filter(Membership.user_id==p.user_1).first()
            m2 = Membership.query.filter(Membership.tournament_id==t).filter(Membership.user_id==p.user_2).first()
            if p.result_1 is not None and p.result_2 is not None:
                if p.result_1 > p.result_2:
                    m.wins = m.wins+1
                    m2.loses = m2.loses+1
                    db.session.commit()
                elif p.result_1 == p.result_2:
                    m.ties = m.ties+1
                    m2.ties = m2.ties+1
                    db.session.commit()
                else:
                    m2.wins = m2.wins+1
                    m.loses = m.loses+1
                    db.session.commit()
            else:
                m.ties= m.ties+1
                m2.ties = m2.ties+1
                db.session.commit()
        
        byes = Pairing.query.filter(Pairing.id_tournament==t).filter(Pairing.round==tournament.max_rounds).filter(or_(Pairing.user_1==0, Pairing.user_2==0)).all()
        for b in byes:
            if b.user_1 != 0:
                m = Membership.query.filter(Membership.tournament_id==t).filter(Membership.user_id==b.user_1).first()
                m.wins = m.wins+1
                db.session.commit()
            else:
                m = Membership.query.filter(Membership.tournament_id==t).filter(Membership.user_id==b.user_2).first()
                m.wins = m.wins+1
                db.session.commit()

        membership_results = Membership.query.filter(Membership.tournament_id==t).filter(Membership.banned==False).order_by(Membership.wins.desc()).order_by(Membership.loses).order_by(Membership.ties).order_by(Membership.name)
        for index, m in enumerate(membership_results):
            m.result = index+1
            t_alert = TournamentAlert(tournament_id = t, type=3, user_id = m.user_id, round = 0, message ="El torneo " + tournament.name + " - ha terminado")
            db.session.add(t_alert)
            m.participant.add_notification('tournament_alert_count', 0, m.participant.new_alerts())
            db.session.commit()
        
        tournament.in_progress = False
        db.session.commit()
