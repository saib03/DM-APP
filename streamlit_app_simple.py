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
        raise ValueError("Your CSV must contain student and course columns.")

    for row in reader:
        student = (row.get("student") or "").strip()
        course = (row.get("course") or "").strip()
        if student and course:
            students.setdefault(student, set()).add(course)

    return students


def build_graph(students):
    """Courses = vertices. Edge between two courses if a student takes both."""
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
    """DSATUR: colour the most constrained course first, smallest free colour."""
    slot_of = {}

    while len(slot_of) < len(graph):

        def priority(course):
            saturation = len({slot_of[n] for n in graph[course] if n in slot_of})
            return saturation, len(graph[course])

        course = max(
            (c for c in sorted(graph) if c not in slot_of), key=priority
        )
        used = {slot_of[n] for n in graph[course] if n in slot_of}

        slot = 0
        while slot in used:
            slot += 1
        slot_of[course] = slot

    return slot_of


def draw_graph(graph, slot_of):
    names = sorted(graph)
    n = len(names)
    pos = {
        c: (math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n))
        for i, c in enumerate(names)
    }

    fig, ax = plt.subplots(figsize=(7, 7))

    for a in graph:
        for b in graph[a]:
            if a < b:
                ax.plot(
                    [pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]],
                    color="#bbbbbb", linewidth=1, zorder=1,
                )

    colours = plt.get_cmap("tab10")
    for c in names:
        x, y = pos[c]
        ax.scatter(x, y, s=1800, color=colours(slot_of[c] % 10),
                   edgecolors="black", zorder=2)
        ax.text(x, y, f"{c}\nSlot {slot_of[c] + 1}",
                ha="center", va="center", fontsize=7, zorder=3)

    ax.set_aspect("equal")
    ax.axis("off")
    return fig


# ---------------- App ----------------
st.title("Exam Clash-Free Scheduler")
st.write(
    "Courses are vertices. Two courses are joined by an edge if a student "
    "takes both. Graph coloring gives clashing courses different exam slots."
)

with st.sidebar:
    st.header("Settings")
    file = st.file_uploader("Enrolment CSV (student, course)", type="csv")
    start = st.date_input("First exam day", date.today() + timedelta(days=14))
    per_day = st.number_input("Sessions per day", min_value=1, max_value=4, value=2)

if file:
    try:
        students = read_enrolments(file.getvalue().decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as e:
        st.error(str(e))
        st.stop()
else:
    students = {s: set(c) for s, c in DEMO.items()}
    st.info("Showing demo data. Upload your own CSV in the sidebar.")

graph = build_graph(students)
if not graph:
    st.error("No valid student-course data found in the file.")
    st.stop()

slot_of = colour_graph(graph)
slots_used = max(slot_of.values()) + 1
degree_sum = sum(len(v) for v in graph.values())
edges = degree_sum // 2

m1, m2, m3, m4 = st.columns(4)
m1.metric("Students", len(students))
m2.metric("Courses", len(graph))
m3.metric("Clash pairs (edges)", edges)
m4.metric("Slots used", slots_used)

rows = []
for course in sorted(graph, key=lambda x: (slot_of[x], x)):
    slot = slot_of[course]
    rows.append({
        "Slot": slot + 1,
        "Date": (start + timedelta(days=slot // per_day)).strftime("%a %d %b %Y"),
        "Session": slot % per_day + 1,
        "Course": course,
    })

tab1, tab2, tab3 = st.tabs(["Timetable", "Clash graph", "Check a student"])

with tab1:
    st.dataframe(rows, use_container_width=True, hide_index=True)

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    st.download_button("Download timetable CSV", out.getvalue(),
                       "timetable.csv", mime="text/csv")

with tab2:
    left, right = st.columns([3, 2])
    left.pyplot(draw_graph(graph, slot_of))
    right.write("Same colour = same slot. A line means the two courses "
                "share at least one student.")
    right.write("**Degree of each course (number of clashes)**")
    right.dataframe(
        [{"Course": c, "Degree": len(graph[c])}
         for c in sorted(graph, key=lambda c: -len(graph[c]))],
        hide_index=True, use_container_width=True,
    )
    right.caption(
        f"Handshaking lemma: sum of degrees = {degree_sum} = 2 x {edges} edges"
    )

with tab3:
    who = st.selectbox("Student", sorted(students))
    st.dataframe(
        [{"Course": c, "Slot": slot_of[c] + 1}
         for c in sorted(students[who], key=lambda c: slot_of[c])],
        hide_index=True,
    )

    all_ok = all(
        len({slot_of[c] for c in courses}) == len(courses)
        for courses in students.values()
    )
    if all_ok:
        st.success("Checked all students: nobody has two exams in the same slot.")
    else:
        st.error("Some student has a clash!")
