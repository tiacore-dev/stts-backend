"""Added cascade delete to User relationships

Revision ID: a1aec2e0862d
Revises: 2c0134be860b
Create Date: 2024-11-07 22:34:28.940106

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1aec2e0862d'
down_revision: Union[str, None] = '2c0134be860b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # Удаляем старые ограничения внешних ключей
    op.drop_constraint('analysis_transcription_id_fkey', 'analysis', type_='foreignkey')
    op.drop_constraint('analysis_prompt_id_fkey', 'analysis', type_='foreignkey')
    
    # Добавляем новые ограничения с каскадным удалением
    op.create_foreign_key(
        'fk_user_audio_files', 'audio_files', 'users', ['user_id'], ['user_id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_user_prompts', 'prompts', 'users', ['user_id'], ['user_id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_user_transcriptions', 'transcriptions', 'users', ['user_id'], ['user_id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_user_analysis', 'analysis', 'users', ['user_id'], ['user_id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_user_api_keys', 'api_keys', 'users', ['user_id'], ['user_id'], ondelete='CASCADE'
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # Удаляем каскадные ограничения
    op.drop_constraint('fk_user_audio_files', 'audio_files', type_='foreignkey')
    op.drop_constraint('fk_user_prompts', 'prompts', type_='foreignkey')
    op.drop_constraint('fk_user_transcriptions', 'transcriptions', type_='foreignkey')
    op.drop_constraint('fk_user_analysis', 'analysis', type_='foreignkey')
    op.drop_constraint('fk_user_api_keys', 'api_keys', type_='foreignkey')
    
    # Восстанавливаем старые ограничения без каскадного удаления
    op.create_foreign_key('analysis_prompt_id_fkey', 'analysis', 'prompts', ['prompt_id'], ['prompt_id'])
    op.create_foreign_key('analysis_transcription_id_fkey', 'analysis', 'transcriptions', ['transcription_id'], ['transcription_id'])
    # ### end Alembic commands ###