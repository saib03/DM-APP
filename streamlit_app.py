import csv
import io
import math
from datetime import date, timedelta

import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title="Exam Clash-Free Scheduler", layout="wide")

# Built-in demo data: student -> courses they take
DEMO = {
    "S01": ["Maths", "Physics", "Chemistry"], "S02": ["Maths", "Physics", "English"],
    "S03": ["Physics", "Chemistry", "Economics"], "S04": ["DSA", "DBMS", "OS"],
    "S05": ["DSA", "OS", "CN"], "S06": ["DBMS", "CN", "AI"],
    "S07": ["OS", "CN", "AI"], "S08": ["DSA", "AI", "English"],
    "S09": ["English", "Economics", "Maths"], "S10": ["Economics", "DBMS", "English"],
}


# ---------- 1. read data: {student: set of courses} ----------
def read_enrolments(text):
    students = {}
    for row in csv.DictReader(io.StringIO(text)):
        students.setdefault(row["student"].strip(), set()).add(row["course"].strip())
    return students


# ---------- 2. build graph: {course: set of clashing courses} ----------
def build_graph(students):
    graph = {}
    for courses in students.values():
        for c in courses:
            graph.setdefault(c, set())
        for a in courses:
            for b in courses:
                if a != b:
                    graph[a].add(b)
    return graph


# ---------- 3. DSATUR colouring: {course: slot number starting at 0} ----------
def colour_graph(graph):
    slot_of = {}
    while len(slot_of) < len(graph):
        def priority(c):
            saturation = len({slot_of[n] for n in graph[c] if n in slot_of})
            return (saturation, len(graph[c]))  # most constrained course first
        course = max((c for c in sorted(graph) if c not in slot_of), key=priority)
        used = {slot_of[n] for n in graph[course] if n in slot_of}
        slot = 0
        while slot in used:
            slot += 1
        slot_of[course] = slot
    return slot_of


# ---------- 4. largest group of mutually clashing courses (a complete subgraph) ----------
def largest_clique(graph):
    best = 0

    def grow(size, candidates):
        nonlocal best
        best = max(best, size)
        for v in list(candidates):
            grow(size + 1, candidates & graph[v])
            candidates = candidates - {v}

    grow(0, set(graph))
    return best


# ---------- 5. draw the graph (courses on a circle, coloured by slot) ----------
def draw_graph(graph, slot_of):
    names = sorted(graph)
    n = len(names)
    pos = {c: (math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n))
           for i, c in enumerate(names)}
    fig, ax = plt.subplots(figsize=(7, 7))
    for a in graph:
        for b in graph[a]:
            if a < b:
                ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]],
                        color="#bbbbbb", linewidth=1, zorder=1)
    colours = plt.get_cmap("tab10")
    for c in names:
        x, y = pos[c]
        ax.scatter(x, y, s=1800, color=colours(slot_of[c] % 10), edgecolors="black", zorder=2)
        ax.text(x, y, f"{c}\nSlot {slot_of[c] + 1}", ha="center", va="center", fontsize=7, zorder=3)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig


# =================== the web page ===================
st.title("Exam Clash-Free Scheduler")
st.write("Courses are **vertices**. Two courses are joined by an **edge** if a student takes both. "
         "Colouring the graph so that joined courses get different colours gives a clash-free timetable.")

with st.sidebar:
    st.header("Settings")
    file = st.file_uploader("Enrolment CSV (student,course)", type="csv")
    start = st.date_input("First exam day", date.today() + timedelta(days=14))
    per_day = st.number_input("Sessions per day", 1, 4, 2)
    capacity = st.number_input("Hall capacity per slot (0 = ignore)", 0, 10000, 0)

if file:
    try:
        students = read_enrolments(file.getvalue().decode("utf-8"))
    except KeyError:
        st.error("The CSV needs a header row with exactly: student,course")
        st.stop()
else:
    students = {s: set(c) for s, c in DEMO.items()}
    st.info("Showing demo data. Upload your own CSV in the sidebar to replace it.")

graph = build_graph(students)
if not graph:
    st.error("No data found in the file.")
    st.stop()

slot_of = colour_graph(graph)
slots_used = max(slot_of.values()) + 1
lower_bound = largest_clique(graph)
edges = sum(len(v) for v in graph.values()) // 2
size = {c: sum(c in cs for cs in students.values()) for c in graph}

# summary numbers
a, b, c, d, e = st.columns(5)
a.metric("Students", len(students))
b.metric("Courses", len(graph))
c.metric("Clash pairs (edges)", edges)
d.metric("Slots used", slots_used)
e.metric("Minimum possible", lower_bound)

if slots_used == lower_bound:
    st.success("Optimal: no timetable can use fewer slots (the largest clique forces this many).")
else:
    st.info(f"The true minimum is between {lower_bound} and {slots_used} slots.")

# build timetable rows
rows = []
for course in sorted(graph, key=lambda x: (slot_of[x], x)):
    s = slot_of[course]
    day = start + timedelta(days=s // per_day)
    rows.append({"Slot": s + 1, "Date": day.strftime("%a %d %b %Y"),
                 "Session": s % per_day + 1, "Course": course, "Students": size[course]})

tab1, tab2, tab3 = st.tabs(["Timetable", "Clash graph", "Check a student"])

with tab1:
    st.dataframe(rows, use_container_width=True, hide_index=True)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    st.download_button("Download timetable CSV", out.getvalue(), "timetable.csv")
    if capacity:
        for s in range(slots_used):
            total = sum(size[x] for x in graph if slot_of[x] == s)
            if total > capacity:
                st.warning(f"Slot {s + 1} has {total} students, over the capacity of {capacity}.")

with tab2:
    left, right = st.columns([3, 2])
    left.pyplot(draw_graph(graph, slot_of))
    right.write("Same colour = same slot. A line means the two courses share at least one student.")
    right.write("**Most clash-prone courses (highest degree)**")
    ranked = sorted(graph, key=lambda x: -len(graph[x]))
    right.dataframe([{"Course": x, "Clashes": len(graph[x])} for x in ranked],
                    hide_index=True, use_container_width=True)
    right.caption(f"Handshaking lemma: sum of degrees = {sum(len(v) for v in graph.values())} "
                  f"= 2 x {edges} edges")

with tab3:
    who = st.selectbox("Student", sorted(students))
    mine = sorted(students[who], key=lambda x: slot_of[x])
    st.dataframe([{"Course": x, "Slot": slot_of[x] + 1,
                   "Date": (start + timedelta(days=slot_of[x] // per_day)).strftime("%a %d %b")}
                  for x in mine], hide_index=True)
    all_ok = all(len({slot_of[x] for x in cs}) == len(cs) for cs in students.values())
    st.write("Check for ALL students: nobody has two exams in the same slot."
             if all_ok else "Error: some student has a clash!")
