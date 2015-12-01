"""empty message

Revision ID: 7310aac914
Revises: None
Create Date: 2015-05-10 16:58:25.378606

"""

# revision identifiers, used by Alembic.
revision = '7310aac914'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('project',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_name'), 'project', ['name'], unique=False)
    op.create_table('story',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=True),
    sa.Column('role', sa.Text(), nullable=True),
    sa.Column('means', sa.Text(), nullable=True),
    sa.Column('ends', sa.Text(), nullable=True),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('defect',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('highlight', sa.Text(), nullable=False),
    sa.Column('kind', sa.String(length=120), nullable=False),
    sa.Column('subkind', sa.String(length=120), nullable=False),
    sa.Column('severity', sa.String(length=120), nullable=False),
    sa.Column('story_id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['story_id'], ['story.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_defect_kind'), 'defect', ['kind'], unique=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_defect_kind'), table_name='defect')
    op.drop_table('defect')
    op.drop_table('story')
    op.drop_index(op.f('ix_project_name'), table_name='project')
    op.drop_table('project')
    ### end Alembic commands ###
