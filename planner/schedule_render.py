"""
Markdown rendering for tool-generated degree schedules.
Matches templates.md: paired Fall/Spring tables per year, totals, elective list.
"""

from __future__ import annotations

from typing import Any

from .course_scheduler import normalize_course_code


def _is_gen_ed(course: dict[str, Any]) -> bool:
    if course.get("category") == "General Education":
        return True
    compact = normalize_course_code(course.get("code") or "")
    return compact == "GENED"


def _escape_md_cell(text: str) -> str:
    return (text or "").replace("|", " ").replace("\n", " ").strip()


def _course_row_text(course: dict[str, Any]) -> str:
    if _is_gen_ed(course):
        return "General Education Course"
    code = (course.get("code") or "").strip()
    title = (course.get("title") or "").strip()
    if title.startswith(code):
        return _escape_md_cell(title)
    if title:
        return _escape_md_cell(f"{code}. {title}")
    return _escape_md_cell(code)


def _gen_ed_credits_planned(semesters: list[dict[str, Any]]) -> int:
    n = 0
    for sem in semesters:
        for c in sem.get("courses", []):
            if _is_gen_ed(c):
                n += int(c.get("credits") or 0)
    return n


def _paired_year_tables(semesters: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    year_names = ["First Year", "Second Year", "Third Year", "Fourth Year"]
    n = len(semesters)
    pair_count = (n + 1) // 2
    for p in range(pair_count):
        i = p * 2
        if i + 1 >= n:
            break
        fall = semesters[i]
        spring = semesters[i + 1]
        label = year_names[p] if p < len(year_names) else f"Year {p + 1}"
        lines.append(f"#### {label}")
        lines.append(
            "| Fall Semester Courses | Credits | Spring Semester Courses | Credits |\n"
            "|---|---:|---|---:|"
        )
        fc = list(fall.get("courses") or [])
        sc = list(spring.get("courses") or [])
        rows = max(len(fc), len(sc))
        for r in range(rows):
            f_c, s_c = (fc[r] if r < len(fc) else None), (sc[r] if r < len(sc) else None)
            fl = str(f_c["credits"]) if f_c else ""
            sl = str(s_c["credits"]) if s_c else ""
            ft = _course_row_text(f_c) if f_c else ""
            st = _course_row_text(s_c) if s_c else ""
            lines.append(f"| {ft} | {fl} | {st} | {sl} |")
        ft_tot, st_tot = fall.get("total_credits", 0), spring.get("total_credits", 0)
        lines.append(f"| **Total Hours** | **{ft_tot}** | **Total Hours** | **{st_tot}** |")
        lines.append("")
    return lines


def _elective_options_block(
    concentration: str,
    options: list[dict[str, Any]] | None,
) -> list[str]:
    if not options:
        return []
    lines = [
        f"**For the {concentration.title()} concentration, you can choose 12 credits from the following elective courses:**",
    ]
    for o in options:
        code = normalize_course_code(o.get("code") or "")
        title = (o.get("title") or "").strip()
        cr = int(o.get("credits") or 3)
        lines.append(f"- {code}. {title} — {cr} credits")
    lines.append("")
    lines.append(
        f"**You will need to select courses totaling 12 credits from this list to fulfill the "
        f"{concentration.title()} concentration requirements.**"
    )
    lines.append("")
    return lines


def _selected_concentration_lines(
    selected_codes: list[str],
    options: list[dict[str, Any]] | None,
) -> list[str]:
    if not selected_codes:
        return []
    by_code = {normalize_course_code(o.get("code") or ""): o for o in (options or [])}
    lines: list[str] = ["**Your concentration course selections (in this plan):**", ""]
    for raw in selected_codes:
        code = normalize_course_code(raw)
        o = by_code.get(code)
        if o:
            lines.append(f"- {code}. {(o.get('title') or '').strip()} — {int(o.get('credits') or 3)} credits")
        else:
            lines.append(f"- {code}")
    lines.append("")
    return lines


def format_schedule_message(
    concentration: str,
    sector: str,
    selected_courses: list[str],
    schedule_output: dict[str, Any],
    concentration_elective_options: list[dict[str, Any]] | None = None,
    credits_completed_prior: int = 0,
) -> str:
    """
    Build markdown aligned with templates.md (paired Fall/Spring tables per year).
    """
    semesters = schedule_output.get("semesters") or []
    notes = schedule_output.get("notes") or []
    totals = schedule_output.get("totals") or {}
    planned = int(totals.get("planned_credits") or 0)
    target = int(totals.get("degree_target") or 120)
    gen_sum = _gen_ed_credits_planned(semesters)

    out: list[str] = [
        f"Below is a four-year sample plan for the **{concentration.title()}** concentration "
        f"with the **{sector.title()}** sector.",
        "",
        f"**Credits satisfied (completed):** {credits_completed_prior}",
        "",
    ]

    out.extend(_paired_year_tables(semesters))

    out.append("### Final summary row")
    out.append(f"**Total Planned Credits:** {planned} / {target}  ")
    out.append(f"**Total General Education Credits Planned:** {gen_sum} / 41  ")
    out.append("")

    out.extend(_selected_concentration_lines(selected_courses, concentration_elective_options))
    out.extend(_elective_options_block(concentration, concentration_elective_options))

    out.append("### Notes")
    out.append(
        "- Check with your advisor to confirm course availability, prerequisites, and how this plan aligns with your goals."
    )
    for note in notes:
        if note:
            out.append(f"- {note}")
    out.append("")
    out.append("Do you want to make any changes or edits to your schedule?")
    return "\n".join(out)
