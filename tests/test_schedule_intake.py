import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from LangGraph.main import _get_intake_state, _handle_schedule_intake


def _history(*pairs: tuple[str, str]) -> list[dict]:
    out: list[dict] = []
    for role, content in pairs:
        out.append({"role": role, "content": content})
    return out


class TestScheduleIntake(unittest.TestCase):
    def test_starts_with_standing(self) -> None:
        state, _ = _get_intake_state("Generate a course schedule", [])
        self.assertEqual(state, "awaiting_standing")
        prompt = _handle_schedule_intake("Generate a course schedule", [])
        self.assertIn("What year standing are you?", prompt)

    def test_intake_order_through_generate(self) -> None:
        h = _history(
            ("user", "Generate a course schedule"),
            ("assistant", "What year standing are you? Choose one: Freshman (0–29 credits)."),
        )
        state, _ = _get_intake_state("Freshman (0–29 credits)", h)
        self.assertEqual(state, "awaiting_graduation_timing")

        h += _history(
            ("user", "Freshman (0–29 credits)"),
            ("assistant", "Are you planning to graduate on time with your class year? Choose one: On time."),
        )
        state, _ = _get_intake_state("On time", h)
        self.assertEqual(state, "awaiting_gen_ed_credits")

        h += _history(
            ("user", "On time"),
            (
                "assistant",
                "How many General Education credits have you already completed? "
                "The requirement is 41 credits. Type a number from 0 to 41, or choose one: None yet (0).",
            ),
        )
        state, payload = _get_intake_state("None yet (0)", h)
        self.assertEqual(state, "awaiting_completed_courses")
        self.assertEqual(payload["gen_ed_credits"], 0)

        h += _history(
            ("user", "None yet (0)"),
            (
                "assistant",
                "Which of these ISAT core courses have you already completed? Check all that apply, or choose None yet.\n\n"
                "Issues in Science and Technology: ISAT 112, ISAT 113",
            ),
        )
        state, payload = _get_intake_state("None yet", h)
        self.assertEqual(state, "awaiting_concentration")
        self.assertEqual(payload["taken_courses"], [])

        h += _history(
            ("user", "None yet"),
            ("assistant", "What concentration do you want to complete?"),
        )
        state, _ = _get_intake_state("Applied Computing", h)
        self.assertEqual(state, "awaiting_sector")

        h += _history(
            ("user", "Applied Computing"),
            ("assistant", "Which sector do you want to complete? Available sectors: Energy."),
        )
        state, _ = _get_intake_state("Energy", h)
        self.assertEqual(state, "awaiting_concentration_course_selection")

        h += _history(
            ("user", "Energy"),
            (
                "assistant",
                "For Applied Computing, choose exactly 4 concentration courses from: ISAT 440, ISAT 441, ISAT 445, ISAT 447, ISAT 449.",
            ),
        )
        state, _ = _get_intake_state("ISAT 440, ISAT 441, ISAT 445, ISAT 449", h)
        self.assertEqual(state, "awaiting_timing_constraints")

        h += _history(
            ("user", "ISAT 440, ISAT 441, ISAT 445, ISAT 449"),
            (
                "assistant",
                "If you need specific courses in specific terms, type that now, or choose Generate my schedule.",
            ),
        )
        state, payload = _get_intake_state("Generate my schedule", h)
        self.assertEqual(state, "ready_to_generate_schedule")
        self.assertEqual(payload["standing"], "freshman")
        self.assertEqual(payload["concentration"], "applied computing")
        self.assertEqual(payload["sector"], "energy")

    def test_edit_followup_after_schedule(self) -> None:
        h = _history(
            ("user", "Generate a course schedule"),
            ("assistant", "What year standing are you? Choose one: Freshman (0–29 credits)."),
            ("user", "Freshman (0–29 credits)"),
            ("assistant", "Are you planning to graduate on time with your class year? Choose one: On time."),
            ("user", "On time"),
            (
                "assistant",
                "How many General Education credits have you already completed? "
                "The requirement is 41 credits. Type a number from 0 to 41, or choose one: None yet (0).",
            ),
            ("user", "None yet (0)"),
            (
                "assistant",
                "Which of these ISAT core courses have you already completed? Check all that apply, or choose None yet.",
            ),
            ("user", "None yet"),
            ("assistant", "What concentration do you want to complete?"),
            ("user", "Applied Computing"),
            ("assistant", "Which sector do you want to complete? Available sectors: Energy."),
            ("user", "Energy"),
            (
                "assistant",
                "For Applied Computing, choose exactly 4 concentration courses from: ISAT 440, ISAT 441, ISAT 445, ISAT 449.",
            ),
            ("user", "ISAT 440, ISAT 441, ISAT 445, ISAT 449"),
            (
                "assistant",
                "If you need specific courses in specific terms, type that now, or choose Generate my schedule.",
            ),
            ("user", "Generate my schedule"),
            (
                "assistant",
                "Below is a four-year sample plan for the **Applied Computing** concentration "
                "with the **Energy** sector.\n\nDo you want to make any changes or edits to your schedule?",
            ),
        )
        state, _ = _get_intake_state("I already took ISAT 252", h)
        self.assertEqual(state, "awaiting_schedule_edits")

    def test_gen_ed_prompt_after_graduation(self) -> None:
        prompt = _handle_schedule_intake(
            "On time",
            _history(
                ("user", "Generate a course schedule"),
                ("assistant", "What year standing are you? Choose one: Sophomore (30–59 credits)."),
                ("user", "Sophomore (30–59 credits)"),
                (
                    "assistant",
                    "Are you planning to graduate on time with your class year? Choose one: On time.",
                ),
            ),
        )
        self.assertIn("How many General Education credits have you already completed?", prompt)


if __name__ == "__main__":
    unittest.main()
