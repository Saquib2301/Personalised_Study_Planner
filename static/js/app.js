/**
 * SmartStudy AI - Frontend Application Logic
 * Interactive study planner, roadmap viewer, daily checklist, active timer,
 * code runner, self-assessment quiz engine, and dynamic plan regeneration.
 */

let currentStudentId = localStorage.getItem("smartstudy_student_id") || null;
let customTopics = [];
let activeSessionData = null;
let timerInterval = null;
let timerSecondsRemaining = 45 * 60;
let timerRunning = false;
let timeSpentSeconds = 0;

// Chart.js references
let dailyHoursChart = null;
let taskStatusChart = null;

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  // Set default assessment date to 14 days in future
  const defaultDate = new Date();
  defaultDate.setDate(defaultDate.getDate() + 14);
  const examDateInput = document.getElementById("input-exam-date");
  if (examDateInput) {
    examDateInput.value = defaultDate.toISOString().split("T")[0];
  }

  // Preload sample profile 1 if none loaded yet
  if (!currentStudentId) {
    loadSampleProfile("profile_1_beginner");
  } else {
    refreshAllStudentViews();
  }
});

// Navigation & View Switching
function switchView(viewName) {
  const sections = document.querySelectorAll(".view-section");
  sections.forEach(s => s.classList.remove("active"));

  const targetSection = document.getElementById(`view-${viewName}`);
  if (targetSection) {
    targetSection.classList.add("active");
  }

  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach(item => item.classList.remove("active"));
  const activeNav = Array.from(navItems).find(i => i.getAttribute("onclick")?.includes(viewName));
  if (activeNav) {
    activeNav.classList.add("active");
  }

  // Update headers
  const titles = {
    "onboarding": { title: "Onboarding & Custom Topics", desc: "Define your assessment, available study hours, and topics" },
    "roadmap": { title: "AI Learning Roadmap", desc: "Concept hierarchy, learning activities, exercises, and priority rationale" },
    "checklist": { title: "Daily Task Checklist", desc: "Actionable tasks scheduled for today with timer and accountability" },
    "calendar": { title: "Weekly Timetable", desc: "Non-overlapping daily sessions strictly audited against available study hours" },
    "dashboard": { title: "Progress Dashboard", desc: "Analytics, readiness score indicator, and completion statistics" },
    "quiz-center": { title: "Quiz & Practice Center", desc: "Active recall quizzes, problem sets, and revision tracking" },
    "settings": { title: "Dynamic Rescheduling & Settings", desc: "Regenerate schedule, adapt to progress, and preserve completed work" }
  };

  if (titles[viewName]) {
    document.getElementById("page-title-text").innerText = titles[viewName].title;
    document.getElementById("page-desc-text").innerText = titles[viewName].desc;
  }

  if (viewName === "dashboard") {
    loadDashboardAnalytics();
  } else if (viewName === "calendar") {
    loadCalendarView();
  } else if (viewName === "checklist") {
    loadTodayChecklist();
  } else if (viewName === "roadmap") {
    loadRoadmapView();
  } else if (viewName === "quiz-center") {
    loadQuizCenter();
  }
}

// ============================================================
// SAMPLE PROFILES LOADER
// ============================================================
async function loadSampleProfile(profileId) {
  try {
    const res = await fetch(`/api/sample-profiles/${profileId}/load`, { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      currentStudentId = data.student_id;
      localStorage.setItem("smartstudy_student_id", currentStudentId);
      
      // Check capacity warning
      handleCapacityWarning(data.capacity_warning);

      await refreshAllStudentViews();
      switchView("dashboard");
    } else {
      alert("Error loading sample profile: " + data.detail);
    }
  } catch (err) {
    console.error("Failed to load sample profile:", err);
  }
}

// Refresh all active data for current student
async function refreshAllStudentViews() {
  if (!currentStudentId) return;
  try {
    const res = await fetch(`/api/students/${currentStudentId}`);
    if (res.ok) {
      const student = await res.json();
      document.getElementById("active-student-label").innerText = student.name;
      document.getElementById("active-exam-label").innerText = `${student.subject_name} • ${student.assessment_date}`;
      
      // Populate onboarding form if viewing it
      document.getElementById("input-student-name").value = student.name;
      document.getElementById("input-exam-name").value = student.assessment_name;
      document.getElementById("input-subject-name").value = student.subject_name;
      document.getElementById("input-daily-hours").value = student.daily_available_hours;
      document.getElementById("input-exam-date").value = student.assessment_date;
      document.getElementById("input-start-time").value = student.preferred_start_time;
      document.getElementById("input-end-time").value = student.preferred_end_time;
      document.getElementById("input-duration").value = student.preferred_session_duration;
    }
    loadDashboardAnalytics();
    loadTodayChecklist();
    loadRoadmapView();
    loadCalendarView();
  } catch (e) {
    console.error("Error refreshing views:", e);
  }
}

function handleCapacityWarning(warning) {
  const banner = document.getElementById("capacity-warning-banner");
  if (warning && warning.has_warning) {
    banner.style.display = "block";
    banner.className = "alert alert-warning";
    banner.innerHTML = `
      <div>
        <strong>⚠️ Workload Capacity Warning:</strong> ${warning.message}
        <div style="margin-top: 4px; font-size: 0.82rem;">Top recommended priorities: ${warning.recommended_priorities.join(", ")}</div>
      </div>
    `;
  } else {
    banner.style.display = "none";
  }
}

// ============================================================
// CUSTOM TOPIC ENTRY & ONBOARDING
// ============================================================
function addCustomTopic() {
  const nameInput = document.getElementById("custom-topic-input");
  const masteryInput = document.getElementById("custom-mastery-input");
  const importanceInput = document.getElementById("custom-importance-input");

  const name = nameInput.value.trim();
  if (!name) {
    alert("Please enter a topic name.");
    return;
  }

  customTopics.push({
    name: name,
    mastery_level: masteryInput.value,
    importance: importanceInput.value
  });

  nameInput.value = "";
  renderCustomTopicsList();
}

function removeCustomTopic(index) {
  customTopics.splice(index, 1);
  renderCustomTopicsList();
}

function renderCustomTopicsList() {
  const container = document.getElementById("topics-list-container");
  const countBadge = document.getElementById("topics-count-badge");
  countBadge.innerText = customTopics.length;
  container.innerHTML = "";

  customTopics.forEach((t, idx) => {
    const item = document.createElement("div");
    item.style.display = "flex";
    item.style.justifyContent = "space-between";
    item.style.alignItems = "center";
    item.style.padding = "8px 12px";
    item.style.background = "#f1f5f9";
    item.style.borderRadius = "8px";
    item.style.fontSize = "0.88rem";

    const masteryClass = t.mastery_level === "Beginner" ? "badge-danger" : (t.mastery_level === "Intermediate" ? "badge-quiz" : "badge-success");
    const impClass = t.importance === "High" ? "badge-danger" : "badge-study";

    item.innerHTML = `
      <div>
        <strong>${t.name}</strong> 
        <span class="badge ${masteryClass}" style="margin-left: 6px;">${t.mastery_level}</span>
        <span class="badge ${impClass}" style="margin-left: 4px;">${t.importance} Weight</span>
      </div>
      <button onclick="removeCustomTopic(${idx})" style="background:none; border:none; color:#ef4444; font-weight:bold; cursor:pointer;">&times;</button>
    `;
    container.appendChild(item);
  });
}

async function submitOnboardingPlan() {
  const name = document.getElementById("input-student-name").value.trim();
  const exam = document.getElementById("input-exam-name").value.trim();
  const subject = document.getElementById("input-subject-name").value.trim();
  const hours = parseFloat(document.getElementById("input-daily-hours").value);
  const examDate = document.getElementById("input-exam-date").value;
  const startTime = document.getElementById("input-start-time").value;
  const endTime = document.getElementById("input-end-time").value;
  const duration = parseInt(document.getElementById("input-duration").value);

  const selectedDays = Array.from(document.querySelectorAll("#study-days-checkboxes input:checked")).map(cb => cb.value);

  if (!name || !exam || !subject || !examDate) {
    alert("Please fill in student name, exam name, subject, and exam date.");
    return;
  }

  if (customTopics.length === 0) {
    alert("Please add at least one topic to study!");
    return;
  }

  const payload = {
    name: name,
    assessment_name: exam,
    subject_name: subject,
    daily_available_hours: hours,
    preferred_start_time: startTime,
    preferred_end_time: endTime,
    assessment_date: examDate,
    preferred_session_duration: duration,
    available_days: selectedDays,
    topics: customTopics
  };

  try {
    const res = await fetch("/api/students", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
      currentStudentId = data.student_id;
      localStorage.setItem("smartstudy_student_id", currentStudentId);
      handleCapacityWarning(data.capacity_warning);
      await refreshAllStudentViews();
      switchView("roadmap");
    } else {
      alert("Error: " + data.detail);
    }
  } catch (e) {
    console.error("Submission failed:", e);
  }
}

// ============================================================
// VIEW: AI LEARNING ROADMAP
// ============================================================
async function loadRoadmapView() {
  if (!currentStudentId) return;
  const res = await fetch(`/api/students/${currentStudentId}`);
  if (!res.ok) return;
  const student = await res.json();
  const container = document.getElementById("roadmap-cards-container");
  container.innerHTML = "";

  student.topics.forEach((t, idx) => {
    const details = t.roadmap_details || {};
    const subtopics = details.subtopics || [];
    const card = document.createElement("div");
    card.className = "card";
    card.style.marginBottom = "18px";
    card.style.borderLeft = "5px solid #4f46e5";

    const subtopicsHtml = subtopics.map(st => `
      <li style="margin-bottom: 4px; display: flex; justify-content: space-between;">
        <span>• ${st.name}</span>
        <span class="badge ${st.difficulty === 'Easy' ? 'badge-success' : (st.difficulty === 'Medium' ? 'badge-quiz' : 'badge-danger')}">${st.difficulty} • ${st.est_minutes}m</span>
      </li>
    `).join("");

    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
        <div>
          <span class="badge badge-study">Priority #${t.priority_score ? idx+1 : 1} (Score: ${t.priority_score || 'N/A'}/10)</span>
          <h3 style="font-size: 1.2rem; font-weight: 700; margin-top: 4px;">${t.name}</h3>
          <div style="font-size: 0.85rem; color: #64748b;">Mastery: <strong>${t.mastery_level}</strong> | Importance: <strong>${t.importance}</strong> | Est. Time: <strong>${t.estimated_hours} hrs</strong></div>
        </div>
        <span class="badge ${t.status === 'Completed' ? 'badge-success' : (t.status === 'Needs Revision' ? 'badge-danger' : 'badge-study')}">${t.status}</span>
      </div>

      <p style="font-size: 0.9rem; color: #334155; margin-bottom: 14px;">${details.overview || 'Overview of topic foundations.'}</p>

      <div class="alert alert-info" style="font-size: 0.85rem; padding: 10px 14px; margin-bottom: 14px;">
        <strong>💡 AI Prioritisation Rationale:</strong> ${t.priority_rationale || 'Prioritized based on your current knowledge gap and exam importance.'}
      </div>

      <div class="grid-2" style="margin-top: 10px; font-size: 0.88rem;">
        <div>
          <strong>Subtopics (Easy → Hard):</strong>
          <ul style="list-style: none; margin-top: 6px;">${subtopicsHtml || '<li>Foundational breakdown</li>'}</ul>
        </div>
        <div>
          <strong>Prerequisites:</strong>
          <p style="color: #64748b; margin-top: 4px;">${(details.prerequisites || []).join(", ") || "None"}</p>
          <strong style="display: block; margin-top: 8px;">Completion Criteria:</strong>
          <p style="color: #64748b; margin-top: 2px; white-space: pre-line;">${details.completion_criteria || "Score >= 70% on quiz and complete practice exercise."}</p>
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

// ============================================================
// VIEW: DAILY TASK CHECKLIST & INTERACTIVE RUNNER
// ============================================================
async function loadTodayChecklist(filter = "all") {
  if (!currentStudentId) return;
  const res = await fetch(`/api/students/${currentStudentId}/checklist/today`);
  if (!res.ok) return;
  const data = await res.json();
  const container = document.getElementById("checklist-tasks-container");
  document.getElementById("checklist-date-header").innerText = `Scheduled for: ${data.date_str}`;
  container.innerHTML = "";

  let tasks = data.tasks;
  if (filter === "pending") tasks = tasks.filter(t => t.status !== "Completed");
  if (filter === "completed") tasks = tasks.filter(t => t.status === "Completed");

  if (tasks.length === 0) {
    container.innerHTML = `<div style="text-align: center; padding: 40px; color: #94a3b8;">No tasks match this filter for today.</div>`;
    return;
  }

  tasks.forEach(t => {
    const card = document.createElement("div");
    card.style.display = "flex";
    card.style.justifyContent = "space-between";
    card.style.alignItems = "center";
    card.style.padding = "16px 20px";
    card.style.background = t.status === "Completed" ? "#f8fafc" : "#ffffff";
    card.style.border = "1px solid var(--border)";
    card.style.borderRadius = "10px";
    card.style.marginBottom = "12px";

    const badgeTypeClass = t.session_type === "Concept Study" ? "badge-study" : (t.session_type === "Practice Task" ? "badge-practice" : (t.session_type === "Self-Assessment Quiz" ? "badge-quiz" : "badge-revision"));

    card.innerHTML = `
      <div>
        <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 4px;">
          <span class="badge ${badgeTypeClass}">${t.session_type}</span>
          <span style="font-size: 0.8rem; color: #64748b;">${t.start_time} - ${t.end_time} (${t.duration_minutes}m)</span>
          <span class="badge ${t.status === 'Completed' ? 'badge-success' : (t.status === 'Needs Revision' ? 'badge-danger' : 'badge-study')}">${t.status}</span>
        </div>
        <div style="font-weight: 700; font-size: 1.05rem;">${t.topic_name} — <span style="font-weight: 500; color: #475569;">${t.subtopic_name}</span></div>
        <div style="font-size: 0.85rem; color: #64748b; margin-top: 2px;">🎯 ${t.learning_objectives}</div>
      </div>
      <div>
        ${t.status === 'Completed' 
          ? `<button class="btn btn-secondary btn-sm" onclick="openTaskModal(${t.id})">Review Task</button>` 
          : `<button class="btn btn-primary btn-sm" onclick="openTaskModal(${t.id})">▶ Start Task</button>`}
      </div>
    `;
    container.appendChild(card);
  });
}

function filterChecklist(filter) {
  loadTodayChecklist(filter);
}

// ============================================================
// INTERACTIVE TASK RUNNER MODAL (Timer, Code, Quiz, Accountability)
// ============================================================
async function openTaskModal(sessionId) {
  const res = await fetch(`/api/sessions/${sessionId}/start`, { method: "POST" });
  if (!res.ok) return;
  activeSessionData = await res.json();

  document.getElementById("modal-task-title").innerText = activeSessionData.topic_name;
  document.getElementById("modal-task-sub").innerText = activeSessionData.subtopic_name;
  document.getElementById("modal-task-badge").innerText = activeSessionData.session_type;
  document.getElementById("modal-learning-obj").innerText = activeSessionData.learning_objectives || "Master concept principles.";
  document.getElementById("modal-study-material").innerText = activeSessionData.study_material || "Review the core ideas, boundary conditions, and execution patterns.";

  // Timer setup
  timerSecondsRemaining = activeSessionData.duration_minutes * 60;
  timeSpentSeconds = 0;
  updateTimerDisplay();

  // Practical exercise section
  const codeSection = document.getElementById("modal-code-section");
  if (activeSessionData.session_type === "Practice Task") {
    codeSection.style.display = "block";
    document.getElementById("modal-code-prompt").innerText = activeSessionData.practice_exercise || "Solve implementation challenge.";
    document.getElementById("modal-code-textarea").value = "# Write your Python solution here\ndef solve():\n    pass\n";
    document.getElementById("code-result-badge").innerText = "";
    document.getElementById("code-eval-output").innerText = "";
  } else {
    codeSection.style.display = "none";
  }

  // Quiz section
  const quizSection = document.getElementById("modal-quiz-section");
  const quizContainer = document.getElementById("modal-quiz-questions-container");
  quizContainer.innerHTML = "";
  document.getElementById("quiz-result-box").style.display = "none";

  const questions = (activeSessionData.quiz_data && activeSessionData.quiz_data.questions) || [];
  if (activeSessionData.session_type === "Self-Assessment Quiz" && questions.length > 0) {
    quizSection.style.display = "block";
    questions.forEach((q, qIdx) => {
      const qDiv = document.createElement("div");
      qDiv.style.marginBottom = "14px";
      qDiv.innerHTML = `<div style="font-weight: 600; font-size: 0.9rem; margin-bottom: 6px;">${qIdx+1}. ${q.question}</div>`;

      q.options.forEach((opt, optIdx) => {
        const optLabel = document.createElement("label");
        optLabel.style.display = "block";
        optLabel.style.fontSize = "0.85rem";
        optLabel.style.margin = "4px 0";
        optLabel.innerHTML = `
          <input type="radio" name="quiz_q_${qIdx}" value="${optIdx}"> ${opt}
        `;
        qDiv.appendChild(optLabel);
      });
      quizContainer.appendChild(qDiv);
    });
  } else {
    quizSection.style.display = "none";
  }

  document.getElementById("task-modal").classList.add("open");
}

function closeTaskModal() {
  pauseTimer();
  document.getElementById("task-modal").classList.remove("open");
}

// Timer Controls
function toggleTimer() {
  if (timerRunning) {
    pauseTimer();
  } else {
    startTimer();
  }
}

function startTimer() {
  timerRunning = true;
  document.getElementById("btn-timer-toggle").innerText = "⏸ Pause";
  timerInterval = setInterval(() => {
    if (timerSecondsRemaining > 0) {
      timerSecondsRemaining--;
      timeSpentSeconds++;
      updateTimerDisplay();
    } else {
      pauseTimer();
      alert("Session study time completed! Great focus. Please complete your tasks and reflection.");
    }
  }, 1000);
}

function pauseTimer() {
  timerRunning = false;
  clearInterval(timerInterval);
  document.getElementById("btn-timer-toggle").innerText = "▶ Start";
}

function resetTimer() {
  pauseTimer();
  timerSecondsRemaining = (activeSessionData ? activeSessionData.duration_minutes : 45) * 60;
  updateTimerDisplay();
}

function updateTimerDisplay() {
  const mins = Math.floor(timerSecondsRemaining / 60);
  const secs = timerSecondsRemaining % 60;
  document.getElementById("timer-display").innerText = 
    `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Interactive Code Runner & Test Cases
async function submitCodeSolution() {
  const code = document.getElementById("modal-code-textarea").value;
  const res = await fetch(`/api/sessions/${activeSessionData.session_id}/code/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code: code })
  });
  const data = await res.json();
  const badge = document.getElementById("code-result-badge");
  const output = document.getElementById("code-eval-output");

  if (data.eval_result.all_passed) {
    badge.className = "badge badge-success";
    badge.innerText = "✅ All Test Cases Passed!";
    output.innerText = data.eval_result.message;
  } else {
    badge.className = "badge badge-danger";
    badge.innerText = `❌ ${data.eval_result.passed_count}/${data.eval_result.total_count} Passed`;
    output.innerText = data.eval_result.error || data.eval_result.message;
  }
}

// Interactive Quiz Submissions
async function submitQuizAttempt() {
  const questions = (activeSessionData.quiz_data && activeSessionData.quiz_data.questions) || [];
  const answers = {};

  questions.forEach((q, idx) => {
    const selected = document.querySelector(`input[name="quiz_q_${idx}"]:checked`);
    if (selected) {
      answers[idx] = parseInt(selected.value);
    }
  });

  const res = await fetch(`/api/sessions/${activeSessionData.session_id}/quiz/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ submitted_answers: answers })
  });
  const data = await res.json();
  const resBox = document.getElementById("quiz-result-box");
  resBox.style.display = "block";

  const gr = data.grade_result;
  const isPass = gr.passed;

  resBox.className = isPass ? "alert alert-success" : "alert alert-warning";
  resBox.innerHTML = `
    <strong>Score: ${gr.score_percentage}% (${gr.correct_answers}/${gr.total_questions} Correct)</strong>
    <p style="margin-top: 4px;">${gr.feedback}</p>
  `;
}

async function markTaskCompleted() {
  if (!activeSessionData) return;
  const notes = document.getElementById("modal-student-notes").value;
  const res = await fetch(`/api/sessions/${activeSessionData.session_id}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes: notes, time_spent_seconds: timeSpentSeconds })
  });

  if (res.ok) {
    closeTaskModal();
    loadTodayChecklist();
    loadDashboardAnalytics();
    loadCalendarView();
  }
}

// ============================================================
// VIEW: WEEKLY TIMETABLE
// ============================================================
async function loadCalendarView() {
  if (!currentStudentId) return;
  const res = await fetch(`/api/students/${currentStudentId}/schedule`);
  if (!res.ok) return;
  const data = await res.json();
  const container = document.getElementById("calendar-days-container");
  container.innerHTML = "";

  data.days.forEach(d => {
    const dayBox = document.createElement("div");
    dayBox.style.border = "1px solid var(--border)";
    dayBox.style.borderRadius = "10px";
    dayBox.style.padding = "16px";
    dayBox.style.marginBottom = "16px";
    dayBox.style.background = "#ffffff";

    let totalDayMinutes = d.sessions.reduce((acc, s) => acc + s.duration_minutes, 0);
    let totalDayHours = (totalDayMinutes / 60).toFixed(1);

    const sessionsHtml = d.sessions.map(s => `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: #f8fafc; border-radius: 8px; margin-bottom: 6px; font-size: 0.88rem;">
        <div>
          <span style="font-weight: 600; color: #4338ca;">${s.start_time} - ${s.end_time}</span>
          <span style="margin: 0 6px;">|</span>
          <strong>${s.topic_name}</strong>: ${s.subtopic_name}
        </div>
        <div>
          <span class="badge ${s.status === 'Completed' ? 'badge-success' : (s.status === 'Needs Revision' ? 'badge-danger' : 'badge-study')}">${s.status}</span>
        </div>
      </div>
    `).join("");

    dayBox.innerHTML = `
      <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
        <h4 style="font-weight: 700;">${d.day_name} (${d.date_str})</h4>
        <span style="font-size: 0.85rem; color: #64748b;">Scheduled: <strong>${totalDayHours}h</strong> / Available: <strong>${data.daily_available_hours}h</strong></span>
      </div>
      <div>${sessionsHtml || '<p style="font-size: 0.85rem; color: #94a3b8;">Rest day / No sessions scheduled</p>'}</div>
    `;
    container.appendChild(dayBox);
  });
}

// ============================================================
// VIEW: PROGRESS DASHBOARD & ANALYTICS
// ============================================================
async function loadDashboardAnalytics() {
  if (!currentStudentId) return;
  const res = await fetch(`/api/students/${currentStudentId}/dashboard`);
  if (!res.ok) return;
  const m = await res.json();

  document.getElementById("kpi-progress").innerText = `${m.overall_progress_pct}%`;
  document.getElementById("kpi-progress-sub").innerText = `${m.completed_tasks} of ${m.total_tasks} tasks completed`;
  document.getElementById("kpi-readiness").innerText = `${m.readiness_score}%`;
  document.getElementById("kpi-remaining-hours").innerText = `${m.remaining_study_hours} hrs`;
  document.getElementById("kpi-days-remaining").innerText = `${m.days_remaining} days to deadline`;
  document.getElementById("kpi-revision-count").innerText = `${m.needs_revision_tasks}`;
  document.getElementById("readiness-disclaimer-text").innerText = m.readiness_disclaimer;

  // Chart 1: Daily Hours vs Available
  const ctxDaily = document.getElementById("chart-daily-hours").getContext("2d");
  const chartLabels = m.daily_chart_data.map(d => d.date.slice(5)); // MM-DD
  const schedData = m.daily_chart_data.map(d => d.scheduled_hours.toFixed(1));
  const availData = m.daily_chart_data.map(d => d.available_hours);

  if (dailyHoursChart) dailyHoursChart.destroy();
  dailyHoursChart = new Chart(ctxDaily, {
    type: "bar",
    data: {
      labels: chartLabels,
      datasets: [
        { label: "Scheduled Hours", data: schedData, backgroundColor: "#4f46e5", borderRadius: 6 },
        { label: "Daily Available Limit", data: availData, type: "line", borderColor: "#10b981", borderDash: [5, 5], fill: false }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, title: { display: true, text: "Hours" } } }
    }
  });

  // Chart 2: Task Status Distribution
  const ctxStatus = document.getElementById("chart-task-status").getContext("2d");
  if (taskStatusChart) taskStatusChart.destroy();
  taskStatusChart = new Chart(ctxStatus, {
    type: "doughnut",
    data: {
      labels: ["Completed", "Pending", "Needs Revision"],
      datasets: [{
        data: [m.completed_tasks, m.pending_tasks, m.needs_revision_tasks],
        backgroundColor: ["#10b981", "#3b82f6", "#ef4444"]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  });
}

// ============================================================
// DYNAMIC RESCHEDULING
// ============================================================
async function triggerRegeneratePlan() {
  if (!currentStudentId) return;
  const res = await fetch(`/api/students/${currentStudentId}/reschedule`, { method: "POST" });
  if (res.ok) {
    const data = await res.json();
    const expBox = document.getElementById("regeneration-explanation-box");
    expBox.style.display = "block";
    document.getElementById("regeneration-explanation-text").innerText = data.explanation;
    
    handleCapacityWarning(data.capacity_warning);
    await refreshAllStudentViews();
  }
}

// ============================================================
// VIEW: QUIZ CENTER
// ============================================================
async function loadQuizCenter() {
  if (!currentStudentId) return;
  const res = await fetch(`/api/students/${currentStudentId}/schedule`);
  if (!res.ok) return;
  const data = await res.json();
  const container = document.getElementById("quiz-list-container");
  container.innerHTML = "";

  const allSessions = data.days.flatMap(d => d.sessions);
  const quizSessions = allSessions.filter(s => s.session_type === "Self-Assessment Quiz");

  if (quizSessions.length === 0) {
    container.innerHTML = "<p style='color: #64748b;'>No quizzes currently scheduled.</p>";
    return;
  }

  quizSessions.forEach(q => {
    const item = document.createElement("div");
    item.style.display = "flex";
    item.style.justifyContent = "space-between";
    item.style.alignItems = "center";
    item.style.padding = "14px 18px";
    item.style.border = "1px solid var(--border)";
    item.style.borderRadius = "10px";
    item.style.marginBottom = "10px";
    item.style.background = "#fff";

    const scoreDisplay = q.quiz_score !== null ? `${q.quiz_score}%` : "Not attempted";
    const statusClass = q.status === "Completed" ? "badge-success" : (q.status === "Needs Revision" ? "badge-danger" : "badge-quiz");

    item.innerHTML = `
      <div>
        <strong>${q.topic_name}</strong> — ${q.subtopic_name}
        <div style="font-size: 0.82rem; color: #64748b; margin-top: 2px;">Score: <strong>${scoreDisplay}</strong></div>
      </div>
      <div style="display: flex; gap: 10px; align-items: center;">
        <span class="badge ${statusClass}">${q.status}</span>
        <button class="btn btn-sm btn-primary" onclick="openTaskModal(${q.id})">Launch Quiz</button>
      </div>
    `;
    container.appendChild(item);
  });
}
