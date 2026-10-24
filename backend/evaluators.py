"""
Evaluation engine for SmartStudy AI.
Handles:
1. Automated Quiz Grading with instant feedback and revision recommendations.
2. Safe Python Code Evaluation against predefined test cases.
"""

import sys
import io
import traceback
from typing import Dict, Any, List


class QuizEvaluator:
    """Grades self-assessment quizzes and returns performance metrics."""

    @classmethod
    def grade_quiz(cls, questions: List[Dict[str, Any]], submitted_answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Grades submitted options against correct_index.
        """
        total = len(questions)
        if total == 0:
            return {
                "total_questions": 0,
                "correct_answers": 0,
                "score_percentage": 100.0,
                "passed": True,
                "feedback": "No questions to grade.",
                "details": []
            }

        correct_count = 0
        details = []

        for idx, q in enumerate(questions):
            # submitted answers can be keyed by str(idx) or int
            user_choice = submitted_answers.get(str(idx), submitted_answers.get(idx))
            correct_choice = q.get("correct_index", 0)

            is_correct = False
            if user_choice is not None and int(user_choice) == int(correct_choice):
                correct_count += 1
                is_correct = True

            details.append({
                "question_index": idx,
                "question": q.get("question"),
                "options": q.get("options", []),
                "user_selected": user_choice,
                "correct_index": correct_choice,
                "is_correct": is_correct,
                "explanation": q.get("explanation", "")
            })

        score_pct = round((correct_count / total) * 100, 1)
        passed = score_pct >= 70.0

        if passed:
            feedback = f"Great work! You scored {score_pct}%. Topic mastery verified."
        else:
            feedback = (
                f"Score: {score_pct}%. Your score is below the 70% threshold. "
                f"This topic has been flagged as 'Needs Revision'. Additional practice drills are recommended."
            )

        return {
            "total_questions": total,
            "correct_answers": correct_count,
            "score_percentage": score_pct,
            "passed": passed,
            "feedback": feedback,
            "details": details
        }


class CodeEvaluator:
    """Safely validates student code submissions against test cases."""

    @classmethod
    def evaluate_code(cls, submitted_code: str, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not submitted_code or submitted_code.strip() == "":
            return {
                "all_passed": False,
                "passed_count": 0,
                "total_count": len(test_cases),
                "message": "No code submitted."
            }

        # Safe execution namespace
        safe_globals = {
            "__builtins__": {
                "range": range,
                "len": len,
                "min": min,
                "max": max,
                "sum": sum,
                "sorted": sorted,
                "list": list,
                "dict": dict,
                "set": set,
                "int": int,
                "float": float,
                "str": str,
                "bool": bool,
                "print": print,
                "enumerate": enumerate,
                "zip": zip,
                "abs": abs
            }
        }
        safe_locals = {}

        try:
            exec(submitted_code, safe_globals, safe_locals)
        except Exception as e:
            return {
                "all_passed": False,
                "passed_count": 0,
                "total_count": len(test_cases),
                "error": f"Syntax or Execution Error: {str(e)}",
                "test_results": []
            }

        results = []
        passed_count = 0

        # Run test cases
        for idx, tc in enumerate(test_cases, 1):
            input_expr = tc.get("input", "()")
            expected_str = tc.get("expected", "")

            # Look for callable in locals
            callables = [f for f in safe_locals.values() if callable(f)]
            if not callables:
                return {
                    "all_passed": False,
                    "passed_count": 0,
                    "total_count": len(test_cases),
                    "error": "No function definition found in your submission.",
                    "test_results": []
                }

            target_func = callables[0]
            try:
                # evaluate input expression
                args = eval(input_expr)
                if not isinstance(args, tuple):
                    args = (args,)
                
                actual_output = target_func(*args)
                actual_str = str(actual_output)
                
                # Check match
                is_pass = actual_str.strip() == expected_str.strip()
                if is_pass:
                    passed_count += 1

                results.append({
                    "test_case": idx,
                    "input": input_expr,
                    "expected": expected_str,
                    "actual": actual_str,
                    "passed": is_pass
                })
            except Exception as e:
                results.append({
                    "test_case": idx,
                    "input": input_expr,
                    "expected": expected_str,
                    "actual": f"Runtime Error: {str(e)}",
                    "passed": False
                })

        all_passed = (passed_count == len(test_cases)) if test_cases else True
        return {
            "all_passed": all_passed,
            "passed_count": passed_count,
            "total_count": len(test_cases),
            "test_results": results,
            "message": "All test cases passed!" if all_passed else f"{passed_count}/{len(test_cases)} test cases passed."
        }
