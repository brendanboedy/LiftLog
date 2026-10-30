"""Allow predefined workout templates (empty user_id)

Revision ID: 7a3d5f9e2b16
Revises: e1b4c8a07f25
Create Date: 2026-10-30 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7a3d5f9e2b16'
down_revision = 'e1b4c8a07f25'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('workout_templates', schema=None) as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.Integer(), nullable=True)


def downgrade():
    # Predefined templates have no owner, so they have to go before user_id can be required again.
    # Done by hand because SQLite doesn't always apply ON DELETE rules.
    predefined = 'SELECT id FROM workout_templates WHERE user_id IS NULL'
    op.execute(f'DELETE FROM workout_template_exercises WHERE template_id IN ({predefined})')
    op.execute(f'UPDATE workout_sessions SET template_id = NULL WHERE template_id IN ({predefined})')
    op.execute('DELETE FROM workout_templates WHERE user_id IS NULL')
    with op.batch_alter_table('workout_templates', schema=None) as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.Integer(), nullable=False)
