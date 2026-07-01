"""add_phase_11_compliance_tables

Revision ID: f5936021fcf8
Revises: de0a4f2b8bff
Create Date: 2026-07-01 18:52:27.916621

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5936021fcf8'
down_revision: Union[str, Sequence[str], None] = 'de0a4f2b8bff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('compliance_profiles',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('organization_id', sa.String(length=36), nullable=False),
    sa.Column('client_id', sa.String(length=36), nullable=False),
    sa.Column('compliance_type', sa.String(length=100), nullable=False),
    sa.Column('registration_number', sa.String(length=100), nullable=True),
    sa.Column('frequency', sa.String(length=50), nullable=True),
    sa.Column('due_day', sa.Integer(), nullable=True),
    sa.Column('assigned_manager', sa.String(length=255), nullable=True),
    sa.Column('assigned_partner', sa.String(length=255), nullable=True),
    sa.Column('risk_level', sa.String(length=50), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('compliance_tasks',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('organization_id', sa.String(length=36), nullable=False),
    sa.Column('client_id', sa.String(length=36), nullable=False),
    sa.Column('profile_id', sa.String(length=36), nullable=False),
    sa.Column('task_name', sa.String(length=255), nullable=False),
    sa.Column('due_date', sa.DateTime(), nullable=False),
    sa.Column('priority', sa.String(length=50), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('assigned_user_id', sa.String(length=36), nullable=True),
    sa.Column('document_id', sa.String(length=36), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['assigned_user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.ForeignKeyConstraint(['document_id'], ['raw_documents.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.ForeignKeyConstraint(['profile_id'], ['compliance_profiles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('compliance_history',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('organization_id', sa.String(length=36), nullable=False),
    sa.Column('client_id', sa.String(length=36), nullable=False),
    sa.Column('task_id', sa.String(length=36), nullable=False),
    sa.Column('filing_date', sa.DateTime(), nullable=True),
    sa.Column('acknowledgement_number', sa.String(length=255), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.ForeignKeyConstraint(['task_id'], ['compliance_tasks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('compliance_alerts',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('organization_id', sa.String(length=36), nullable=False),
    sa.Column('client_id', sa.String(length=36), nullable=False),
    sa.Column('task_id', sa.String(length=36), nullable=True),
    sa.Column('alert_type', sa.String(length=100), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('is_resolved', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.ForeignKeyConstraint(['task_id'], ['compliance_tasks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('compliance_alerts')
    op.drop_table('compliance_history')
    op.drop_table('compliance_tasks')
    op.drop_table('compliance_profiles')
