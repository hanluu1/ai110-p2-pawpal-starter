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

buddy = Pet(pet_id="p1", name="Buddy", species="Dog", age=3, health_notes="Healthy")
whiskers = Pet(pet_id="p2", name="Whiskers", species="Cat", age=5, health_notes="Needs dental checkup")

# --- Tasks for Buddy (Dog) ---
buddy.add_task(Task(
    task_id="t1", pet_id="p1",
    title="Morning Walk",
    category="Exercise",
    duration_minutes=30,
    priority="high",
    due_window="07:00-09:00",
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
    due_window="09:00-10:00",
    recurrence="once",
    is_required=True,
    start_date=date.today(),
))

# --- Tasks for Whiskers (Cat) ---
whiskers.add_task(Task(
    task_id="t3", pet_id="p2",
    title="Brush Teeth",
    category="Grooming",
    duration_minutes=10,
    priority="medium",
    due_window="18:00-19:00",
    recurrence="weekly",
    is_required=False,
    start_date=date.today(),
))
whiskers.add_task(Task(
    task_id="t4", pet_id="p2",
    title="Evening Playtime",
    category="Exercise",
    duration_minutes=20,
    priority="low",
    due_window="17:00-18:00",
    recurrence="daily",
    is_required=False,
    start_date=date.today(),
))

owner.add_pet(buddy)
owner.add_pet(whiskers)

# --- Schedule ---
scheduler = Scheduler(max_daily_minutes=90)
plan = scheduler.generate_plan(owner, date.today())

# --- Print Today's Schedule ---
print("=" * 40)
print("       PawPal+ — Today's Schedule")
print(f"       {date.today().strftime('%A, %B %d %Y')}")
print("=" * 40)

if plan["selected_tasks"]:
    for task in plan["selected_tasks"]:
        pet_name = next(p.name for p in owner.pets if p.pet_id == task.pet_id)
        window = f"  [{task.due_window}]" if task.due_window else ""
        required_tag = " *" if task.is_required else ""
        print(f"  [{pet_name}] {task.title}{required_tag} — {task.duration_minutes} min{window}")
else:
    print("  No tasks scheduled for today.")

print("-" * 40)
print(f"  Time used : {plan['used_minutes']} / {plan['available_minutes']} min")

if plan["unscheduled_tasks"]:
    deferred = ", ".join(t.title for t in plan["unscheduled_tasks"])
    print(f"  Deferred  : {deferred}")

print("=" * 40)
print("  * = required task")
