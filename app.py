import streamlit as st
from datetime import date, datetime
from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")
st.title("🐾 PawPal+")

# ── Session state init ────────────────────────────────────────────────────────

def init_state():
    if "owner" not in st.session_state:
        st.session_state.owner = Owner(
            owner_id="owner-main",
            name="Alex",
            available_minutes_per_day=120,
            preferred_time_blocks=[],
            max_tasks_per_day=0,
        )
    if "scheduler" not in st.session_state:
        st.session_state.scheduler = Scheduler()
    if "last_plan" not in st.session_state:
        st.session_state.last_plan = None

init_state()
owner: Owner = st.session_state.owner
scheduler: Scheduler = st.session_state.scheduler

# ── Helpers ───────────────────────────────────────────────────────────────────

PRIORITY_LABEL = {"low": "🔵 Low", "medium": "🟡 Medium", "high": "🔴 High"}

def pet_name_for(task: Task) -> str:
    return next((p.name for p in owner.pets if p.pet_id == task.pet_id), "?")

# ── Sidebar: owner settings ───────────────────────────────────────────────────

with st.sidebar:
    st.header("Owner Settings")
    new_name = st.text_input("Owner name", value=owner.name)
    new_minutes = st.number_input(
        "Available minutes/day", min_value=0, max_value=1440, value=owner.available_minutes_per_day
    )
    new_max_tasks = st.number_input(
        "Max tasks/day (0 = no limit)", min_value=0, value=owner.max_tasks_per_day
    )
    time_blocks_raw = st.text_input(
        "Preferred time blocks (comma-separated, HH:MM-HH:MM)",
        value=", ".join(owner.preferred_time_blocks),
    )

    if st.button("Save settings"):
        owner.name = new_name
        owner.set_daily_availability(int(new_minutes))
        blocks = [b.strip() for b in time_blocks_raw.split(",") if b.strip()]
        owner.update_preferences(blocks, int(new_max_tasks))
        st.success("Settings saved.")

    st.divider()
    st.header("Add Pet")
    new_pet_name = st.text_input("Pet name")
    new_pet_species = st.selectbox("Species", ["Dog", "Cat", "Bird", "Rabbit", "Other"])
    new_pet_age = st.number_input("Age (years)", min_value=0, max_value=30, value=1)
    new_pet_notes = st.text_area("Health notes", height=60)

    if st.button("Add pet") and new_pet_name.strip():
        pet_id = f"pet-{len(owner.pets) + 1}-{new_pet_name.lower().replace(' ', '-')}"
        if any(p.name.lower() == new_pet_name.strip().lower() for p in owner.pets):
            st.warning(f"A pet named '{new_pet_name}' already exists.")
        else:
            new_pet = Pet(
                pet_id=pet_id,
                name=new_pet_name.strip(),
                species=new_pet_species,
                age=int(new_pet_age),
                health_notes=new_pet_notes.strip(),
            )
            owner.add_pet(new_pet)
            st.success(f"Added {new_pet_name}!")

# ── Main tabs ─────────────────────────────────────────────────────────────────

tab_tasks, tab_schedule = st.tabs(["Pets & Tasks", "Schedule"])

# ── Tab 1: Pets & Tasks ───────────────────────────────────────────────────────

with tab_tasks:
    if not owner.pets:
        st.info("No pets yet. Add one in the sidebar.")
    else:
        pet_names = [p.name for p in owner.pets]
        selected_pet_name = st.selectbox("Select pet", pet_names)
        pet: Pet = next(p for p in owner.pets if p.name == selected_pet_name)

        st.subheader(f"{pet.name} — {pet.species}, age {pet.age}")
        if pet.health_notes:
            st.caption(f"Health notes: {pet.health_notes}")

        # Add task form
        with st.expander("Add task", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1:
                task_title = st.text_input("Title", key="task_title")
                task_category = st.text_input("Category", value="General", key="task_cat")
                task_duration = st.number_input(
                    "Duration (min)", min_value=1, max_value=480, value=15, key="task_dur"
                )
            with c2:
                task_priority = st.selectbox("Priority", ["low", "medium", "high"], index=1, key="task_pri")
                task_recurrence = st.selectbox(
                    "Recurrence", ["daily", "weekly", "once"], key="task_rec"
                )
                task_required = st.checkbox("Required", key="task_req")
            with c3:
                task_due_window = st.text_input(
                    "Due window (HH:MM-HH:MM, optional)", key="task_win"
                )
                task_start_date = st.date_input("Start date", value=date.today(), key="task_start")

            if st.button("Add task") and task_title.strip():
                task_id = f"task-{pet.pet_id}-{len(pet.task_list) + 1}"
                due_window = task_due_window.strip() if task_due_window.strip() else None
                new_task = Task(
                    task_id=task_id,
                    pet_id=pet.pet_id,
                    title=task_title.strip(),
                    category=task_category.strip(),
                    duration_minutes=int(task_duration),
                    priority=task_priority,
                    due_window=due_window,
                    recurrence=task_recurrence,
                    is_required=task_required,
                    start_date=task_start_date,
                )
                pet.add_task(new_task)
                st.success(f"Task '{task_title}' added.")

        st.markdown("---")

        if not pet.task_list:
            st.info("No tasks yet. Use 'Add task' above.")
        else:
            today = date.today()

            # Metrics row
            total = len(pet.task_list)
            done_count = sum(1 for t in pet.task_list if t.is_completed_on(today))
            required_count = len(pet.get_required_tasks())
            m1, m2, m3 = st.columns(3)
            m1.metric("Total tasks", total)
            m2.metric("Done today", done_count)
            m3.metric("Required remaining", required_count)

            # Conflict warnings via scheduler.warn_conflicts
            conflict_warnings = scheduler.warn_conflicts(pet.task_list)
            for msg in conflict_warnings:
                st.warning(msg)

            # Task list ranked by priority/urgency via scheduler.rank_tasks
            st.markdown("#### Tasks (ranked by priority & urgency)")
            ranked = scheduler.rank_tasks(pet.task_list)

            for task in ranked:
                done_today = task.is_completed_on(today)
                with st.container(border=True):
                    col_info, col_badges, col_action = st.columns([4, 3, 1])

                    with col_info:
                        title_display = f"~~{task.title}~~" if done_today else f"**{task.title}**"
                        required_badge = " `required`" if task.is_required else ""
                        st.markdown(f"{title_display}{required_badge}")
                        st.caption(f"{task.category} · {task.recurrence} · {task.duration_minutes} min")

                    with col_badges:
                        st.markdown(PRIORITY_LABEL.get(task.priority, task.priority))
                        window_text = f"🕐 {task.due_window}" if task.due_window else "No time window"
                        st.caption(window_text)

                    with col_action:
                        if done_today:
                            st.success("Done")
                        else:
                            if st.button("Complete", key=f"complete-{task.task_id}"):
                                pet.complete_task(task.task_id, today)
                                st.rerun()

# ── Tab 2: Schedule ───────────────────────────────────────────────────────────

with tab_schedule:
    if not owner.pets:
        st.info("Add a pet first.")
    else:
        plan_date = st.date_input("Plan for date", value=date.today(), key="plan_date")

        if st.button("Generate schedule", type="primary"):
            plan = scheduler.generate_plan(owner, plan_date)
            st.session_state.last_plan = plan

        plan = st.session_state.last_plan
        if plan is None:
            st.caption("Press 'Generate schedule' to build a plan.")
        else:
            st.markdown(f"### Plan for {plan['date']}")

            # Metrics row
            used = plan["used_minutes"]
            avail = plan["available_minutes"]
            remaining = avail - used
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Available (min)", avail)
            s2.metric("Scheduled (min)", used)
            s3.metric("Remaining (min)", remaining)
            s4.metric("Tasks scheduled", len(plan["selected_tasks"]))

            # Time usage bar
            st.progress(min(used / avail, 1.0) if avail > 0 else 0.0)

            st.markdown("---")

            # Conflict warnings via scheduler.warn_conflicts (formatted strings)
            conflict_warnings = scheduler.warn_conflicts(plan["selected_tasks"])
            if conflict_warnings:
                for msg in conflict_warnings:
                    st.warning(msg)
            else:
                st.success("No time window conflicts in this plan.")

            # Scheduled tasks — sorted by due_window via scheduler.sort_tasks_by_time
            st.markdown("#### Scheduled tasks")
            if plan["selected_tasks"]:
                sorted_selected = scheduler.sort_tasks_by_time(plan["selected_tasks"])
                rows = []
                for t in sorted_selected:
                    rows.append({
                        "Pet": pet_name_for(t),
                        "Task": ("★ " if t.is_required else "") + t.title,
                        "Category": t.category,
                        "Priority": PRIORITY_LABEL.get(t.priority, t.priority),
                        "Duration (min)": t.duration_minutes,
                        "Window": t.due_window or "—",
                    })
                st.table(rows)
            else:
                st.warning("No tasks fit within the available time.")

            # Deferred tasks
            if plan["unscheduled_tasks"]:
                st.markdown("#### Deferred (did not fit)")
                deferred_rows = []
                for t in plan["unscheduled_tasks"]:
                    deferred_rows.append({
                        "Pet": pet_name_for(t),
                        "Task": t.title,
                        "Priority": PRIORITY_LABEL.get(t.priority, t.priority),
                        "Duration (min)": t.duration_minutes,
                        "Window": t.due_window or "—",
                    })
                st.table(deferred_rows)
            else:
                st.success("All due tasks fit in today's schedule!")

            # Explanation from scheduler.explain_selection
            with st.expander("How this plan was built"):
                st.write(scheduler.explain_selection())
