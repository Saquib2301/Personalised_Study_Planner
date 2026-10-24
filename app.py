"""
Personalized AI Study Planner - Streamlit Interactive Web Application.
Target Assessment Date: 24 October 2026.
Features:
- Multi-factor AI topic prioritization with explainable reasoning
- Schedule generator with Concept Study, Practice Tasks, and Revision
- Real-time Availability Compliance verification check
- Interactive Progress Update and Dynamic Plan Regeneration with diff reporting
- At least three pre-loaded sample student profiles (Alex, Maya, Sam)
"""

from copy import deepcopy
from datetime import date, datetime
import pandas as pd
import streamlit as st

from models import SessionType, StudentProfile, TopicAssessment
from planner_service import StudyPlannerService
from sample_data import get_default_curriculum, get_sample_students
from verifier import AvailabilityVerifier

st.set_page_config(
    page_title="AI Personalized Study Planner",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for modern aesthetic
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(120deg, #2563eb, #7c3aed, #db2777);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #4b5563;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .audit-pass {
        background-color: #ecfdf5;
        border: 1px solid #10b981;
        border-radius: 8px;
        padding: 12px 16px;
        color: #065f46;
        font-weight: 600;
    }
    .session-badge-study {
        background-color: #dbeafe;
        color: #1e40af;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .session-badge-practice {
        background-color: #dcfce7;
        color: #166534;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .session-badge-revision {
        background-color: #f3e8ff;
        color: #6b21a8;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .priority-card {
        background: #ffffff;
        border-left: 5px solid #3b82f6;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_base_data():
    curriculum = get_default_curriculum()
    students = get_sample_students()
    service = StudyPlannerService(curriculum)
    return curriculum, students, service


curriculum, sample_students, service = load_base_data()

# Initialize session state
if "active_student" not in st.session_state:
    st.session_state.active_student = deepcopy(sample_students["alex_rivera"])
if "current_plan" not in st.session_state:
    plan, audit = service.generate_initial_plan(st.session_state.active_student)
    st.session_state.current_plan = plan
    st.session_state.current_audit = audit
if "previous_plan" not in st.session_state:
    st.session_state.previous_plan = None
if "adaptation_log" not in st.session_state:
    st.session_state.adaptation_log = ""

# Sidebar Configuration
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/graduation-cap.png", width=64)
    st.title("Study Planner")
    st.caption("AI-driven scheduling with guaranteed availability limits")

    st.subheader("1. Select Student Profile")
    profile_options = {
        "alex_rivera": "Alex Rivera (High Hours • Beginner Gaps)",
        "maya_chen": "Maya Chen (Strict 10.5h • Working Pro)",
        "sam_taylor": "Sam Taylor (17.5h • Uneven Blindspots)",
        "custom": "+ Create Custom Profile"
    }

    selected_profile_key = st.selectbox(
        "Choose Profile",
        options=list(profile_options.keys()),
        format_func=lambda k: profile_options[k]
    )

    if st.button("Load Profile Baseline", type="secondary"):
        if selected_profile_key != "custom":
            st.session_state.active_student = deepcopy(sample_students[selected_profile_key])
        else:
            # Create a blank/custom student
            custom_assessments = {
                t_id: TopicAssessment(topic_id=t_id, mastery_level=0.5)
                for t_id in curriculum
            }
            st.session_state.active_student = StudentProfile(
                id="custom_user",
                name="Custom Learner",
                persona_tagline="Custom Student Configuration",
                daily_availability={d: 2.0 for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]},
                assessments=custom_assessments,
                assessment_date=date(2026, 10, 24)
            )
        plan, audit = service.generate_initial_plan(st.session_state.active_student)
        st.session_state.current_plan = plan
        st.session_state.current_audit = audit
        st.session_state.previous_plan = None
        st.session_state.adaptation_log = ""
        st.rerun()

    st.markdown("---")
    st.subheader("2. Assessment Target")
    assessment_date_input = st.date_input(
        "Assessment Deadline",
        value=date(2026, 10, 24),
        help="Target date for the programming assessment"
    )

    current_date_input = st.date_input(
        "Current Start Date",
        value=date(2026, 10, 17),
        help="Start date for the 7-day study week"
    )

    days_left = max(0, (assessment_date_input - current_date_input).days)
    st.metric("Days Remaining", f"{days_left} Days")

    st.markdown("---")
    st.subheader("3. Stated Daily Availability (Hours)")
    days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    new_daily_avail = {}
    for d in days_list:
        current_val = float(st.session_state.active_student.daily_availability.get(d, 2.0))
        new_daily_avail[d] = st.slider(f"{d}", min_value=0.0, max_value=8.0, value=current_val, step=0.5)

    st.session_state.active_student.daily_availability = new_daily_avail
    total_avail = sum(new_daily_avail.values())
    st.info(f"Total Available: **{total_avail:.1f} hours/week**")

    if st.button("Re-compute Plan with Current Sliders", type="primary"):
        plan, audit = service.generate_initial_plan(
            student=st.session_state.active_student,
            start_date=current_date_input,
            assessment_date=assessment_date_input
        )
        st.session_state.current_plan = plan
        st.session_state.current_audit = audit
        st.rerun()


# Main View Header
active_student = st.session_state.active_student
current_plan = st.session_state.current_plan
current_audit = st.session_state.current_audit

st.markdown('<div class="main-header">Personalized AI Study Planner</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="sub-header">Student: <strong>{active_student.name}</strong> • '
    f'<em>{active_student.persona_tagline}</em> • '
    f'Target Assessment: <strong>{current_plan.assessment_date}</strong> ({current_plan.days_until_assessment} days remaining)</div>',
    unsafe_allow_html=True
)

# Top KPI Summary Cards
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric("Stated Weekly Availability", f"{current_audit['total_available_hours']:.1f} hrs")
with kpi2:
    st.metric("Total Scheduled Study Time", f"{current_audit['total_scheduled_hours']:.1f} hrs")
with kpi3:
    st.metric("Flexibility Reserve Buffer", f"{current_audit['total_buffer_hours']:.1f} hrs")
with kpi4:
    if current_audit["all_passed"]:
        st.markdown(
            '<div class="audit-pass">✅ CONSTRAINT CHECK: PASS<br><small>Scheduled study time &le; stated availability</small></div>',
            unsafe_allow_html=True
        )
    else:
        st.error("CONSTRAINT VIOLATION")

st.markdown("<br>", unsafe_allow_html=True)

# Tabs Navigation
tab_priorities, tab_schedule, tab_compliance, tab_tracker = st.tabs([
    "🎯 AI Prioritization & Explanations",
    "📅 Weekly Schedule (Study/Practice/Rev)",
    "🛡️ Availability Compliance Check",
    "🔄 Progress Tracker & Dynamic Re-plan"
])

# -------------------------------------------------------------
# TAB 1: AI Topic Prioritization & Explainable Reasoning
# -------------------------------------------------------------
with tab_priorities:
    st.markdown("### Topic Prioritization & Explainability")
    st.markdown(
        "The AI ranks topics using a multi-factor formula: "
        "$\\text{Priority} = f(\\text{Knowledge Gap}, \\text{Exam Weight}, \\text{Difficulty}, \\text{Prerequisite Impact}, \\text{Time Remaining})$. "
        "Below is each topic's transparent reasoning and recommended weekly study split."
    )

    for p in current_plan.priorities:
        with st.container():
            col_rank, col_info, col_split = st.columns([1, 4, 3])
            
            with col_rank:
                st.markdown(f"### #{p.rank}")
                st.caption(f"Score: **{p.normalized_score}/10**")
                st.metric("Allocated", f"{p.recommended_hours:.1f} h")

            with col_info:
                st.markdown(f"**{p.topic.name}** &nbsp; `{p.topic.category}`")
                st.progress(
                    float(p.mastery_level),
                    text=f"Mastery: {int(p.mastery_level*100)}% | Exam Weight: {p.topic.exam_weight}/10 | Difficulty: {p.topic.difficulty}/5"
                )
                st.markdown(f"💡 **AI Rationale**: {p.rationale}")
                if "Warning" in p.prerequisite_status:
                    st.warning(p.prerequisite_status)

            with col_split:
                st.markdown("**Session Type Breakdown:**")
                st.markdown(
                    f"- 🔵 Concept Study: **{int(p.study_ratio*100)}%**<br>"
                    f"- 🟢 Practice Tasks: **{int(p.practice_ratio*100)}%**<br>"
                    f"- 🟣 Revision & Recall: **{int(p.revision_ratio*100)}%**",
                    unsafe_allow_html=True
                )
            st.divider()

# -------------------------------------------------------------
# TAB 2: Weekly Schedule
# -------------------------------------------------------------
with tab_schedule:
    st.markdown("### Actionable 7-Day Study Schedule")
    st.markdown("Sessions are structured into **Concept Study**, **Practice Tasks**, and **Revision Time**.")

    for day in current_plan.days:
        status_text = "✅ Within Limits" if day.is_valid else "❌ Over Limit"
        expander_title = (
            f"📌 {day.day_name} ({day.date_str}) — Scheduled: {day.scheduled_hours:.1f}h / "
            f"Available: {day.available_hours:.1f}h (Buffer: {day.remaining_buffer_hours:.1f}h) — {status_text}"
        )
        
        with st.expander(expander_title, expanded=(day.scheduled_hours > 0)):
            if not day.sessions:
                st.info("No study sessions scheduled for this day (Rest / Free day).")
            else:
                for idx, s in enumerate(day.sessions, 1):
                    c1, c2, c3 = st.columns([2, 5, 2])
                    with c1:
                        if s.session_type == SessionType.CONCEPT_STUDY:
                            badge_html = f'<span class="session-badge-study">{s.session_type.value}</span>'
                        elif s.session_type == SessionType.PRACTICE_TASK:
                            badge_html = f'<span class="session-badge-practice">{s.session_type.value}</span>'
                        else:
                            badge_html = f'<span class="session-badge-revision">{s.session_type.value}</span>'
                        st.markdown(badge_html, unsafe_allow_html=True)
                        st.markdown(f"**Duration: {s.duration_hours:.1f} hrs**")
                    with c2:
                        st.markdown(f"**{s.topic_name}**")
                        st.caption(f"🎯 *Objective:* {s.objective}")
                        st.markdown(f"💻 *Task:* {s.task_description}")
                    with c3:
                        done = st.checkbox("Done", key=f"chk_{s.session_id}")
                        if done:
                            st.caption("✅ Logged complete")
                    st.markdown("---")

# -------------------------------------------------------------
# TAB 3: Availability Compliance Check (Core Deliverable)
# -------------------------------------------------------------
with tab_compliance:
    st.markdown("### Mathematical Availability Audit")
    st.markdown(
        "Formal invariant verification ensuring that scheduled study hours **never exceed** "
        "the student's stated availability on any day or globally for the week."
    )

    audit_data = []
    for d in current_audit["daily_audits"]:
        audit_data.append({
            "Day": d["day_name"],
            "Date": d["date_str"],
            "Stated Available (hrs)": d["available_hours"],
            "Scheduled Time (hrs)": d["scheduled_hours"],
            "Unallocated Buffer (hrs)": d["buffer_hours"],
            "Utilization Rate": f"{d['utilization_pct']}%",
            "Constraint Status": "✅ PASS" if d["is_valid"] else "❌ FAIL"
        })

    df_audit = pd.DataFrame(audit_data)
    st.dataframe(df_audit, use_container_width=True)

    # Chart comparison
    st.markdown("#### Stated Available vs Scheduled Study Hours")
    chart_df = pd.DataFrame({
        "Day": [d["day_name"] for d in current_audit["daily_audits"]],
        "Available Hours": [d["available_hours"] for d in current_audit["daily_audits"]],
        "Scheduled Hours": [d["scheduled_hours"] for d in current_audit["daily_audits"]],
        "Buffer Hours": [d["buffer_hours"] for d in current_audit["daily_audits"]]
    }).set_index("Day")
    st.bar_chart(chart_df[["Available Hours", "Scheduled Hours"]])

    if current_audit["all_passed"]:
        st.success(
            f"VERIFICATION CONFIRMED: All 7 days satisfy the constraint! "
            f"Scheduled time ({current_audit['total_scheduled_hours']}h) &le; "
            f"Available time ({current_audit['total_available_hours']}h). "
            f"Flexibility buffer of {current_audit['total_buffer_hours']}h protects student from burnout."
        )

# -------------------------------------------------------------
# TAB 4: Dynamic Progress Tracking & Re-Planning
# -------------------------------------------------------------
with tab_tracker:
    st.markdown("### Update Progress & Regenerate Schedule")
    st.markdown(
        "As the student completes study sessions or practice tasks, update their mastery level below. "
        "Click **Regenerate AI Plan** to adapt the schedule dynamically and inspect the AI's explanation of the shifts."
    )

    col_up1, col_up2 = st.columns([1, 1])

    with col_up1:
        st.subheader("Update Topic Mastery Self-Assessments")
        updated_mastery_dict = {}
        for t_id, topic in curriculum.items():
            curr_val = float(active_student.assessments[t_id].mastery_level)
            new_val = st.slider(
                f"{topic.name}",
                min_value=0.0,
                max_value=1.0,
                value=curr_val,
                step=0.05,
                key=f"slider_mastery_{t_id}"
            )
            updated_mastery_dict[t_id] = new_val

    with col_up2:
        st.subheader("Simulate Advancing Schedule Date")
        simulated_new_start = st.date_input(
            "Regeneration Date",
            value=date(2026, 10, 20),
            help="Simulate reaching Tuesday/Wednesday of the study cycle"
        )
        days_rem = max(0, (active_student.assessment_date - simulated_new_start).days)
        st.info(f"Assessment: **{active_student.assessment_date}** ({days_rem} days remaining)")

        if st.button("🚀 Regenerate AI Plan with Updated Progress", type="primary"):
            st.session_state.previous_plan = deepcopy(st.session_state.current_plan)
            new_plan, new_audit, diff_text = service.update_progress_and_regenerate(
                student=st.session_state.active_student,
                previous_plan=st.session_state.previous_plan,
                topic_updates=updated_mastery_dict,
                new_start_date=simulated_new_start,
                assessment_date=active_student.assessment_date
            )
            st.session_state.current_plan = new_plan
            st.session_state.current_audit = new_audit
            st.session_state.adaptation_log = diff_text
            st.success("Plan successfully regenerated!")
            st.rerun()

    if st.session_state.adaptation_log:
        st.markdown("---")
        st.subheader("🤖 AI Adaptation & Re-Prioritization Report")
        st.code(st.session_state.adaptation_log, language="markdown")
