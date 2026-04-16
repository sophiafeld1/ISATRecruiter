import os
import re
import sys
import unittest

# Ensure project root is on sys.path when running this file directly.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from planner.course_scheduler import CourseScheduler, normalize_course_code


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
                print("Subtest passed.")


if __name__ == "__main__":
    unittest.main()
    