import csv
import io

import streamlit as st

SAMPLE = """student,course
S01,Maths
S01,DSA
S01,DBMS
S02,Maths
S02,OS
S02,CN
S03,DSA
S03,OS
S03,AI
S04,DBMS
S04,CN
S04,AI
S05,Maths
S05,DSA
S05,OS
S06,CN
S06,AI
S06,DSA
S07,DBMS
S07,OS
S07,Maths
S08,AI
S08,CN
S08,Maths
S09,DSA
S09,DBMS
S09,CN
S10,OS
S10,AI
S10,DBMS
"""


# STEP 1: read the CSV text -> {student: set of courses}
def read_enrolments(text):
    students = {}
    for row in csv.DictReader(io.StringIO(text)):
        students.setdefault(row["student"].strip(), set()).add(row["course"].strip())
    return students


# STEP 2: build the graph -> {course: set of clashing courses}
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


# STEP 3: greedy colouring -> {course: slot number}
def colour_graph(graph):
    slot_of = {}
    for course in sorted(graph, key=lambda c: len(graph[c]), reverse=True):
        used = {slot_of[n] for n in graph[course] if n in slot_of}
        slot = 1
        while slot in used:
            slot += 1
        slot_of[course] = slot
    return slot_of


# ---------------- the web page ----------------
st.title("Exam Clash-Free Scheduler")
st.write("Upload a CSV with columns `student,course`. Courses that share a "
         "student are never placed in the same slot (graph colouring).")

file = st.file_uploader("Enrolment CSV", type="csv")
if file:
    text = file.getvalue().decode("utf-8")
else:
    text = SAMPLE
    st.info("Showing sample data. Upload your own CSV to replace it.")

try:
    graph = build_graph(read_enrolments(text))
except KeyError:
    st.error("The CSV needs a header row with exactly: student,course")
    st.stop()

if not graph:
    st.error("No data found in the file.")
    st.stop()

slot_of = colour_graph(graph)
total_slots = max(slot_of.values())

st.subheader(f"Timetable ({total_slots} slots)")
timetable_csv = "slot,course\n"
for slot in range(1, total_slots + 1):
    names = sorted(c for c in slot_of if slot_of[c] == slot)
    st.write(f"**Slot {slot}:** " + ", ".join(names))
    for n in names:
        timetable_csv += f"{slot},{n}\n"
st.download_button("Download timetable CSV", timetable_csv, "timetable.csv")

st.subheader("Clash graph")
st.table({
    "Course": sorted(graph),
    "Clashes": [len(graph[c]) for c in sorted(graph)],
    "Clashes with": [", ".join(sorted(graph[c])) for c in sorted(graph)],
})

ok = all(slot_of[a] != slot_of[b] for a in graph for b in graph[a])
st.write("Check: no two clashing courses share a slot." if ok else "Error in colouring!")
