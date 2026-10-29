"""Create workout session tables

Revision ID: c5a2e7f0d913
Revises: 8d4f1a6b2e90
Create Date: 2026-10-29 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5a2e7f0d913'
down_revision = '8d4f1a6b2e90'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('workout_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('template_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('duration_minutes', sa.Integer(), nullable=True),
    sa.Column('energy_rating', sa.Integer(), nullable=True),
    sa.Column('completed', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('date_performed', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('energy_rating IS NULL OR energy_rating BETWEEN 1 AND 5', name='ck_ws_energy_rating_range'),
    sa.CheckConstraint('duration_minutes IS NULL OR duration_minutes >= 1', name='ck_ws_duration_positive'),
    sa.ForeignKeyConstraint(['template_id'], ['workout_templates.id'], name='fk_workout_sessions_template_id_workout_templates', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_workout_sessions_user_id_users', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('workout_sessions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workout_sessions_template_id'), ['template_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_workout_sessions_user_id'), ['user_id'], unique=False)

    op.create_table('workout_session_exercises',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('session_id', sa.Integer(), nullable=False),
    sa.Column('exercise_id', sa.Integer(), nullable=False),
    sa.Column('order_index', sa.Integer(), nullable=False),
    sa.Column('target_sets', sa.Integer(), nullable=True),
    sa.Column('rep_range_min', sa.Integer(), nullable=True),
    sa.Column('rep_range_max', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], name='fk_wse_exercise_id_exercises'),
    sa.ForeignKeyConstraint(['session_id'], ['workout_sessions.id'], name='fk_wse_session_id_workout_sessions', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('workout_session_exercises', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workout_session_exercises_exercise_id'), ['exercise_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_workout_session_exercises_session_id'), ['session_id'], unique=False)

    op.create_table('set_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('session_exercise_id', sa.Integer(), nullable=False),
    sa.Column('set_number', sa.Integer(), nullable=False),
    sa.Column('weight', sa.Float(), nullable=False),
    sa.Column('reps', sa.Integer(), nullable=False),
    sa.Column('notes', sa.String(length=200), nullable=True),
    sa.CheckConstraint('set_number >= 1', name='ck_set_entries_set_number_positive'),
    sa.CheckConstraint('weight >= 0', name='ck_set_entries_weight_not_negative'),
    sa.CheckConstraint('reps >= 1', name='ck_set_entries_reps_positive'),
    sa.ForeignKeyConstraint(['session_exercise_id'], ['workout_session_exercises.id'], name='fk_set_entries_session_exercise_id_workout_session_exercises', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('set_entries', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_set_entries_session_exercise_id'), ['session_exercise_id'], unique=False)


def downgrade():
    with op.batch_alter_table('set_entries', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_set_entries_session_exercise_id'))
    op.drop_table('set_entries')

    with op.batch_alter_table('workout_session_exercises', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workout_session_exercises_session_id'))
        batch_op.drop_index(batch_op.f('ix_workout_session_exercises_exercise_id'))
    op.drop_table('workout_session_exercises')

    with op.batch_alter_table('workout_sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workout_sessions_user_id'))
        batch_op.drop_index(batch_op.f('ix_workout_sessions_template_id'))
    op.drop_table('workout_sessions')
