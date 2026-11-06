import os
import re
import sys
import unittest

# Ensure project root is on sys.path when running this file directly.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from planner.course_scheduler import CourseScheduler, normalize_course_code
from database.db_write import LinkDatabase, is_trustworthy_abet_course_title


COURSE_RE = re.compile(r"ISAT\s*\d{3}[A-Z]?", re.IGNORECASE)


def _project_root() -> str:
    return PROJECT_ROOT


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _extract_codes(text: str) -> set[str]:
    return {normalize_course_code(m.group(0)) for m in COURSE_RE.finditer(text)}


def _flatten_schedule_codes(schedule_output: dict) -> list[str]:
    codes: list[str] = []
    for sem in schedule_output["semesters"]:
        for course in sem["courses"]:
            codes.append(normalize_course_code(course["code"]))
    return codes


class TestCourseSchedulerAccuracy(unittest.TestCase):
    CASES = [
        (
            "applied computing",
            "energy",
            ["ISAT 440", "ISAT 441", "ISAT 445", "ISAT 449"],
            ["ISAT 301", "ISAT 310", "ISAT 311"],
        ),
        (
            "applied biotechnology",
            "applied biotechnology",
            ["ISAT 451", "ISAT 452", "ISAT 454", "ISAT 455"],
            ["ISAT 305", "ISAT 350", "ISAT 351"],
        ),
        (
            "industrial and manufacturing systems",
            "industrial and manufacturing systems",
            ["ISAT 430", "ISAT 431", "ISAT 432", "ISAT 433"],
            ["ISAT 303", "ISAT 330", "ISAT 331"],
        ),
    ]

    def test_generated_schedule_matches_reference_constraints(self) -> None:
        """
        Validate generated schedule against three source docs:
        1) ISAT_RAG_requirements_reference.md
        2) data_isat_website/aboutconcentrations.md
        3) data_isat_website/program_schedules.md
        """
        root = _project_root()
        requirements_text = _read(os.path.join(root, "ISAT_RAG_requirements_reference.md"))
        concentrations_text = _read(os.path.join(root, "data_isat_website", "aboutconcentrations.md"))
        program_text = _read(os.path.join(root, "data_isat_website", "program_schedules.md"))

        trusted_codes = _extract_codes(requirements_text) | _extract_codes(program_text)
        scheduler = CourseScheduler(project_root=root)

        for concentration, sector, selected_courses, expected_sector_courses in self.CASES:
            with self.subTest(concentration=concentration, sector=sector):
                print("\n" + "=" * 72)
                print(f"Running scheduler accuracy subtest")
                print(f"Concentration: {concentration}")
                print(f"Sector: {sector}")
                print(f"Selected concentration courses: {selected_courses}")
                output = scheduler.plan(
                    {
                        "concentration": concentration,
                        "sector": sector,
                        "selected_concentration_courses": selected_courses,
                    }
                )
                print(f"Generated semesters: {len(output['semesters'])}")
                print(f"Totals: {output['totals']}")

                # 1) Must be exactly 4 years (8 semesters) + totals from requirements reference (120 credits)
                self.assertEqual(len(output["semesters"]), 8)
                self.assertEqual(output["totals"]["planned_credits"], 120)
                self.assertEqual(output["totals"]["degree_target"], 120)
                self.assertGreaterEqual(output["semesters"][0]["total_credits"], 12)
                self.assertLessEqual(output["semesters"][0]["total_credits"], 18)
                self.assertGreaterEqual(output["semesters"][1]["total_credits"], 12)
                self.assertLessEqual(output["semesters"][1]["total_credits"], 18)

                # 2) Course validity from requirements/program docs
                generated_codes = _flatten_schedule_codes(output)
                invalid = [c for c in generated_codes if c not in trusted_codes and c != "GENED"]
                self.assertFalse(invalid, msg=f"Generated unknown course codes not in references: {invalid}")

                # 3) Capstone sequence from program_schedules
                capstone_position: dict[str, int] = {}
                for idx, sem in enumerate(output["semesters"]):
                    for course in sem["courses"]:
                        code = normalize_course_code(course["code"])
                        if code in {"ISAT 490", "ISAT 491", "ISAT 492", "ISAT 493"}:
                            capstone_position[code] = idx
                print(f"Capstone positions: {capstone_position}")
                self.assertLess(capstone_position["ISAT 490"], capstone_position["ISAT 491"])
                self.assertLess(capstone_position["ISAT 491"], capstone_position["ISAT 492"])
                self.assertLess(capstone_position["ISAT 492"], capstone_position["ISAT 493"])

                # 4) Selected concentration courses must appear in plan and be documented in reference sources.
                for selected in selected_courses:
                    self.assertIn(selected, generated_codes)
                    self.assertIn(selected, trusted_codes)

                # 5) Sector-specific course presence from program_schedules
                for sector_course in expected_sector_courses:
                    self.assertIn(sector_course, generated_codes)
                    self.assertIn(sector_course, trusted_codes)

                # 6) aboutconcentrations coverage: names in scheduler options are represented in concentration doc.
                about_lower = concentrations_text.lower()
                for name in [
                    "applied biotechnology",
                    "applied computing",
                    "energy",
                    "environment",
                    "industrial",
                    "public interest technology",
                ]:
                    self.assertIn(name, about_lower)

                # Semester headers must match the sum of listed course rows (no drift).
                for sem in output["semesters"]:
                    self.assertEqual(
                        sem["total_credits"],
                        sum(c["credits"] for c in sem["courses"]),
                        msg=sem["term"],
                    )

                # 7) Keep upper-year semester loads reasonable (avoid extreme 18 vs 3 swings).
                upper_year = output["semesters"][4:8]
                for sem in upper_year:
                    self.assertGreaterEqual(
                        sem["total_credits"],
                        12,
                        msg=f"Upper-year semester too light: {sem['term']}",
                    )

    def _base_input(self, **overrides) -> dict:
        data = {
            "concentration": "applied computing",
            "sector": "energy",
            "selected_concentration_courses": ["ISAT 440", "ISAT 441", "ISAT 445", "ISAT 449"],
            "standing": "freshman",
            "graduation_timing": "on_time",
            "taken_courses": [],
        }
        data.update(overrides)
        return data

    def test_plan_graph_contains_required_prereqs_and_taken(self) -> None:
        scheduler = CourseScheduler(project_root=_project_root())
        taken = ["ISAT 112", "ISAT 151"]
        graph = scheduler.build_graph(self._base_input(taken_courses=taken))
        self.assertIn("ISAT 112", graph.taken_codes)
        self.assertIn("ISAT 151", graph.taken_codes)
        self.assertNotIn("ISAT 112", graph.remaining_codes)
        for code in ["ISAT 112", "ISAT 211", "ISAT 252", "ISAT 300", "ISAT 490", "ISAT 440", "ISAT 301"]:
            self.assertIn(code, graph.nodes, msg=f"missing required node {code}")
        self.assertEqual(set(graph.prereq_graph), set(graph.nodes))
        for code, prereqs in graph.prereq_graph.items():
            for p in prereqs:
                self.assertIn(p, graph.nodes)

    def test_taken_first_year_courses_are_not_replanned(self) -> None:
        scheduler = CourseScheduler(project_root=_project_root())
        taken = ["ISAT 112", "ISAT 113", "ISAT 113L"]
        output = scheduler.plan(self._base_input(taken_courses=taken))
        copies = [
            (idx, c)
            for idx, sem in enumerate(output["semesters"])
            for c in sem["courses"]
            if normalize_course_code(c["code"]) == "ISAT 112"
        ]
        self.assertEqual(len(copies), 1)
        self.assertEqual(copies[0][1].get("status"), "taken")
        remaining_112 = [
            c
            for sem in output["semesters"]
            for c in sem["courses"]
            if normalize_course_code(c["code"]) == "ISAT 112" and c.get("status") != "taken"
        ]
        self.assertFalse(remaining_112)

    def _inject_prereq_pair(self, graph) -> None:
        from planner.plan_graph import CourseNode

        for code, title, prereqs, status in (
            ("ISAT 350", "Biotechnology for the New Millennium I", [], "remaining"),
            ("ISAT 351", "Biotechnology for the New Millennium II", ["ISAT 350"], "remaining"),
        ):
            if code not in graph.nodes:
                graph.nodes[code] = CourseNode(
                    code=code,
                    title=title,
                    credits=3,
                    category="Sector",
                    prereqs=prereqs,
                    status=status,
                )
            else:
                graph.nodes[code].prereqs = prereqs
                graph.nodes[code].status = status
            graph.prereq_graph[code] = list(prereqs)
            if status == "remaining" and code not in graph.remaining_codes:
                graph.remaining_codes.append(code)

    def test_remaining_course_never_before_prereqs(self) -> None:
        scheduler = CourseScheduler(project_root=_project_root())
        graph = scheduler.build_graph(self._base_input())
        self._inject_prereq_pair(graph)
        output = scheduler.plan_from_graph(graph)
        positions: dict[str, int] = {}
        for idx, sem in enumerate(output["semesters"]):
            for course in sem["courses"]:
                code = normalize_course_code(course["code"])
                if code in {"ISAT 350", "ISAT 351"}:
                    positions[code] = idx
        self.assertLess(positions["ISAT 350"], positions["ISAT 351"])

        taken_graph = scheduler.build_graph(self._base_input(taken_courses=["ISAT 350"]))
        self._inject_prereq_pair(taken_graph)
        taken_graph.mark_taken("ISAT 350")
        taken_out = scheduler.plan_from_graph(taken_graph)
        pos = {}
        status_350 = None
        for idx, sem in enumerate(taken_out["semesters"]):
            for course in sem["courses"]:
                code = normalize_course_code(course["code"])
                if code in {"ISAT 350", "ISAT 351"}:
                    pos[code] = idx
                if code == "ISAT 350":
                    status_350 = course.get("status")
        self.assertEqual(status_350, "taken")
        self.assertGreaterEqual(pos["ISAT 351"], pos["ISAT 350"])

    def test_sophomore_standing_keeps_first_year_as_past(self) -> None:
        scheduler = CourseScheduler(project_root=_project_root())
        first_year = [
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
        output = scheduler.plan(
            self._base_input(standing="sophomore", taken_courses=first_year)
        )
        self.assertGreaterEqual(len(output["semesters"]), 8)
        for sem in output["semesters"][:2]:
            for course in sem["courses"]:
                if normalize_course_code(course["code"]).startswith("ISAT"):
                    self.assertEqual(course.get("status"), "taken", msg=course)
        remaining_first_year = [
            normalize_course_code(c["code"])
            for sem in output["semesters"][2:]
            for c in sem["courses"]
            if normalize_course_code(c["code"]) in set(first_year) and c.get("status") != "taken"
        ]
        self.assertFalse(remaining_first_year)

    def test_sophomore_with_only_gen_ed_credits(self) -> None:
        scheduler = CourseScheduler(project_root=_project_root())
        graph = scheduler.build_graph(
            self._base_input(standing="sophomore", taken_courses=[], gen_ed_credits=30)
        )
        self.assertEqual(graph.major_credits_completed, 0)
        self.assertEqual(graph.gen_ed_credits_completed, 30)
        self.assertEqual(graph.gen_ed_credits_remaining, 11)
        self.assertEqual(graph.credits_completed, 30)

        output = scheduler.plan_from_graph(graph)
        totals = output["totals"]
        self.assertEqual(totals["major_credits_completed"], 0)
        self.assertEqual(totals["gen_ed_credits_completed"], 30)
        self.assertGreaterEqual(totals["gen_ed_credits_planned"], 41)

        first_year_isat_remaining = [
            c
            for sem in output["semesters"][:2]
            for c in sem["courses"]
            if normalize_course_code(c["code"]).startswith("ISAT") and c.get("status") != "taken"
        ]
        self.assertFalse(first_year_isat_remaining)
        taken_gen = [
            c
            for sem in output["semesters"][:2]
            for c in sem["courses"]
            if c.get("category") == "General Education" and c.get("status") == "taken"
        ]
        self.assertGreaterEqual(sum(c["credits"] for c in taken_gen), 30)

    def test_already_took_followup_marks_course_taken(self) -> None:
        from planner.plan_graph import apply_plan_edits
        from planner.schedule_render import format_schedule_message

        scheduler = CourseScheduler(project_root=_project_root())
        graph = scheduler.build_graph(self._base_input())
        self.assertIn("ISAT 252", graph.remaining_codes)
        apply_plan_edits(graph, "I already took ISAT 252")
        self.assertIn("ISAT 252", graph.taken_codes)
        self.assertNotIn("ISAT 252", graph.remaining_codes)
        output = scheduler.plan_from_graph(graph)
        copies = [
            c
            for sem in output["semesters"]
            for c in sem["courses"]
            if normalize_course_code(c["code"]) == "ISAT 252"
        ]
        self.assertTrue(copies)
        self.assertTrue(all(c.get("status") == "taken" for c in copies))
        rendered = format_schedule_message(
            "applied computing",
            "energy",
            ["ISAT 440", "ISAT 441", "ISAT 445", "ISAT 449"],
            output,
            credits_completed_prior=int(output["totals"].get("credits_completed") or 0),
        )
        self.assertIn("Completed coursework", rendered)
        self.assertIn("past-course", rendered)
        self.assertIn("ISAT 252", rendered)
        self.assertIn("ISAT major credits completed", rendered)
        self.assertIn("General Education credits completed", rendered)

    def test_abet_title_sanity_rejects_boilerplate(self) -> None:
        bad = (
            "Please use the following format for the course syllabi "
            "(2 pages maximum in Times New Roman 12-point font)"
        )
        self.assertFalse(is_trustworthy_abet_course_title(bad))
        self.assertTrue(is_trustworthy_abet_course_title("Systems Integration"))

    def test_abet_is_primary_source_when_available(self) -> None:
        """
        ABET syllabi override the courses table when both exist; course titles from ABET
        are used only when they pass sanity checks (otherwise the catalog name is kept).
        """
        db = LinkDatabase()
        try:
            abet_rows = db.fetch_all_abet_syllabi()
            if not abet_rows:
                self.skipTest("No ABET rows found to validate precedence.")

            merged = db.fetch_course_catalog_abet_first()
            merged_by_code = {row["course_code"]: row for row in merged}
            abet_codes = {normalize_course_code(row.get("course_code") or "") for row in abet_rows}
            abet_codes = {c for c in abet_codes if c}

            # Validate precedence on a representative subset of ABET codes present in merged catalog.
            checked = 0
            for code in sorted(abet_codes):
                row = merged_by_code.get(code)
                if not row:
                    continue
                self.assertEqual(row.get("source"), "abet_syllabi", msg=f"Expected ABET source for {code}")
                checked += 1
                if checked >= 10:
                    break
            self.assertGreater(checked, 0, "No overlapping ABET/catalog course codes were validated.")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
    