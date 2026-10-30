export interface UserProfile {
  id: string; email: string | null; full_name: string | null; department: string | null
  year_of_study: number | null; skills: string[]; interests: string[]; career_goals: string[]
  created_at: string
}
export interface DocumentItem {
  id: string; original_filename: string; document_type: string; subject: string | null
  content_type: string; file_size_bytes: number; page_count: number; status: string; created_at: string
}
export interface Citation { source_number: number; document_id: string; document_name: string; page_number: number | null; excerpt: string }
export interface Conversation { id: string; title: string; created_at: string; updated_at: string }
export interface ChatMessage { id: string; role: string; content: string; citations: Citation[]; created_at: string }
export interface PlanTask { id: string; title: string; topic: string; scheduled_date: string | null; estimated_minutes: number; status: string; notes: string | null; completed_at: string | null }
export interface StudyPlan {
  id: string; title: string; subject: string; exam_date: string; available_minutes_per_day: number
  overloaded: boolean; unscheduled_minutes: number; tasks: PlanTask[]; created_at: string
}
export interface Project { id: string; name: string; description: string | null; status: string; skills: string[]; repository_url: string | null; created_at: string }
export interface DSARecord { id: string; problem_name: string; topic: string; platform: string | null; difficulty: string; status: string; notes: string | null; created_at: string }
export interface Application { id: string; company: string; role: string; status: string; source_url: string | null; applied_on: string | null; next_step_date: string | null; notes: string | null; created_at: string }
export interface InterviewSession { id: string; role: string; status: string; skill_focus: string[]; created_at: string; summary: Record<string, unknown>; turns?: InterviewTurn[] }
export interface InterviewTurn { id: string; role: string; content: string; evaluation: Record<string, unknown>; created_at: string }
export interface ResumeAnalysis {
  id: string; document_id: string | null; resume_filename: string; extracted_data: Record<string, unknown>
  feedback: Record<string, any>; resume_score: number; score_breakdown: Record<string, any>
  job_description_alignment: Record<string, any>; created_at: string
}
export interface Analytics {
  documents_total: number; resume_analyses_total: number; study_plans_total: number
  study_tasks_completed: number; study_tasks_pending: number; interview_sessions_total: number
  projects_total: number; projects_completed: number; dsa_problems_solved: number
  dsa_problems_attempted: number; applications_total: number
  applications_by_status: Record<string, number>; upcoming_deadlines: { kind: string; id: string; title: string; date: string }[]
}
