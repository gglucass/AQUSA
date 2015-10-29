"""empty message

Revision ID: 1516781f333
Revises: 56580e83683
Create Date: 2015-09-09 17:50:03.200301

"""

# revision identifiers, used by Alembic.
revision = '1516781f333'
down_revision = '56580e83683'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('comment', sa.Column('error_id', sa.Integer(), nullable=False))
    op.create_foreign_key(None, 'comment', 'error', ['error_id'], ['id'])
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'comment', type_='foreignkey')
    op.drop_column('comment', 'error_id')
    ### end Alembic commands ###