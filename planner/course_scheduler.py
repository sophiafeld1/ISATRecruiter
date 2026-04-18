import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import TypedDict

from database.db_write import LinkDatabase, is_trustworthy_abet_course_title

class Course(TypedDict):
    code: str
    title: str
    credits: int
    category: str
    prereqs: list[str]


class Semester(TypedDict):
    term: str
    courses: list[Course]
    total_credits: int


class SchedulerInput(TypedDict):
    concentration: str
    sector: str
    selected_concentration_courses: list[str]


class SchedulerOutput(TypedDict):
    semesters: list[Semester]
    notes: list[str]
    totals: dict


@dataclass
class ProgramRules:
    first_year_fall: list[Course]
    first_year_spring: list[Course]
    stage2: list[Course]
    stage5: list[Course]
    sector_by_name: dict[str, list[Course]]
    concentration_options: dict[str, list[Course]]


def normalize_course_code(code: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9]", "", (code or "").upper())
    if not clean:
        return ""
    if re.fullmatch(r"\d{3}[A-Z]?", clean):
        return f"ISAT {clean}"
    if clean.startswith("ISAT") and len(clean) >= 7:
        return f"ISAT {clean[4:]}"
    return clean


def _course(code: str, title: str, credits: int, category: str) -> Course:
    return {"code": normalize_course_code(code), "title": title.strip(), "credits": credits, "category": category, "prereqs": []}


def _parse_credit(line: str, default: int = 3) -> int:
    m = re.search(r"Credits:\s*([0-9]+(?:\.[0-9]+)?)", line, re.IGNORECASE)
    if not m:
        return default
    return int(float(m.group(1)))


def _course_level(code: str) -> int:
    m = re.search(r"(\d{3})", code)
    return int(m.group(1)) if m else 999


def _is_gen_ed(c: Course) -> bool:
    return c.get("category") == "General Education" or normalize_course_code(c["code"]) == "GENED"


def _is_isat(c: Course) -> bool:
    return normalize_course_code(c["code"]).startswith("ISAT")


def _gen_ed_placeholder() -> Course:
    return _course("GEN ED", "General Education", 3, "General Education")


def _prereqs_satisfied_before(course: Course, semester_idx: int, semesters: list[Semester]) -> bool:
    prereqs = course.get("prereqs") or []
    for p in prereqs:
        pc = normalize_course_code(p)
        found = False
        for s in range(semester_idx):
            for c in semesters[s]["courses"]:
                if normalize_course_code(c["code"]) == pc:
                    found = True
                    break
            if found:
                break
        if not found:
            return False
    return True


CAPSTONE_CODES = frozenset({"ISAT 490", "ISAT 491", "ISAT 492", "ISAT 493"})


def _rebalance_gen_ed_avoid_singles(
    semesters: list[Semester],
    term_credit_caps: list[int],
    first_two_year_floor: int = 18,
) -> None:
    """Merge lone GEN ED rows into another semester that already has GEN ED (or room)."""
    for _ in range(64):
        counts = [sum(1 for c in s["courses"] if _is_gen_ed(c)) for s in semesters]
        singles = [i for i, n in enumerate(counts) if n == 1]
        if not singles:
            return
        moved = False
        for i in singles:
            gi = next((k for k, c in enumerate(semesters[i]["courses"]) if _is_gen_ed(c)), None)
            if gi is None:
                continue
            for j in range(len(semesters)):
                if j == i:
                    continue
                cap = term_credit_caps[j] if j > 3 else max(term_credit_caps[j], first_two_year_floor)
                if counts[j] >= 1 and semesters[j]["total_credits"] + 3 <= cap:
                    taken = semesters[i]["courses"].pop(gi)
                    semesters[i]["total_credits"] -= 3
                    semesters[j]["courses"].append(taken)
                    semesters[j]["total_credits"] += 3
                    moved = True
                    break
            if moved:
                break
        if not moved:
            break


def _ensure_min_two_isat_per_semester(
    semesters: list[Semester],
    term_credit_caps: list[int],
    min_index_fn,
    first_two_year_floor: int = 18,
) -> None:
    """Pull ISAT courses forward from earlier semesters into thin semesters (need 2+ ISAT each term)."""
    for _ in range(120):
        thin = [i for i, s in enumerate(semesters) if sum(1 for c in s["courses"] if _is_isat(c)) < 2]
        if not thin:
            return
        moved_any = False
        for i in thin:
            if i == 0:
                continue
            for j in range(i - 1, -1, -1):
                for ei in range(len(semesters[j]["courses"]) - 1, -1, -1):
                    c = semesters[j]["courses"][ei]
                    if not _is_isat(c):
                        continue
                    code = normalize_course_code(c["code"])
                    if code in CAPSTONE_CODES:
                        continue
                    if min_index_fn(code) > i:
                        continue
                    if not _prereqs_satisfied_before(c, i, semesters):
                        continue
                    cap = term_credit_caps[i] if i > 3 else max(term_credit_caps[i], first_two_year_floor)
                    if semesters[i]["total_credits"] + c["credits"] > cap:
                        continue
                    semesters[j]["courses"].pop(ei)
                    semesters[j]["total_credits"] -= c["credits"]
                    semesters[i]["courses"].append(c)
                    semesters[i]["total_credits"] += c["credits"]
                    moved_any = True
                    break
                if moved_any:
                    break
            if moved_any:
                break
        if not moved_any:
            break


@lru_cache(maxsize=1)
def _catalog_map_abet_first() -> dict[str, dict]:
    db = LinkDatabase()
    try:
        out: dict[str, dict] = {}
        for row in db.fetch_course_catalog_abet_first():
            code = normalize_course_code(row.get("course_code") or "")
            if code:
                out[code] = row
        return out
    finally:
        db.close()


def _hydrate_course_metadata(course: Course) -> Course:
    row = _catalog_map_abet_first().get(normalize_course_code(course["code"]))
    if not row:
        return course
    out = dict(course)
    name = row.get("course_name")
    if name and is_trustworthy_abet_course_title(str(name).strip()):
        out["title"] = str(name).strip()
    prereq_text = row.get("prerequisites") or ""
    prereqs = [normalize_course_code(m.group(0)) for m in re.finditer(r"ISAT\s*\d{3}[A-Z]?", prereq_text, re.IGNORECASE)]
    if prereqs:
        out["prereqs"] = prereqs
    return out


@lru_cache(maxsize=1)
def load_program_rules(program_schedules_path: str) -> ProgramRules:
    with open(program_schedules_path, encoding="utf-8") as f:
        text = f.read()
    lines = [ln.strip() for ln in text.splitlines()]

    course_line = re.compile(r"^(ISAT\s*\d{3}[A-Z]?)\.\s*(.+)$", re.IGNORECASE)
    stage2_codes = {"ISAT 190", "ISAT 290", "ISAT 390", "ISAT 391"}
    stage5_codes = {"ISAT 490", "ISAT 491", "ISAT 492", "ISAT 493"}

    all_courses: dict[str, Course] = {}
    for ln in lines:
        m = course_line.match(ln)
        if not m:
            continue
        code = normalize_course_code(m.group(1))
        rest = m.group(2)
        title = re.sub(r"Credits:.*$", "", rest, flags=re.IGNORECASE).strip()
        credits = _parse_credit(ln)
        all_courses[code] = _course(code, title, credits, "Catalog")

    # Trusted first-year recommendation (from issues/methods/social-context core in program_schedules.md).
    first_year_fall_codes = ["ISAT 112", "ISAT 113", "ISAT 113L", "ISAT 151", "ISAT 171"]
    # Keep freshman spring lighter (12-15 credits target). ISAT 271 moves to sophomore-year tail.
    first_year_spring_codes = ["ISAT 211", "ISAT 212", "ISAT 152", "ISAT 251"]
    first_year_fall = [all_courses[c] for c in first_year_fall_codes if c in all_courses]
    first_year_spring = [all_courses[c] for c in first_year_spring_codes if c in all_courses]
    stage2 = [all_courses[c] for c in ["ISAT 190", "ISAT 290", "ISAT 390", "ISAT 391"] if c in all_courses]
    stage5 = [all_courses[c] for c in ["ISAT 490", "ISAT 491", "ISAT 492", "ISAT 493"] if c in all_courses]

    sector_by_name: dict[str, list[Course]] = {
        "applied biotechnology": [all_courses[c] for c in ["ISAT 305", "ISAT 350", "ISAT 351"] if c in all_courses],
        "applied computing": [all_courses[c] for c in ["ISAT 340", "ISAT 341"] if c in all_courses],
        "energy": [all_courses[c] for c in ["ISAT 301", "ISAT 310", "ISAT 311"] if c in all_courses],
        "environment and sustainability": [all_courses[c] for c in ["ISAT 320", "ISAT 321"] if c in all_courses],
        "industrial and manufacturing systems": [all_courses[c] for c in ["ISAT 303", "ISAT 330", "ISAT 331"] if c in all_courses],
        "public interest technology and science": [],
        "tailored": [],
    }

    concentration_options: dict[str, list[Course]] = {
        "applied biotechnology": [all_courses[c] for c in ["ISAT 451", "ISAT 452", "ISAT 454", "ISAT 455", "ISAT 456", "ISAT 459", "ISAT 485"] if c in all_courses],
        "applied computing": [all_courses[c] for c in ["ISAT 440", "ISAT 441", "ISAT 445", "ISAT 447", "ISAT 449"] if c in all_courses],
        "energy": [all_courses[c] for c in ["ISAT 411", "ISAT 413", "ISAT 410", "ISAT 414", "ISAT 416"] if c in all_courses],
        "environment and sustainability": [all_courses[c] for c in ["ISAT 420", "ISAT 421", "ISAT 422", "ISAT 423", "ISAT 424", "ISAT 425", "ISAT 426", "ISAT 427", "ISAT 428", "ISAT 429", "ISAT 473", "ISAT 474"] if c in all_courses],
        "industrial and manufacturing systems": [all_courses[c] for c in ["ISAT 430", "ISAT 431", "ISAT 432", "ISAT 433", "ISAT 434", "ISAT 435", "ISAT 437"] if c in all_courses],
        "public interest technology and science": [all_courses[c] for c in ["ISAT 411", "ISAT 421", "ISAT 440", "ISAT 455", "ISAT 456", "ISAT 485", "ISAT 483", "ISAT 487"] if c in all_courses],
        "tailored": [],
    }
    return ProgramRules(
        first_year_fall=first_year_fall,
        first_year_spring=first_year_spring,
        stage2=stage2,
        stage5=stage5,
        sector_by_name=sector_by_name,
        concentration_options=concentration_options,
    )


class CourseScheduler:
    def __init__(self, project_root: str):
        self.program_path = os.path.join(project_root, "data_isat_website", "program_schedules.md")
        self.rules = load_program_rules(self.program_path)

    def concentration_options(self, concentration: str) -> list[Course]:
        return self.rules.concentration_options.get(concentration, [])

    def sector_options(self) -> list[str]:
        return [
            "Applied Biotechnology",
            "Applied Computing",
            "Energy",
            "Environment and Sustainability",
            "Industrial and Manufacturing Systems",
        ]

    @staticmethod
    def _dedupe_courses(courses: list[Course]) -> list[Course]:
        out: list[Course] = []
        seen: set[str] = set()
        for c in courses:
            code = normalize_course_code(c["code"])
            if code in seen:
                continue
            seen.add(code)
            out.append(c)
        return out

    def plan(self, scheduler_input: SchedulerInput) -> SchedulerOutput:
        concentration = scheduler_input["concentration"]
        sector = scheduler_input["sector"].strip().lower()
        selected = [normalize_course_code(c) for c in scheduler_input["selected_concentration_courses"] if normalize_course_code(c)]
        option_map = {normalize_course_code(c["code"]): c for c in self.rules.concentration_options.get(concentration, [])}
        selected_courses = [option_map[c] for c in selected if c in option_map]

        # Build full four-year requirements for a standard path.
        required_tail = self._dedupe_courses(
            [{"code": "ISAT 252", "title": "Programming and Problem Solving", "credits": 3, "category": "Core", "prereqs": []},
             {"code": "ISAT 300", "title": "Applied Computing, Instrumentation and Measurement", "credits": 3, "category": "Core", "prereqs": []},
             {"code": "ISAT 271", "title": "Technology, Science and Society", "credits": 3, "category": "Core", "prereqs": []}]
            + self.rules.stage2
            + self.rules.sector_by_name.get(sector, [])
            + selected_courses
            + self.rules.stage5
        )
        required_tail = [_hydrate_course_metadata(c) for c in required_tail]

        labels = [
            "First Year Fall",
            "First Year Spring",
            "Second Year Fall",
            "Second Year Spring",
            "Third Year Fall",
            "Third Year Spring",
            "Fourth Year Fall",
            "Fourth Year Spring",
        ]
        semesters: list[Semester] = [
            {"term": "First Year Fall", "courses": [_hydrate_course_metadata(c) for c in self.rules.first_year_fall], "total_credits": sum(c["credits"] for c in self.rules.first_year_fall)},
            {"term": "First Year Spring", "courses": [_hydrate_course_metadata(c) for c in self.rules.first_year_spring], "total_credits": sum(c["credits"] for c in self.rules.first_year_spring)},
        ]
        for label in labels[2:]:
            semesters.append({"term": label, "courses": [], "total_credits": 0})
        # Keep freshman year lighter; later terms can be heavier.
        term_credit_caps = [15, 15, 18, 18, 18, 18, 18, 18]

        # Honor sequence constraints and level progression.
        # Index map: 0/1=first year, 2/3=second year, 4/5=third year, 6/7=fourth year.
        capstone_fixed_index = {
            "ISAT 490": 4,  # Third Year Fall
            "ISAT 491": 5,  # Third Year Spring
            "ISAT 492": 6,  # Fourth Year Fall
            "ISAT 493": 7,  # Fourth Year Spring
        }
        explicit_min_index = {
            "ISAT 252": 2,
            "ISAT 300": 4,
            "ISAT 190": 2,
            "ISAT 290": 3,
            "ISAT 390": 4,
            "ISAT 391": 5,
        }

        def min_index_for_course(code: str) -> int:
            if code in capstone_fixed_index:
                return capstone_fixed_index[code]
            if code in explicit_min_index:
                return explicit_min_index[code]
            level = _course_level(code)
            if level >= 400:
                return 5
            if level >= 300:
                return 4
            if level >= 200:
                return 2
            return 0

        # Place capstone sequence in fixed order/semesters before general balancing.
        remaining_tail: list[Course] = []
        for course in required_tail:
            code = normalize_course_code(course["code"])
            if code not in capstone_fixed_index:
                remaining_tail.append(course)
                continue
            idx = capstone_fixed_index[code]
            while idx >= len(semesters):
                # Guardrail: keep plan within standard 4-year structure.
                idx = len(semesters) - 1
                break
            semesters[idx]["courses"].append(course)
            semesters[idx]["total_credits"] += course["credits"]

        ordered_tail = sorted(
            remaining_tail,
            key=lambda c: (
                min_index_for_course(normalize_course_code(c["code"])),
                _course_level(normalize_course_code(c["code"])),
                normalize_course_code(c["code"]),
            ),
        )

        for course in ordered_tail:
            code = normalize_course_code(course["code"])
            idx = min_index_for_course(code)
            while idx >= len(semesters):
                semesters.append({"term": f"Additional Semester {len(semesters) - 7}", "courses": [], "total_credits": 0})
                term_credit_caps.append(18)
            while idx < len(semesters) and semesters[idx]["total_credits"] + course["credits"] > term_credit_caps[idx]:
                idx += 1
                while idx >= len(semesters):
                    semesters.append({"term": f"Additional Semester {len(semesters) - 7}", "courses": [], "total_credits": 0})
                    term_credit_caps.append(18)
            semesters[idx]["courses"].append(course)
            semesters[idx]["total_credits"] += course["credits"]

        # General Education placeholders to 120 credits: prefer years 1–2 (semesters 0–3), then spill.
        planned_core = sum(s["total_credits"] for s in semesters)
        gen_ed_needed = max(0, 120 - planned_core)
        first_two_floor = 18
        rotation = 0
        guard = 0
        while gen_ed_needed > 0 and guard < 500:
            guard += 1
            placed = False
            for step in range(4):
                sem_idx = (rotation + step) % 4
                cap = max(term_credit_caps[sem_idx], first_two_floor)
                sem = semesters[sem_idx]
                if sem["total_credits"] + 3 <= cap:
                    sem["courses"].append(_gen_ed_placeholder())
                    sem["total_credits"] += 3
                    gen_ed_needed -= 3
                    placed = True
                    rotation = (sem_idx + 1) % 4
                    break
            if not placed:
                for sem_idx in range(4, len(semesters)):
                    cap = term_credit_caps[sem_idx]
                    sem = semesters[sem_idx]
                    if sem["total_credits"] + 3 <= cap:
                        sem["courses"].append(_gen_ed_placeholder())
                        sem["total_credits"] += 3
                        gen_ed_needed -= 3
                        placed = True
                        break
            if not placed:
                break

        _rebalance_gen_ed_avoid_singles(semesters, term_credit_caps, first_two_floor)
        _ensure_min_two_isat_per_semester(semesters, term_credit_caps, min_index_for_course, first_two_floor)

        for sem in semesters:
            sem["total_credits"] = sum(c["credits"] for c in sem["courses"])

        totals = {
            "planned_credits": sum(s["total_credits"] for s in semesters),
            "degree_target": 120,
        }

        notes = []
        notes.append(f"Sector selected: {scheduler_input['sector'].title()}")
        return {
            "semesters": semesters,
            "notes": notes,
            "totals": totals,
        }
