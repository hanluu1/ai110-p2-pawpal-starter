from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Task:
	task_id: str
	pet_id: str
	title: str
	category: str
	duration_minutes: int
	priority: str
	due_window: Optional[str] = None
	recurrence: str = "daily"
	is_required: bool = False
	start_date: Optional[date] = None
	completed: bool = False
	last_completed_date: Optional[date] = None

	def is_due_on(self, target_date: date) -> bool:
		"""Check if the task is due on the given date based on recurrence pattern."""
		recurrence_value = self.recurrence.strip().lower()

		if recurrence_value == "daily":
			return True

		if recurrence_value == "weekly":
			anchor_date = self.start_date or target_date
			return target_date.weekday() == anchor_date.weekday()

		if recurrence_value in {"once", "one-time", "onetime"}:
			if self.start_date is None:
				return True
			return target_date == self.start_date

		return True

	def estimate_urgency(self, current_time: datetime) -> int:
		"""Calculate urgency score based on priority, required status, and due window."""
		priority_score = {
			"low": 1,
			"medium": 2,
			"high": 3,
		}.get(self.priority.strip().lower(), 1)

		score = priority_score * 10
		if self.is_required:
			score += 20

		window = self._parse_due_window()
		if window is None:
			return score

		start_minutes, end_minutes = window
		now_minutes = current_time.hour * 60 + current_time.minute

		if now_minutes > end_minutes:
			score += 25
		elif start_minutes <= now_minutes <= end_minutes:
			score += 15
		else:
			distance = abs(start_minutes - now_minutes)
			score += max(0, 10 - distance // 30)

		return score

	def mark_completed(self, target_date: Optional[date] = None) -> None:
		"""Mark the task as completed. Records the completion date for recurring tasks."""
		self.completed = True
		self.last_completed_date = target_date or date.today()

	def next_occurrence(self, completed_date: Optional[date] = None) -> Optional[Task]:
		"""Return a new Task for the next occurrence after completion, or None for one-time tasks.

		Computes the next due date based on recurrence:
		- ``daily``  → completed_date + 1 day
		- ``weekly`` → completed_date + 7 days
		- ``once`` / ``one-time`` / ``onetime`` → returns None (no future occurrence)
		- Any other recurrence value → returns None (treated as non-recurring)

		The returned Task is a fresh copy with all fields preserved (title, category,
		duration, priority, due_window, is_required) and completion state reset
		(``completed=False``, ``last_completed_date=None``).  The new task_id is
		derived from the original by appending the next date in ISO format
		(e.g. ``"walk-2026-04-01"``), making chained IDs traceable.

		Args:
			completed_date: The date the task was completed. Defaults to today if omitted.

		Returns:
			A new Task whose start_date is the next occurrence date, or None if the
			task does not recur.
		"""
		recurrence_value = self.recurrence.strip().lower()
		if recurrence_value in {"once", "one-time", "onetime"}:
			return None

		base = completed_date or date.today()
		if recurrence_value == "daily":
			next_date = base + timedelta(days=1)
		elif recurrence_value == "weekly":
			next_date = base + timedelta(weeks=1)
		else:
			return None

		return Task(
			task_id=f"{self.task_id}-{next_date.isoformat()}",
			pet_id=self.pet_id,
			title=self.title,
			category=self.category,
			duration_minutes=self.duration_minutes,
			priority=self.priority,
			due_window=self.due_window,
			recurrence=self.recurrence,
			is_required=self.is_required,
			start_date=next_date,
		)

	def is_completed_on(self, target_date: date) -> bool:
		"""Return True if the task is completed for the given date.

		For recurring tasks (daily/weekly), checks whether last_completed_date matches
		the target date so the task reappears on future occurrences.
		For one-time tasks, completion is permanent.
		"""
		recurrence_value = self.recurrence.strip().lower()
		if recurrence_value in {"once", "one-time", "onetime"}:
			return self.completed
		return self.last_completed_date == target_date

	def update_priority(self, new_priority: str) -> None:
		"""Update task priority; must be 'low', 'medium', or 'high'."""
		normalized_priority = new_priority.strip().lower()
		if normalized_priority not in {"low", "medium", "high"}:
			raise ValueError("Priority must be one of: low, medium, high.")
		self.priority = normalized_priority

	def _parse_due_window(self) -> Optional[Tuple[int, int]]:
		"""Parse due_window string (HH:MM-HH:MM) to start and end minutes tuple."""
		if not self.due_window:
			return None

		parts = self.due_window.split("-")
		if len(parts) != 2:
			return None

		try:
			start_hour, start_minute = [int(p) for p in parts[0].split(":")]
			end_hour, end_minute = [int(p) for p in parts[1].split(":")]
		except ValueError:
			return None

		start_minutes = start_hour * 60 + start_minute
		end_minutes = end_hour * 60 + end_minute
		if end_minutes < start_minutes:
			return None

		return start_minutes, end_minutes


@dataclass
class Pet:
	pet_id: str
	name: str
	species: str
	age: int
	health_notes: str
	owner_id: Optional[str] = None
	task_list: List[Task] = field(default_factory=list)

	def add_task(self, task: Task) -> None:
		"""Add a task to the pet's task list if not already present."""
		if task.pet_id and task.pet_id != self.pet_id:
			raise ValueError("Task pet_id does not match this pet.")

		for existing_task in self.task_list:
			if existing_task.task_id == task.task_id:
				return

		task.pet_id = self.pet_id
		self.task_list.append(task)

	def remove_task(self, task_id: str) -> None:
		"""Remove a task by ID from the pet's task list."""
		for index, task in enumerate(self.task_list):
			if task.task_id == task_id:
				del self.task_list[index]
				return

	def get_tasks_for_day(self, target_date: date) -> List[Task]:
		"""Get all uncompleted tasks due on a specific date."""
		return [
			task for task in self.task_list
			if task.is_due_on(target_date) and not task.is_completed_on(target_date)
		]

	def get_required_tasks(self) -> List[Task]:
		"""Get all uncompleted required tasks."""
		return [task for task in self.task_list if task.is_required and not task.completed]

	def complete_task(self, task_id: str, target_date: Optional[date] = None) -> Optional[Task]:
		"""Mark a task complete and automatically schedule its next occurrence.

		Finds the task by ID, calls ``mark_completed``, then calls
		``next_occurrence`` on it.  If a next occurrence is produced (i.e. the task
		is daily or weekly), it is appended to this pet's ``task_list`` so it will
		appear in future calls to ``get_tasks_for_day``.

		One-time tasks (``once`` / ``one-time`` / ``onetime``) are marked complete
		but no new task is created.

		If no task with the given ID exists on this pet, the method returns None
		without raising.

		Args:
			task_id: ID of the task to complete.
			target_date: The completion date recorded on the task. Defaults to today.

		Returns:
			The newly created next-occurrence Task, or None if the task is one-time
			or was not found.
		"""
		for task in self.task_list:
			if task.task_id == task_id:
				task.mark_completed(target_date)
				next_task = task.next_occurrence(target_date or date.today())
				if next_task is not None:
					self.add_task(next_task)
				return next_task
		return None


@dataclass
class Owner:
	owner_id: str
	name: str
	available_minutes_per_day: int
	preferred_time_blocks: List[str] = field(default_factory=list)
	max_tasks_per_day: int = 0
	pets: List[Pet] = field(default_factory=list)

	def update_preferences(self, preferred_time_blocks: List[str], max_tasks_per_day: int) -> None:
		"""Update owner's preferred time blocks and maximum tasks per day."""
		self.preferred_time_blocks = [block.strip() for block in preferred_time_blocks if block.strip()]
		if max_tasks_per_day < 0:
			raise ValueError("max_tasks_per_day cannot be negative.")
		self.max_tasks_per_day = max_tasks_per_day

	def set_daily_availability(self, minutes: int) -> None:
		"""Set the owner's daily available minutes."""
		if minutes < 0:
			raise ValueError("available minutes cannot be negative.")
		self.available_minutes_per_day = minutes

	def add_pet(self, pet: Pet) -> None:
		"""Add a pet to the owner's pet list if not already present."""
		if pet.owner_id is not None and pet.owner_id != self.owner_id:
			raise ValueError("Pet is already assigned to a different owner.")

		for existing_pet in self.pets:
			if existing_pet.pet_id == pet.pet_id:
				return

		pet.owner_id = self.owner_id
		self.pets.append(pet)

	def remove_pet(self, pet_id: str) -> None:
		"""Remove a pet by ID from the owner's pet list."""
		for index, pet in enumerate(self.pets):
			if pet.pet_id == pet_id:
				pet.owner_id = None
				del self.pets[index]
				return

	def get_tasks_by_pet(self, pet_id: str, target_date: Optional[date] = None) -> List[Task]:
		"""Get uncompleted tasks for a specific pet, optionally filtered by date."""
		for pet in self.pets:
			if pet.pet_id == pet_id:
				if target_date is None:
					return [task for task in pet.task_list if not task.completed]
				return pet.get_tasks_for_day(target_date)
		return []

	def get_tasks_by_status(self, completed: bool, target_date: Optional[date] = None) -> List[Task]:
		"""Get tasks filtered by completion status across all pets.

		When target_date is given, completion is evaluated per-day (respecting recurrence).
		"""
		result: List[Task] = []
		for pet in self.pets:
			for task in pet.task_list:
				if target_date is not None:
					is_done = task.is_completed_on(target_date)
					if completed == is_done and (not completed or task.is_due_on(target_date)):
						result.append(task)
				else:
					if task.completed == completed:
						result.append(task)
		return result

	def filter_tasks(
		self,
		completed: Optional[bool] = None,
		pet_name: Optional[str] = None,
		target_date: Optional[date] = None,
	) -> List[Task]:
		"""Filter tasks across all pets by completion status and/or pet name.

		Args:
			completed: If provided, include only tasks matching this completion state.
			           When target_date is given, per-day completion is used for recurring tasks.
			pet_name: If provided, include only tasks belonging to pets with this name (case-insensitive).
			target_date: When given, completion is evaluated per-day (respecting recurrence).
		"""
		result: List[Task] = []
		for pet in self.pets:
			if pet_name is not None and pet.name.strip().lower() != pet_name.strip().lower():
				continue
			for task in pet.task_list:
				if completed is not None:
					is_done = task.is_completed_on(target_date) if target_date is not None else task.completed
					if is_done != completed:
						continue
				result.append(task)
		return result

	def get_all_tasks(self, target_date: Optional[date] = None) -> List[Task]:
		"""Get all uncompleted tasks for the owner's pets, optionally filtered by date."""
		all_tasks: List[Task] = []
		for pet in self.pets:
			if target_date is None:
				all_tasks.extend([task for task in pet.task_list if not task.completed])
			else:
				all_tasks.extend(pet.get_tasks_for_day(target_date))
		return all_tasks


@dataclass
class Scheduler:
	max_daily_minutes: int = 0
	last_plan: Dict[str, Any] = field(default_factory=dict, repr=False)

	def generate_plan(self, owner: Owner, target_date: date):
		"""Generate a daily task plan for an owner on the target date."""
		available_minutes = owner.available_minutes_per_day
		if self.max_daily_minutes > 0:
			available_minutes = min(available_minutes, self.max_daily_minutes)

		due_tasks = owner.get_all_tasks(target_date)
		ranked_tasks = self.rank_tasks(due_tasks)

		if owner.max_tasks_per_day > 0:
			ranked_tasks = ranked_tasks[: owner.max_tasks_per_day]

		selected_tasks = self.fit_tasks_into_time(ranked_tasks, available_minutes)
		selected_ids = {task.task_id for task in selected_tasks}
		unscheduled_tasks = [task for task in ranked_tasks if task.task_id not in selected_ids]

		total_minutes = sum(task.duration_minutes for task in selected_tasks)
		conflicts = self.detect_conflicts(selected_tasks)
		explanation = self._build_explanation(selected_tasks, unscheduled_tasks, available_minutes, total_minutes, conflicts)

		self.last_plan = {
			"date": target_date.isoformat(),
			"selected_tasks": selected_tasks,
			"unscheduled_tasks": unscheduled_tasks,
			"available_minutes": available_minutes,
			"used_minutes": total_minutes,
			"conflicts": conflicts,
			"explanation": explanation,
		}

		return self.last_plan

	def sort_tasks_by_time(self, tasks: List[Task]) -> List[Task]:
		"""Sort tasks by due_window start time (earliest first). Tasks without a window sort last."""
		def _window_start(task: Task) -> int:
			window = task._parse_due_window()
			return window[0] if window is not None else 24 * 60

		return sorted(tasks, key=_window_start)

	def detect_conflicts(self, tasks: List[Task]) -> List[Tuple[Task, Task]]:
		"""Return pairs of tasks whose due_window ranges overlap."""
		windowed = [(task, task._parse_due_window()) for task in tasks]
		windowed = [(task, window) for task, window in windowed if window is not None]

		conflicts: List[Tuple[Task, Task]] = []
		for i in range(len(windowed)):
			for j in range(i + 1, len(windowed)):
				task_a, (a_start, a_end) = windowed[i]
				task_b, (b_start, b_end) = windowed[j]
				if a_start < b_end and b_start < a_end:
					conflicts.append((task_a, task_b))
		return conflicts

	def warn_conflicts(self, tasks: List[Task]) -> List[str]:
		"""Return warning messages for any tasks whose due_window ranges overlap.

		Works across tasks from any pet. Returns an empty list when there are no
		conflicts, so callers can safely check ``if warnings`` without try/except.
		"""
		warnings: List[str] = []
		for task_a, task_b in self.detect_conflicts(tasks):
			msg = (
				f"WARNING: '{task_a.title}' ({task_a.due_window}) overlaps with "
				f"'{task_b.title}' ({task_b.due_window})"
			)
			warnings.append(msg)
		return warnings

	def rank_tasks(self, tasks: List[Task]) -> List[Task]:
		"""Sort tasks by required status, urgency, duration, and title."""
		now = datetime.now()
		return sorted(
			tasks,
			key=lambda task: (
				not task.is_required,
				-task.estimate_urgency(now),
				task.duration_minutes,
				task.title.lower(),
			),
		)

	def fit_tasks_into_time(self, tasks: List[Task], available_minutes: int) -> List[Task]:
		"""Select tasks that fit within the available minutes."""
		selected: List[Task] = []
		used_minutes = 0

		for task in tasks:
			if used_minutes + task.duration_minutes <= available_minutes:
				selected.append(task)
				used_minutes += task.duration_minutes

		return selected

	def explain_selection(self) -> str:
		"""Return explanation of the last generated plan."""
		if not self.last_plan:
			return "No plan has been generated yet."

		return self.last_plan["explanation"]

	def _build_explanation(
		self,
		selected_tasks: List[Task],
		unscheduled_tasks: List[Task],
		available_minutes: int,
		used_minutes: int,
		conflicts: Optional[List[Tuple[Task, Task]]] = None,
	) -> str:
		"""Build an explanation string for the task selection."""
		selected_titles = ", ".join(task.title for task in selected_tasks) or "none"
		unscheduled_titles = ", ".join(task.title for task in unscheduled_tasks) or "none"

		explanation = (
			f"Selected tasks by required/priority/urgency within {available_minutes} minutes. "
			f"Used {used_minutes} minutes. "
			f"Scheduled: {selected_titles}. "
			f"Deferred: {unscheduled_titles}."
		)

		if conflicts:
			conflict_strs = [f"'{a.title}' and '{b.title}'" for a, b in conflicts]
			explanation += f" Conflicts: {'; '.join(conflict_strs)}."

		return explanation
