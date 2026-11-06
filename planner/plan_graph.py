"""
Intermediary academic graph for the ISAT course planner.

Holds every required course, catalog prerequisites, and which courses the
student has already taken. CourseScheduler.plan consumes this object.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Literal, Sequence

from .course_scheduler import (
    Course,
    ProgramRules,
    _course_level,
    _hydrate_course_metadata,
    min_index_for_course,
    normalize_course_code,
)

Standing = Literal["freshman", "sophomore", "junior", "senior"]
GraduationTiming = Literal["on_time", "extra_semester", "extra_year", "semester_early"]
CourseStatus = Literal["taken", "remaining"]

DEGREE_TARGET = 120
GEN_ED_TARGET = 41

STANDING_CREDIT_BANDS: dict[str, tuple[int, int]] = {
    "freshman": (0, 29),
    "sophomore": (30, 59),
    "junior": (60, 89),
    "senior": (90, 120),
}

STANDING_REMAINING_TERMS_ON_TIME: dict[str, int] = {
    "freshman": 8,
    "sophomore": 6,
    "junior": 4,
    "senior": 2,
}

STANDING_FIRST_FUTURE: dict[str, int] = {
    "freshman": 0,
    "sophomore": 2,
    "junior": 4,
    "senior": 6,
}

STANDING_OPTIONS = [
    "Freshman (0–29 credits)",
    "Sophomore (30–59 credits)",
    "Junior (60–89 credits)",
    "Senior (90+ credits)",
]

GRADUATION_OPTIONS = [
    "On time",
    "Extra semester",
    "Extra year",
    "Graduate a semester early",
    "Graduate a year early",
]

GEN_ED_CREDIT_OPTIONS = [
    "None yet (0)",
    "15 credits",
    "30 credits",
    "41 credits",
]

CORE_COURSE_GROUPS: list[tuple[str, list[str]]] = [
    ("Issues in Science and Technology", ["ISAT 112", "ISAT 113", "ISAT 113L", "ISAT 211", "ISAT 212"]),
    ("Analytical Methods", ["ISAT 151", "ISAT 152", "ISAT 251", "ISAT 252", "ISAT 300"]),
    ("Social Context of Technology and Science", ["ISAT 171", "ISAT 271"]),
    ("Holistic Problem Solving", ["ISAT 190", "ISAT 290", "ISAT 390", "ISAT 391"]),
]

CAPSTONE_GROUP: tuple[str, list[str]] = (
    "Senior Capstone Project",
    ["ISAT 490", "ISAT 491", "ISAT 492", "ISAT 493"],
)

_CORE_EXTRAS: list[tuple[str, str, int]] = [
    ("ISAT 252", "Programming and Problem Solving", 3),
    ("ISAT 300", "Applied Computing, Instrumentation and Measurement", 3),
    ("ISAT 271", "Technology, Science and Society", 3),
]

_TERM_LABEL_INDEX: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"first\s+year\s+fall|freshman\s+fall", re.I), 0),
    (re.compile(r"first\s+year\s+spring|freshman\s+spring", re.I), 1),
    (re.compile(r"second\s+year\s+fall|sophomore\s+fall", re.I), 2),
    (re.compile(r"second\s+year\s+spring|sophomore\s+spring", re.I), 3),
    (re.compile(r"third\s+year\s+fall|junior\s+fall", re.I), 4),
    (re.compile(r"third\s+year\s+spring|junior\s+spring", re.I), 5),
    (re.compile(r"fourth\s+year\s+fall|senior\s+fall", re.I), 6),
    (re.compile(r"fourth\s+year\s+spring|senior\s+spring", re.I), 7),
]

_COURSE_IN_TEXT = re.compile(r"(?:ISAT\s*)?\d{3}[A-Za-z]?", re.I)
_TOOK_RE = re.compile(
    r"\b(already\s+(took|completed|finished)|i\s+(already\s+)?(took|have\s+taken)|have\s+completed)\b",
    re.I,
)
_DROP_RE = re.compile(r"\b(drop|remove|don't want|do not want|without)\b", re.I)
_ADD_RE = re.compile(r"\b(add|include|instead take)\b", re.I)
_SWAP_RE = re.compile(
    r"swap\s+(ISAT\s*\d{3}[A-Za-z]?).{0,24}(?:for|with)\s+(ISAT\s*\d{3}[A-Za-z]?)",
    re.I,
)


@dataclass
class CourseNode:
    code: str
    title: str
    credits: int
    category: str
    prereqs: list[str]
    status: CourseStatus

    def to_course(self) -> Course:
        return {
            "code": self.code,
            "title": self.title,
            "credits": self.credits,
            "category": self.category,
            "prereqs": list(self.prereqs),
            "status": self.status,
        }


@dataclass
class StudentPlanGraph:
    standing: str
    credit_band: tuple[int, int]
    credits_completed: int
    major_credits_completed: int
    major_credits_remaining: int
    gen_ed_credits_completed: int
    gen_ed_credits_remaining: int
    graduation_timing: str
    remaining_term_count: int
    first_future_semester: int
    concentration: str
    sector: str
    selected_concentration_courses: list[str]
    nodes: dict[str, CourseNode]
    prereq_graph: dict[str, list[str]]
    taken_codes: set[str]
    remaining_codes: list[str]
    timing_constraints: dict[str, int]
    notes: list[str] = field(default_factory=list)

    def mark_taken(self, code: str) -> None:
        code = normalize_course_code(code)
        if not code:
            return
        self.taken_codes.add(code)
        node = self.nodes.get(code)
        if node:
            node.status = "taken"
        self.remaining_codes = [c for c in self.remaining_codes if c != code]
        self._refresh_completed_credits()

    def set_timing(self, code: str, term_idx: int) -> None:
        code = normalize_course_code(code)
        if code:
            self.timing_constraints[code] = term_idx

    def replace_selected(self, old: str, new: str) -> None:
        old_c = normalize_course_code(old)
        new_c = normalize_course_code(new)
        self.selected_concentration_courses = [
            new_c if normalize_course_code(c) == old_c else c
            for c in self.selected_concentration_courses
        ]
        if new_c and new_c not in self.selected_concentration_courses:
            self.selected_concentration_courses.append(new_c)

    def _refresh_completed_credits(self) -> None:
        taken_isat = sum(
            n.credits
            for n in self.nodes.values()
            if n.status == "taken" and n.category != "General Education" and n.code != "GENED"
        )
        remaining_isat = sum(
            n.credits
            for n in self.nodes.values()
            if n.status != "taken" and n.category != "General Education" and n.code != "GENED"
        )
        self.major_credits_completed = taken_isat
        self.major_credits_remaining = remaining_isat
        completed_gen = min(max(int(self.gen_ed_credits_completed or 0), 0), GEN_ED_TARGET)
        self.gen_ed_credits_completed = completed_gen
        self.gen_ed_credits_remaining = max(0, GEN_ED_TARGET - completed_gen)
        self.credits_completed = taken_isat + completed_gen


def remaining_term_count(standing: str, timing: str) -> int:
    base = STANDING_REMAINING_TERMS_ON_TIME.get(standing, 8)
    if timing == "extra_semester":
        return base + 1
    if timing == "extra_year":
        return base + 2
    if timing == "year_early":
        return max(1, base - 2)
    if timing == "semester_early":
        return max(1, base - 1)
    return base


def first_future_semester(standing: str) -> int:
    return STANDING_FIRST_FUTURE.get(standing, 0)


def core_checklist_groups(standing: str) -> list[tuple[str, list[str]]]:
    groups = list(CORE_COURSE_GROUPS)
    if standing in {"junior", "senior"}:
        groups.append(CAPSTONE_GROUP)
    return groups


def parse_standing(text: str) -> str | None:
    low = (text or "").lower()
    patterns = [
        ("freshman", r"\bfreshman\b|\bfirst[\s-]?year\b"),
        ("sophomore", r"\bsophomore\b|\bsoftmore\b|\bsecond[\s-]?year\b"),
        ("junior", r"\bjunior\b|\bthird[\s-]?year\b"),
        ("senior", r"\bsenior\b|\bfourth[\s-]?year\b"),
    ]
    for key, pat in patterns:
        if re.search(pat, low):
            return key
    return None


def parse_graduation_timing(text: str) -> str | None:
    low = (text or "").lower()
    if re.search(r"year\s+early|a\s+year\s+early", low):
        return "year_early"
    if re.search(r"semester\s+early|a\s+semester\s+early", low):
        return "semester_early"
    if re.search(r"extra\s+year|another\s+year|additional\s+year", low):
        return "extra_year"
    if re.search(r"extra\s+semester|additional\s+semester|another\s+semester", low):
        return "extra_semester"
    if re.search(r"on\s+time", low):
        return "on_time"
    return None


def parse_gen_ed_credits(text: str) -> tuple[bool, int | None]:
    """
    Returns (answered, credits). Credits are clamped to 0–41.
    'None yet' is an answered 0.
    """
    raw = (text or "").strip()
    if not raw:
        return False, None
    low = raw.lower()
    if re.search(r"\bnone\b", low):
        return True, 0
    match = re.search(r"(\d{1,3})\s*credits", low)
    if not match:
        match = re.search(r"\b(\d{1,3})\b", low)
    if not match:
        return False, None
    n = int(match.group(1))
    return True, min(GEN_ED_TARGET, max(0, n))


def extract_course_codes(text: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in _COURSE_IN_TEXT.findall(text or ""):
        code = normalize_course_code(raw)
        if code and code not in seen:
            seen.add(code)
            out.append(code)
    return out


def parse_completed_courses(text: str) -> tuple[bool, list[str]]:
    """
    Returns (answered, codes).
    'None yet' is an answered empty list.
    """
    low = (text or "").strip().lower()
    if not low:
        return False, []
    if re.search(r"\bnone\b", low) and not extract_course_codes(text):
        return True, []
    codes = extract_course_codes(text)
    if codes or re.search(r"\bnone\b", low):
        return True, codes
    return False, []


def parse_timing_constraints(text: str, first_future: int = 0) -> dict[str, int]:
    out: dict[str, int] = {}
    blob = text or ""
    for pattern, idx in _TERM_LABEL_INDEX:
        for m in pattern.finditer(blob):
            window = blob[max(0, m.start() - 48) : m.end() + 48]
            for code in extract_course_codes(window):
                out[code] = idx
    if out:
        return out
    codes = extract_course_codes(blob)
    if not codes:
        return out
    low = blob.lower()
    if re.search(r"\bspring\b", low) and not re.search(r"\bfall\b", low):
        idx = first_future if first_future % 2 == 1 else first_future + 1
        for code in codes:
            out[code] = idx
    elif re.search(r"\bfall\b", low) and not re.search(r"\bspring\b", low):
        idx = first_future if first_future % 2 == 0 else first_future + 1
        for code in codes:
            out[code] = idx
    return out


def looks_like_schedule_edit(text: str) -> bool:
    low = (text or "").lower()
    if "generate my schedule" in low:
        return True
    if _TOOK_RE.search(low) or _DROP_RE.search(low) or _ADD_RE.search(low) or _SWAP_RE.search(text or ""):
        return True
    if re.search(r"\b(move|switch|change|replace|instead)\b", low) and extract_course_codes(text):
        return True
    return False


def apply_plan_edits(graph: StudentPlanGraph, edit_text: str, extra_nodes: Sequence[Course] | None = None) -> StudentPlanGraph:
    """Mutate graph from a follow-up edit (already took / move / swap / drop / add)."""
    extra_map = {normalize_course_code(c["code"]): c for c in (extra_nodes or []) if c.get("code")}
    if _TOOK_RE.search(edit_text or ""):
        for code in extract_course_codes(edit_text):
            if code not in graph.nodes and code in extra_map:
                c = extra_map[code]
                graph.nodes[code] = CourseNode(
                    code=code,
                    title=str(c.get("title") or code),
                    credits=int(c.get("credits") or 3),
                    category=str(c.get("category") or "Core"),
                    prereqs=list(c.get("prereqs") or []),
                    status="taken",
                )
                graph.prereq_graph[code] = list(c.get("prereqs") or [])
            graph.mark_taken(code)
    timing = parse_timing_constraints(edit_text, first_future=graph.first_future_semester)
    for code, idx in timing.items():
        graph.set_timing(code, idx)
    swap = _SWAP_RE.search(edit_text or "")
    if swap:
        old_c = normalize_course_code(swap.group(1))
        new_c = normalize_course_code(swap.group(2))
        graph.replace_selected(old_c, new_c)
        if new_c in extra_map and new_c not in graph.nodes:
            c = extra_map[new_c]
            graph.nodes[new_c] = CourseNode(
                code=new_c,
                title=str(c.get("title") or new_c),
                credits=int(c.get("credits") or 3),
                category=str(c.get("category") or "Concentration"),
                prereqs=list(c.get("prereqs") or []),
                status="remaining",
            )
            graph.prereq_graph[new_c] = list(c.get("prereqs") or [])
            graph.remaining_codes.append(new_c)
        if old_c in graph.nodes and old_c not in graph.taken_codes:
            graph.remaining_codes = [c for c in graph.remaining_codes if c != old_c]
            graph.nodes.pop(old_c, None)
            graph.prereq_graph.pop(old_c, None)
    elif _DROP_RE.search(edit_text or "") and not _TOOK_RE.search(edit_text or ""):
        for code in extract_course_codes(edit_text):
            graph.selected_concentration_courses = [
                c for c in graph.selected_concentration_courses if normalize_course_code(c) != code
            ]
            if code in graph.nodes and code not in graph.taken_codes:
                graph.remaining_codes = [c for c in graph.remaining_codes if c != code]
                graph.nodes.pop(code, None)
                graph.prereq_graph.pop(code, None)
    elif _ADD_RE.search(edit_text or ""):
        for code in extract_course_codes(edit_text):
            if code not in graph.selected_concentration_courses:
                graph.selected_concentration_courses.append(code)
            if code in extra_map and code not in graph.nodes:
                c = extra_map[code]
                graph.nodes[code] = CourseNode(
                    code=code,
                    title=str(c.get("title") or code),
                    credits=int(c.get("credits") or 3),
                    category=str(c.get("category") or "Concentration"),
                    prereqs=list(c.get("prereqs") or []),
                    status="remaining",
                )
                graph.prereq_graph[code] = list(c.get("prereqs") or [])
                graph.remaining_codes.append(code)
    graph._refresh_completed_credits()
    return graph


def _course_map(rules: ProgramRules) -> dict[str, Course]:
    out: dict[str, Course] = {}
    if getattr(rules, "all_courses", None):
        for code, course in rules.all_courses.items():
            out[normalize_course_code(code)] = dict(course)
    for group in (
        rules.first_year_fall,
        rules.first_year_spring,
        rules.stage2,
        rules.stage5,
    ):
        for course in group:
            out[normalize_course_code(course["code"])] = dict(course)
    for group in rules.sector_by_name.values():
        for course in group:
            out[normalize_course_code(course["code"])] = dict(course)
    for group in rules.concentration_options.values():
        for course in group:
            out[normalize_course_code(course["code"])] = dict(course)
    for code, title, credits in _CORE_EXTRAS:
        out.setdefault(
            code,
            {
                "code": code,
                "title": title,
                "credits": credits,
                "category": "Core",
                "prereqs": [],
                "status": "remaining",
            },
        )
    return out


def _as_node(course: Course, status: CourseStatus) -> CourseNode:
    hydrated = _hydrate_course_metadata(dict(course))
    prereqs = [normalize_course_code(p) for p in (hydrated.get("prereqs") or []) if normalize_course_code(p)]
    return CourseNode(
        code=normalize_course_code(hydrated["code"]),
        title=str(hydrated.get("title") or hydrated["code"]),
        credits=int(hydrated.get("credits") or 3),
        category=str(hydrated.get("category") or "Core"),
        prereqs=prereqs,
        status=status,
    )


def required_courses_for_student(
    rules: ProgramRules,
    concentration: str,
    sector: str,
    selected_concentration_courses: Iterable[str],
) -> list[Course]:
    catalog = _course_map(rules)
    selected_norm = [normalize_course_code(c) for c in selected_concentration_courses if normalize_course_code(c)]
    codes: list[str] = []
    for course in rules.first_year_fall + rules.first_year_spring:
        codes.append(normalize_course_code(course["code"]))
    for code, _, _ in _CORE_EXTRAS:
        codes.append(code)
    for course in rules.stage2 + rules.stage5:
        codes.append(normalize_course_code(course["code"]))
    for course in rules.sector_by_name.get(sector.strip().lower(), []):
        codes.append(normalize_course_code(course["code"]))
    option_map = {
        normalize_course_code(c["code"]): c for c in rules.concentration_options.get(concentration, [])
    }
    for code in selected_norm:
        if code in option_map:
            codes.append(code)
    out: list[Course] = []
    seen: set[str] = set()
    for code in codes:
        if not code or code in seen:
            continue
        seen.add(code)
        if code in catalog:
            out.append(dict(catalog[code]))
        elif code in option_map:
            out.append(dict(option_map[code]))
    return out


def build_student_plan_graph(
    rules: ProgramRules,
    *,
    concentration: str,
    sector: str,
    selected_concentration_courses: Sequence[str],
    standing: str = "freshman",
    graduation_timing: str = "on_time",
    taken_courses: Sequence[str] | None = None,
    gen_ed_credits: int = 0,
    timing_constraints: dict[str, int] | None = None,
) -> StudentPlanGraph:
    standing_key = standing if standing in STANDING_CREDIT_BANDS else "freshman"
    timing_key = graduation_timing if graduation_timing in {
        "on_time",
        "extra_semester",
        "extra_year",
        "semester_early",
        "year_early",
    } else "on_time"
    taken = {normalize_course_code(c) for c in (taken_courses or []) if normalize_course_code(c)}
    required = required_courses_for_student(rules, concentration, sector, selected_concentration_courses)
    nodes: dict[str, CourseNode] = {}
    for course in required:
        node = _as_node(course, "taken" if normalize_course_code(course["code"]) in taken else "remaining")
        # Only keep prereqs that are also in the degree plan or already taken.
        nodes[node.code] = node

    catalog = _course_map(rules)
    for code in taken:
        if code in nodes:
            continue
        if code in catalog:
            nodes[code] = _as_node(catalog[code], "taken")
        else:
            nodes[code] = CourseNode(
                code=code,
                title=code,
                credits=3,
                category="Transfer",
                prereqs=[],
                status="taken",
            )

    plan_codes = set(nodes)
    for node in nodes.values():
        node.prereqs = [p for p in node.prereqs if p in plan_codes or p in taken]

    prereq_graph = {code: list(node.prereqs) for code, node in nodes.items()}
    remaining_codes = sorted(
        (code for code, node in nodes.items() if node.status != "taken"),
        key=lambda c: (min_index_for_course(c), _course_level(c), c),
    )
    timing_norm = {
        normalize_course_code(k): int(v)
        for k, v in (timing_constraints or {}).items()
        if normalize_course_code(k)
    }
    graph = StudentPlanGraph(
        standing=standing_key,
        credit_band=STANDING_CREDIT_BANDS[standing_key],
        credits_completed=0,
        major_credits_completed=0,
        major_credits_remaining=0,
        gen_ed_credits_completed=min(max(int(gen_ed_credits or 0), 0), GEN_ED_TARGET),
        gen_ed_credits_remaining=GEN_ED_TARGET,
        graduation_timing=timing_key,
        remaining_term_count=remaining_term_count(standing_key, timing_key),
        first_future_semester=first_future_semester(standing_key),
        concentration=concentration,
        sector=sector.strip().lower(),
        selected_concentration_courses=[
            normalize_course_code(c) for c in selected_concentration_courses if normalize_course_code(c)
        ],
        nodes=nodes,
        prereq_graph=prereq_graph,
        taken_codes={c for c, n in nodes.items() if n.status == "taken"},
        remaining_codes=remaining_codes,
        timing_constraints=timing_norm,
    )
    graph._refresh_completed_credits()
    return graph
