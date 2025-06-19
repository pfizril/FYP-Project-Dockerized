"""add remote servers

Revision ID: add_remote_servers
Revises: 
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_remote_servers'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'remote_servers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('base_url', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_checked', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='offline'),
        sa.Column('api_key', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('health_check_url', sa.String(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.String(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('base_url')
    )
    
    # Create indexes
    op.create_index(op.f('ix_remote_servers_id'), 'remote_servers', ['id'], unique=False)
    op.create_index(op.f('ix_remote_servers_name'), 'remote_servers', ['name'], unique=True)
    op.create_index(op.f('ix_remote_servers_base_url'), 'remote_servers', ['base_url'], unique=True)
    op.create_index(op.f('ix_remote_servers_status'), 'remote_servers', ['status'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_remote_servers_status'), table_name='remote_servers')
    op.drop_index(op.f('ix_remote_servers_base_url'), table_name='remote_servers')
    op.drop_index(op.f('ix_remote_servers_name'), table_name='remote_servers')
    op.drop_index(op.f('ix_remote_servers_id'), table_name='remote_servers')
    op.drop_table('remote_servers') 