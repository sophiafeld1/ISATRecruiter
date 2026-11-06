import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from planner.plan_graph import (
    apply_plan_edits,
    core_checklist_groups,
    looks_like_schedule_edit,
    parse_completed_courses,
    parse_gen_ed_credits,
    parse_graduation_timing,
    parse_standing,
    parse_timing_constraints,
)


class TestPlanGraphParsers(unittest.TestCase):
    def test_parse_standing_from_chip_labels(self) -> None:
        self.assertEqual(parse_standing("Freshman (0–29 credits)"), "freshman")
        self.assertEqual(parse_standing("Sophomore (30–59 credits)"), "sophomore")
        self.assertEqual(parse_standing("Junior (60–89 credits)"), "junior")
        self.assertEqual(parse_standing("Senior (90+ credits)"), "senior")
        self.assertEqual(parse_standing("softmore"), "sophomore")

    def test_parse_graduation_timing(self) -> None:
        self.assertEqual(parse_graduation_timing("On time"), "on_time")
        self.assertEqual(parse_graduation_timing("Extra semester"), "extra_semester")
        self.assertEqual(parse_graduation_timing("Extra year"), "extra_year")
        self.assertEqual(parse_graduation_timing("Graduate a semester early"), "semester_early")
        self.assertEqual(parse_graduation_timing("Graduate a year early"), "year_early")

    def test_parse_gen_ed_credits(self) -> None:
        answered, n = parse_gen_ed_credits("None yet (0)")
        self.assertTrue(answered)
        self.assertEqual(n, 0)
        answered, n = parse_gen_ed_credits("30 credits")
        self.assertTrue(answered)
        self.assertEqual(n, 30)
        answered, n = parse_gen_ed_credits("I have 15")
        self.assertTrue(answered)
        self.assertEqual(n, 15)
        answered, n = parse_gen_ed_credits("50")
        self.assertTrue(answered)
        self.assertEqual(n, 41)

    def test_parse_completed_courses_none_yet(self) -> None:
        answered, codes = parse_completed_courses("None yet")
        self.assertTrue(answered)
        self.assertEqual(codes, [])

    def test_parse_completed_courses_codes(self) -> None:
        answered, codes = parse_completed_courses("ISAT 112, ISAT 151")
        self.assertTrue(answered)
        self.assertEqual(codes, ["ISAT 112", "ISAT 151"])

    def test_parse_timing_constraints_explicit_term(self) -> None:
        out = parse_timing_constraints("take ISAT 300 in Third Year Fall")
        self.assertEqual(out.get("ISAT 300"), 4)

    def test_looks_like_schedule_edit(self) -> None:
        self.assertTrue(looks_like_schedule_edit("I already took ISAT 252"))
        self.assertTrue(looks_like_schedule_edit("move ISAT 300 to Third Year Spring"))
        self.assertFalse(looks_like_schedule_edit("What is ISAT?"))

    def test_core_checklist_includes_capstone_for_juniors(self) -> None:
        freshman_titles = [t for t, _ in core_checklist_groups("freshman")]
        junior_titles = [t for t, _ in core_checklist_groups("junior")]
        self.assertNotIn("Senior Capstone Project", freshman_titles)
        self.assertIn("Senior Capstone Project", junior_titles)


class TestApplyPlanEdits(unittest.TestCase):
    def test_swap_concentration_course(self) -> None:
        from planner.course_scheduler import CourseScheduler
        from planner.plan_graph import CourseNode

        scheduler = CourseScheduler(project_root=PROJECT_ROOT)
        graph = scheduler.build_graph(
            {
                "concentration": "applied computing",
                "sector": "energy",
                "selected_concentration_courses": ["ISAT 440", "ISAT 441", "ISAT 445", "ISAT 449"],
            }
        )
        extra = scheduler.concentration_options("applied computing")
        apply_plan_edits(graph, "swap ISAT 449 for ISAT 447", extra_nodes=extra)
        self.assertIn("ISAT 447", graph.selected_concentration_courses)
        self.assertNotIn("ISAT 449", graph.selected_concentration_courses)
        self.assertIsInstance(graph.nodes.get("ISAT 447"), CourseNode)


if __name__ == "__main__":
    unittest.main()
