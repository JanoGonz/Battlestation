"""first

Revision ID: a0b1fac8eadc
Revises: 
Create Date: 2021-06-16 18:23:12.542402

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a0b1fac8eadc'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('organization',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=True),
    sa.Column('location', sa.Text(), nullable=True),
    sa.Column('website', sa.Text(), nullable=True),
    sa.Column('contact', sa.Text(), nullable=True),
    sa.Column('profile_pic', sa.String(length=20), nullable=True),
    sa.Column('last_message_read_time', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=True),
    sa.Column('email', sa.String(length=120), nullable=True),
    sa.Column('password_hash', sa.String(length=128), nullable=True),
    sa.Column('register_date', sa.Date(), nullable=True),
    sa.Column('last_login', sa.DateTime(), nullable=True),
    sa.Column('about_me', sa.String(length=120), nullable=True),
    sa.Column('last_message_read_time', sa.DateTime(), nullable=True),
    sa.Column('last_notification_read_time', sa.DateTime(), nullable=True),
    sa.Column('profile_pic', sa.String(length=20), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    op.create_index(op.f('ix_user_username'), 'user', ['username'], unique=True)
    op.create_table('message',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sender_id', sa.Integer(), nullable=True),
    sa.Column('recipient_id', sa.Integer(), nullable=True),
    sa.Column('body', sa.String(length=10000), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['recipient_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['sender_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_message_timestamp'), 'message', ['timestamp'], unique=False)
    op.create_table('notification',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('timestamp', sa.Float(), nullable=True),
    sa.Column('type', sa.Integer(), nullable=True),
    sa.Column('payload_json', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_name'), 'notification', ['name'], unique=False)
    op.create_index(op.f('ix_notification_timestamp'), 'notification', ['timestamp'], unique=False)
    op.create_table('organization_invitation_request',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('organization_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.Integer(), nullable=True),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organization_invitation_request_timestamp'), 'organization_invitation_request', ['timestamp'], unique=False)
    op.create_table('organization_message',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sender_id', sa.Integer(), nullable=True),
    sa.Column('org_id', sa.Integer(), nullable=True),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['org_id'], ['organization.id'], ),
    sa.ForeignKeyConstraint(['sender_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organization_message_timestamp'), 'organization_message', ['timestamp'], unique=False)
    op.create_table('organization_post',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('post_author_id', sa.Integer(), nullable=True),
    sa.Column('organization_id', sa.Integer(), nullable=True),
    sa.Column('body', sa.Text(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
    sa.ForeignKeyConstraint(['post_author_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organization_post_timestamp'), 'organization_post', ['timestamp'], unique=False)
    op.create_table('organizer',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('organization_id', sa.Integer(), nullable=True),
    sa.Column('edit', sa.Boolean(), nullable=True),
    sa.Column('create', sa.Boolean(), nullable=True),
    sa.Column('delete', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('tournament',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.Column('organizer_id', sa.Integer(), nullable=True),
    sa.Column('game', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('starts_at', sa.DateTime(), nullable=True),
    sa.Column('type_pairing', sa.Integer(), nullable=True),
    sa.Column('type_registration', sa.Integer(), nullable=True),
    sa.Column('min_participants', sa.Integer(), nullable=True),
    sa.Column('max_participants', sa.Integer(), nullable=True),
    sa.Column('organizer_user_id', sa.Integer(), nullable=True),
    sa.Column('in_progress', sa.Boolean(), nullable=True),
    sa.Column('visible', sa.Boolean(), nullable=True),
    sa.Column('between_rounds', sa.Integer(), nullable=True),
    sa.Column('active_round', sa.Integer(), nullable=True),
    sa.Column('max_rounds', sa.Integer(), nullable=True),
    sa.Column('type', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['organizer_id'], ['organization.id'], ),
    sa.ForeignKeyConstraint(['organizer_user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tournament_created_at'), 'tournament', ['created_at'], unique=False)
    op.create_index(op.f('ix_tournament_game'), 'tournament', ['game'], unique=False)
    op.create_index(op.f('ix_tournament_name'), 'tournament', ['name'], unique=False)
    op.create_index(op.f('ix_tournament_starts_at'), 'tournament', ['starts_at'], unique=False)
    op.create_table('membership',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('tournament_id', sa.Integer(), nullable=True),
    sa.Column('wins', sa.Integer(), nullable=True),
    sa.Column('loses', sa.Integer(), nullable=True),
    sa.Column('ties', sa.Integer(), nullable=True),
    sa.Column('result', sa.Text(), nullable=True),
    sa.Column('ready', sa.Boolean(), nullable=True),
    sa.Column('banned', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['tournament_id'], ['tournament.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('organization_message_reply',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message_id', sa.Integer(), nullable=True),
    sa.Column('sender_id', sa.Integer(), nullable=True),
    sa.Column('organization_id', sa.Integer(), nullable=True),
    sa.Column('sent_by_org', sa.Boolean(), nullable=True),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['message_id'], ['organization_message.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
    sa.ForeignKeyConstraint(['sender_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organization_message_reply_timestamp'), 'organization_message_reply', ['timestamp'], unique=False)
    op.create_table('pairing',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('id_tournament', sa.Integer(), nullable=True),
    sa.Column('user_1', sa.Integer(), nullable=True),
    sa.Column('user_2', sa.Integer(), nullable=True),
    sa.Column('result_1', sa.Integer(), nullable=True),
    sa.Column('result_2', sa.Integer(), nullable=True),
    sa.Column('ready_1', sa.Boolean(), nullable=True),
    sa.Column('ready_2', sa.Boolean(), nullable=True),
    sa.Column('round', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['id_tournament'], ['tournament.id'], ),
    sa.ForeignKeyConstraint(['user_1'], ['user.id'], ),
    sa.ForeignKeyConstraint(['user_2'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('tournament__info',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('id_tournament', sa.Integer(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('location', sa.Text(), nullable=True),
    sa.Column('rules', sa.Text(), nullable=True),
    sa.Column('schedule', sa.Text(), nullable=True),
    sa.Column('prizes', sa.Text(), nullable=True),
    sa.Column('contact', sa.Text(), nullable=True),
    sa.Column('img_url', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['id_tournament'], ['tournament.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('tournament_alert',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tournament_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('round', sa.Integer(), nullable=True),
    sa.Column('type', sa.Integer(), nullable=True),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['tournament_id'], ['tournament.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tournament_alert_timestamp'), 'tournament_alert', ['timestamp'], unique=False)
    op.drop_index('ix_apscheduler_jobs_next_run_time', table_name='apscheduler_jobs')
    op.drop_table('apscheduler_jobs')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('apscheduler_jobs',
    sa.Column('id', sa.VARCHAR(length=191), nullable=False),
    sa.Column('next_run_time', sa.FLOAT(), nullable=True),
    sa.Column('job_state', sa.BLOB(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_apscheduler_jobs_next_run_time', 'apscheduler_jobs', ['next_run_time'], unique=False)
    op.drop_index(op.f('ix_tournament_alert_timestamp'), table_name='tournament_alert')
    op.drop_table('tournament_alert')
    op.drop_table('tournament__info')
    op.drop_table('pairing')
    op.drop_index(op.f('ix_organization_message_reply_timestamp'), table_name='organization_message_reply')
    op.drop_table('organization_message_reply')
    op.drop_table('membership')
    op.drop_index(op.f('ix_tournament_starts_at'), table_name='tournament')
    op.drop_index(op.f('ix_tournament_name'), table_name='tournament')
    op.drop_index(op.f('ix_tournament_game'), table_name='tournament')
    op.drop_index(op.f('ix_tournament_created_at'), table_name='tournament')
    op.drop_table('tournament')
    op.drop_table('organizer')
    op.drop_index(op.f('ix_organization_post_timestamp'), table_name='organization_post')
    op.drop_table('organization_post')
    op.drop_index(op.f('ix_organization_message_timestamp'), table_name='organization_message')
    op.drop_table('organization_message')
    op.drop_index(op.f('ix_organization_invitation_request_timestamp'), table_name='organization_invitation_request')
    op.drop_table('organization_invitation_request')
    op.drop_index(op.f('ix_notification_timestamp'), table_name='notification')
    op.drop_index(op.f('ix_notification_name'), table_name='notification')
    op.drop_table('notification')
    op.drop_index(op.f('ix_message_timestamp'), table_name='message')
    op.drop_table('message')
    op.drop_index(op.f('ix_user_username'), table_name='user')
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.drop_table('user')
    op.drop_table('organization')
    # ### end Alembic commands ###
