"""Create exercises table

Revision ID: 3b7e9d2c41a8
Revises: fc078ebab41c
Create Date: 2026-10-22 16:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3b7e9d2c41a8'
down_revision = 'fc078ebab41c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('exercises',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('muscle_group', sa.String(length=30), nullable=False),
    sa.Column('equipment_type', sa.String(length=30), nullable=False),
    sa.Column('movement_type', sa.String(length=20), nullable=False),
    sa.Column('difficulty', sa.String(length=20), nullable=False),
    sa.Column('instructions', sa.Text(), nullable=True),
    sa.Column('is_archived', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_exercises_created_by_users', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('exercises', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_exercises_created_by'), ['created_by'], unique=False)
        batch_op.create_index(batch_op.f('ix_exercises_name'), ['name'], unique=False)


def downgrade():
    with op.batch_alter_table('exercises', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_exercises_name'))
        batch_op.drop_index(batch_op.f('ix_exercises_created_by'))

    op.drop_table('exercises')
