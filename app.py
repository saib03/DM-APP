import csv

# STEP 1: read the CSV. Each student -> set of courses they take.
students = {}
with open("enrolments.csv") as f:
    for row in csv.DictReader(f):
        students.setdefault(row["student"], set()).add(row["course"])

# STEP 2: build the graph as a dictionary.
# graph["Maths"] = {"DSA", "OS", ...}  means Maths is adjacent to those courses.
graph = {}
for courses in students.values():
    for c in courses:
        graph.setdefault(c, set())
    for a in courses:
        for b in courses:
            if a != b:
                graph[a].add(b)

# STEP 3: greedy colouring.
# Take courses with the most clashes first. Give each the smallest
# slot number not already used by one of its neighbours.
slot_of = {}
for course in sorted(graph, key=lambda c: len(graph[c]), reverse=True):
    used = {slot_of[n] for n in graph[course] if n in slot_of}
    slot = 1
    while slot in used:
        slot += 1
    slot_of[course] = slot

# STEP 4: print the results.
print("Clash graph (course: clashes with)")
for course in sorted(graph):
    print(f"  {course}: {', '.join(sorted(graph[course]))}")

print("\nTimetable")
for slot in range(1, max(slot_of.values()) + 1):
    names = [c for c in slot_of if slot_of[c] == slot]
    print(f"  Slot {slot}: {', '.join(sorted(names))}")

# STEP 5: check that no two clashing courses share a slot.
ok = all(slot_of[a] != slot_of[b] for a in graph for b in graph[a])
print("\nNo clashes:", ok)