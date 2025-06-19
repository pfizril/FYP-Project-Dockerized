"""Add created_by to remote_servers

Revision ID: add_created_by_to_remote_servers
Revises: add_remote_servers
Create Date: 2024-03-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_created_by_to_remote_servers'
down_revision = 'add_remote_servers'  # Set this to the previous migration
branch_labels = None
depends_on = None

def upgrade():
    # Add created_by column to remote_servers table
    op.add_column('remote_servers', sa.Column('created_by', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_remote_servers_created_by_users',
        'remote_servers', 'Users',
        ['created_by'], ['user_id']
    )
    
    # Make the column non-nullable after adding the foreign key
    op.alter_column('remote_servers', 'created_by',
                    existing_type=sa.Integer(),
                    nullable=False)

def downgrade():
    # Remove foreign key constraint
    op.drop_constraint('fk_remote_servers_created_by_users', 'remote_servers', type_='foreignkey')
    
    # Remove created_by column
    op.drop_column('remote_servers', 'created_by') 