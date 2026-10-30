"""Initial schema for the Campus Intelligence backend.

Revision ID: 0001_initial
Revises: None
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE TABLE users (\n\tid UUID NOT NULL, \n\tfirebase_uid VARCHAR(128) NOT NULL, \n\temail VARCHAR(320), \n\tfull_name VARCHAR(160), \n\tdepartment VARCHAR(160), \n\tyear_of_study INTEGER, \n\tskills JSON NOT NULL, \n\tinterests JSON NOT NULL, \n\tcareer_goals JSON NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id)\n)')
    op.execute('CREATE TABLE conversations (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\ttitle VARCHAR(240) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n)')
    op.execute('CREATE TABLE documents (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\toriginal_filename VARCHAR(255) NOT NULL, \n\tstored_filename VARCHAR(80) NOT NULL, \n\tdocument_type VARCHAR(40) NOT NULL, \n\tsubject VARCHAR(160), \n\tcontent_type VARCHAR(120) NOT NULL, \n\tfile_size_bytes INTEGER NOT NULL, \n\tpage_count INTEGER NOT NULL, \n\tstatus VARCHAR(24) NOT NULL, \n\textracted_text TEXT NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tUNIQUE (stored_filename)\n)')
    op.execute('CREATE TABLE dsa_records (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\tproblem_name VARCHAR(240) NOT NULL, \n\ttopic VARCHAR(120) NOT NULL, \n\tplatform VARCHAR(120), \n\tdifficulty VARCHAR(24) NOT NULL, \n\tstatus VARCHAR(24) NOT NULL, \n\tnotes TEXT, \n\tsolved_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n)')
    op.execute('CREATE TABLE interview_sessions (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\trole VARCHAR(200) NOT NULL, \n\tjob_description TEXT, \n\tskill_focus JSON NOT NULL, \n\tstatus VARCHAR(24) NOT NULL, \n\tsummary JSON NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tended_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n)')
    op.execute('CREATE TABLE job_applications (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\tcompany VARCHAR(200) NOT NULL, \n\trole VARCHAR(200) NOT NULL, \n\tsource_url VARCHAR(1000), \n\tstatus VARCHAR(24) NOT NULL, \n\tapplied_on DATE, \n\tnext_step_date DATE, \n\tnotes TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n)')
    op.execute('CREATE TABLE projects (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\tname VARCHAR(200) NOT NULL, \n\tdescription TEXT, \n\tstatus VARCHAR(24) NOT NULL, \n\tskills JSON NOT NULL, \n\tmilestones JSON NOT NULL, \n\trepository_url VARCHAR(500), \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n)')
    op.execute('CREATE TABLE study_plans (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\ttitle VARCHAR(240) NOT NULL, \n\tsubject VARCHAR(160) NOT NULL, \n\texam_date DATE NOT NULL, \n\tavailable_minutes_per_day INTEGER NOT NULL, \n\tstudy_weekdays JSON NOT NULL, \n\ttopics JSON NOT NULL, \n\toverloaded BOOLEAN NOT NULL, \n\tunscheduled_minutes INTEGER NOT NULL, \n\tsource_document_ids JSON NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n)')
    op.execute('CREATE TABLE document_chunks (\n\tid UUID NOT NULL, \n\tdocument_id UUID NOT NULL, \n\tchunk_index INTEGER NOT NULL, \n\tpage_number INTEGER, \n\ttext_content TEXT NOT NULL, \n\tembedding JSON, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE\n)')
    op.execute('CREATE TABLE interview_turns (\n\tid UUID NOT NULL, \n\tsession_id UUID NOT NULL, \n\trole VARCHAR(24) NOT NULL, \n\tcontent TEXT NOT NULL, \n\tevaluation JSON NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(session_id) REFERENCES interview_sessions (id) ON DELETE CASCADE\n)')
    op.execute('CREATE TABLE messages (\n\tid UUID NOT NULL, \n\tconversation_id UUID NOT NULL, \n\trole VARCHAR(24) NOT NULL, \n\tcontent TEXT NOT NULL, \n\tcitations JSON NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE\n)')
    op.execute('CREATE TABLE resume_analyses (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\tdocument_id UUID, \n\tresume_filename VARCHAR(255) NOT NULL, \n\textracted_data JSON NOT NULL, \n\tfeedback JSON NOT NULL, \n\tresume_score INTEGER NOT NULL, \n\tscore_breakdown JSON NOT NULL, \n\tkeyword_coverage JSON NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tFOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE SET NULL\n)')
    op.execute('CREATE TABLE study_tasks (\n\tid UUID NOT NULL, \n\tplan_id UUID NOT NULL, \n\ttitle VARCHAR(240) NOT NULL, \n\ttopic VARCHAR(240) NOT NULL, \n\tscheduled_date DATE, \n\testimated_minutes INTEGER NOT NULL, \n\tstatus VARCHAR(24) NOT NULL, \n\tnotes TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tcompleted_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(plan_id) REFERENCES study_plans (id) ON DELETE CASCADE\n)')
    op.execute('CREATE INDEX ix_users_email ON users (email)')
    op.execute('CREATE UNIQUE INDEX ix_users_firebase_uid ON users (firebase_uid)')
    op.execute('CREATE INDEX ix_conversations_user_id ON conversations (user_id)')
    op.execute('CREATE INDEX ix_documents_document_type ON documents (document_type)')
    op.execute('CREATE INDEX ix_documents_status ON documents (status)')
    op.execute('CREATE INDEX ix_documents_subject ON documents (subject)')
    op.execute('CREATE INDEX ix_documents_user_id ON documents (user_id)')
    op.execute('CREATE INDEX ix_dsa_records_topic ON dsa_records (topic)')
    op.execute('CREATE INDEX ix_dsa_records_user_id ON dsa_records (user_id)')
    op.execute('CREATE INDEX ix_interview_sessions_status ON interview_sessions (status)')
    op.execute('CREATE INDEX ix_interview_sessions_user_id ON interview_sessions (user_id)')
    op.execute('CREATE INDEX ix_job_applications_status ON job_applications (status)')
    op.execute('CREATE INDEX ix_job_applications_user_id ON job_applications (user_id)')
    op.execute('CREATE INDEX ix_projects_user_id ON projects (user_id)')
    op.execute('CREATE INDEX ix_study_plans_user_id ON study_plans (user_id)')
    op.execute('CREATE INDEX ix_document_chunks_document_id ON document_chunks (document_id)')
    op.execute('CREATE INDEX ix_interview_turns_session_id ON interview_turns (session_id)')
    op.execute('CREATE INDEX ix_messages_conversation_id ON messages (conversation_id)')
    op.execute('CREATE INDEX ix_resume_analyses_document_id ON resume_analyses (document_id)')
    op.execute('CREATE INDEX ix_resume_analyses_user_id ON resume_analyses (user_id)')
    op.execute('CREATE INDEX ix_study_tasks_plan_id ON study_tasks (plan_id)')
    op.execute('CREATE INDEX ix_study_tasks_scheduled_date ON study_tasks (scheduled_date)')
    op.execute('CREATE INDEX ix_study_tasks_status ON study_tasks (status)')


def downgrade() -> None:
    op.drop_table('study_tasks')
    op.drop_table('resume_analyses')
    op.drop_table('messages')
    op.drop_table('interview_turns')
    op.drop_table('document_chunks')
    op.drop_table('study_plans')
    op.drop_table('projects')
    op.drop_table('job_applications')
    op.drop_table('interview_sessions')
    op.drop_table('dsa_records')
    op.drop_table('documents')
    op.drop_table('conversations')
    op.drop_table('users')
