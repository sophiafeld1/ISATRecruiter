"""
Student-profile use cases for the course planner, plus follow-up edit checks.
"""

from __future__ import annotations

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from LangGraph.main import _get_intake_state, _handle_schedule_intake
from planner.course_scheduler import CourseScheduler, normalize_course_code
from planner.plan_graph import apply_plan_edits
from planner.schedule_render import format_schedule_message


FIRST_YEAR_ISAT = [
    "ISAT 112",
    "ISAT 113",
    "ISAT 113L",
    "ISAT 151",
    "ISAT 171",
    "ISAT 211",
    "ISAT 212",
    "ISAT 152",
    "ISAT 251",
]
SOPHOMORE_ISAT = FIRST_YEAR_ISAT + ["ISAT 190", "ISAT 252", "ISAT 271"]
JUNIOR_ISAT = SOPHOMORE_ISAT + ["ISAT 290", "ISAT 300", "ISAT 390"]
SENIOR_ISAT = JUNIOR_ISAT + ["ISAT 391", "ISAT 301", "ISAT 310", "ISAT 311", "ISAT 490", "ISAT 491"]
ELECTIVES = ["ISAT 440", "ISAT 441", "ISAT 445", "ISAT 449"]


def _positions(output: dict) -> tuple[dict[str, int], dict[str, str]]:
    pos: dict[str, int] = {}
    status: dict[str, str] = {}
    for idx, sem in enumerate(output["semesters"]):
        for course in sem["courses"]:
            code = normalize_course_code(course.get("code") or "")
            if not code or code == "GENED":
                continue
            pos[code] = idx
            status[code] = course.get("status") or "remaining"
    return pos, status


def _isat_codes(output: dict, *, taken: bool | None = None) -> set[str]:
    out: set[str] = set()
    for sem in output["semesters"]:
        for course in sem["courses"]:
            code = normalize_course_code(course.get("code") or "")
            if not code.startswith("ISAT"):
                continue
            is_taken = (course.get("status") or "") == "taken"
            if taken is None or is_taken is taken:
                out.add(code)
    return out


class TestScheduleUseCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scheduler = CourseScheduler(project_root=PROJECT_ROOT)

    def _input(self, **overrides) -> dict:
        data = {
            "concentration": "applied computing",
            "sector": "energy",
            "selected_concentration_courses": list(ELECTIVES),
            "standing": "freshman",
            "graduation_timing": "on_time",
            "taken_courses": [],
            "gen_ed_credits": 0,
        }
        data.update(overrides)
        return data

    def _plan(self, **overrides):
        payload = self._input(**overrides)
        graph = self.scheduler.build_graph(payload)
        output = self.scheduler.plan_from_graph(graph)
        return graph, output

    def _assert_prereqs_held(self, graph, output: dict) -> None:
        pos, status = _positions(output)
        for code, prereqs in graph.prereq_graph.items():
            if code not in pos or status.get(code) == "taken":
                continue
            for prereq in prereqs:
                pc = normalize_course_code(prereq)
                if not pc:
                    continue
                if pc in graph.taken_codes or status.get(pc) == "taken":
                    continue
                self.assertIn(pc, pos, msg=f"{code} is missing prerequisite {pc} in the schedule")
                self.assertLess(
                    pos[pc],
                    pos[code],
                    msg=f"{pc} must be scheduled before {code}",
                )

    def _assert_taken_not_replanned(self, output: dict, taken: list[str]) -> None:
        remaining = _isat_codes(output, taken=False)
        for code in taken:
            self.assertNotIn(normalize_course_code(code), remaining)

    def test_prospective_student_full_four_year_plan(self) -> None:
        graph, output = self._plan()
        self.assertEqual(graph.standing, "freshman")
        self.assertEqual(graph.major_credits_completed, 0)
        self.assertEqual(graph.gen_ed_credits_completed, 0)
        self.assertEqual(len(output["semesters"]), 8)
        self.assertEqual(output["totals"]["planned_credits"], 120)
        self.assertEqual(output["totals"]["degree_target"], 120)
        generated = _isat_codes(output)
        for code in ELECTIVES + ["ISAT 490", "ISAT 491", "ISAT 492", "ISAT 493", "ISAT 112"]:
            self.assertIn(code, generated)
        self.assertFalse(_isat_codes(output, taken=True))
        self._assert_prereqs_held(graph, output)

        rendered = format_schedule_message(
            "applied computing",
            "energy",
            ELECTIVES,
            output,
        )
        self.assertIn("ISAT major credits completed:** 0", rendered)
        self.assertIn("General Education credits completed:** 0 / 41", rendered)
        self.assertIn("#### First Year", rendered)
        self.assertIn("#### Fourth Year", rendered)

    def test_sophomore_with_gen_ed_and_one_isat_course(self) -> None:
        taken = ["ISAT 112"]
        graph, output = self._plan(
            standing="sophomore",
            taken_courses=taken,
            gen_ed_credits=30,
        )
        self.assertEqual(graph.gen_ed_credits_completed, 30)
        self.assertEqual(graph.major_credits_completed, graph.nodes["ISAT 112"].credits)
        self.assertEqual(graph.credits_completed, 30 + graph.nodes["ISAT 112"].credits)
        self.assertIn("ISAT 112", graph.taken_codes)
        self._assert_taken_not_replanned(output, taken)
        self.assertEqual(_isat_codes(output, taken=True), {"ISAT 112"})

        remaining_in_first_year = [
            normalize_course_code(c["code"])
            for sem in output["semesters"][:2]
            for c in sem["courses"]
            if normalize_course_code(c["code"]).startswith("ISAT") and c.get("status") != "taken"
        ]
        self.assertFalse(remaining_in_first_year)
        taken_gen = [
            c
            for sem in output["semesters"]
            for c in sem["courses"]
            if c.get("category") == "General Education" and c.get("status") == "taken"
        ]
        placed_gen = sum(int(c["credits"]) for c in taken_gen)
        unplaced = int(output["totals"].get("unplaced_completed_gen_ed") or 0)
        self.assertGreater(placed_gen, 0)
        self.assertGreaterEqual(placed_gen + unplaced, 30)
        self.assertEqual(output["totals"]["gen_ed_credits_completed"], 30)
        self.assertGreaterEqual(output["totals"]["gen_ed_credits_planned"], 41)
        self._assert_prereqs_held(graph, output)

    def test_sophomore_isat_only_no_gen_ed(self) -> None:
        graph, output = self._plan(
            standing="sophomore",
            taken_courses=FIRST_YEAR_ISAT,
            gen_ed_credits=0,
        )
        self.assertEqual(graph.gen_ed_credits_completed, 0)
        self.assertGreater(graph.major_credits_completed, 0)
        self.assertEqual(graph.gen_ed_credits_remaining, 41)
        self._assert_taken_not_replanned(output, FIRST_YEAR_ISAT)
        for code in FIRST_YEAR_ISAT:
            self.assertIn(code, _isat_codes(output, taken=True))
        self.assertGreaterEqual(output["totals"]["gen_ed_credits_planned"], 41)
        self._assert_prereqs_held(graph, output)

    def test_junior_with_gen_ed_and_isat_progress(self) -> None:
        graph, output = self._plan(
            standing="junior",
            taken_courses=JUNIOR_ISAT,
            gen_ed_credits=30,
        )
        self.assertEqual(graph.standing, "junior")
        self.assertEqual(graph.first_future_semester, 4)
        self.assertEqual(graph.gen_ed_credits_completed, 30)
        self.assertGreater(graph.major_credits_completed, graph.nodes["ISAT 112"].credits)
        self._assert_taken_not_replanned(output, JUNIOR_ISAT)
        remaining = _isat_codes(output, taken=False)
        self.assertTrue(remaining)
        self.assertIn("ISAT 492", remaining)
        self.assertIn("ISAT 493", remaining)
        for code in JUNIOR_ISAT:
            self.assertNotIn(code, remaining)
        self._assert_prereqs_held(graph, output)

    def test_senior_planning_last_year(self) -> None:
        graph, output = self._plan(
            standing="senior",
            taken_courses=SENIOR_ISAT + ["ISAT 440", "ISAT 441"],
            gen_ed_credits=41,
            selected_concentration_courses=ELECTIVES,
        )
        self.assertEqual(graph.standing, "senior")
        self.assertEqual(graph.first_future_semester, 6)
        self.assertEqual(graph.remaining_term_count, 2)
        self.assertEqual(graph.gen_ed_credits_completed, 41)
        self.assertEqual(graph.gen_ed_credits_remaining, 0)
        remaining = _isat_codes(output, taken=False)
        self.assertIn("ISAT 492", remaining)
        self.assertIn("ISAT 493", remaining)
        self.assertNotIn("ISAT 490", remaining)
        self.assertNotIn("ISAT 112", remaining)
        pos, _ = _positions(output)
        self.assertGreaterEqual(pos["ISAT 492"], 6)
        self.assertGreater(pos["ISAT 493"], pos["ISAT 492"])
        self._assert_prereqs_held(graph, output)

    def test_semester_early_with_high_school_gen_ed(self) -> None:
        graph, output = self._plan(
            standing="freshman",
            graduation_timing="semester_early",
            taken_courses=[],
            gen_ed_credits=41,
        )
        self.assertEqual(graph.graduation_timing, "semester_early")
        self.assertEqual(graph.remaining_term_count, 7)
        self.assertEqual(graph.gen_ed_credits_completed, 41)
        self.assertEqual(graph.gen_ed_credits_remaining, 0)
        self.assertEqual(output["totals"]["gen_ed_credits_completed"], 41)
        self.assertGreaterEqual(len(output["semesters"]), 8)
        self._assert_prereqs_held(graph, output)

    def test_all_gen_ed_behind_on_isat_semester_late(self) -> None:
        graph, output = self._plan(
            standing="sophomore",
            graduation_timing="extra_semester",
            taken_courses=["ISAT 112", "ISAT 151"],
            gen_ed_credits=41,
        )
        self.assertEqual(graph.gen_ed_credits_completed, 41)
        self.assertEqual(graph.gen_ed_credits_remaining, 0)
        self.assertEqual(graph.remaining_term_count, 7)
        self.assertGreaterEqual(len(output["semesters"]), 9)
        self.assertIn("Additional Semester 1", [s["term"] for s in output["semesters"]])
        remaining = _isat_codes(output, taken=False)
        self.assertIn("ISAT 211", remaining)
        self.assertNotIn("ISAT 112", remaining)
        self._assert_prereqs_held(graph, output)

    def test_graduate_a_year_late(self) -> None:
        graph, output = self._plan(
            standing="junior",
            graduation_timing="extra_year",
            taken_courses=FIRST_YEAR_ISAT,
            gen_ed_credits=15,
        )
        self.assertEqual(graph.graduation_timing, "extra_year")
        self.assertEqual(graph.remaining_term_count, 6)
        self.assertGreaterEqual(len(output["semesters"]), 10)
        extra_terms = [s["term"] for s in output["semesters"] if s["term"].startswith("Additional")]
        self.assertGreaterEqual(len(extra_terms), 2)
        self._assert_prereqs_held(graph, output)

    def test_edits_already_took_course_keeps_prereqs(self) -> None:
        graph, _ = self._plan()
        self.assertIn("ISAT 252", graph.remaining_codes)
        apply_plan_edits(graph, "I already took ISAT 252")
        output = self.scheduler.plan_from_graph(graph)
        self.assertIn("ISAT 252", graph.taken_codes)
        self.assertNotIn("ISAT 252", graph.remaining_codes)
        self._assert_taken_not_replanned(output, ["ISAT 252"])
        self._assert_prereqs_held(graph, output)
        copies = [
            c
            for sem in output["semesters"]
            for c in sem["courses"]
            if normalize_course_code(c["code"]) == "ISAT 252"
        ]
        self.assertTrue(copies)
        self.assertTrue(all(c.get("status") == "taken" for c in copies))

    def test_edits_move_and_swap_keep_prereqs(self) -> None:
        graph, before = self._plan(standing="sophomore", taken_courses=FIRST_YEAR_ISAT, gen_ed_credits=0)
        extra = self.scheduler.concentration_options("applied computing")
        apply_plan_edits(graph, "move ISAT 300 to Third Year Fall", extra_nodes=extra)
        apply_plan_edits(graph, "swap ISAT 449 for ISAT 447", extra_nodes=extra)
        after = self.scheduler.plan_from_graph(graph)

        pos, status = _positions(after)
        self.assertEqual(pos.get("ISAT 300"), 4)
        self.assertEqual(status.get("ISAT 300"), "remaining")
        self.assertIn("ISAT 447", graph.selected_concentration_courses)
        self.assertNotIn("ISAT 449", graph.selected_concentration_courses)
        self.assertIn("ISAT 447", _isat_codes(after))
        self.assertNotIn("ISAT 449", _isat_codes(after, taken=False))
        self._assert_prereqs_held(graph, after)

        before_pos, _ = _positions(before)
        self.assertIn("ISAT 449", before_pos)

    def test_intake_then_edit_is_reflected_in_message(self) -> None:
        history = [
            {"role": "user", "content": "Generate a course schedule"},
            {"role": "assistant", "content": "What year standing are you? Choose one: Freshman (0–29 credits)."},
            {"role": "user", "content": "Freshman (0–29 credits)"},
            {
                "role": "assistant",
                "content": "Are you planning to graduate on time with your class year? Choose one: On time.",
            },
            {"role": "user", "content": "On time"},
            {
                "role": "assistant",
                "content": (
                    "How many General Education credits have you already completed? "
                    "The requirement is 41 credits. Type a number from 0 to 41, or choose one: None yet (0)."
                ),
            },
            {"role": "user", "content": "None yet (0)"},
            {
                "role": "assistant",
                "content": (
                    "Which of these ISAT core courses have you already completed? "
                    "Check all that apply, or choose None yet."
                ),
            },
            {"role": "user", "content": "None yet"},
            {"role": "assistant", "content": "What concentration do you want to complete?"},
            {"role": "user", "content": "Applied Computing"},
            {"role": "assistant", "content": "Which sector do you want to complete? Available sectors: Energy."},
            {"role": "user", "content": "Energy"},
            {
                "role": "assistant",
                "content": (
                    "For Applied Computing, choose exactly 4 concentration courses from: "
                    "ISAT 440, ISAT 441, ISAT 445, ISAT 447, ISAT 449."
                ),
            },
            {"role": "user", "content": "ISAT 440, ISAT 441, ISAT 445, ISAT 449"},
            {
                "role": "assistant",
                "content": (
                    "If you need specific courses in specific terms, type that now, "
                    "or choose Generate my schedule."
                ),
            },
        ]
        state, _ = _get_intake_state("Generate my schedule", history)
        self.assertEqual(state, "ready_to_generate_schedule")
        schedule = _handle_schedule_intake("Generate my schedule", history)
        self.assertIn("four-year sample plan", schedule.lower())
        self.assertIn("ISAT major credits completed:** 0", schedule)

        after_schedule = history + [
            {"role": "user", "content": "Generate my schedule"},
            {"role": "assistant", "content": schedule},
        ]
        state, _ = _get_intake_state("I already took ISAT 252", after_schedule)
        self.assertEqual(state, "awaiting_schedule_edits")
        edited = _handle_schedule_intake("I already took ISAT 252", after_schedule)
        self.assertIn("ISAT 252", edited)
        self.assertIn("past-course", edited)
        self.assertIn("Completed coursework", edited)


if __name__ == "__main__":
    unittest.main()
