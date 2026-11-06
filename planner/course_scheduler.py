import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import TypedDict

from database.db_write import LinkDatabase, is_trustworthy_abet_course_title

class Course(TypedDict, total=False):
    code: str
    title: str
    credits: int
    category: str
    prereqs: list[str]
    status: str


class Semester(TypedDict):
    term: str
    courses: list[Course]
    total_credits: int


class SchedulerInput(TypedDict, total=False):
    concentration: str
    sector: str
    selected_concentration_courses: list[str]
    standing: str
    graduation_timing: str
    taken_courses: list[str]
    gen_ed_credits: int
    timing_constraints: dict[str, int]


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
    all_courses: dict[str, Course]


def normalize_course_code(code: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9]", "", (code or "").upper())
    if not clean:
        return ""
    if re.fullmatch(r"\d{3}[A-Z]?", clean):
        return f"ISAT {clean}"
    if clean.startswith("ISAT") and len(clean) >= 7:
        return f"ISAT {clean[4:]}"
    return clean


def _course(code: str, title: str, credits: int, category: str, status: str = "remaining") -> Course:
    return {
        "code": normalize_course_code(code),
        "title": title.strip(),
        "credits": credits,
        "category": category,
        "prereqs": [],
        "status": status,
    }


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


def _gen_ed_placeholder(status: str = "remaining") -> Course:
    return _course("GEN ED", "General Education", 3, "General Education", status=status)


def _prereqs_satisfied_before(
    course: Course,
    semester_idx: int,
    semesters: list[Semester],
    taken_codes: set[str] | None = None,
) -> bool:
    taken = {normalize_course_code(c) for c in (taken_codes or set())}
    if not taken:
        taken = {
            normalize_course_code(c["code"])
            for sem in semesters
            for c in sem["courses"]
            if c.get("status") == "taken"
        }
    prereqs = course.get("prereqs") or []
    for p in prereqs:
        pc = normalize_course_code(p)
        if not pc or pc in taken:
            continue
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
CAPSTONE_FIXED_INDEX = {
    "ISAT 490": 4,
    "ISAT 491": 5,
    "ISAT 492": 6,
    "ISAT 493": 7,
}
EXPLICIT_MIN_INDEX = {
    "ISAT 252": 2,
    "ISAT 300": 4,
    "ISAT 190": 2,
    "ISAT 290": 3,
    "ISAT 390": 4,
    "ISAT 391": 5,
}
SEMESTER_LABELS = [
    "First Year Fall",
    "First Year Spring",
    "Second Year Fall",
    "Second Year Spring",
    "Third Year Fall",
    "Third Year Spring",
    "Fourth Year Fall",
    "Fourth Year Spring",
]


def min_index_for_course(code: str) -> int:
    code = normalize_course_code(code)
    if code in CAPSTONE_FIXED_INDEX:
        return CAPSTONE_FIXED_INDEX[code]
    if code in EXPLICIT_MIN_INDEX:
        return EXPLICIT_MIN_INDEX[code]
    level = _course_level(code)
    if level >= 400:
        return 5
    if level >= 300:
        return 4
    if level >= 200:
        return 2
    return 0


def _is_taken(course: Course) -> bool:
    return (course.get("status") or "") == "taken"


def _rebalance_gen_ed_avoid_singles(
    semesters: list[Semester],
    term_credit_caps: list[int],
    first_two_year_floor: int = 18,
    first_future_semester: int = 0,
) -> None:
    """Merge lone GEN ED rows into another semester that already has GEN ED (or room)."""
    for _ in range(64):
        counts = [sum(1 for c in s["courses"] if _is_gen_ed(c) and not _is_taken(c)) for s in semesters]
        singles = [i for i, n in enumerate(counts) if n == 1 and i >= first_future_semester]
        if not singles:
            return
        moved = False
        for i in singles:
            gi = next(
                (k for k, c in enumerate(semesters[i]["courses"]) if _is_gen_ed(c) and not _is_taken(c)),
                None,
            )
            if gi is None:
                continue
            for j in range(first_future_semester, len(semesters)):
                if j == i:
                    continue
                cap = term_credit_caps[j] if j > 3 else max(term_credit_caps[j], first_two_year_floor)
                if counts[j] >= 1 and semesters[j]["total_credits"] + 3 <= cap:
                    moved_course = semesters[i]["courses"].pop(gi)
                    semesters[i]["total_credits"] -= 3
                    semesters[j]["courses"].append(moved_course)
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
    first_future_semester: int = 0,
    taken_codes: set[str] | None = None,
) -> None:
    """Pull ISAT courses forward from earlier semesters into thin semesters (need 2+ ISAT each term)."""
    taken = taken_codes or set()
    for _ in range(120):
        thin = [
            i
            for i, s in enumerate(semesters)
            if i >= first_future_semester and sum(1 for c in s["courses"] if _is_isat(c)) < 2
        ]
        if not thin:
            return
        moved_any = False
        for i in thin:
            if i == 0:
                continue
            for j in range(i - 1, first_future_semester - 1, -1):
                if j < first_future_semester:
                    continue
                for ei in range(len(semesters[j]["courses"]) - 1, -1, -1):
                    c = semesters[j]["courses"][ei]
                    if not _is_isat(c) or _is_taken(c):
                        continue
                    code = normalize_course_code(c["code"])
                    if code in CAPSTONE_CODES:
                        continue
                    if min_index_fn(code) > i:
                        continue
                    if not _prereqs_satisfied_before(c, i, semesters, taken):
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


def _course_is_prereq_in_range(
    course_code: str,
    semesters: list[Semester],
    start_exclusive: int,
    end_inclusive: int,
) -> bool:
    target = normalize_course_code(course_code)
    for idx in range(start_exclusive + 1, min(end_inclusive, len(semesters) - 1) + 1):
        for c in semesters[idx]["courses"]:
            prereqs = c.get("prereqs") or []
            if any(normalize_course_code(p) == target for p in prereqs):
                return True
    return False


def _rebalance_upper_year_credit_floor(
    semesters: list[Semester],
    term_credit_caps: list[int],
    min_index_fn,
    floor: int = 12,
    start_semester: int = 4,
) -> None:
    """
    Raise thin upper-year semesters by moving movable courses from heavier prior terms.
    Keep capstones fixed and preserve prerequisite ordering.
    """
    for _ in range(120):
        thin = [
            i for i in range(start_semester, len(semesters))
            if semesters[i]["total_credits"] < floor
        ]
        if not thin:
            return
        moved_any = False
        for i in thin:
            for j in range(i - 1, start_semester - 1, -1):
                if semesters[j]["total_credits"] <= floor:
                    continue
                for ei in range(len(semesters[j]["courses"]) - 1, -1, -1):
                    c = semesters[j]["courses"][ei]
                    if _is_taken(c):
                        continue
                    code = normalize_course_code(c["code"])
                    if code in CAPSTONE_CODES:
                        continue
                    if min_index_fn(code) > i:
                        continue
                    if semesters[i]["total_credits"] + c["credits"] > term_credit_caps[i]:
                        continue
                    # If this course is needed as a prereq by any course before its new term, don't move it later.
                    if _course_is_prereq_in_range(code, semesters, j, i):
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
        all_courses=all_courses,
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

    def preferred_semester_index(self, code: str) -> int:
        code = normalize_course_code(code)
        for course in self.rules.first_year_fall:
            if normalize_course_code(course["code"]) == code:
                return 0
        for course in self.rules.first_year_spring:
            if normalize_course_code(course["code"]) == code:
                return 1
        return min_index_for_course(code)

    def core_checklist_groups(self, standing: str) -> list[tuple[str, list[str]]]:
        from .plan_graph import core_checklist_groups

        return core_checklist_groups(standing)

    def build_graph(self, scheduler_input: SchedulerInput):
        from .plan_graph import build_student_plan_graph

        return build_student_plan_graph(
            self.rules,
            concentration=scheduler_input["concentration"],
            sector=scheduler_input["sector"],
            selected_concentration_courses=list(scheduler_input.get("selected_concentration_courses") or []),
            standing=scheduler_input.get("standing") or "freshman",
            graduation_timing=scheduler_input.get("graduation_timing") or "on_time",
            taken_courses=list(scheduler_input.get("taken_courses") or []),
            gen_ed_credits=int(scheduler_input.get("gen_ed_credits") or 0),
            timing_constraints=dict(scheduler_input.get("timing_constraints") or {}),
        )

    def plan(self, scheduler_input: SchedulerInput) -> SchedulerOutput:
        graph = self.build_graph(scheduler_input)
        return self.plan_from_graph(graph)

    @staticmethod
    def _ensure_semester_capacity(semesters: list[Semester], term_credit_caps: list[int], idx: int) -> int:
        while idx >= len(semesters):
            extra = len(semesters) - 7
            label = f"Additional Semester {extra}" if extra > 0 else f"Semester {len(semesters) + 1}"
            semesters.append({"term": label, "courses": [], "total_credits": 0})
            term_credit_caps.append(18)
        return idx

    def _place_at(self, semesters: list[Semester], term_credit_caps: list[int], course: Course, idx: int) -> int:
        idx = self._ensure_semester_capacity(semesters, term_credit_caps, idx)
        while idx < len(semesters) and semesters[idx]["total_credits"] + course["credits"] > term_credit_caps[idx]:
            idx += 1
            idx = self._ensure_semester_capacity(semesters, term_credit_caps, idx)
        semesters[idx]["courses"].append(course)
        semesters[idx]["total_credits"] += course["credits"]
        return idx

    def _order_remaining(self, courses: list[Course]) -> list[Course]:
        by_code = {normalize_course_code(c["code"]): c for c in courses}
        remaining = set(by_code)
        out: list[Course] = []
        while remaining:
            ready: list[str] = []
            for code in remaining:
                prereqs = [
                    normalize_course_code(p)
                    for p in (by_code[code].get("prereqs") or [])
                    if normalize_course_code(p) in remaining
                ]
                if not prereqs:
                    ready.append(code)
            if not ready:
                ready = list(remaining)
            ready.sort(key=lambda c: (min_index_for_course(c), _course_level(c), c))
            pick = ready[0]
            out.append(by_code[pick])
            remaining.remove(pick)
        return out

    def plan_from_graph(self, graph) -> SchedulerOutput:
        needed = max(8, graph.first_future_semester + graph.remaining_term_count)
        semesters: list[Semester] = []
        term_credit_caps: list[int] = []
        for i in range(needed):
            if i < len(SEMESTER_LABELS):
                label = SEMESTER_LABELS[i]
            else:
                label = f"Additional Semester {i - 7}"
            semesters.append({"term": label, "courses": [], "total_credits": 0})
            term_credit_caps.append(15 if i < 2 else 18)

        last_allowed = max(graph.first_future_semester + graph.remaining_term_count - 1, graph.first_future_semester)
        first_future = graph.first_future_semester
        taken_codes: set[str] = set(graph.taken_codes)

        # Place completed ISAT courses in their curriculum slots (grey / taken).
        taken_nodes = sorted(
            (graph.nodes[c] for c in taken_codes if c in graph.nodes),
            key=lambda n: (self.preferred_semester_index(n.code), n.code),
        )
        for node in taken_nodes:
            course = node.to_course()
            course["status"] = "taken"
            idx = self.preferred_semester_index(node.code)
            idx = max(0, min(idx, max(len(semesters) - 1, 0)))
            self._place_at(semesters, term_credit_caps, course, idx)

        # Completed Gen Ed is a separate counter from ISAT major credits.
        # Sophomore+ students often bring standing from Gen Ed only — place those
        # credits in past year blocks. Freshman AP/transfer Gen Ed is counted
        # without occupying upcoming ISAT seats.
        from .plan_graph import DEGREE_TARGET, GEN_ED_TARGET

        completed_gen = int(graph.gen_ed_credits_completed or 0)
        placed_completed_gen = 0
        past_end = max(first_future, 0)
        if past_end > 0 and completed_gen >= 3:
            leftover = completed_gen
            past_idx = 0
            guard = 0
            while leftover >= 3 and guard < 80:
                guard += 1
                cap = 18 if past_idx < 4 else term_credit_caps[past_idx]
                if semesters[past_idx]["total_credits"] + 3 <= cap:
                    # Place in-place so overflow cannot spill completed Gen Ed into future terms.
                    semesters[past_idx]["courses"].append(_gen_ed_placeholder(status="taken"))
                    semesters[past_idx]["total_credits"] += 3
                    leftover -= 3
                    placed_completed_gen += 3
                past_idx = (past_idx + 1) % past_end
                if leftover >= 3 and all(
                    semesters[i]["total_credits"] + 3
                    > (max(term_credit_caps[i], 18) if i < 4 else term_credit_caps[i])
                    for i in range(past_end)
                ):
                    break
        unplaced_completed_gen = max(0, completed_gen - placed_completed_gen)

        remaining_courses = [
            graph.nodes[code].to_course()
            for code in graph.remaining_codes
            if code in graph.nodes
        ]
        remaining_capstone: list[Course] = []
        remaining_other: list[Course] = []
        for course in remaining_courses:
            code = normalize_course_code(course["code"])
            course["status"] = "remaining"
            if code in CAPSTONE_FIXED_INDEX:
                remaining_capstone.append(course)
            else:
                remaining_other.append(course)

        for course in remaining_capstone:
            code = normalize_course_code(course["code"])
            idx = max(CAPSTONE_FIXED_INDEX[code], first_future)
            idx = min(idx, last_allowed)
            self._place_at(semesters, term_credit_caps, course, idx)

        for course in self._order_remaining(remaining_other):
            code = normalize_course_code(course["code"])
            idx = max(self.preferred_semester_index(code), first_future)
            if code in graph.timing_constraints:
                preferred = graph.timing_constraints[code]
                if preferred >= first_future:
                    idx = max(idx, preferred)
            # Wait until remaining prereqs are in an earlier term (taken prereqs already count).
            while idx <= last_allowed and not _prereqs_satisfied_before(course, idx, semesters, taken_codes):
                idx += 1
            idx = min(max(idx, first_future), max(last_allowed, first_future))
            self._place_at(semesters, term_credit_caps, course, idx)

        def _place_remaining_gen_ed() -> bool:
            first_two_floor = 18
            future_first_two = [i for i in range(max(first_future, 0), min(4, len(semesters)))]
            search = future_first_two or list(range(first_future, len(semesters)))
            for sem_idx in search:
                cap = max(term_credit_caps[sem_idx], first_two_floor) if sem_idx < 4 else term_credit_caps[sem_idx]
                sem = semesters[sem_idx]
                if sem["total_credits"] + 3 <= cap:
                    sem["courses"].append(_gen_ed_placeholder())
                    sem["total_credits"] += 3
                    return True
            candidates = []
            start = max(4, first_future)
            for sem_idx in range(start, len(semesters)):
                cap = term_credit_caps[sem_idx]
                sem = semesters[sem_idx]
                if sem["total_credits"] + 3 <= cap:
                    candidates.append((sem["total_credits"], sem_idx))
            if candidates:
                _, sem_idx = min(candidates)
                semesters[sem_idx]["courses"].append(_gen_ed_placeholder())
                semesters[sem_idx]["total_credits"] += 3
                return True
            return False

        remaining_gen_needed = max(0, GEN_ED_TARGET - completed_gen)
        guard = 0
        while remaining_gen_needed > 0 and guard < 200:
            guard += 1
            if not _place_remaining_gen_ed():
                break
            remaining_gen_needed -= 3

        accounted = sum(s["total_credits"] for s in semesters) + unplaced_completed_gen
        guard = 0
        while accounted < DEGREE_TARGET and guard < 200:
            guard += 1
            if not _place_remaining_gen_ed():
                break
            accounted += 3

        first_two_floor = 18
        _rebalance_gen_ed_avoid_singles(
            semesters, term_credit_caps, first_two_floor, first_future_semester=first_future
        )
        _ensure_min_two_isat_per_semester(
            semesters,
            term_credit_caps,
            min_index_for_course,
            first_two_floor,
            first_future_semester=first_future,
            taken_codes=taken_codes,
        )
        _rebalance_upper_year_credit_floor(
            semesters,
            term_credit_caps,
            min_index_for_course,
            floor=12,
            start_semester=max(4, first_future),
        )

        for sem in semesters:
            sem["total_credits"] = sum(c["credits"] for c in sem["courses"])

        # Always keep at least the standard eight semester tables.
        while len(semesters) < 8:
            idx = len(semesters)
            semesters.append({"term": SEMESTER_LABELS[idx], "courses": [], "total_credits": 0})

        table_sum = sum(s["total_credits"] for s in semesters)
        gen_in_tables = sum(
            int(c["credits"])
            for s in semesters
            for c in s["courses"]
            if _is_gen_ed(c)
        )
        major_planned = table_sum - gen_in_tables
        gen_planned = gen_in_tables + unplaced_completed_gen
        totals = {
            "planned_credits": table_sum + unplaced_completed_gen,
            "degree_target": DEGREE_TARGET,
            "credits_completed": graph.credits_completed,
            "major_credits_completed": graph.major_credits_completed,
            "major_credits_remaining": graph.major_credits_remaining,
            "major_credits_planned": major_planned,
            "gen_ed_credits_completed": graph.gen_ed_credits_completed,
            "gen_ed_credits_remaining": graph.gen_ed_credits_remaining,
            "gen_ed_credits_planned": gen_planned,
            "gen_ed_target": GEN_ED_TARGET,
            "unplaced_completed_gen_ed": unplaced_completed_gen,
        }
        notes = [
            f"Sector selected: {graph.sector.title()}",
            f"Class standing: {graph.standing.title()}",
            f"ISAT major credits completed: {graph.major_credits_completed}",
            f"General Education credits completed: {graph.gen_ed_credits_completed} / {GEN_ED_TARGET}",
        ]
        if graph.graduation_timing != "on_time":
            notes.append(f"Graduation timing: {graph.graduation_timing.replace('_', ' ')}")
        return {
            "semesters": semesters,
            "notes": notes,
            "totals": totals,
        }
