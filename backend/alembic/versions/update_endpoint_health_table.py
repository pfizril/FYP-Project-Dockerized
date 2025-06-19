"""update endpoint health table

Revision ID: update_endpoint_health_table
Revises: add_discovered_endpoints_table
Create Date: 2024-03-17 21:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'update_endpoint_health_table'
down_revision = 'add_discovered_endpoints_table'
branch_labels = None
depends_on = None

def upgrade():
    # Add the new discovered_endpoint_id column (nullable initially)
    op.add_column('endpoint_health',
        sa.Column('discovered_endpoint_id', sa.Integer(), nullable=True)
    )
    
    # Copy data from endpoint_id to discovered_endpoint_id
    op.execute("""
        UPDATE endpoint_health 
        SET discovered_endpoint_id = endpoint_id 
        WHERE endpoint_id IS NOT NULL
    """)
    
    # Make discovered_endpoint_id non-nullable
    op.alter_column('endpoint_health', 'discovered_endpoint_id',
        existing_type=sa.Integer(),
        nullable=False
    )
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_endpoint_health_discovered_endpoint',
        'endpoint_health', 'discovered_endpoints',
        ['discovered_endpoint_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Create index on discovered_endpoint_id
    op.create_index(
        'ix_endpoint_health_discovered_endpoint_id',
        'endpoint_health',
        ['discovered_endpoint_id']
    )
    
    # Drop the old endpoint_id column
    op.drop_column('endpoint_health', 'endpoint_id')

def downgrade():
    # Add back the old endpoint_id column (nullable initially)
    op.add_column('endpoint_health',
        sa.Column('endpoint_id', sa.Integer(), nullable=True)
    )
    
    # Copy data back from discovered_endpoint_id to endpoint_id
    op.execute("""
        UPDATE endpoint_health 
        SET endpoint_id = discovered_endpoint_id 
        WHERE discovered_endpoint_id IS NOT NULL
    """)
    
    # Drop the foreign key constraint
    op.drop_constraint('fk_endpoint_health_discovered_endpoint', 'endpoint_health', type_='foreignkey')
    
    # Drop the index
    op.drop_index('ix_endpoint_health_discovered_endpoint_id', table_name='endpoint_health')
    
    # Drop the new column
    op.drop_column('endpoint_health', 'discovered_endpoint_id') 