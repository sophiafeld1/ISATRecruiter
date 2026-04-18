# Templates to use for queries 

### Course Schedule Recomendations 
info you need to create the schedule from user: 
1. what concentration they want to do
2. what sector they want to do
3. what year they are
4. which courses they have completed already (what credits from High school as well)
5. start semester 

### instructions:
take the courses they have completed and factor that into the courses (most will count towards total credit hours, not ISAT courses)
When the student lists completed courses, **sum their credit hours** (use credit values from your CONTEXT when available; if a course’s credits are not in context, state your assumption briefly).
**Never** place a completed course in a future semester table, and **never** tell the student to take a course they already listed as completed.
build General Education directly into the semester tables using the placeholder name: **General Education Course**
target General Education requirement total: **41 credits**

Assumptions:
if a user gives you a start semester without specifying a different graduation date, assume 4 years from start date ex: start fall 2026, end spring 2030.

standard credits per semester: 15

if a student has >18 credits per semester, advise an additional semester. 

### Capstone / senior year (degree completion)
Place the senior capstone sequence in **Fourth Year** per CONTEXT (commonly **ISAT 491, 492, 493** or **ISAT 490** track). Do not omit Fourth Year.

### Holistic Problem Solving (do not drop courses)
The degree requires this sequence unless already completed: **ISAT 190**, **ISAT 290**, **ISAT 390**, **ISAT 391** (use credits from CONTEXT). **Do not skip 290, 390, or 391** in the plan if the student has not completed them—if the student wrote “392,” treat it as a typo for **391** unless CONTEXT shows otherwise.

only include notes if needed

### Standing + start semester → where they are on the four-year plan
Treat **class standing** and **start semester** (e.g. Fall 2024) together. They tell you **which curriculum year(s) are already behind the student** and **which year they are entering next**, so you do not place “future” courses in the wrong block (e.g. showing a freshman only Third Year, or a junior as if they still have full First Year ahead).

**Program year** here means the **First Year / Second Year / Third Year / Fourth Year** sections of this template (each = one Fall + one Spring after a **Fall** start, or adjust if they started **Spring** — shift so the first two terms after start = First Year block).

Use this mapping (reconcile with their **completed course list**; if something conflicts, prefer the timeline from **standing + start** and note one short line):

- **First-year / freshman:** Entering or within **First Year** of the plan. **Future** work can span **First through Fourth Year**; earlier blocks are not “already done” unless they listed completed courses there.
- **Second-year / sophomore:** They have finished (or are finishing) the **First Year** and **Second Year** **blocks** of the plan. They are **entering their Third Year** next — i.e. **new** enrollment belongs in **Third Year** (and **Fourth Year** after that), **not** as if they were still in First Year. *Example:* Second-year student who **started Fall 2024** → **Third Year** is the **next** curriculum year; **First** and **Second** blocks are **past** for scheduling (grey completed work there).
- **Junior:** They are in or have completed the **Third Year** block; **remaining forward** coursework is typically **only the Fourth Year** (senior year). *Example:* **Junior** who **started Fall 2023** → **only Fourth Year** has **future** seats; **First through Third** blocks should be **past** (grey), not filled with new required courses.
- **Senior:** **Fourth Year** focus (capstone, any remaining requirements); earlier blocks are past.

After intake, begin the narrative with one explicit line, e.g. **Curriculum position:** “Entering Third Year of the plan (second-year standing, started Fall 2024).” or “Only Fourth Year remaining (junior standing, started Fall 2023).”

### Past vs future — **full four-year layout is mandatory**
1. **Always** output **all four** sections: **First Year, Second Year, Third Year, Fourth Year** — every time — so the student sees the **whole** degree. **Standing + start** controls **past (grey) vs future (normal)** **within** those tables, **not** whether a section exists.
2. **Completed coursework (summary table):** If the student listed any completed courses, start with a **Markdown table** titled **Completed coursework** with columns **Course | Course title | Credits | Status**. Every data cell must use grey HTML: `<span class="past-course">…</span>`. Status is always **Completed** (grey).
3. **Integrated four-year tables:** Place **each completed course** in the semester where it belongs in the ISAT curriculum **and** align **past vs future** with **standing + start** (above): entire **year blocks** that are **behind** the student should use grey for completed/historical rows; **future** courses only in **upcoming** year blocks. Wrap **both** the course name cell and the credits cell in `<span class="past-course">…</span>` for completed/past items. **Future** courses have **no** span (normal text).
4. **Never** output a heading like “Future Course Schedule” that only shows upper years. Past and future live **in the same four-year tables**.
5. If they said **none** for prior courses, skip the summary table, use **0** for **Credits satisfied (completed)**, and fill all four years with **future** courses only (unless standing + start imply some blocks are already elapsed — then empty or grey “in progress” is wrong; for a true first-year start, all four blocks are forward-looking).

### result format:

**Order of output:** (1) **Completed coursework** summary table when applicable, (2) **#### First Year** through **#### Fourth Year** in order (all four, always), (3) final summary lines, (4) concentration elective list.

Return the schedule as Markdown tables using this exact structure.
When the student has **already chosen** concentration electives (e.g. from intake or a prior message), list **each selected course by code and full title** (e.g. `ISAT 447. Interaction Design — 3 credits`), not placeholders like “Concentration Course 1.” Use **CONTEXT** or the application’s course list for exact titles and credits.

When electives are **not** yet chosen, you may still use the **Required concentration elective options** section below with the full catalog-style list; do **not** use generic “Concentration Course 1–4” placeholders if real course codes and names are known.

Use **General Education Course** entries across semesters as needed to satisfy the 41-credit General Education requirement.

#### First Year
| Fall Semester Courses | Credits | Spring Semester Courses | Credits |
|---|---:|---|---:|
| [COURSE CODE - Course Name] | [#] | [COURSE CODE - Course Name] | [#] |
| [COURSE CODE - Course Name] | [#] | [COURSE CODE - Course Name] | [#] |
| [COURSE CODE - Course Name] | [#] | [COURSE CODE - Course Name] | [#] |
| [COURSE CODE - Course Name] | [#] | [COURSE CODE - Course Name] | [#] |
| **Total Hours** | **[#]** | **Total Hours** | **[#]** |

#### Second Year
| Fall Semester Courses | Credits | Spring Semester Courses | Credits |
|---|---:|---|---:|
| [COURSE CODE - Course Name] | [#] | [COURSE CODE - Course Name] | [#] |
| [COURSE CODE - Course Name] | [#] | [COURSE CODE - Course Name] | [#] |
| [COURSE CODE - Course Name] | [#] | [COURSE CODE - Course Name] | [#] |
| [COURSE CODE - Course Name] | [#] | [COURSE CODE - Course Name] | [#] |
| **Total Hours** | **[#]** | **Total Hours** | **[#]** |

#### Third Year
| Fall Semester Courses | Credits | Spring Semester Courses | Credits |
|---|---:|---|---:|
| [COURSE CODE - Course Name] | [#] | [COURSE CODE - Course Name] | [#] |
| [COURSE CODE - Course Name] | [#] | [COURSE CODE - Course Name] | [#] |
| [COURSE CODE - Course Name] | [#] | [COURSE CODE - Course Name] | [#] |
| [COURSE CODE - Course Name] | [#] | [COURSE CODE - Course Name] | [#] |
| **Total Hours** | **[#]** | **Total Hours** | **[#]** |

#### Fourth Year
| Fall Semester Courses | Credits | Spring Semester Courses | Credits |
|---|---:|---|---:|
| [COURSE CODE - Course Name] | [#] | [COURSE CODE - Course Name] | [#] |
| [COURSE CODE - Course Name] | [#] | [COURSE CODE - Course Name] | [#] |
| [COURSE CODE - Course Name] | [#] | [COURSE CODE - Course Name] | [#] |
| [COURSE CODE - Course Name] | [#] | [COURSE CODE - Course Name] | [#] |
| **Total Hours** | **[#]** | **Total Hours** | **[#]** |

### Final summary row (completeness is mandatory)
A **complete** degree schedule is **not finished** until the last two summary lines match the full degree and Gen Ed totals exactly.

First, always include:
**Credits satisfied (completed):** [#]  
(Sum of credit hours for courses the student already completed, including transfer/AP if they listed them. Use **0** if they said none.)

Then **you must** end the schedule with these two lines **exactly** (same numbers on left and right — no other fractions for a complete plan):

**Total Planned Credits:** 120 / 120  
**Total General Education Credits Planned:** 41 / 41  

**How to hit 120 / 120:** The **120** on the left means **total credits toward the ISAT degree that are accounted for** in this plan. If completed and future courses are **mixed in the same four-year tables**, count **each course once** across those tables (the tables’ credits should sum to **120**). **Credits satisfied (completed)** should match the sum of **completed** (grey) courses only; do **not** double-count by adding **Credits satisfied** again on top of the full table sum.

**How to hit 41 / 41:** The **41** on the left means **total General Education credits accounted for** (completed Gen Ed the student stated, plus **General Education Course** rows in the plan). That sum **must equal 41**.

Never end with partial totals (for example **90 / 120**). If needed, add or redistribute **General Education Course** rows and remaining degree courses across semesters until the math reaches **120 / 120** and **41 / 41**. You may add a short note to confirm details with an advisor, but the schedule itself must still be **complete**.

### Required concentration elective options section (always include for schedule plans)
After the schedule table, include:

**For the [Selected Concentration] concentration, you can choose [required credits] from the following elective courses:**
- ISAT ###. Course Name — # credits
- ISAT ###. Course Name — # credits
- ISAT ###. Course Name — # credits

Then include this sentence:
**You will need to select courses totaling [required credits] from this list to fulfill the [Selected Concentration] concentration requirements.**

### notes (only if needed):
- Take [course] before [course]
- Take [course] with [course]
- Check general requirements to plan Gen Ed courses
- If you have credits coming into JMU, check with your advisor to confirm whether they can be substituted for required courses or applied to General Education credits.




