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
    