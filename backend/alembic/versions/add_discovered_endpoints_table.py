"""add discovered endpoints table

Revision ID: add_discovered_endpoints_table
Revises: 
Create Date: 2024-03-17 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_discovered_endpoints_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create discovered_endpoints table
    op.create_table(
        'discovered_endpoints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('remote_server_id', sa.Integer(), nullable=False),
        sa.Column('path', sa.String(length=255), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parameters', postgresql.JSONB(), nullable=True),
        sa.Column('response_schema', postgresql.JSONB(), nullable=True),
        sa.Column('discovered_at', sa.DateTime(), nullable=False),
        sa.Column('last_checked', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('endpoint_hash', sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(['remote_server_id'], ['remote_servers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_discovered_endpoints_id', 'discovered_endpoints', ['id'])
    op.create_index('ix_discovered_endpoints_remote_server_id', 'discovered_endpoints', ['remote_server_id'])
    op.create_index('ix_discovered_endpoints_path_method', 'discovered_endpoints', ['path', 'method'])
    op.create_index('ix_discovered_endpoints_hash', 'discovered_endpoints', ['endpoint_hash'], unique=True)

def downgrade():
    # Drop indexes
    op.drop_index('ix_discovered_endpoints_hash')
    op.drop_index('ix_discovered_endpoints_path_method')
    op.drop_index('ix_discovered_endpoints_remote_server_id')
    op.drop_index('ix_discovered_endpoints_id')
    
    # Drop table
    op.drop_table('discovered_endpoints') 