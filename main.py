from datetime import date

from pawpal_system import Owner, Pet, Scheduler, Task

# --- Setup ---
owner = Owner(
    owner_id="o1",
    name="Alex",
    available_minutes_per_day=90,
    preferred_time_blocks=["08:00-10:00", "17:00-19:00"],
    max_tasks_per_day=10,
)

buddy    = Pet(pet_id="p1", name="Buddy",    species="Dog", age=3, health_notes="Healthy")
whiskers = Pet(pet_id="p2", name="Whiskers", species="Cat", age=5, health_notes="Needs dental checkup")

# --- Tasks added OUT OF ORDER (late windows first, then early, then no window) ---
buddy.add_task(Task(
    task_id="t3", pet_id="p1",
    title="Evening Walk",
    category="Exercise",
    duration_minutes=30,
    priority="medium",
    due_window="17:00-18:00",   # late
    recurrence="daily",
    start_date=date.today(),
))
buddy.add_task(Task(
    task_id="t1", pet_id="p1",
    title="Morning Walk",
    category="Exercise",
    duration_minutes=30,
    priority="high",
    due_window="07:00-09:00",   # early
    recurrence="daily",
    is_required=True,
    start_date=date.today(),
))
buddy.add_task(Task(
    task_id="t2", pet_id="p1",
    title="Flea Medicine",
    category="Health",
    duration_minutes=5,
    priority="medium",
    due_window="09:00-10:00",   # mid-morning
    recurrence="once",
    is_required=True,
    start_date=date.today(),
))
buddy.add_task(Task(
    task_id="t4", pet_id="p1",
    title="Vitamins",
    category="Health",
    duration_minutes=5,
    priority="low",
    due_window=None,            # no window
    recurrence="daily",
    start_date=date.today(),
))

whiskers.add_task(Task(
    task_id="t6", pet_id="p2",
    title="Brush Teeth",
    category="Grooming",
    duration_minutes=10,
    priority="medium",
    due_window="18:00-19:00",   # late
    recurrence="weekly",
    start_date=date.today(),
))
whiskers.add_task(Task(
    task_id="t5", pet_id="p2",
    title="Litter Box",
    category="Hygiene",
    duration_minutes=10,
    priority="high",
    due_window="08:00-09:00",   # early
    recurrence="daily",
    is_required=True,
    start_date=date.today(),
))
whiskers.add_task(Task(
    task_id="t7", pet_id="p2",
    title="Evening Playtime",
    category="Exercise",
    duration_minutes=20,
    priority="low",
    due_window="17:00-18:00",   # late
    recurrence="daily",
    start_date=date.today(),
))

owner.add_pet(buddy)
owner.add_pet(whiskers)

today     = date.today()
scheduler = Scheduler(max_daily_minutes=90)

# ── Sort by due_window ────────────────────────────────────────────────────────
print("=" * 55)
print("SORT: all due tasks sorted by due_window (earliest first)")
print("=" * 55)
due_tasks    = owner.get_all_tasks(today)
sorted_tasks = scheduler.sort_tasks_by_time(due_tasks)
for t in sorted_tasks:
    window = t.due_window or "no window"
    req    = " *" if t.is_required else ""
    pet    = next(p.name for p in owner.pets if p.pet_id == t.pet_id)
    print(f"  {window:17}  [{t.priority:6}]  {pet:8}  {t.title}{req}")
print("  * = required")

# ── filter_tasks: by pet name ─────────────────────────────────────────────────
print()
print("=" * 55)
print("FILTER: incomplete tasks for Buddy")
print("=" * 55)
for t in owner.filter_tasks(completed=False, pet_name="Buddy"):
    print(f"  [{t.priority:6}]  {t.title} ({t.duration_minutes} min)")

print()
print("=" * 55)
print("FILTER: incomplete tasks for Whiskers")
print("=" * 55)
for t in owner.filter_tasks(completed=False, pet_name="Whiskers"):
    print(f"  [{t.priority:6}]  {t.title} ({t.duration_minutes} min)")

# Mark tasks complete via complete_task — next occurrence is auto-created
print()
print("=" * 55)
print("COMPLETE: Morning Walk (daily) → next occurrence auto-created")
print("=" * 55)
next_walk = buddy.complete_task("t1", today)
if next_walk:
    print(f"  Next occurrence: '{next_walk.title}'  start_date={next_walk.start_date}  id={next_walk.task_id}")

print()
print("COMPLETE: Flea Medicine (one-time) → no next occurrence")
print("=" * 55)
next_flea = buddy.complete_task("t2", today)
print(f"  Next occurrence: {next_flea!r}")

print()
print("=" * 55)
print("FILTER: completed tasks today (all pets)")
print("=" * 55)
completed = owner.filter_tasks(completed=True, target_date=today)
if completed:
    for t in completed:
        pet = next(p.name for p in owner.pets if p.pet_id == t.pet_id)
        print(f"  [done]  {pet:8}  {t.title}")
else:
    print("  (none)")

# ── Conflict detection ───────────────────────────────────────────────────────
# Add two tasks whose windows deliberately overlap to verify warn_conflicts.
buddy.add_task(Task(
    task_id="t8", pet_id="p1",
    title="Vet Call",
    category="Health",
    duration_minutes=15,
    priority="high",
    due_window="17:30-18:30",   # overlaps Evening Walk (17:00-18:00)
    recurrence="once",
    start_date=today,
))
whiskers.add_task(Task(
    task_id="t9", pet_id="p2",
    title="Grooming Appointment",
    category="Grooming",
    duration_minutes=20,
    priority="medium",
    due_window="17:00-18:00",   # overlaps Evening Playtime (17:00-18:00)
    recurrence="once",
    start_date=today,
))

print()
print("=" * 55)
print("CONFLICTS: warn_conflicts across all due tasks")
print("=" * 55)
all_due    = owner.get_all_tasks(today)
warnings   = scheduler.warn_conflicts(all_due)
if warnings:
    for w in warnings:
        print(f"  {w}")
else:
    print("  No conflicts detected.")

# ── Generated schedule ────────────────────────────────────────────────────────
print()
print("=" * 55)
print(f"SCHEDULE: {today.strftime('%A, %B %d %Y')}")
print("=" * 55)
plan = scheduler.generate_plan(owner, today)
if plan["selected_tasks"]:
    for t in plan["selected_tasks"]:
        pet    = next(p.name for p in owner.pets if p.pet_id == t.pet_id)
        window = f"  [{t.due_window}]" if t.due_window else ""
        req    = " *" if t.is_required else ""
        print(f"  [{pet:8}]  {t.title}{req} — {t.duration_minutes} min{window}")
else:
    print("  No tasks scheduled.")
print(f"  Time: {plan['used_minutes']} / {plan['available_minutes']} min used")
if plan["unscheduled_tasks"]:
    print(f"  Deferred: {', '.join(t.title for t in plan['unscheduled_tasks'])}")
print("  * = required")
