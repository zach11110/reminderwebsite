"""Added phone_number to User model

Revision ID: c220b5919af3
Revises: 8b41d2575d3e
Create Date: 2023-08-13 21:20:09.376159

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c220b5919af3'
down_revision = '8b41d2575d3e'
branch_labels = None
depends_on = None

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('phone_number', sa.String(length=15), nullable=True))
        batch_op.add_column(sa.Column('telegram_id', sa.String(length=80), nullable=True))
        
        # Added names for the unique constraints
        batch_op.create_unique_constraint('uq_user_phone_number', ['phone_number'])
        batch_op.create_unique_constraint('uq_user_telegram_id', ['telegram_id'])
    # ### end Alembic commands ###

def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        # Referenced the named constraints while dropping them
        batch_op.drop_constraint('uq_user_telegram_id', type_='unique')
        batch_op.drop_constraint('uq_user_phone_number', type_='unique')
        batch_op.drop_column('telegram_id')
        batch_op.drop_column('phone_number')
    # ### end Alembic commands ###

