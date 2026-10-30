import { useCallback, useEffect, useMemo, useState } from 'react'
import type { CSSProperties, FormEvent, ReactNode } from 'react'
import { api, apiRoot } from './services/api'
import type {
  Analytics, Application, ChatMessage, Conversation, DocumentItem, DSARecord,
  InterviewSession, InterviewTurn, Project, ResumeAnalysis, StudyPlan, UserProfile,
} from './types'
import './App.css'

type Page = 'Dashboard' | 'My Documents' | 'Academic Assistant' | 'Resume Analyzer' | 'Study Planner' | 'Interview Preparation' | 'Progress Tracker' | 'Analytics' | 'Profile'
type Notice = { kind: 'success' | 'error'; message: string } | null

const navItems: { page: Page; icon: string; group: string }[] = [
  { page: 'Dashboard', icon: '⌂', group: 'Workspace' },
  { page: 'My Documents', icon: '▤', group: 'Workspace' },
  { page: 'Academic Assistant', icon: '✳', group: 'Workspace' },
  { page: 'Resume Analyzer', icon: '▧', group: 'Career' },
  { page: 'Study Planner', icon: '▦', group: 'Career' },
  { page: 'Interview Preparation', icon: '◉', group: 'Career' },
  { page: 'Progress Tracker', icon: '↗', group: 'Career' },
  { page: 'Analytics', icon: '▥', group: 'Insights' },
  { page: 'Profile', icon: '◎', group: 'Insights' },
]
const docTypes = [
  ['syllabus', 'Syllabus'], ['notes', 'Notes'], ['previous_year_paper', 'Previous year paper'],
  ['placement_notification', 'Placement notification'], ['job_description', 'Job description'], ['resume', 'Resume'],
] as const
const today = new Date().toISOString().slice(0, 10)
const prettyDate = (value?: string | null) => value ? new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '—'
const prettySize = (bytes: number) => bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(0)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`
const messageOf = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong.'
const emptyAnalytics: Analytics = {
  documents_total: 0, resume_analyses_total: 0, study_plans_total: 0, study_tasks_completed: 0,
  study_tasks_pending: 0, interview_sessions_total: 0, projects_total: 0, projects_completed: 0,
  dsa_problems_solved: 0, dsa_problems_attempted: 0, applications_total: 0,
  applications_by_status: {}, upcoming_deadlines: [],
}

function App() {
  const [page, setPage] = useState<Page>('Dashboard')
  const [dark, setDark] = useState(false)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [health, setHealth] = useState<'checking' | 'online' | 'offline'>('checking')
  const [notice, setNotice] = useState<Notice>(null)
  const [busy, setBusy] = useState(false)
  const [analytics, setAnalytics] = useState<Analytics>(emptyAnalytics)
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [dsa, setDsa] = useState<DSARecord[]>([])
  const [applications, setApplications] = useState<Application[]>([])
  const [plans, setPlans] = useState<StudyPlan[]>([])
  const [interviews, setInterviews] = useState<InterviewSession[]>([])
  const [resumeAnalyses, setResumeAnalyses] = useState<ResumeAnalysis[]>([])

  const notify = useCallback((kind: 'success' | 'error', message: string) => {
    setNotice({ kind, message })
    window.setTimeout(() => setNotice(null), 5500)
  }, [])
  const refreshCore = useCallback(async () => {
    // Resolve the development user first. Both endpoints call get_current_user;
    // sequential requests avoid racing to create the first local user row.
    const me = await api.get<UserProfile>('/users/me')
    const stats = await api.get<Analytics>('/analytics/overview')
    setProfile(me)
    setAnalytics(stats)
  }, [])
  const refreshAll = useCallback(async () => {
    try {
      const [docs, projectRows, dsaRows, appRows, planRows, interviewRows, resumeRows] = await Promise.all([
        api.get<DocumentItem[]>('/documents'),
        api.get<Project[]>('/progress/projects'),
        api.get<DSARecord[]>('/progress/dsa'),
        api.get<Application[]>('/applications'),
        api.get<StudyPlan[]>('/study-plans'),
        api.get<InterviewSession[]>('/interviews'),
        api.get<ResumeAnalysis[]>('/resumes/analyses'),
      ])
      setDocuments(docs); setProjects(projectRows); setDsa(dsaRows); setApplications(appRows)
      setPlans(planRows); setInterviews(interviewRows); setResumeAnalyses(resumeRows)
    } catch (error) { notify('error', messageOf(error)) }
  }, [])
  useEffect(() => {
    let active = true
    Promise.all([fetch(`${apiRoot}/health`).then(response => response.ok ? response.json() as Promise<{ status: string }> : null).catch(() => null), refreshCore()])
      .then(async ([result]) => {
        if (!active) return
        setHealth(result ? 'online' : 'offline')
        await refreshAll()
      })
      .catch((error: unknown) => {
        if (!active) return
        setHealth('offline')
        notify('error', messageOf(error))
      })
    return () => { active = false }
  }, [refreshAll, refreshCore])

  const run = async (action: () => Promise<unknown>, success?: string) => {
    setBusy(true)
    try { await action(); if (success) notify('success', success); await refreshCore(); await refreshAll() }
    catch (error) { notify('error', messageOf(error)) }
    finally { setBusy(false) }
  }

  const pageTitle = page
  const initials = (profile?.full_name || profile?.email || 'Student').slice(0, 1).toUpperCase()
  const grouped = useMemo(() => ['Workspace', 'Career', 'Insights'].map(group => ({
    group, items: navItems.filter(item => item.group === group),
  })), [])

  return (
    <div className={`app-shell ${dark ? 'dark' : ''}`}>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">CI</div>
          <div><strong>Campus Intelligence</strong><span>Student command centre</span></div>
        </div>
        <div className="nav-scroll">
          {grouped.map(section => <div className="nav-group" key={section.group}>
            <div className="nav-label">{section.group}</div>
            {section.items.map(item => <button key={item.page} type="button" onClick={() => setPage(item.page)} className={`nav-item ${page === item.page ? 'active' : ''}`}>
              <span className="nav-icon">{item.icon}</span><span>{item.page}</span>
            </button>)}
          </div>)}
        </div>
        <div className="sidebar-bottom">
          <div className="user-mini"><span className="avatar">{initials}</span><div><strong>{profile?.full_name || 'Student account'}</strong><span>{profile?.email || 'Development workspace'}</span></div></div>
          <div className="api-status"><span className={`status-dot ${health}`} /> API {health === 'online' ? 'connected' : health === 'offline' ? 'disconnected' : 'checking'}</div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div><div className="eyebrow">CAMPUS INTELLIGENCE / {page.toUpperCase()}</div><h1>{pageTitle}</h1></div>
          <div className="top-actions">
            <span className={`connection-pill ${health}`}><i />{health === 'online' ? 'Backend online' : health === 'offline' ? 'Backend offline' : 'Connecting'}</span>
            <button className="icon-button" onClick={() => setDark(v => !v)} type="button" title="Toggle theme">{dark ? '☀' : '☾'}</button>
            <button className="profile-button" onClick={() => setPage('Profile')} type="button"><span className="avatar small">{initials}</span><span>{profile?.full_name || 'My profile'}</span></button>
          </div>
        </header>
        {notice && <div className={`notice ${notice.kind}`} role="status"><span>{notice.kind === 'success' ? '✓' : '!'}</span>{notice.message}<button onClick={() => setNotice(null)} aria-label="Dismiss">×</button></div>}
        {health === 'offline' && <div className="warning-banner">The frontend cannot reach the API. Start FastAPI at <code>127.0.0.1:8000</code> and check backend/.env CORS settings.</div>}

          {page === 'Dashboard' && <Dashboard profile={profile} analytics={analytics} docs={documents} plans={plans} onNavigate={setPage} />}
        {page === 'My Documents' && <DocumentsPage documents={documents} busy={busy} run={run} notify={notify} />}
        {page === 'Academic Assistant' && <AcademicPage documents={documents} notify={notify} />}
        {page === 'Resume Analyzer' && <ResumePage documents={documents} analyses={resumeAnalyses} busy={busy} run={run} />}
        {page === 'Study Planner' && <StudyPlannerPage plans={plans} documents={documents} busy={busy} run={run} />}
        {page === 'Interview Preparation' && <InterviewPage sessions={interviews} busy={busy} run={run} />}
        {page === 'Progress Tracker' && <ProgressPage projects={projects} dsa={dsa} applications={applications} busy={busy} run={run} />}
        {page === 'Analytics' && <AnalyticsPage analytics={analytics} />}
        {page === 'Profile' && <ProfilePage profile={profile} busy={busy} run={run} />}
        <footer className="app-footer">Campus Intelligence · Local development workspace · <a href={`${apiRoot}/docs`} target="_blank" rel="noreferrer">API documentation ↗</a></footer>
      </main>
    </div>
  )
}

function PageIntro({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-intro"><div><div className="eyebrow">{eyebrow}</div><h2>{title}</h2><p>{description}</p></div>{action}</div>
}
function StatCard({ label, value, note, icon }: { label: string; value: number | string; note: string; icon: string }) {
  return <div className="stat-card"><div className="stat-top"><span>{label}</span><b>{icon}</b></div><strong>{value}</strong><small>{note}</small></div>
}
function Empty({ title, text }: { title: string; text: string }) {
  return <div className="empty-state"><div className="empty-icon">◇</div><strong>{title}</strong><p>{text}</p></div>
}
function Dashboard({ profile, analytics, docs, plans, onNavigate }: { profile: UserProfile | null; analytics: Analytics; docs: DocumentItem[]; plans: StudyPlan[]; onNavigate: (page: Page) => void }) {
  const completion = analytics.study_tasks_completed + analytics.study_tasks_pending
    ? Math.round(analytics.study_tasks_completed / (analytics.study_tasks_completed + analytics.study_tasks_pending) * 100) : 0
  return <>
    <section className="hero-card"><div><div className="eyebrow light">YOUR STUDENT WORKSPACE</div><h2>{profile?.full_name ? `Welcome back, ${profile.full_name.split(' ')[0]}.` : 'Your academics and placement preparation, in one place.'}</h2><p>Manage learning material, prepare for interviews, track your progress and turn your goals into measurable work.</p><button className="button button-light" onClick={() => onNavigate('My Documents')}>Manage documents <span>→</span></button></div><div className="hero-orbit"><div className="orbit-core">CI</div><span className="orbit-tag tag-one">LEARN</span><span className="orbit-tag tag-two">BUILD</span><span className="orbit-tag tag-three">GROW</span></div></section>
    <div className="stats-grid">
      <StatCard label="Documents" value={analytics.documents_total} note="PDFs in your library" icon="▤"/>
      <StatCard label="Study tasks done" value={analytics.study_tasks_completed} note={`${completion}% completion rate`} icon="✓"/>
      <StatCard label="DSA solved" value={analytics.dsa_problems_solved} note={`${analytics.dsa_problems_attempted} attempted`} icon="⌘"/>
      <StatCard label="Applications" value={analytics.applications_total} note="Manually tracked" icon="↗"/>
    </div>
    <div className="dashboard-grid">
      <section className="panel"><div className="panel-heading"><div><div className="eyebrow">QUICK ACCESS</div><h3>Continue your work</h3></div></div><div className="quick-grid">
        {([['My Documents','Upload and organise PDFs','▤'],['Academic Assistant','Ask questions from your notes','✳'],['Resume Analyzer','Review your resume','▧'],['Study Planner','Plan exam preparation','▦'],['Interview Preparation','Practise technical interviews','◉'],['Progress Tracker','Track DSA, projects and jobs','↗']] as const).map(([name,desc,icon]) => <button className="quick-card" key={name} onClick={() => onNavigate(name)}><span>{icon}</span><strong>{name}</strong><small>{desc}</small><b>Open →</b></button>)}
      </div></section>
      <section className="panel"><div className="panel-heading"><div><div className="eyebrow">UP NEXT</div><h3>Upcoming deadlines</h3></div><button className="text-button" onClick={() => onNavigate('Analytics')}>View all</button></div>
        {analytics.upcoming_deadlines.length ? <div className="deadline-list">{analytics.upcoming_deadlines.slice(0, 7).map((item,index) => <div className="deadline-row" key={`${item.id}-${index}`}><span className="deadline-mark">{item.kind === 'study_task' ? '▦' : '↗'}</span><div><strong>{item.title}</strong><small>{item.kind === 'study_task' ? 'Study task' : 'Application follow-up'}</small></div><time>{prettyDate(item.date)}</time></div>)}</div> : <Empty title="Nothing scheduled yet" text="Create a study plan or add an application follow-up date."/>}
      </section>
    </div>
    <div className="dashboard-bottom">
      <section className="panel"><div className="panel-heading"><div><div className="eyebrow">RECENT LIBRARY</div><h3>Latest documents</h3></div><button className="text-button" onClick={() => onNavigate('My Documents')}>All documents</button></div>
        {docs.slice(0,4).map(doc => <div className="compact-row" key={doc.id}><span className="file-icon">PDF</span><div><strong>{doc.original_filename}</strong><small>{doc.document_type.replaceAll('_',' ')} · {doc.page_count} pages</small></div><span className={`tag ${doc.status}`}>{doc.status}</span></div>)}
        {!docs.length && <Empty title="Your library is empty" text="Upload a syllabus, notes or resume PDF to get started."/>}
      </section>
      <section className="panel"><div className="panel-heading"><div><div className="eyebrow">STUDY PLANS</div><h3>Your preparation</h3></div><button className="text-button" onClick={() => onNavigate('Study Planner')}>Open planner</button></div>
        {plans.slice(0,3).map(plan => { const done = plan.tasks.filter(t => t.status === 'completed').length; const total = plan.tasks.length; return <div className="plan-preview" key={plan.id}><div><strong>{plan.subject}</strong><small>{prettyDate(plan.exam_date)} · {done}/{total} tasks</small></div><div className="progress-track"><span style={{width: `${total ? done / total * 100 : 0}%`}}/></div></div> })}
        {!plans.length && <Empty title="No study plans" text="Create a schedule around your next exam."/>}
      </section>
    </div>
  </>
}

function DocumentsPage({ documents, busy, run, notify }: { documents: DocumentItem[]; busy: boolean; run: (action: () => Promise<unknown>, success?: string) => Promise<void>; notify: (kind: 'success' | 'error', message: string) => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [type, setType] = useState('notes')
  const [subject, setSubject] = useState('')
  const [filter, setFilter] = useState('all')
  const filtered = filter === 'all' ? documents : documents.filter(doc => doc.document_type === filter)
  const upload = async (event: FormEvent) => {
    event.preventDefault()
    if (!file) { notify('error', 'Choose a PDF file first.'); return }
    const body = new FormData(); body.append('file', file); body.append('document_type', type); if (subject.trim()) body.append('subject', subject.trim())
    await run(async () => { await api.upload<DocumentItem>('/documents', body); setFile(null); setSubject(''); const input = document.getElementById('document-file') as HTMLInputElement | null; if (input) input.value = '' }, 'Document uploaded and indexed.')
  }
  return <>
    <PageIntro eyebrow="YOUR PRIVATE PDF LIBRARY" title="Documents" description="Upload text-based PDFs. The backend extracts pages and indexes document chunks for academic retrieval."/>
    <div className="content-grid two-one">
      <section className="panel"><div className="panel-heading"><div><div className="eyebrow">UPLOAD DOCUMENT</div><h3>Add a PDF to your library</h3></div><span className="soft-icon">↑</span></div>
        <form className="form-stack" onSubmit={upload}>
          <label className="dropzone"><input id="document-file" type="file" accept="application/pdf,.pdf" onChange={e => setFile(e.target.files?.[0] || null)}/><span className="upload-symbol">⇧</span><strong>{file ? file.name : 'Choose a PDF or drag it here'}</strong><small>PDF only · Maximum 15 MB · Text-based PDFs work best</small></label>
          <div className="form-row"><label>Document type<select value={type} onChange={e => setType(e.target.value)}>{docTypes.map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Subject (optional)<input value={subject} onChange={e => setSubject(e.target.value)} placeholder="e.g. Data Structures"/></label></div>
          <button className="button primary" disabled={busy || !file}>{busy ? 'Uploading…' : 'Upload and index PDF'}</button>
        </form>
      </section>
      <section className="panel info-panel"><div className="eyebrow">SUPPORTED MATERIAL</div><h3>Keep your workspace organised</h3><p>Use the right type so each feature can select the right source material.</p>{docTypes.map(([value,label]) => <div className="type-line" key={value}><span className="file-icon">PDF</span><div><strong>{label}</strong><small>{value === 'resume' ? 'Resume analysis' : value === 'syllabus' || value === 'notes' || value === 'previous_year_paper' ? 'Academic assistant and study planner' : 'Personal reference material'}</small></div></div>)}</section>
    </div>
    <section className="panel table-panel"><div className="panel-heading"><div><div className="eyebrow">DOCUMENT LIBRARY</div><h3>{documents.length} saved documents</h3></div><select className="filter-select" value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All types</option>{docTypes.map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></div>
      {filtered.length ? <div className="table-wrap"><table><thead><tr><th>Document</th><th>Type</th><th>Size</th><th>Pages</th><th>Status</th><th>Added</th><th/></tr></thead><tbody>{filtered.map(doc => <tr key={doc.id}><td><div className="table-file"><span className="file-icon">PDF</span><strong>{doc.original_filename}</strong></div>{doc.subject && <small className="sub-cell">{doc.subject}</small>}</td><td>{doc.document_type.replaceAll('_',' ')}</td><td>{prettySize(doc.file_size_bytes)}</td><td>{doc.page_count}</td><td><span className={`tag ${doc.status}`}>{doc.status}</span></td><td>{prettyDate(doc.created_at)}</td><td><div className="row-actions"><button className="mini-button" onClick={() => api.download(`/documents/${doc.id}/download`, doc.original_filename).catch(e => notify('error', messageOf(e)))}>↓</button><button className="mini-button danger-text" onClick={() => { if (confirm(`Delete ${doc.original_filename}?`)) void run(() => api.delete(`/documents/${doc.id}`), 'Document deleted.') }}>×</button></div></td></tr>)}</tbody></table></div> : <Empty title="No documents found" text="Upload your first PDF above. Your documents remain scoped to your development user."/>}
    </section>
  </>
}

function AcademicPage({ documents, notify }: { documents: DocumentItem[]; notify: (kind: 'success' | 'error', message: string) => void }) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [question, setQuestion] = useState('')
  const [selectedDocs, setSelectedDocs] = useState<string[]>([])
  const [sending, setSending] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const academicDocs = documents.filter(doc => ['syllabus','notes','previous_year_paper'].includes(doc.document_type) && doc.status === 'ready')
  const loadConversations = useCallback(async () => {
    try { setConversations(await api.get<Conversation[]>('/academic/conversations')) } catch (error) { notify('error', messageOf(error)) }
  }, [notify])
  useEffect(() => { void loadConversations() }, [loadConversations])
  const openConversation = async (id: string) => {
    setLoadingHistory(true)
    try { const data = await api.get<Conversation & {messages: ChatMessage[]}>(`/academic/conversations/${id}`); setConversationId(id); setMessages(data.messages) }
    catch (error) { notify('error', messageOf(error)) } finally { setLoadingHistory(false) }
  }
  const send = async (event: FormEvent) => {
    event.preventDefault()
    if (question.trim().length < 2) return
    const text = question.trim(); setQuestion(''); setSending(true)
    const optimistic: ChatMessage = { id: `temp-${Date.now()}`, role: 'user', content: text, citations: [], created_at: new Date().toISOString() }
    setMessages(old => [...old, optimistic])
    try {
      const result = await api.post<{conversation_id: string; answer: string; citations: ChatMessage['citations']}>('/academic/chat', { question: text, conversation_id: conversationId, document_ids: selectedDocs.length ? selectedDocs : null })
      setConversationId(result.conversation_id)
      setMessages(old => [...old, { id: `answer-${Date.now()}`, role: 'assistant', content: result.answer, citations: result.citations, created_at: new Date().toISOString() }])
      await loadConversations()
    } catch (error) { setMessages(old => old.filter(item => item.id !== optimistic.id)); setQuestion(text); notify('error', messageOf(error)) }
    finally { setSending(false) }
  }
  const newChat = () => { setConversationId(null); setMessages([]); setQuestion('') }
  return <>
    <PageIntro eyebrow="RETRIEVAL-AUGMENTED LEARNING" title="Academic assistant" description="Ask questions grounded in your uploaded syllabus, notes and previous-year papers. Responses cite retrieved source pages." action={<button className="button secondary" onClick={newChat}>＋ New chat</button>}/>
    <div className="chat-layout">
      <aside className="panel chat-history"><div className="panel-heading"><h3>Conversations</h3><span className="count">{conversations.length}</span></div>{conversations.map(item => <button key={item.id} className={`history-item ${conversationId === item.id ? 'selected' : ''}`} onClick={() => void openConversation(item.id)}><strong>{item.title}</strong><small>{prettyDate(item.updated_at)}</small></button>)}{!conversations.length && <p className="muted small-copy">Your saved chats will appear here.</p>}</aside>
      <section className="panel chat-panel">
        <div className="chat-doc-filter"><div><strong>Source documents</strong><small>Select specific sources, or leave empty to search all eligible academic PDFs.</small></div><select value={selectedDocs[0] || ''} onChange={e => setSelectedDocs(e.target.value ? [e.target.value] : [])}><option value="">All academic documents</option>{academicDocs.map(doc => <option key={doc.id} value={doc.id}>{doc.original_filename}</option>)}</select></div>
        <div className="chat-messages">{loadingHistory && <p className="muted">Loading conversation…</p>}{!messages.length && <div className="chat-empty"><div className="assistant-mark">✳</div><h3>What are you studying today?</h3><p>Ask a question about your uploaded course material. Answers without supporting document passages will say so instead of inventing facts.</p><div className="suggestions">{['Summarise the key concepts in my notes','Explain a difficult topic step by step','Create revision questions from my syllabus'].map(item => <button key={item} onClick={() => setQuestion(item)}>{item} ↗</button>)}</div></div>}
          {messages.map(msg => <div className={`message-row ${msg.role}`} key={msg.id}><div className="message-avatar">{msg.role === 'user' ? 'You' : 'AI'}</div><div className="message-body"><div className="message-content">{msg.content}</div>{msg.citations?.length > 0 && <div className="citation-list">{msg.citations.map(c => <div className="citation" key={`${c.document_id}-${c.source_number}`}><strong>[S{c.source_number}] {c.document_name}</strong><small>{c.page_number ? `Page ${c.page_number}` : 'Page not specified'}</small><p>{c.excerpt}</p></div>)}</div>}</div></div>)}
          {sending && <div className="typing">Assistant is checking your documents…</div>}
        </div>
        <form className="chat-composer" onSubmit={send}><textarea value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask something from your academic material…" rows={2}/><button className="button primary" disabled={sending || question.trim().length < 2}>{sending ? 'Thinking…' : 'Send ↑'}</button></form>
      </section>
    </div>
  </>
}


function rubricLabel(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase())
}

function ResumePage({ documents, analyses, busy, run }: { documents: DocumentItem[]; analyses: ResumeAnalysis[]; busy: boolean; run: (action: () => Promise<unknown>, success?: string) => Promise<void> }) {
  const [resumeId, setResumeId] = useState('')
  const [jd, setJd] = useState('')
  const [selectedAnalysis, setSelectedAnalysis] = useState<ResumeAnalysis | null>(analyses[0] || null)
  const resumes = documents.filter(doc => doc.document_type === 'resume' && doc.status === 'ready')
  useEffect(() => { if (!resumeId && resumes.length) setResumeId(resumes[0].id) }, [resumeId, resumes])
  useEffect(() => { if (!selectedAnalysis && analyses.length) setSelectedAnalysis(analyses[0]) }, [analyses, selectedAnalysis])

  const analyze = () => run(async () => {
    if (!resumeId) throw new Error('Upload a PDF with document type Resume first.')
    const result = await api.post<ResumeAnalysis>('/resumes/analyze', { document_id: resumeId, job_description: jd.trim() || null })
    setSelectedAnalysis(result)
  }, 'Resume evaluation completed.')

  const breakdown = (selectedAnalysis?.score_breakdown || {}) as Record<string, any>
  const sections = (breakdown.content_sections || {}) as Record<string, any>
  const format = (breakdown.format || {}) as Record<string, any>
  const feedback = (selectedAnalysis?.feedback || {}) as Record<string, any>
  const total = breakdown.total || {}
  const formatChecks = Array.isArray(format.checks) ? format.checks : []
  const sectionEntries = Object.entries(sections)
  const jdAlignment = feedback.job_description_alignment || selectedAnalysis?.job_description_alignment

  return <>
    <PageIntro eyebrow="TEMPLATE-BASED EVALUATION" title="Resume analyzer" description="Evaluate a resume against the bundled ATS Resume Template 2026 rubric. JD alignment is reported separately and does not change the template score."/>
    <div className="content-grid two-one">
      <section className="panel">
        <div className="eyebrow">NEW ANALYSIS</div><h3>Choose a resume</h3>
        <div className="form-stack">
          <label>Uploaded resume
            <select value={resumeId} onChange={e => setResumeId(e.target.value)}>
              <option value="">Select a resume PDF</option>
              {resumes.map(doc => <option value={doc.id} key={doc.id}>{doc.original_filename}</option>)}
            </select>
          </label>
          <label>Job description (optional)
            <textarea rows={5} value={jd} onChange={e => setJd(e.target.value)} placeholder="Paste the job description to receive a separate evidence-based alignment report."/>
          </label>
          <button className="button primary" disabled={busy || !resumeId} onClick={() => void analyze()}>{busy ? 'Analyzing…' : 'Analyze resume'}</button>
          <small className="muted">AI analysis requires a working Gemini API key in backend/.env. The backend validates evidence against extracted resume text.</small>
        </div>
      </section>
      <section className="panel info-panel">
        <div className="eyebrow">SCORING MODEL</div><h3>100-point rubric</h3>
        <div className="rubric-list">
          {([['Header',10],['Summary',8],['Education',10],['Experience',12],['Projects',18],['Technical skills',12],['Achievements',5],['Certifications',5],['PDF format',20]] as [string,number][]).map(([name,weight]) =>
            <div className="rubric-row" key={name}><span>{name}</span><strong>{weight} pts</strong></div>
          )}
        </div>
      </section>
    </div>

    {selectedAnalysis && <section className="panel analysis-result">
      <div className="analysis-score">
        <div className="score-ring" role="img" aria-label={`Resume score ${selectedAnalysis.resume_score} out of 100`} style={{ '--pct': Math.max(0, Math.min(100, Number(selectedAnalysis.resume_score) || 0)) } as CSSProperties}><strong>{selectedAnalysis.resume_score}</strong><span>/100</span></div>
        <div>
          <div className="eyebrow">LATEST EVALUATION</div>
          <h3>{selectedAnalysis.resume_filename}</h3>
          <p>{String(feedback.summary || feedback.overall_feedback || 'Review the section-level findings and formatting checks below.')}</p>
          <small className="muted">Analyzed {prettyDate(selectedAnalysis.created_at)}</small>
          {total.content_score !== undefined && <p className="muted">Content: {total.content_score}/{total.content_max_score} · PDF format: {total.format_score}/{total.format_max_score}</p>}
        </div>
      </div>

      <div className="panel-heading"><div><div className="eyebrow">RUBRIC BREAKDOWN</div><h3>Section scores</h3></div></div>
      {sectionEntries.length ? <div className="resume-section-grid">
        {sectionEntries.map(([key, section]) => {
          const criteria = Array.isArray(section.criteria) ? section.criteria : []
          const score = Number(section.score || 0)
          const max = Number(section.max_score || 0)
          const pct = max ? Math.max(0, Math.min(100, score / max * 100)) : 0
          return <article className="resume-section-card" key={key}>
            <div className="resume-section-head">
              <div><h4>{section.label || rubricLabel(key)}</h4><span className={`resume-status ${section.status || 'partial'}`}>{rubricLabel(section.status || 'not rated')}</span></div>
              <strong>{score.toFixed(1).replace(/\.0$/, '')}<small> / {max}</small></strong>
            </div>
            <div className="resume-score-track"><span style={{width: `${pct}%`}}/></div>
            <div className="resume-criteria-list">
              {criteria.map((item: any) => {
                const complete = Number(item.score) >= Number(item.max_score)
                const missing = Number(item.score) === 0
                return <div className="resume-criterion" key={item.id}>
                  <div className="resume-criterion-top">
                    <strong>{item.label || rubricLabel(item.id || '')}</strong>
                    <span className={complete ? 'criterion-points complete' : missing ? 'criterion-points missing' : 'criterion-points'}>{item.score}/{item.max_score}</span>
                  </div>
                  <p>{item.finding || 'No finding was returned.'}</p>
                  {item.evidence && <blockquote className="resume-evidence"><span>{item.evidence_source === 'section_excerpt' ? 'Relevant resume excerpt' : 'Evidence'}</span>{item.evidence}</blockquote>}
                  {item.suggestion && <p className="resume-suggestion"><b>Improve:</b> {item.suggestion}</p>}
                </div>
              })}
            </div>
          </article>
        })}
      </div> : <p className="muted">No section-level criteria were returned for this analysis.</p>}

      <div className="resume-lower-grid">
        <section className="resume-subpanel">
          <div className="eyebrow">PDF LAYOUT</div><h3>Format checks · {format.score ?? 0}/{format.max_score ?? 20}</h3>
          {formatChecks.length ? formatChecks.map((check: any) => <div className="format-check" key={check.id}>
            <div><strong>{rubricLabel(check.id || '')}</strong><span>{check.score}/{check.max_score}</span></div>
            <p>{check.finding}</p>
            {check.evidence && <small>{check.evidence}</small>}
            {check.suggestion && check.score < check.max_score && <p className="resume-suggestion"><b>Improve:</b> {check.suggestion}</p>}
          </div>) : <p className="muted">No format checks returned.</p>}
          {Array.isArray(format.limitations) && format.limitations.length > 0 && <ul className="resume-limitations">{format.limitations.map((item: string, index: number) => <li key={index}>{item}</li>)}</ul>}
        </section>

        <section className="resume-subpanel">
          <div className="eyebrow">ACTION PLAN</div><h3>Priority improvements</h3>
          {Array.isArray(feedback.recommended_changes) && feedback.recommended_changes.length > 0
            ? <ol className="resume-priority-list">{feedback.recommended_changes.slice(0, 12).map((item: any, index: number) => <li key={item.criterion_id || index}><strong>{item.section || 'Resume'}</strong><p>{item.suggestion || 'Review this criterion.'}</p><small>{item.score}/{item.max_score} points</small></li>)}</ol>
            : Array.isArray(feedback.priority_changes) && feedback.priority_changes.length > 0
              ? <ul className="resume-priority-list">{feedback.priority_changes.map((item: string, index: number) => <li key={index}>{item}</li>)}</ul>
              : <p className="muted">No priority changes were returned.</p>}
        </section>
      </div>

      {Array.isArray(feedback.general_strengths) && feedback.general_strengths.length > 0 && <section className="resume-subpanel">
        <div className="eyebrow">VERIFIED STRENGTHS</div><h3>What already matches the template</h3>
        <ul className="resume-strength-list">{feedback.general_strengths.map((item: string, index: number) => <li key={index}>{item}</li>)}</ul>
      </section>}

      {jdAlignment && <section className="resume-subpanel jd-result">
        <div className="eyebrow">SEPARATE FROM TEMPLATE SCORE</div><h3>Job description alignment</h3>
        {jdAlignment.available === false
          ? <p className="muted">No job description was provided. Alignment was not calculated.</p>
          : <>
              {jdAlignment.alignment_score !== undefined && jdAlignment.alignment_score !== null && <p className="jd-score">{jdAlignment.alignment_score}% evidence coverage</p>}
              {jdAlignment.summary && <p>{jdAlignment.summary}</p>}
              {Array.isArray(jdAlignment.requirements) && <div className="jd-requirements">
                {jdAlignment.requirements.map((item: any, index: number) => <div className="format-check" key={index}>
                  <div><strong>{item.requirement}</strong><span className={`resume-status ${item.status}`}>{rubricLabel(item.status || '')}</span></div>
                  {item.evidence && <blockquote className="resume-evidence"><span>Resume evidence</span>{item.evidence}</blockquote>}
                  {item.reason && <p>{item.reason}</p>}
                  {item.suggestion && <p className="resume-suggestion"><b>Next step:</b> {item.suggestion}</p>}
                </div>)}
              </div>}
              <small className="muted">{jdAlignment.methodology || 'AI-assisted evidence comparison; missing resume evidence does not prove the candidate lacks a skill.'}</small>
            </>
        }
      </section>}

      <details className="resume-technical-details">
        <summary>Scoring methodology and technical details</summary>
        <p>{feedback.scoring_method || breakdown.scoring_note || 'Scores are calculated using the fixed template-specific rubric.'}</p>
        <p>{feedback.disclaimer || 'This is not an employer ATS prediction.'}</p>
        <pre>{JSON.stringify({rubric: breakdown.rubric_name, total: breakdown.total, scoring_note: breakdown.scoring_note}, null, 2)}</pre>
      </details>
    </section>}

    <section className="panel">
      <div className="panel-heading"><div><div className="eyebrow">ANALYSIS HISTORY</div><h3>Previous evaluations</h3></div><span className="count">{analyses.length}</span></div>
      {analyses.length ? <div className="history-grid">{analyses.map(item =>
        <button className={`analysis-history-card ${selectedAnalysis?.id === item.id ? 'selected' : ''}`} key={item.id} onClick={() => setSelectedAnalysis(item)}>
          <strong>{item.resume_filename}</strong><span className="history-score">{item.resume_score}<small>/100</small></span><small>{prettyDate(item.created_at)}</small>
        </button>
      )}</div> : <Empty title="No evaluations yet" text="Upload a resume PDF, then run your first analysis. If Gemini is not configured, the backend will return an AI-provider error."/>}
    </section>
  </>
}

function StudyPlannerPage({ plans, documents, busy, run }: { plans: StudyPlan[]; documents: DocumentItem[]; busy: boolean; run: (action: () => Promise<unknown>, success?: string) => Promise<void> }) {
  const [title, setTitle] = useState('Exam preparation plan')
  const [subject, setSubject] = useState('')
  const [examDate, setExamDate] = useState('')
  const [minutes, setMinutes] = useState(120)
  const [topicText, setTopicText] = useState('')
  const [sourceId, setSourceId] = useState('')
  const [weekday, setWeekday] = useState<number[]>([0,1,2,3,4,5])
  const [expanded, setExpanded] = useState<string | null>(plans[0]?.id || null)
  const academicDocs = documents.filter(doc => ['syllabus','notes','previous_year_paper'].includes(doc.document_type) && doc.status === 'ready')
  const create = () => run(async () => {
    const topics = topicText.split('\n').map(s => s.trim()).filter(Boolean).map(name => ({name, estimated_minutes: 60, preparation_status: 'not_started'}))
    if (!topics.length && !sourceId) throw new Error('Add at least one topic or choose a syllabus document.')
    const payload = { title, subject, exam_date: examDate, available_minutes_per_day: minutes, study_weekdays: weekday, topics, source_document_ids: sourceId ? [sourceId] : [] }
    const result = await api.post<StudyPlan>('/study-plans', payload)
    setExpanded(result.id); setTitle('Exam preparation plan'); setSubject(''); setExamDate(''); setTopicText(''); setSourceId('')
  }, 'Study plan created.')
  const updateTask = (plan: StudyPlan, taskId: string, status: string) => run(async () => {
    await api.patch(`/study-plans/${plan.id}/tasks/${taskId}`, {status, notes: null})
  }, 'Task status updated.')
  return <>
    <PageIntro eyebrow="DETERMINISTIC STUDY SCHEDULING" title="Study planner" description="Create a realistic daily schedule from topics or an uploaded syllabus. The backend distributes work across your available weekdays and flags unscheduled workload."/>
    <section className="panel"><div className="panel-heading"><div><div className="eyebrow">CREATE PLAN</div><h3>Plan your next exam</h3></div></div>
      <div className="form-grid"><label>Plan title<input value={title} onChange={e => setTitle(e.target.value)}/></label><label>Subject<input value={subject} onChange={e => setSubject(e.target.value)} placeholder="e.g. Operating Systems"/></label><label>Exam date<input type="date" min={today} value={examDate} onChange={e => setExamDate(e.target.value)}/></label><label>Available minutes per day<input type="number" min={15} max={720} value={minutes} onChange={e => setMinutes(Number(e.target.value))}/></label></div>
      <label className="block-label">Topics (one per line, 60-minute estimate each)<textarea rows={4} value={topicText} onChange={e => setTopicText(e.target.value)} placeholder={'Process scheduling\nMemory management\nDeadlocks'}/></label>
      <label className="block-label">Or extract topics from an uploaded academic PDF<select value={sourceId} onChange={e => setSourceId(e.target.value)}><option value="">Do not use a document</option>{academicDocs.map(doc => <option key={doc.id} value={doc.id}>{doc.original_filename}</option>)}</select></label>
      <div className="weekday-picker"><strong>Study days</strong>{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map((day,index) => <label key={day} className={weekday.includes(index) ? 'checked' : ''}><input type="checkbox" checked={weekday.includes(index)} onChange={e => setWeekday(old => e.target.checked ? [...old,index] : old.filter(v => v !== index))}/>{day}</label>)}</div>
      <button className="button primary" disabled={busy || !subject.trim() || !examDate || weekday.length === 0} onClick={() => void create()}>{busy ? 'Creating…' : 'Generate study schedule'}</button>
    </section>
    <section className="panel"><div className="panel-heading"><div><div className="eyebrow">YOUR SCHEDULES</div><h3>{plans.length} study plans</h3></div></div>{plans.map(plan => { const done = plan.tasks.filter(task => task.status === 'completed').length; const total = plan.tasks.length; const open = expanded === plan.id; return <div className="plan-card" key={plan.id}><button className="plan-card-head" onClick={() => setExpanded(open ? null : plan.id)}><div><strong>{plan.title}</strong><small>{plan.subject} · Exam {prettyDate(plan.exam_date)}</small></div><div className="plan-progress"><strong>{done}/{total}</strong><small>completed</small></div><span>{open ? '−' : '+'}</span></button><div className="progress-track"><span style={{width: `${total ? done/total*100 : 0}%`}}/></div>{plan.overloaded && <div className="warning-inline">Schedule overloaded: {plan.unscheduled_minutes} minutes could not be scheduled before the exam.</div>}{open && <div className="task-list">{plan.tasks.map(task => <div className="task-row" key={task.id}><label className="task-check"><input type="checkbox" checked={task.status === 'completed'} onChange={e => void updateTask(plan, task.id, e.target.checked ? 'completed' : 'pending')}/><span><strong>{task.title}</strong><small>{prettyDate(task.scheduled_date)} · {task.estimated_minutes} min · {task.topic}</small></span></label><span className={`tag ${task.status}`}>{task.status.replace('_',' ')}</span></div>)}{!plan.tasks.length && <p className="muted">No tasks were generated.</p>}<button className="text-button danger-text" onClick={() => {if (confirm('Delete this study plan and its tasks?')) void run(() => api.delete(`/study-plans/${plan.id}`), 'Study plan deleted.')}}>Delete plan</button></div>}</div>})}{!plans.length && <Empty title="No study plans yet" text="Create a plan above. Use topics for deterministic scheduling or a syllabus PDF for AI topic extraction (Gemini required)."/>}</section>
  </>
}

const asList = (value: unknown): string[] => Array.isArray(value) ? value.map(item => String(item).trim()).filter(Boolean) : []
const asText = (value: unknown): string => typeof value === 'string' ? value.trim() : ''

function BulletBlock({ title, items, tone }: { title: string; items: string[]; tone: 'good' | 'warn' | 'info' }) {
  if (!items.length) return null
  return <div className={`eval-block ${tone}`}><h5>{title}</h5><ul>{items.map((item, index) => <li key={index}>{item}</li>)}</ul></div>
}

function EvaluationView({ evaluation }: { evaluation: Record<string, unknown> }) {
  const score = Number(evaluation.score)
  const hasScore = evaluation.score !== undefined && evaluation.score !== null && Number.isFinite(score)
  const tone = !hasScore ? 'mid' : score >= 7 ? 'good' : score >= 4 ? 'mid' : 'low'
  const feedback = asText(evaluation.feedback)
  const ideal = asText(evaluation.ideal_answer)
  return <div className="eval-view">
    <div className="eval-head">
      {hasScore && <span className={`eval-score ${tone}`}>{score}<small>/10</small></span>}
      <strong>Answer evaluation</strong>
    </div>
    {feedback && <p className="eval-feedback">{feedback}</p>}
    <BulletBlock title="Strengths" items={asList(evaluation.strengths)} tone="good"/>
    <BulletBlock title="Missing concepts" items={asList(evaluation.missing_concepts)} tone="warn"/>
    {ideal && <details className="eval-ideal"><summary>Show ideal answer</summary><p>{ideal}</p></details>}
  </div>
}

function SummaryView({ summary }: { summary: Record<string, unknown> }) {
  const average = Number(summary.average_score)
  const hasAverage = summary.average_score !== undefined && summary.average_score !== null && Number.isFinite(average)
  const overall = asText(summary.overall_feedback)
  const tone = !hasAverage ? 'mid' : average >= 7 ? 'good' : average >= 4 ? 'mid' : 'low'
  return <div className="eval-view summary">
    <div className="eval-head">
      {hasAverage && <span className={`eval-score ${tone}`}>{Math.round(average * 10) / 10}<small>/10</small></span>}
      <strong>Interview summary</strong>
    </div>
    {overall && <p className="eval-feedback">{overall}</p>}
    <BulletBlock title="Strengths" items={asList(summary.strengths)} tone="good"/>
    <BulletBlock title="Areas to improve" items={asList(summary.improvement_areas)} tone="warn"/>
    <BulletBlock title="Next steps" items={asList(summary.next_steps)} tone="info"/>
  </div>
}

function InterviewPage({ sessions, busy, run }: { sessions: InterviewSession[]; busy: boolean; run: (action: () => Promise<unknown>, success?: string) => Promise<void> }) {
  const [role, setRole] = useState('Python Backend Intern')
  const [skills, setSkills] = useState('Python, FastAPI, SQL')
  const [jd, setJd] = useState('')
  const [active, setActive] = useState<(InterviewSession & {turns?: InterviewTurn[]}) | null>(null)
  const [answer, setAnswer] = useState('')
  const start = () => run(async () => { const result = await api.post<InterviewSession & {turns: InterviewTurn[]}>('/interviews', {role, job_description: jd || null, skill_focus: skills.split(',').map(s => s.trim()).filter(Boolean)}); setActive(result) }, 'Mock interview started.')
  const load = async (id: string) => { try { setActive(await api.get<InterviewSession & {turns: InterviewTurn[]}>(`/interviews/${id}`)) } catch (e) { window.alert(messageOf(e)) } }
  const submit = () => run(async () => { if (!active || !answer.trim()) throw new Error('Write an answer first.'); await api.post<{evaluation: Record<string, unknown>; next_question: string}>(`/interviews/${active.id}/answers`, {answer}); setAnswer(''); setActive(await api.get<InterviewSession & {turns: InterviewTurn[]}>(`/interviews/${active.id}`)) }, 'Answer evaluated.')
  const end = () => run(async () => { if (!active) return; const result = await api.post<InterviewSession & {turns: InterviewTurn[]}>(`/interviews/${active.id}/end`, {}); setActive(result) }, 'Interview ended and summary saved.')
  return <>
    <PageIntro eyebrow="AI MOCK INTERVIEWS" title="Interview preparation" description="Practise role-specific technical questions. Submit answers to receive a score, missing concepts, concrete feedback and a follow-up question."/>
    <div className="content-grid two-one">
      <section className="panel"><div className="eyebrow">START A SESSION</div><h3>Configure your interview</h3><div className="form-stack"><label>Target role<input value={role} onChange={e => setRole(e.target.value)}/></label><label>Focus skills (comma separated)<input value={skills} onChange={e => setSkills(e.target.value)}/></label><label>Job description (optional)<textarea rows={4} value={jd} onChange={e => setJd(e.target.value)} placeholder="Paste the job description."/></label><button className="button primary" disabled={busy || !role.trim()} onClick={() => void start()}>{busy ? 'Starting…' : 'Start mock interview'}</button><small className="muted">Requires Gemini configured on the backend.</small></div></section>
      <section className="panel"><div className="eyebrow">PAST SESSIONS</div><h3>Interview history</h3>{sessions.map(item => <button className={`history-item ${active?.id === item.id ? 'selected' : ''}`} key={item.id} onClick={() => void load(item.id)}><strong>{item.role}</strong><small>{prettyDate(item.created_at)} · {item.status}</small></button>)}{!sessions.length && <p className="muted small-copy">Your interview sessions will appear here.</p>}</section>
    </div>
    {active && <section className="panel interview-room"><div className="panel-heading"><div><div className="eyebrow">LIVE SESSION</div><h3>{active.role}</h3></div><span className={`tag ${active.status}`}>{active.status}</span></div><div className="transcript">{active.turns?.map(turn => <div className={`transcript-turn ${turn.role}`} key={turn.id}><small>{turn.role === 'interviewer' ? 'INTERVIEWER' : 'YOUR ANSWER'}</small><p>{turn.content}</p>{turn.role === 'candidate' && turn.evaluation && Object.keys(turn.evaluation).length > 0 && <EvaluationView evaluation={turn.evaluation}/>}</div>)}</div>{active.status === 'active' && <><div className="answer-box"><label>Your answer<textarea rows={5} value={answer} onChange={e => setAnswer(e.target.value)} placeholder="Explain your approach, reasoning and trade-offs…"/></label><button className="button primary" disabled={busy || !answer.trim()} onClick={() => void submit()}>Submit answer</button></div><button className="button secondary" disabled={busy} onClick={() => void end()}>End interview and generate summary</button></>}{active.status === 'ended' && active.summary && Object.keys(active.summary).length > 0 && <SummaryView summary={active.summary}/>}</section>}
  </>
}

function ProgressPage({ projects, dsa, applications, busy, run }: { projects: Project[]; dsa: DSARecord[]; applications: Application[]; busy: boolean; run: (action: () => Promise<unknown>, success?: string) => Promise<void> }) {
  const [tab, setTab] = useState<'Projects' | 'DSA' | 'Applications'>('Projects')
  const [projectName, setProjectName] = useState('')
  const [projectStatus, setProjectStatus] = useState('in_progress')
  const [repo, setRepo] = useState('')
  const [problem, setProblem] = useState('')
  const [topic, setTopic] = useState('')
  const [difficulty, setDifficulty] = useState('medium')
  const [dsaStatus, setDsaStatus] = useState('solved')
  const [company, setCompany] = useState('')
  const [role, setRole] = useState('')
  const [appStatus, setAppStatus] = useState('applied')
  const addProject = () => run(async () => { await api.post('/progress/projects', {name: projectName, status: projectStatus, repository_url: repo || null, skills: [], milestones: []}); setProjectName(''); setRepo('') }, 'Project added.')
  const addDsa = () => run(async () => { await api.post('/progress/dsa', {problem_name: problem, topic, difficulty, status: dsaStatus}); setProblem(''); setTopic('') }, 'DSA record added.')
  const addApplication = () => run(async () => { await api.post('/applications', {company, role, status: appStatus}); setCompany(''); setRole('') }, 'Application added.')
  return <>
    <PageIntro eyebrow="CAREER EXECUTION" title="Progress tracker" description="Track projects, DSA practice and job applications. Records are saved against your current development user."/>
    <div className="tabs">{(['Projects','DSA','Applications'] as const).map(item => <button key={item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)}>{item} <span>{item === 'Projects' ? projects.length : item === 'DSA' ? dsa.length : applications.length}</span></button>)}</div>
    {tab === 'Projects' && <section className="panel"><h3>Add a project</h3><div className="form-grid"><label>Project name<input value={projectName} onChange={e => setProjectName(e.target.value)} placeholder="Project name"/></label><label>Status<select value={projectStatus} onChange={e => setProjectStatus(e.target.value)}><option value="planned">Planned</option><option value="in_progress">In progress</option><option value="completed">Completed</option><option value="on_hold">On hold</option></select></label><label className="span-two">Repository URL (optional)<input value={repo} onChange={e => setRepo(e.target.value)} placeholder="https://github.com/…"/></label></div><button className="button primary" disabled={busy || !projectName.trim()} onClick={() => void addProject()}>Add project</button><div className="record-list">{projects.map(item => <div className="record-row" key={item.id}><div><strong>{item.name}</strong><small>{item.description || 'No description'} {item.repository_url && <>· <a href={item.repository_url} target="_blank" rel="noreferrer">Repository ↗</a></>}</small></div><span className={`tag ${item.status}`}>{item.status.replace('_',' ')}</span><button className="mini-button danger-text" onClick={() => {if(confirm('Delete this project?')) void run(() => api.delete(`/progress/projects/${item.id}`), 'Project deleted.')}}>×</button></div>)}{!projects.length && <Empty title="No projects tracked" text="Add your academic and personal projects."/>}</div></section>}
    {tab === 'DSA' && <section className="panel"><h3>Record a solved or attempted problem</h3><div className="form-grid"><label>Problem name<input value={problem} onChange={e => setProblem(e.target.value)} placeholder="Two Sum"/></label><label>Topic<input value={topic} onChange={e => setTopic(e.target.value)} placeholder="Arrays"/></label><label>Difficulty<select value={difficulty} onChange={e => setDifficulty(e.target.value)}><option>easy</option><option>medium</option><option>hard</option><option>unknown</option></select></label><label>Status<select value={dsaStatus} onChange={e => setDsaStatus(e.target.value)}><option value="solved">Solved</option><option value="attempted">Attempted</option><option value="revisit">Revisit</option></select></label></div><button className="button primary" disabled={busy || !problem.trim() || !topic.trim()} onClick={() => void addDsa()}>Save DSA record</button><div className="record-list">{dsa.map(item => <div className="record-row" key={item.id}><div><strong>{item.problem_name}</strong><small>{item.topic} · {item.difficulty} · {prettyDate(item.created_at)}</small></div><span className={`tag ${item.status}`}>{item.status}</span><button className="mini-button danger-text" onClick={() => {if(confirm('Delete this DSA record?')) void run(() => api.delete(`/progress/dsa/${item.id}`), 'DSA record deleted.')}}>×</button></div>)}{!dsa.length && <Empty title="No DSA activity yet" text="Start recording your problem-solving practice."/>}</div></section>}
    {tab === 'Applications' && <section className="panel"><h3>Track an application</h3><div className="form-grid"><label>Company<input value={company} onChange={e => setCompany(e.target.value)} placeholder="Company name"/></label><label>Role<input value={role} onChange={e => setRole(e.target.value)} placeholder="Software Engineer Intern"/></label><label>Status<select value={appStatus} onChange={e => setAppStatus(e.target.value)}>{['saved','applied','screening','interview','offer','rejected','withdrawn'].map(v => <option key={v}>{v}</option>)}</select></label></div><button className="button primary" disabled={busy || !company.trim() || !role.trim()} onClick={() => void addApplication()}>Add application</button><div className="record-list">{applications.map(item => <div className="record-row" key={item.id}><div><strong>{item.company} · {item.role}</strong><small>{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">Job link ↗</a>} {item.next_step_date && `· Follow up ${prettyDate(item.next_step_date)}`}</small></div><select className="status-select" value={item.status} onChange={e => void run(() => api.patch(`/applications/${item.id}`, {status: e.target.value}), 'Application status updated.')}>{['saved','applied','screening','interview','offer','rejected','withdrawn'].map(v => <option key={v}>{v}</option>)}</select><button className="mini-button danger-text" onClick={() => {if(confirm('Delete this application?')) void run(() => api.delete(`/applications/${item.id}`), 'Application deleted.')}}>×</button></div>)}{!applications.length && <Empty title="No applications tracked" text="Add applications manually; this project does not scrape job sites or recommend jobs automatically."/>}</div></section>}
  </>
}

function AnalyticsPage({ analytics }: { analytics: Analytics }) {
  const max = Math.max(1, ...Object.values(analytics.applications_by_status))
  return <>
    <PageIntro eyebrow="YOUR ACTIVITY AT A GLANCE" title="Analytics" description="All metrics are aggregated by the backend from your saved records. No demo numbers are inserted."/>
    <div className="stats-grid">
      <StatCard label="Documents" value={analytics.documents_total} note="PDF library" icon="▤"/>
      <StatCard label="Resume analyses" value={analytics.resume_analyses_total} note="Saved evaluations" icon="▧"/>
      <StatCard label="Study plans" value={analytics.study_plans_total} note={`${analytics.study_tasks_pending} pending tasks`} icon="▦"/>
      <StatCard label="Mock interviews" value={analytics.interview_sessions_total} note="All sessions" icon="◉"/>
      <StatCard label="Projects completed" value={`${analytics.projects_completed}/${analytics.projects_total}`} note="Tracked projects" icon="⌘"/>
      <StatCard label="DSA solved" value={analytics.dsa_problems_solved} note={`${analytics.dsa_problems_attempted} attempted`} icon="⌁"/>
    </div>
    <div className="content-grid two-one"><section className="panel"><div className="eyebrow">APPLICATION PIPELINE</div><h3>Application status</h3>{Object.entries(analytics.applications_by_status).length ? Object.entries(analytics.applications_by_status).map(([status,count]) => <div className="bar-row" key={status}><span>{status}</span><div className="bar-track"><i style={{width: `${count/max*100}%`}}/></div><strong>{count}</strong></div>) : <Empty title="No application data" text="Add applications in Progress Tracker to populate this chart."/>}</section><section className="panel"><div className="eyebrow">STUDY CONSISTENCY</div><h3>Task completion</h3><div className="big-percent">{analytics.study_tasks_completed + analytics.study_tasks_pending ? Math.round(analytics.study_tasks_completed/(analytics.study_tasks_completed+analytics.study_tasks_pending)*100) : 0}<small>%</small></div><div className="progress-track large"><span style={{width: `${analytics.study_tasks_completed + analytics.study_tasks_pending ? analytics.study_tasks_completed/(analytics.study_tasks_completed+analytics.study_tasks_pending)*100 : 0}%`}}/></div><div className="split-stats"><span><b>{analytics.study_tasks_completed}</b> Completed</span><span><b>{analytics.study_tasks_pending}</b> Pending</span></div></section></div>
    <section className="panel"><div className="eyebrow">UPCOMING</div><h3>Deadlines and follow-ups</h3>{analytics.upcoming_deadlines.map(item => <div className="deadline-row" key={item.id}><span className="deadline-mark">◷</span><div><strong>{item.title}</strong><small>{item.kind.replaceAll('_',' ')}</small></div><time>{prettyDate(item.date)}</time></div>)}{!analytics.upcoming_deadlines.length && <Empty title="No upcoming dates" text="Add study plans or application follow-up dates."/>}</section>
  </>
}

function ProfilePage({ profile, busy, run }: { profile: UserProfile | null; busy: boolean; run: (action: () => Promise<unknown>, success?: string) => Promise<void> }) {
  const [name, setName] = useState(profile?.full_name || '')
  const [department, setDepartment] = useState(profile?.department || '')
  const [year, setYear] = useState(profile?.year_of_study?.toString() || '')
  const [skills, setSkills] = useState(profile?.skills.join(', ') || '')
  const [interests, setInterests] = useState(profile?.interests.join(', ') || '')
  const [goals, setGoals] = useState(profile?.career_goals.join(', ') || '')
  useEffect(() => { setName(profile?.full_name || ''); setDepartment(profile?.department || ''); setYear(profile?.year_of_study?.toString() || ''); setSkills(profile?.skills.join(', ') || ''); setInterests(profile?.interests.join(', ') || ''); setGoals(profile?.career_goals.join(', ') || '') }, [profile])
  const save = (event: FormEvent) => { event.preventDefault(); void run(() => api.patch('/users/me', {full_name: name || null, department: department || null, year_of_study: year ? Number(year) : null, skills: skills.split(',').map(v=>v.trim()).filter(Boolean), interests: interests.split(',').map(v=>v.trim()).filter(Boolean), career_goals: goals.split(',').map(v=>v.trim()).filter(Boolean)}), 'Profile updated.') }
  return <>
    <PageIntro eyebrow="YOUR ACCOUNT" title="Profile" description="Manage the student profile associated with your current development identity."/>
    <section className="panel profile-panel"><div className="profile-header"><span className="avatar profile-avatar">{(name || profile?.email || 'S').slice(0,1).toUpperCase()}</span><div><h3>{name || 'Student profile'}</h3><p>{profile?.email || 'No email available'} · Development authentication</p></div></div><form className="form-grid" onSubmit={save}><label>Full name<input value={name} onChange={e => setName(e.target.value)} maxLength={160}/></label><label>Email (managed by authentication)<input value={profile?.email || ''} disabled/></label><label>Department<input value={department} onChange={e => setDepartment(e.target.value)} placeholder="Computer Science & Engineering"/></label><label>Year of study<input type="number" min="1" max="8" value={year} onChange={e => setYear(e.target.value)}/></label><label className="span-two">Skills (comma separated)<input value={skills} onChange={e => setSkills(e.target.value)} placeholder="Python, FastAPI, PostgreSQL"/></label><label className="span-two">Interests (comma separated)<input value={interests} onChange={e => setInterests(e.target.value)} placeholder="Generative AI, backend engineering"/></label><label className="span-two">Career goals (comma separated)<textarea rows={3} value={goals} onChange={e => setGoals(e.target.value)}/></label><div className="span-two"><button className="button primary" disabled={busy}>Save profile</button></div></form></section>
  </>
}

export default App
