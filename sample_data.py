"""
Sample data for the AI Study Planner:
- Comprehensive programming assessment curriculum with prerequisite relationships,
  concrete practice tasks, and revision prompts.
- Three diverse, realistic sample student profiles (Alex, Maya, Sam) meeting all
  assessment scenario specifications.
"""

from datetime import date
from typing import Dict
from models import StudentProfile, Topic, TopicAssessment


def get_default_curriculum() -> Dict[str, Topic]:
    """Returns standard curriculum for the programming assessment on 24 October 2026."""
    topics_list = [
        Topic(
            id="PY_FUND",
            name="Python Fundamentals & Data Structures",
            category="Core Language",
            exam_weight=6.0,
            difficulty=1.5,
            estimated_hours=4.0,
            prerequisites=[],
            practice_prompts=[
                "Implement a word-frequency counter utilizing dict comprehensions and string slicing.",
                "Solve 3 string manipulation challenges with two-pointer techniques."
            ],
            revision_prompts=[
                "Review time complexity of list vs dict vs set lookups in Python.",
                "Quick active-recall: mutable vs immutable defaults in function arguments."
            ]
        ),
        Topic(
            id="COMPLEXITY",
            name="Asymptotic Analysis & Big-O",
            category="Foundations",
            exam_weight=8.0,
            difficulty=2.5,
            estimated_hours=5.0,
            prerequisites=["PY_FUND"],
            practice_prompts=[
                "Calculate and formally prove the time/space complexity of 5 recursive and iterative code snippets.",
                "Optimize an O(N^2) search algorithm into O(N log N) or O(N)."
            ],
            revision_prompts=[
                "Recite the Big-O master theorem shortcuts and log-space vs linear-space trade-offs.",
                "Review common complexity traps in nested loops and Python generator expressions."
            ]
        ),
        Topic(
            id="RECURSION",
            name="Recursion & Backtracking",
            category="Algorithms",
            exam_weight=8.5,
            difficulty=3.8,
            estimated_hours=7.0,
            prerequisites=["PY_FUND"],
            practice_prompts=[
                "Code the N-Queens problem or Sudoku solver using backtracking with pruning.",
                "Implement subsets and permutations generator using recursion."
            ],
            revision_prompts=[
                "Draw call stack diagrams for tree recursion vs tail recursion.",
                "Review base case safety guidelines to prevent RecursionError stack overflows."
            ]
        ),
        Topic(
            id="OOP",
            name="Object-Oriented Design & Classes",
            category="Software Engineering",
            exam_weight=7.5,
            difficulty=2.8,
            estimated_hours=6.0,
            prerequisites=["PY_FUND"],
            practice_prompts=[
                "Design a clean Parking Lot or Library Management system with inheritance and abstract base classes.",
                "Refactor procedural code into modular SOLID classes with dunder methods (__repr__, __eq__, __iter__)."
            ],
            revision_prompts=[
                "Explain Polymorphism vs Composition with a crisp 2-minute whiteboarding example.",
                "Review method resolution order (MRO) in Python multiple inheritance."
            ]
        ),
        Topic(
            id="LINEAR_DS",
            name="Linear Data Structures (Stacks, Queues, Linked Lists)",
            category="Data Structures",
            exam_weight=8.5,
            difficulty=3.2,
            estimated_hours=8.0,
            prerequisites=["OOP"],
            practice_prompts=[
                "Build a LRU Cache from scratch using a doubly linked list and hashmap.",
                "Solve the Valid Parentheses and Daily Temperatures problems using monotonic stacks."
            ],
            revision_prompts=[
                "Flashcard review: circular buffer mechanics vs collections.deque implementation.",
                "Trace pointer reversals in single and doubly linked lists."
            ]
        ),
        Topic(
            id="TREES_GRAPHS",
            name="Trees, BSTs, & Graph Traversal (BFS/DFS)",
            category="Data Structures & Algorithms",
            exam_weight=9.5,
            difficulty=4.2,
            estimated_hours=10.0,
            prerequisites=["RECURSION", "LINEAR_DS"],
            practice_prompts=[
                "Implement Lowest Common Ancestor (LCA) and BST validation with recursion.",
                "Implement BFS level-order traversal and DFS topological sort for course schedule problem."
            ],
            revision_prompts=[
                "Recall difference between BFS queue traversal and DFS recursion stack.",
                "Review properties of balanced vs degenerate trees and Dijkstra's algorithm basics."
            ]
        ),
        Topic(
            id="DYN_PROG",
            name="Dynamic Programming & Memoization",
            category="Advanced Algorithms",
            exam_weight=9.5,
            difficulty=4.8,
            estimated_hours=12.0,
            prerequisites=["RECURSION"],
            practice_prompts=[
                "Solve 0/1 Knapsack problem first with top-down memoization, then bottom-up tabulation.",
                "Code Longest Common Subsequence (LCS) and Coin Change with state space diagrams."
            ],
            revision_prompts=[
                "Identify overlapping subproblems and optimal substructure in word-break problems.",
                "Template for 1D vs 2D DP array space-optimization tricks."
            ]
        ),
        Topic(
            id="TESTING_DEBUG",
            name="Testing, Edge Cases & Error Handling",
            category="Software Engineering",
            exam_weight=6.5,
            difficulty=2.2,
            estimated_hours=4.0,
            prerequisites=["PY_FUND"],
            practice_prompts=[
                "Write comprehensive pytest test suites for sorting algorithms including boundary/null cases.",
                "Implement custom exception hierarchies and context managers (with statement)."
            ],
            revision_prompts=[
                "Review off-by-one errors, empty input checks, and floating-point precision traps.",
                "Checklist for pre-submission code review in a competitive exam."
            ]
        )
    ]
    return {t.id: t for t in topics_list}


def get_sample_students() -> Dict[str, StudentProfile]:
    """
    Returns 3 distinct, realistic sample student profiles for the assessment scenario.
    All targeting Assessment Date: 24 October 2026.
    """
    curriculum = get_default_curriculum()
    target_deadline = date(2026, 10, 24)

    # -------------------------------------------------------------
    # Student 1: Alex Rivera (Beginner with High Available Study Hours)
    # -------------------------------------------------------------
    # Persona: Full-time student on study leave, 26 hours/week.
    # Strengths: Basic Python syntax.
    # Deficits: Trees, Dynamic Programming, Recursion, Big-O analysis.
    alex_assessments = {
        "PY_FUND": TopicAssessment("PY_FUND", mastery_level=0.85, confidence=0.85),
        "COMPLEXITY": TopicAssessment("COMPLEXITY", mastery_level=0.35, confidence=0.30),
        "RECURSION": TopicAssessment("RECURSION", mastery_level=0.30, confidence=0.25),
        "OOP": TopicAssessment("OOP", mastery_level=0.45, confidence=0.40),
        "LINEAR_DS": TopicAssessment("LINEAR_DS", mastery_level=0.40, confidence=0.35),
        "TREES_GRAPHS": TopicAssessment("TREES_GRAPHS", mastery_level=0.15, confidence=0.15),
        "DYN_PROG": TopicAssessment("DYN_PROG", mastery_level=0.10, confidence=0.10),
        "TESTING_DEBUG": TopicAssessment("TESTING_DEBUG", mastery_level=0.60, confidence=0.60),
    }
    alex = StudentProfile(
        id="alex_rivera",
        name="Alex Rivera",
        persona_tagline="Full-time Learner • High Availability (26 hrs/wk) • Foundational Knowledge Gaps",
        daily_availability={
            "Monday": 4.0,
            "Tuesday": 3.5,
            "Wednesday": 4.0,
            "Thursday": 3.5,
            "Friday": 3.0,
            "Saturday": 4.0,
            "Sunday": 4.0,
        },
        assessments=alex_assessments,
        assessment_date=target_deadline
    )

    # -------------------------------------------------------------
    # Student 2: Maya Chen (Working Professional • Time-Constrained)
    # -------------------------------------------------------------
    # Persona: Working full-time, only 10.5 hours/week.
    # Strengths: Strong fundamentals, OOP, testing from job experience.
    # Deficits: Advanced algorithmic puzzles (Dynamic Programming & Graphs).
    maya_assessments = {
        "PY_FUND": TopicAssessment("PY_FUND", mastery_level=0.95, confidence=0.95),
        "COMPLEXITY": TopicAssessment("COMPLEXITY", mastery_level=0.70, confidence=0.70),
        "RECURSION": TopicAssessment("RECURSION", mastery_level=0.65, confidence=0.60),
        "OOP": TopicAssessment("OOP", mastery_level=0.90, confidence=0.90),
        "LINEAR_DS": TopicAssessment("LINEAR_DS", mastery_level=0.70, confidence=0.70),
        "TREES_GRAPHS": TopicAssessment("TREES_GRAPHS", mastery_level=0.30, confidence=0.30),
        "DYN_PROG": TopicAssessment("DYN_PROG", mastery_level=0.25, confidence=0.20),
        "TESTING_DEBUG": TopicAssessment("TESTING_DEBUG", mastery_level=0.85, confidence=0.85),
    }
    maya = StudentProfile(
        id="maya_chen",
        name="Maya Chen",
        persona_tagline="Working Professional • Strict Availability (10.5 hrs/wk) • Targeted Advanced Gaps",
        daily_availability={
            "Monday": 1.5,
            "Tuesday": 1.0,
            "Wednesday": 1.5,
            "Thursday": 1.0,
            "Friday": 1.0,
            "Saturday": 2.5,
            "Sunday": 2.0,
        },
        assessments=maya_assessments,
        assessment_date=target_deadline
    )

    # -------------------------------------------------------------
    # Student 3: Sam Taylor (Uneven Specialist • Critical High-Weight Blindspots)
    # -------------------------------------------------------------
    # Persona: 17.5 hours/week. Loves recursion and DP math puzzles,
    # but has critical blind spots in Trees/Graphs and Big-O formal proofs.
    sam_assessments = {
        "PY_FUND": TopicAssessment("PY_FUND", mastery_level=0.90, confidence=0.90),
        "COMPLEXITY": TopicAssessment("COMPLEXITY", mastery_level=0.35, confidence=0.35),
        "RECURSION": TopicAssessment("RECURSION", mastery_level=0.85, confidence=0.85),
        "OOP": TopicAssessment("OOP", mastery_level=0.60, confidence=0.60),
        "LINEAR_DS": TopicAssessment("LINEAR_DS", mastery_level=0.55, confidence=0.50),
        "TREES_GRAPHS": TopicAssessment("TREES_GRAPHS", mastery_level=0.30, confidence=0.25),
        "DYN_PROG": TopicAssessment("DYN_PROG", mastery_level=0.80, confidence=0.80),
        "TESTING_DEBUG": TopicAssessment("TESTING_DEBUG", mastery_level=0.50, confidence=0.50),
    }
    sam = StudentProfile(
        id="sam_taylor",
        name="Sam Taylor",
        persona_tagline="Uneven Specialist • Balanced Availability (17.5 hrs/wk) • High-Risk Structural Blindspots",
        daily_availability={
            "Monday": 2.5,
            "Tuesday": 2.0,
            "Wednesday": 2.5,
            "Thursday": 2.0,
            "Friday": 2.0,
            "Saturday": 3.5,
            "Sunday": 3.0,
        },
        assessments=sam_assessments,
        assessment_date=target_deadline
    )

    return {
        alex.id: alex,
        maya.id: maya,
        sam.id: sam
    }
