"""Create workout template tables

Revision ID: 8d4f1a6b2e90
Revises: 3b7e9d2c41a8
Create Date: 2026-10-22 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8d4f1a6b2e90'
down_revision = '3b7e9d2c41a8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('workout_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('difficulty', sa.String(length=20), nullable=False),
    sa.Column('is_public', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_workout_templates_user_id_users', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('workout_templates', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workout_templates_user_id'), ['user_id'], unique=False)

    op.create_table('workout_template_exercises',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('template_id', sa.Integer(), nullable=False),
    sa.Column('exercise_id', sa.Integer(), nullable=False),
    sa.Column('order_index', sa.Integer(), nullable=False),
    sa.Column('target_sets', sa.Integer(), nullable=False),
    sa.Column('rep_range_min', sa.Integer(), nullable=False),
    sa.Column('rep_range_max', sa.Integer(), nullable=False),
    sa.CheckConstraint('target_sets >= 1', name='ck_wte_target_sets_positive'),
    sa.CheckConstraint('rep_range_min >= 1', name='ck_wte_rep_range_min_positive'),
    sa.CheckConstraint('rep_range_min <= rep_range_max', name='ck_wte_rep_range_order'),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], name='fk_wte_exercise_id_exercises'),
    sa.ForeignKeyConstraint(['template_id'], ['workout_templates.id'], name='fk_wte_template_id_workout_templates', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('workout_template_exercises', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workout_template_exercises_exercise_id'), ['exercise_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_workout_template_exercises_template_id'), ['template_id'], unique=False)


def downgrade():
    with op.batch_alter_table('workout_template_exercises', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workout_template_exercises_template_id'))
        batch_op.drop_index(batch_op.f('ix_workout_template_exercises_exercise_id'))

    op.drop_table('workout_template_exercises')

    with op.batch_alter_table('workout_templates', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workout_templates_user_id'))

    op.drop_table('workout_templates')
