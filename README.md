# AI Personalised Study Planner 🎓

The **AI Personalised Study Planner** is an intelligent learning platform designed to help students prepare for examinations through personalised study schedules, topic prioritisation, and progress tracking. The system analyses the topics provided by students, their current knowledge level, topic importance, available study hours, and examination deadlines to create an effective and achievable study plan.

Students can enter their own subjects and topics, classify their mastery level as Beginner, Intermediate, or Advanced, and specify their daily availability. Based on this information, the AI identifies topics that require more attention and arranges them according to priority. It generates a structured timetable containing concept learning, practice exercises, quizzes, and revision sessions.

The system also encourages students to complete their assigned tasks instead of simply following a timetable. Students can track tasks as Not Started, In Progress, or Completed, attempt quizzes, and monitor their learning progress. If a student misses a task, performs poorly in a quiz, or changes their availability, the system can dynamically update the remaining schedule.

The planner ensures that scheduled study time does not exceed the student's available hours. It also provides explanations for topic prioritisation, helping students understand why certain topics need more attention. A dashboard displays completion percentages, pending tasks, quiz performance, and overall preparation progress.

The main objective of this project is to make studying more organised, personalised, and productive. By combining AI-based recommendations, intelligent scheduling, and progress monitoring, the system helps students manage their time effectively, strengthen weak areas, and prepare for examinations with greater confidence.

---

## 🌟 Key Capabilities & Features

### 1. User Input & Personalisation
- **Student Onboarding**: Collects Student Name, Assessment Name, Subject Name, Daily Available Study Hours, Preferred Study Window (Start & End Times), Assessment Date (configurable date picker), Preferred Session Duration (30, 45, 60, 90 mins), and Available Study Days (Monday–Sunday).
- **Custom Topic Entry**: Students can enter any topic manually, add multiple topics, set mastery levels (**Beginner, Intermediate, Advanced**) and importance (**Low, Medium, High**), and remove or edit them. Topics are completely dynamic and not restricted to a fixed list.

### 2. AI-Powered Study Roadmap Generation
For every topic entered, the AI generates a complete 10-point learning roadmap:
1. **Topic Overview**: Clear conceptual grounding.
2. **Important Concepts**: Key definitions, invariants, and mental models.
3. **Subtopics (Easy → Hard)**: Structured sequence with time estimates.
4. **Prerequisites**: Identified gateway topics.
5. **Recommended Learning Activities**: Reading, tracing, active recall.
6. **Practical Exercises**: Algorithmic problem statements and programming challenges.
7. **Self-Assessment Quizzes**: 3 curated questions with options, correct indices, and detailed explanations.
8. **Estimated Time**: Calibrated to student mastery and topic importance.
9. **Revision Tasks**: Spaced repetition drills and Feynman technique prompts.
10. **Completion Criteria**: Explicit milestones to achieve mastery.

### 3. Intelligent Multi-Factor Topic Prioritisation
- Formula combines:
  $$\text{Knowledge Gap} \times \text{Exam Weight} \times \text{Difficulty Factor} \times \text{Urgency Multiplier}$$
- Generates natural-language rationales explaining *why* each topic was ranked (e.g., *"Variables & Primitive Types has been given TOP PRIORITY because your mastery is Beginner and importance is High, requiring deep conceptual foundation..."*).
- Topics needing revision or with low quiz scores receive automatic priority escalation.

### 4. Automatic Personalised Schedule Generation & Strict Invariants
- **Daily Availability Cap**: Never allocates more study time than stated daily hours.
- **Non-Overlapping Slots**: Sessions are scheduled sequentially with automated 10-minute breaks between longer study blocks.
- **Available Days & Times**: Only schedules on student-selected days during preferred study hours.
- **Capacity Deficit Warning**: If the requested workload exceeds remaining study time before the deadline, the system alerts the student, computes the exact deficit, and recommends top priorities without silently removing topics.

### 5. Task Completion & Accountability System
- **Interactive Task Modal**:
  - **Active Study Timer**: Play, Pause, Reset, with automated session duration tracking.
  - **Learning Material & Objectives**: Core concepts and execution tracing.
  - **Python Code Runner**: In-browser code editor with instant test case execution.
  - **Interactive Quiz Engine**: Multiple-choice assessment with instant grading, explanations, and automatic *"Needs Revision"* tagging if score is $< 70\%$.
  - **Reflection & Notes**: Record difficulties encountered.
  - **Explicit Completion**: Tasks are only completed when explicitly submitted.

### 6. Dynamic Rescheduling & Plan Regeneration
- **"Regenerate My Plan"**:
  - Preserves all previously completed tasks.
  - Identifies incomplete, overdue, or *"Needs Revision"* tasks.
  - Recalculates priorities based on recent quiz scores and remaining days to assessment.
  - Repacks unfinished work into future available slots within daily limits.
  - Generates an explainable AI Adaptation Report detailing all shifts.

### 7. Progress & Readiness Dashboard
- KPIs: Overall Progress %, Total Tasks, Tasks Completed Today, Pending, Overdue, Needs Revision, Remaining Study Hours, Days to Exam.
- **Exam Readiness Score**: Multi-factor synthesis of task completion ($40\%$), quiz accuracy ($35\%$), and mastery baseline ($25\%$) with explicit disclaimer.
- Interactive Chart.js Visualisations:
  - Chart 1: Daily Scheduled Hours vs. Daily Available Limit.
  - Chart 2: Task Completion Status Breakdown.

### 8. Three Pre-Configured Demonstration Profiles
- **Profile 1: Alex Rivera (Beginner Programmer)**: Variables, Loops, Functions, Arrays • 2.0 hrs/day • CS101 Practical.
- **Profile 2: Maya Chen (Intermediate Programmer)**: Recursion, Binary Search, Sorting, Linked Lists • 3.0 hrs/day • DSA Midterm.
- **Profile 3: Sam Taylor (Operating Systems Student)**: Process Scheduling, Synchronization, Deadlocks, Virtual Memory • 1.5 hrs/day • OS Exam.

---

## 🛠️ Quick Start & Execution

### Option 1: Modern Web Application (Recommended)
Launch the unified FastAPI web application:
```powershell
py -3.10 server.py
```
Open your browser at:
👉 **[http://localhost:8000](http://localhost:8000)**

### Option 2: Run Evaluation Test Suites
Run the 10 scenario test suite:
```powershell
py -3.10 -m unittest tests/test_smartstudy_scenarios.py
```
Run the baseline availability constraint test suite:
```powershell
py -3.10 test_planner.py
```

---

## 🧪 Scenario Evaluation Test Results

| # | Evaluation Scenario | Expected Outcome | Test Result |
| :---: | :--- | :--- | :---: |
| 1 | **Beginner with limited study hours (1.5h/d)** | Daily scheduled $\le 1.5$h, zero overage | **PASS ✅** |
| 2 | **Advanced student with more hours (4.0h/d)** | Prioritizes revision drills, daily $\le 4.0$h | **PASS ✅** |
| 3 | **Mixed topic mastery (Beginner vs Advanced)** | Beginner/High-weight topic ranked #1 | **PASS ✅** |
| 4 | **Deadline approaching (3 days away)** | Urgency multiplier applied to critical gaps | **PASS ✅** |
| 5 | **Missed / overdue tasks** | Overdue tasks detected and tracked separately | **PASS ✅** |
| 6 | **Poor quiz performance ($< 70\%$)** | Flagged as Needs Revision, priority boosted | **PASS ✅** |
| 7 | **Availability adjustment (3.0h $\rightarrow$ 1.5h)** | Schedule strictly repacked to 1.5h cap | **PASS ✅** |
| 8 | **Adding & removing topics dynamically** | Dynamic array handling without schedule corrupt | **PASS ✅** |
| 9 | **Plan regeneration preserves completed tasks** | Completed sessions preserved with zero loss | **PASS ✅** |
| 10 | **Workload exceeds available time capacity** | Workload warning with deficit hours emitted | **PASS ✅** |

*All 10 test scenarios pass with 100% compliance in 0.14 seconds.*

---

## 🏗️ Architecture & Database Setup

- **Backend**: FastAPI with SQLite (`smartstudy.db`) via SQLAlchemy. Supports MySQL by setting `DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/smartstudy_db`.
- **Frontend**: Responsive Single-Page Application (HTML5, Vanilla CSS3 with Glassmorphism, JavaScript ES6+, Chart.js).
- **AI Engine**: External LLM (OpenAI/Gemini via environment variables) with an automated intelligent fallback engine that generates specialized roadmaps for any topic offline.
