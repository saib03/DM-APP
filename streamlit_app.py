
import csv
import io
import math
from datetime import date, timedelta

import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title="Exam Clash-Free Scheduler", layout="wide")

DEMO = {
    "S01": ["Maths", "Physics", "Chemistry"],
    "S02": ["Maths", "Physics", "English"],
    "S03": ["Physics", "Chemistry", "Economics"],
    "S04": ["DSA", "DBMS", "OS"],
    "S05": ["DSA", "OS", "CN"],
    "S06": ["DBMS", "CN", "AI"],
    "S07": ["OS", "CN", "AI"],
    "S08": ["DSA", "AI", "English"],
    "S09": ["English", "Economics", "Maths"],
    "S10": ["Economics", "DBMS", "English"],
}


def read_enrolments(text):
    students = {}

    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))

    if not reader.fieldnames:
        raise ValueError("The CSV file is empty.")

    reader.fieldnames = [
        name.strip().lower().replace(" ", "").replace("_", "")
        for name in reader.fieldnames
    ]

    if "student" not in reader.fieldnames or "course" not in reader.fieldnames:
        raise ValueError(
            "Missing columns. Your CSV must contain student and course columns."
        )

    for row in reader:
        student = (row.get("student") or "").strip()
        course = (row.get("course") or "").strip()

        if student and course:
            students.setdefault(student, set()).add(course)

    return students


def build_graph(students):
    graph = {}

    for courses in students.values():
        for course in courses:
            graph.setdefault(course, set())

        for a in courses:
            for b in courses:
                if a != b:
                    graph[a].add(b)

    return graph


def colour_graph(graph):
    slot_of = {}

    while len(slot_of) < len(graph):

        def priority(course):
            saturation = len({
                slot_of[n] for n in graph[course] if n in slot_of
            })
            return saturation, len(graph[course])

        course = max(
            (c for c in sorted(graph) if c not in slot_of),
            key=priority
        )

        used = {
            slot_of[n] for n in graph[course] if n in slot_of
        }

        slot = 0
        while slot in used:
            slot += 1

        slot_of[course] = slot

    return slot_of


def largest_clique(graph):
    best = 0

    def grow(size, candidates):
        nonlocal best
        best = max(best, size)

        for vertex in list(candidates):
            grow(size + 1, candidates & graph[vertex])
            candidates = candidates - {vertex}

    grow(0, set(graph))
    return best


def draw_graph(graph, slot_of):
    names = sorted(graph)
    n = len(names)

    pos = {
        course: (
            math.cos(2 * math.pi * i / n),
            math.sin(2 * math.pi * i / n)
        )
        for i, course in enumerate(names)
    }

    fig, ax = plt.subplots(figsize=(7, 7))

    for a in graph:
        for b in graph[a]:
            if a < b:
                ax.plot(
                    [pos[a][0], pos[b][0]],
                    [pos[a][1], pos[b][1]],
                    color="#bbbbbb",
                    linewidth=1,
                    zorder=1
                )

    colours = plt.get_cmap("tab10")

    for course in names:
        x, y = pos[course]

        ax.scatter(
            x, y,
            s=1800,
            color=colours(slot_of[course] % 10),
            edgecolors="black",
            zorder=2
        )

        ax.text(
            x, y,
            f"{course}\nSlot {slot_of[course] + 1}",
            ha="center",
            va="center",
            fontsize=7,
            zorder=3
        )

    ax.set_aspect("equal")
    ax.axis("off")

    return fig


st.title("Exam Clash-Free Scheduler")

st.write(
    "Courses are **vertices**. Two courses are joined by an **edge** "
    "if a student takes both. Graph coloring assigns different exam "
    "slots to courses that clash."
)

with st.sidebar:
    st.header("Settings")

    file = st.file_uploader(
        "Enrolment CSV (student, course)",
        type="csv"
    )

    start = st.date_input(
        "First exam day",
        date.today() + timedelta(days=14)
    )

    per_day = st.number_input(
        "Sessions per day",
        min_value=1,
        max_value=4,
        value=2
    )

    capacity = st.number_input(
        "Hall capacity per slot (0 = ignore)",
        min_value=0,
        max_value=10000,
        value=0
    )


if file:
    try:
        students = read_enrolments(
            file.getvalue().decode("utf-8-sig")
        )
    except (KeyError, ValueError, UnicodeDecodeError) as e:
        st.error(str(e))
        st.stop()
else:
    students = {s: set(courses) for s, courses in DEMO.items()}
    st.info(
        "Showing demo data. Upload your own CSV in the sidebar to replace it."
    )


graph = build_graph(students)

if not graph:
    st.error("No valid student-course data found in the file.")
    st.stop()


slot_of = colour_graph(graph)
slots_used = max(slot_of.values()) + 1
lower_bound = largest_clique(graph)
edges = sum(len(v) for v in graph.values()) // 2

size = {
    course: sum(course in courses for courses in students.values())
    for course in graph
}


a, b, c, d, e = st.columns(5)

a.metric("Students", len(students))
b.metric("Courses", len(graph))
c.metric("Clash pairs (edges)", edges)
d.metric("Slots used", slots_used)
e.metric("Minimum possible", lower_bound)


if slots_used == lower_bound:
    st.success(
        "Optimal: no timetable can use fewer slots "
        "because the largest clique requires this many."
    )
else:
    st.info(
        f"The true minimum is between {lower_bound} and {slots_used} slots."
    )


rows = []

for course in sorted(graph, key=lambda x: (slot_of[x], x)):
    slot = slot_of[course]
    exam_day = start + timedelta(days=slot // per_day)

    rows.append({
        "Slot": slot + 1,
        "Date": exam_day.strftime("%a %d %b %Y"),
        "Session": slot % per_day + 1,
        "Course": course,
        "Students": size[course]
    })


tab1, tab2, tab3 = st.tabs([
    "Timetable",
    "Clash graph",
    "Check a student"
])


with tab1:
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True
    )

    out = io.StringIO()

    writer = csv.DictWriter(
        out,
        fieldnames=list(rows[0])
    )

    writer.writeheader()
    writer.writerows(rows)

    st.download_button(
        "Download timetable CSV",
        out.getvalue(),
        "timetable.csv",
        mime="text/csv"
    )

    if capacity:
        for slot in range(slots_used):
            total = sum(
                size[course]
                for course in graph
                if slot_of[course] == slot
            )

            if total > capacity:
                st.warning(
                    f"Slot {slot + 1} has {total} students, "
                    f"over the capacity of {capacity}."
                )


with tab2:
    left, right = st.columns([3, 2])

    left.pyplot(draw_graph(graph, slot_of))

    right.write(
        "Same colour = same slot. A line means the two courses "
        "share at least one student."
    )

    right.write("**Most clash-prone courses (highest degree)**")

    ranked = sorted(
        graph,
        key=lambda course: -len(graph[course])
    )

    right.dataframe(
        [
            {"Course": course, "Clashes": len(graph[course])}
            for course in ranked
        ],
        hide_index=True,
        use_container_width=True
    )

    right.caption(
        f"Handshaking lemma: sum of degrees = "
        f"{sum(len(v) for v in graph.values())} = 2 x {edges} edges"
    )


with tab3:
    who = st.selectbox("Student", sorted(students))

    mine = sorted(
        students[who],
        key=lambda course: slot_of[course]
    )

    st.dataframe(
        [
            {
                "Course": course,
                "Slot": slot_of[course] + 1,
                "Date": (
                    start + timedelta(
                        days=slot_of[course] // per_day
                    )
                ).strftime("%a %d %b")
            }
            for course in mine
        ],
        hide_index=True
    )

    all_ok = all(
        len({slot_of[course] for course in courses}) == len(courses)
        for courses in students.values()
    )

    if all_ok:
        st.success(
            "Check for ALL students: nobody has two exams in the same slot."
        )
    else:
        st.error("Some student has a clash!")
