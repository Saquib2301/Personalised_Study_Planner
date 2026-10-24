"""
Availability Verification Engine.
Performs strict mathematical and constraint checks to ensure that
scheduled study time NEVER exceeds any student's stated daily or weekly availability.
"""

from typing import Any, Dict, List
from models import StudyPlan


class AvailabilityVerifier:
    """
    Validates adherence to availability constraints and produces
    detailed audit reports.
    """

    TOLERANCE = 1e-4

    @classmethod
    def verify(cls, plan: StudyPlan) -> Dict[str, Any]:
        """
        Executes a rigorous audit of the generated study plan against the student's constraints.
        Returns a dictionary with comprehensive audit metrics and validation status.
        """
        daily_audits: List[Dict[str, Any]] = []
        violations: List[str] = []

        total_available = plan.total_available_hours
        total_scheduled = 0.0

        for day in plan.days:
            sched = day.scheduled_hours
            avail = day.available_hours
            buffer = round(avail - sched, 2)
            utilization_pct = round((sched / avail * 100) if avail > 0 else 0.0, 1)

            # Strict Invariant: Scheduled <= Available + TOLERANCE
            is_valid = sched <= (avail + cls.TOLERANCE)
            if not is_valid:
                overage = round(sched - avail, 2)
                violations.append(
                    f"VIOLATION on {day.day_name} ({day.date_str}): "
                    f"Scheduled {sched} hrs exceeds availability of {avail} hrs by {overage} hrs!"
                )

            daily_audits.append({
                "day_name": day.day_name,
                "date_str": day.date_str,
                "available_hours": avail,
                "scheduled_hours": sched,
                "buffer_hours": buffer,
                "utilization_pct": utilization_pct,
                "session_count": len(day.sessions),
                "is_valid": is_valid
            })
            total_scheduled += sched

        total_scheduled = round(total_scheduled, 2)
        total_buffer = round(total_available - total_scheduled, 2)
        total_utilization = round((total_scheduled / total_available * 100) if total_available > 0 else 0.0, 1)

        total_is_valid = total_scheduled <= (total_available + cls.TOLERANCE)
        if not total_is_valid:
            violations.append(
                f"GLOBAL VIOLATION: Total scheduled ({total_scheduled}h) "
                f"exceeds total weekly availability ({total_available}h)!"
            )

        all_passed = total_is_valid and (len(violations) == 0)

        return {
            "student_name": plan.student_name,
            "student_id": plan.student_id,
            "all_passed": all_passed,
            "status": "PASS" if all_passed else "FAIL",
            "total_available_hours": total_available,
            "total_scheduled_hours": total_scheduled,
            "total_buffer_hours": total_buffer,
            "overall_utilization_pct": total_utilization,
            "violations": violations,
            "daily_audits": daily_audits,
        }

    @classmethod
    def format_report_text(cls, audit: Dict[str, Any]) -> str:
        """Formats audit results into a clean, human-readable terminal table."""
        lines = []
        lines.append("=" * 78)
        status_tag = "[PASS] ALL CONSTRAINTS SATISFIED" if audit["all_passed"] else "[FAIL] CONSTRAINTS VIOLATED"
        lines.append(f" AVAILABILITY COMPLIANCE AUDIT: {audit['student_name']} -> {status_tag}")
        lines.append("=" * 78)
        lines.append(f"{'Day':<11} | {'Date':<10} | {'Available':<10} | {'Scheduled':<10} | {'Buffer':<8} | {'Util %':<7} | {'Status':<6}")
        lines.append("-" * 78)

        for d in audit["daily_audits"]:
            status = "PASS" if d["is_valid"] else "FAIL"
            lines.append(
                f"{d['day_name']:<11} | "
                f"{d['date_str']:<10} | "
                f"{d['available_hours']:>7.1f} h | "
                f"{d['scheduled_hours']:>7.1f} h | "
                f"{d['buffer_hours']:>5.1f} h | "
                f"{d['utilization_pct']:>5.1f}% | "
                f"{status}"
            )

        lines.append("-" * 78)
        lines.append(
            f"{'TOTAL':<11} | {'7 Days':<10} | "
            f"{audit['total_available_hours']:>7.1f} h | "
            f"{audit['total_scheduled_hours']:>7.1f} h | "
            f"{audit['total_buffer_hours']:>5.1f} h | "
            f"{audit['overall_utilization_pct']:>5.1f}% | "
            f"{audit['status']}"
        )
        lines.append("=" * 78)

        if audit["violations"]:
            lines.append("VIOLATIONS DETECTED:")
            for v in audit["violations"]:
                lines.append(f" - {v}")
        else:
            lines.append("CHECK CONFIRMED: Scheduled study time does not exceed stated availability on any day.")
            lines.append(f"Reserve buffer maintained: {audit['total_buffer_hours']} hours unallocated for flexibility/rest.")

        lines.append("")
        return "\n".join(lines)
