"""update endpoint health schema

Revision ID: update_endpoint_health_schema
Revises: update_endpoint_health_table
Create Date: 2024-03-17 22:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'update_endpoint_health_schema'
down_revision = 'update_endpoint_health_table'
branch_labels = None
depends_on = None

def upgrade():
    # Drop existing foreign key if it exists
    op.drop_constraint('fk_endpoint_health_discovered_endpoint', 'endpoint_health', type_='foreignkey')
    
    # Drop existing index if it exists
    op.drop_index('ix_endpoint_health_discovered_endpoint_id', table_name='endpoint_health')
    
    # Drop existing columns
    op.drop_column('endpoint_health', 'discovered_endpoint_id')
    op.drop_column('endpoint_health', 'endpoint_id')
    
    # Add new columns
    op.add_column('endpoint_health',
        sa.Column('discovered_endpoint_id', sa.Integer(), nullable=False)
    )
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_endpoint_health_discovered_endpoint',
        'endpoint_health', 'discovered_endpoints',
        ['discovered_endpoint_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Create index
    op.create_index(
        'ix_endpoint_health_discovered_endpoint_id',
        'endpoint_health',
        ['discovered_endpoint_id']
    )

def downgrade():
    # Drop foreign key constraint
    op.drop_constraint('fk_endpoint_health_discovered_endpoint', 'endpoint_health', type_='foreignkey')
    
    # Drop index
    op.drop_index('ix_endpoint_health_discovered_endpoint_id', table_name='endpoint_health')
    
    # Drop column
    op.drop_column('endpoint_health', 'discovered_endpoint_id')
    
    # Add back old column
    op.add_column('endpoint_health',
        sa.Column('endpoint_id', sa.Integer(), nullable=True)
    ) 