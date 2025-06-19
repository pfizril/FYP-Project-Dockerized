"""update endpoint health status

Revision ID: update_endpoint_health_status
Revises: update_endpoint_health_table
Create Date: 2024-06-17 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'update_endpoint_health_status'
down_revision = 'update_endpoint_health_table'
branch_labels = None
depends_on = None

def upgrade():
    # Create a temporary column for the new status
    op.add_column('endpoint_health', sa.Column('new_status', sa.String(), nullable=True))
    op.add_column('endpoint_health', sa.Column('is_healthy', sa.Boolean(), nullable=True))
    
    # Update the new status column based on the old boolean status
    op.execute("""
        UPDATE endpoint_health 
        SET new_status = CASE 
            WHEN status = true THEN 'success'
            ELSE 'error'
        END,
        is_healthy = status
    """)
    
    # Drop the old status column
    op.drop_column('endpoint_health', 'status')
    
    # Rename the new status column to status
    op.alter_column('endpoint_health', 'new_status', new_column_name='status')
    
    # Make the columns non-nullable
    op.alter_column('endpoint_health', 'status', nullable=False)
    op.alter_column('endpoint_health', 'is_healthy', nullable=False)

def downgrade():
    # Create a temporary column for the old status
    op.add_column('endpoint_health', sa.Column('old_status', sa.Boolean(), nullable=True))
    
    # Update the old status column based on the new status
    op.execute("""
        UPDATE endpoint_health 
        SET old_status = CASE 
            WHEN status = 'success' THEN true
            ELSE false
        END
    """)
    
    # Drop the new columns
    op.drop_column('endpoint_health', 'status')
    op.drop_column('endpoint_health', 'is_healthy')
    
    # Rename the old status column back to status
    op.alter_column('endpoint_health', 'old_status', new_column_name='status')
    
    # Make the status column non-nullable
    op.alter_column('endpoint_health', 'status', nullable=False) 