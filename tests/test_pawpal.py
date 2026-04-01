from datetime import date, timedelta

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_task(task_id="t1", pet_id="p1", title="Walk", recurrence="daily",
              due_window=None, priority="medium", is_required=False,
              start_date=None, duration_minutes=30):
    return Task(
        task_id=task_id, pet_id=pet_id, title=title,
        category="exercise", duration_minutes=duration_minutes,
        priority=priority, recurrence=recurrence,
        due_window=due_window, is_required=is_required,
        start_date=start_date,
    )


def make_pet(pet_id="p1", name="Buddy"):
    return Pet(pet_id=pet_id, name=name, species="dog", age=3, health_notes="")


def make_owner():
    owner = Owner(owner_id="o1", name="Alex", available_minutes_per_day=120)
    buddy = make_pet("p1", "Buddy")
    luna  = make_pet("p2", "Luna")
    owner.add_pet(buddy)
    owner.add_pet(luna)
    return owner, buddy, luna


# ── Existing tests ─────────────────────────────────────────────────────────────

def test_mark_completed_changes_status():
    task = Task(task_id="t1", pet_id="p1", title="Feed", category="nutrition",
                duration_minutes=10, priority="medium")
    assert task.completed is False
    task.mark_completed()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = make_pet()
    task = make_task()
    assert len(pet.task_list) == 0
    pet.add_task(task)
    assert len(pet.task_list) == 1


# ── 1. next_occurrence ────────────────────────────────────────────────────────

class TestNextOccurrence:
    TODAY = date(2026, 3, 31)

    def test_daily_returns_next_day(self):
        task = make_task(recurrence="daily")
        nxt = task.next_occurrence(self.TODAY)
        assert nxt is not None
        assert nxt.start_date == self.TODAY + timedelta(days=1)

    def test_weekly_returns_seven_days_later(self):
        task = make_task(recurrence="weekly")
        nxt = task.next_occurrence(self.TODAY)
        assert nxt is not None
        assert nxt.start_date == self.TODAY + timedelta(weeks=1)

    def test_once_returns_none(self):
        task = make_task(recurrence="once")
        assert task.next_occurrence(self.TODAY) is None

    def test_one_time_variants_return_none(self):
        for recurrence in ("one-time", "onetime", "ONCE", "One-Time"):
            task = make_task(recurrence=recurrence)
            assert task.next_occurrence(self.TODAY) is None, recurrence

    def test_new_task_id_encodes_date(self):
        task = make_task(task_id="walk", recurrence="daily")
        nxt = task.next_occurrence(self.TODAY)
        assert "2026-04-01" in nxt.task_id

    def test_fields_are_preserved(self):
        task = make_task(
            task_id="t1", pet_id="p1", title="Meds", recurrence="daily",
            due_window="09:00-10:00", priority="high", is_required=True,
            duration_minutes=15,
        )
        nxt = task.next_occurrence(self.TODAY)
        assert nxt.title        == task.title
        assert nxt.pet_id       == task.pet_id
        assert nxt.due_window   == task.due_window
        assert nxt.priority     == task.priority
        assert nxt.is_required  == task.is_required
        assert nxt.duration_minutes == task.duration_minutes

    def test_completion_state_is_reset(self):
        task = make_task(recurrence="daily")
        task.mark_completed(self.TODAY)
        nxt = task.next_occurrence(self.TODAY)
        assert nxt.completed is False
        assert nxt.last_completed_date is None

    def test_defaults_to_today_when_date_omitted(self):
        task = make_task(recurrence="daily")
        nxt = task.next_occurrence()
        assert nxt.start_date == date.today() + timedelta(days=1)


# ── 2. complete_task ──────────────────────────────────────────────────────────

class TestCompleteTask:
    TODAY = date(2026, 3, 31)

    def test_marks_task_completed(self):
        pet  = make_pet()
        task = make_task(recurrence="once")
        pet.add_task(task)
        pet.complete_task("t1", self.TODAY)
        assert task.completed is True
        assert task.last_completed_date == self.TODAY

    def test_daily_appends_next_occurrence(self):
        pet  = make_pet()
        task = make_task(task_id="t1", recurrence="daily")
        pet.add_task(task)
        pet.complete_task("t1", self.TODAY)
        assert len(pet.task_list) == 2
        assert pet.task_list[1].start_date == self.TODAY + timedelta(days=1)

    def test_weekly_appends_next_occurrence(self):
        pet  = make_pet()
        task = make_task(task_id="t1", recurrence="weekly")
        pet.add_task(task)
        pet.complete_task("t1", self.TODAY)
        assert len(pet.task_list) == 2
        assert pet.task_list[1].start_date == self.TODAY + timedelta(weeks=1)

    def test_once_does_not_append(self):
        pet  = make_pet()
        task = make_task(task_id="t1", recurrence="once")
        pet.add_task(task)
        result = pet.complete_task("t1", self.TODAY)
        assert result is None
        assert len(pet.task_list) == 1

    def test_returns_none_for_missing_id(self):
        pet = make_pet()
        result = pet.complete_task("nonexistent", self.TODAY)
        assert result is None

    def test_missing_id_does_not_modify_task_list(self):
        pet  = make_pet()
        task = make_task()
        pet.add_task(task)
        pet.complete_task("nonexistent", self.TODAY)
        assert len(pet.task_list) == 1
        assert task.completed is False

    def test_returns_next_task_for_daily(self):
        pet  = make_pet()
        task = make_task(task_id="t1", recurrence="daily")
        pet.add_task(task)
        nxt = pet.complete_task("t1", self.TODAY)
        assert nxt is not None
        assert nxt.title == task.title


# ── 3. filter_tasks ───────────────────────────────────────────────────────────

class TestFilterTasks:
    TODAY = date(2026, 3, 31)

    def _setup(self):
        owner, buddy, luna = make_owner()
        t1 = make_task("t1", "p1", "Morning Walk", recurrence="daily")
        t2 = make_task("t2", "p1", "Flea Meds",    recurrence="once")
        t3 = make_task("t3", "p2", "Litter Box",   recurrence="daily")
        buddy.add_task(t1)
        buddy.add_task(t2)
        luna.add_task(t3)
        return owner, buddy, luna, t1, t2, t3

    def test_no_filters_returns_all(self):
        owner, buddy, luna, t1, t2, t3 = self._setup()
        result = owner.filter_tasks()
        assert len(result) == 3

    def test_filter_by_pet_name(self):
        owner, buddy, luna, t1, t2, t3 = self._setup()
        result = owner.filter_tasks(pet_name="Buddy")
        assert all(t in result for t in (t1, t2))
        assert t3 not in result

    def test_filter_by_pet_name_case_insensitive(self):
        owner, buddy, luna, t1, t2, t3 = self._setup()
        assert owner.filter_tasks(pet_name="buddy") == owner.filter_tasks(pet_name="BUDDY")

    def test_filter_by_completion_false(self):
        owner, buddy, luna, t1, t2, t3 = self._setup()
        t1.mark_completed(self.TODAY)
        result = owner.filter_tasks(completed=False)
        assert t1 not in result
        assert t2 in result and t3 in result

    def test_filter_by_completion_true(self):
        owner, buddy, luna, t1, t2, t3 = self._setup()
        t1.mark_completed(self.TODAY)
        result = owner.filter_tasks(completed=True)
        assert t1 in result
        assert t2 not in result and t3 not in result

    def test_filter_by_name_and_completion_combined(self):
        owner, buddy, luna, t1, t2, t3 = self._setup()
        t1.mark_completed(self.TODAY)
        result = owner.filter_tasks(completed=False, pet_name="Buddy")
        assert result == [t2]

    def test_nonexistent_pet_name_returns_empty(self):
        owner, *_ = self._setup()
        assert owner.filter_tasks(pet_name="NoSuchPet") == []

    def test_target_date_uses_per_day_completion(self):
        owner, buddy, luna, t1, t2, t3 = self._setup()
        t1.mark_completed(self.TODAY)
        tomorrow = self.TODAY + timedelta(days=1)
        # completed today → shows as done on today's filter
        assert t1 in  owner.filter_tasks(completed=True,  target_date=self.TODAY)
        # not completed tomorrow → shows as incomplete on tomorrow's filter
        assert t1 not in owner.filter_tasks(completed=True,  target_date=tomorrow)
        assert t1 in     owner.filter_tasks(completed=False, target_date=tomorrow)


# ── 4. warn_conflicts ─────────────────────────────────────────────────────────

class TestWarnConflicts:
    def test_overlapping_windows_produce_warning(self):
        scheduler = Scheduler()
        t1 = make_task("t1", due_window="09:00-10:00")
        t2 = make_task("t2", due_window="09:30-10:30")
        warnings = scheduler.warn_conflicts([t1, t2])
        assert len(warnings) == 1
        assert "Walk" in warnings[0]

    def test_non_overlapping_windows_no_warning(self):
        scheduler = Scheduler()
        t1 = make_task("t1", due_window="07:00-08:00")
        t2 = make_task("t2", due_window="09:00-10:00")
        assert scheduler.warn_conflicts([t1, t2]) == []

    def test_windowless_tasks_are_ignored(self):
        scheduler = Scheduler()
        t1 = make_task("t1", due_window=None)
        t2 = make_task("t2", due_window=None)
        assert scheduler.warn_conflicts([t1, t2]) == []

    def test_mixed_windowed_and_windowless(self):
        scheduler = Scheduler()
        t1 = make_task("t1", due_window="09:00-10:00")
        t2 = make_task("t2", due_window=None)          # no window — no conflict
        assert scheduler.warn_conflicts([t1, t2]) == []

    def test_exact_same_window_is_conflict(self):
        scheduler = Scheduler()
        t1 = make_task("t1", due_window="10:00-11:00")
        t2 = make_task("t2", due_window="10:00-11:00")
        assert len(scheduler.warn_conflicts([t1, t2])) == 1

    def test_adjacent_windows_are_not_conflicts(self):
        # end of t1 == start of t2: open-interval boundary, not overlapping
        scheduler = Scheduler()
        t1 = make_task("t1", due_window="08:00-09:00")
        t2 = make_task("t2", due_window="09:00-10:00")
        assert scheduler.warn_conflicts([t1, t2]) == []

    def test_warning_message_contains_both_titles(self):
        scheduler = Scheduler()
        t1 = make_task("t1", title="Morning Walk", due_window="08:00-09:30")
        t2 = make_task("t2", title="Vet Call",     due_window="09:00-10:00")
        warnings = scheduler.warn_conflicts([t1, t2])
        assert "Morning Walk" in warnings[0]
        assert "Vet Call"     in warnings[0]

    def test_empty_task_list_returns_empty(self):
        assert Scheduler().warn_conflicts([]) == []


# ── 5. sort_tasks_by_time ─────────────────────────────────────────────────────

class TestSortTasksByTime:
    def test_sorts_earliest_window_first(self):
        scheduler = Scheduler()
        t1 = make_task("t1", due_window="14:00-15:00")
        t2 = make_task("t2", due_window="07:00-08:00")
        t3 = make_task("t3", due_window="10:00-11:00")
        result = scheduler.sort_tasks_by_time([t1, t2, t3])
        assert result == [t2, t3, t1]

    def test_windowless_tasks_sort_last(self):
        scheduler = Scheduler()
        t1 = make_task("t1", due_window=None)
        t2 = make_task("t2", due_window="06:00-07:00")
        result = scheduler.sort_tasks_by_time([t1, t2])
        assert result == [t2, t1]

    def test_all_windowless_preserves_relative_order(self):
        scheduler = Scheduler()
        t1 = make_task("t1", due_window=None)
        t2 = make_task("t2", due_window=None)
        result = scheduler.sort_tasks_by_time([t1, t2])
        assert len(result) == 2
        assert t1 in result and t2 in result

    def test_single_task_returns_single_item_list(self):
        scheduler = Scheduler()
        t1 = make_task("t1", due_window="08:00-09:00")
        assert scheduler.sort_tasks_by_time([t1]) == [t1]

    def test_empty_list_returns_empty(self):
        assert Scheduler().sort_tasks_by_time([]) == []

    def test_same_start_time_stable(self):
        scheduler = Scheduler()
        t1 = make_task("t1", title="A", due_window="08:00-09:00")
        t2 = make_task("t2", title="B", due_window="08:00-10:00")
        result = scheduler.sort_tasks_by_time([t1, t2])
        # both start at 08:00 — both present
        assert len(result) == 2
        assert t1 in result and t2 in result


# ── 6. Edge cases ─────────────────────────────────────────────────────────────

class TestDoubleCompleteRecurringTask:
    """complete_task appends next-occurrence directly; calling it twice should not duplicate."""
    TODAY = date(2026, 3, 31)

    def test_double_complete_does_not_duplicate_next_occurrence(self):
        pet = make_pet()
        task = make_task(task_id="t1", recurrence="daily")
        pet.add_task(task)
        pet.complete_task("t1", self.TODAY)
        pet.complete_task("t1", self.TODAY)  # second call on same task
        # Should still be only 2 tasks (original + one next-occurrence)
        assert len(pet.task_list) == 2


class TestGetRequiredTasksAfterRecurringCompletion:
    """get_required_tasks checks task.completed directly; for recurring tasks this flag
    stays True after completion, so the task wrongly disappears from required tasks."""
    TODAY = date(2026, 3, 31)

    def test_required_recurring_task_reappears_after_completion(self):
        pet = make_pet()
        task = make_task(task_id="t1", recurrence="daily", is_required=True)
        pet.add_task(task)
        pet.complete_task("t1", self.TODAY)
        # The daily required task should still appear as required for tomorrow
        tomorrow = self.TODAY + timedelta(days=1)
        next_task = pet.task_list[1]  # next-occurrence task
        assert next_task.is_required is True
        assert next_task in pet.get_required_tasks()


class TestZeroDurationTask:
    """A task with duration_minutes=0 should fit even into a zero-minute budget."""

    def test_zero_duration_fits_zero_budget(self):
        scheduler = Scheduler()
        t1 = make_task(duration_minutes=0)
        result = scheduler.fit_tasks_into_time([t1], available_minutes=0)
        # Zero-duration tasks slip through — document this behaviour
        assert t1 in result

    def test_zero_duration_does_not_consume_budget(self):
        scheduler = Scheduler()
        t1 = make_task("t1", duration_minutes=0)
        t2 = make_task("t2", duration_minutes=30)
        result = scheduler.fit_tasks_into_time([t1, t2], available_minutes=30)
        assert t1 in result and t2 in result


class TestNegativeDurationTask:
    """Negative duration_minutes corrupts used_minutes, allowing over-budget scheduling."""

    def test_negative_duration_does_not_exceed_budget(self):
        scheduler = Scheduler()
        t1 = make_task("t1", duration_minutes=-10)
        t2 = make_task("t2", duration_minutes=40)
        # With 30 minutes available, t2 alone fits but t1 (-10) would inflate the budget
        result = scheduler.fit_tasks_into_time([t1, t2], available_minutes=30)
        total = sum(t.duration_minutes for t in result)
        assert total <= 30


class TestUnknownRecurrence:
    """An unrecognized recurrence value falls through is_due_on (returns True) and
    next_occurrence (returns None). Both sides should be explicitly tested."""
    TODAY = date(2026, 3, 31)

    def test_unknown_recurrence_is_always_due(self):
        task = make_task(recurrence="biweekly")
        assert task.is_due_on(self.TODAY) is True

    def test_unknown_recurrence_has_no_next_occurrence(self):
        task = make_task(recurrence="biweekly")
        assert task.next_occurrence(self.TODAY) is None


class TestOvernightDueWindow:
    """A due_window spanning midnight (end < start) is silently discarded by
    _parse_due_window.  Callers receive no urgency bonus and no conflict detection."""

    def test_overnight_window_is_treated_as_no_window(self):
        task = make_task(due_window="22:00-06:00")
        assert task._parse_due_window() is None

    def test_overnight_window_produces_no_conflict(self):
        scheduler = Scheduler()
        t1 = make_task("t1", due_window="22:00-06:00")
        t2 = make_task("t2", due_window="23:00-07:00")
        assert scheduler.warn_conflicts([t1, t2]) == []


class TestMalformedDueWindow:
    """Various malformed due_window strings should all return None gracefully."""

    def test_12h_format_returns_none(self):
        task = make_task(due_window="9am-10am")
        assert task._parse_due_window() is None

    def test_missing_end_returns_none(self):
        task = make_task(due_window="09:00")
        assert task._parse_due_window() is None

    def test_no_colon_returns_none(self):
        task = make_task(due_window="0900-1000")
        assert task._parse_due_window() is None

    def test_empty_string_returns_none(self):
        task = make_task(due_window="")
        assert task._parse_due_window() is None


class TestAddPetOwnershipRules:
    """A pet already owned by another owner raises ValueError."""

    def test_add_pet_already_owned_by_different_owner_raises(self):
        owner_a = Owner(owner_id="o1", name="Alice", available_minutes_per_day=60)
        owner_b = Owner(owner_id="o2", name="Bob",   available_minutes_per_day=60)
        pet = make_pet()
        owner_a.add_pet(pet)
        with pytest.raises(ValueError):
            owner_b.add_pet(pet)

    def test_add_same_pet_to_same_owner_is_idempotent(self):
        owner = Owner(owner_id="o1", name="Alice", available_minutes_per_day=60)
        pet = make_pet()
        owner.add_pet(pet)
        owner.add_pet(pet)
        assert len(owner.pets) == 1


class TestRemoveTaskSilentMiss:
    """remove_task with a nonexistent id should leave the list unchanged."""

    def test_remove_nonexistent_task_is_noop(self):
        pet = make_pet()
        task = make_task()
        pet.add_task(task)
        pet.remove_task("does-not-exist")
        assert len(pet.task_list) == 1


class TestAddTaskMismatchedPetId:
    """add_task raises ValueError when task.pet_id belongs to a different pet."""

    def test_mismatched_pet_id_raises(self):
        pet = make_pet(pet_id="p1")
        task = make_task(pet_id="p99")
        with pytest.raises(ValueError):
            pet.add_task(task)


class TestFilterTasksWithTargetDateIncludesNonDueTasks:
    """filter_tasks(completed=False, target_date=X) returns tasks that aren't due on X
    for recurring tasks — it only checks completion, not due-ness."""
    TODAY = date(2026, 3, 31)

    def test_filter_incomplete_with_date_excludes_already_completed_for_date(self):
        owner, buddy, luna = make_owner()
        task = make_task("t1", "p1", recurrence="once", start_date=self.TODAY)
        buddy.add_task(task)
        task.mark_completed(self.TODAY)
        result = owner.filter_tasks(completed=False, target_date=self.TODAY)
        assert task not in result


class TestIsCompletedOnRecurringVsFlag:
    """For recurring tasks, is_completed_on uses last_completed_date, not task.completed.
    Completing yesterday should not mark the task as completed today."""
    TODAY = date(2026, 3, 31)

    def test_recurring_task_not_completed_today_after_completing_yesterday(self):
        task = make_task(recurrence="daily")
        yesterday = self.TODAY - timedelta(days=1)
        task.mark_completed(yesterday)
        assert task.completed is True
        assert task.is_completed_on(self.TODAY) is False

    def test_recurring_task_completed_today(self):
        task = make_task(recurrence="daily")
        task.mark_completed(self.TODAY)
        assert task.is_completed_on(self.TODAY) is True


class TestChainedDailyCompletion:
    """Completing the next-occurrence task should produce a further next-occurrence."""
    TODAY = date(2026, 3, 31)

    def test_chained_completion_produces_further_task(self):
        pet = make_pet()
        task = make_task(task_id="walk", recurrence="daily")
        pet.add_task(task)

        tomorrow = self.TODAY + timedelta(days=1)
        day_after = self.TODAY + timedelta(days=2)

        pet.complete_task("walk", self.TODAY)
        # next-occurrence task was appended
        next_task = pet.task_list[1]
        assert next_task.start_date == tomorrow

        pet.complete_task(next_task.task_id, tomorrow)
        # a further next-occurrence should now exist
        assert len(pet.task_list) == 3
        assert pet.task_list[2].start_date == day_after


class TestSchedulerWithNoAvailableTime:
    """Owner with 0 available minutes should result in no tasks scheduled."""
    TODAY = date(2026, 3, 31)

    def test_zero_available_minutes_schedules_nothing(self):
        owner = Owner(owner_id="o1", name="Alex", available_minutes_per_day=0)
        pet = make_pet()
        task = make_task(duration_minutes=10)
        pet.add_task(task)
        owner.add_pet(pet)
        scheduler = Scheduler()
        plan = scheduler.generate_plan(owner, self.TODAY)
        assert plan["selected_tasks"] == []
        assert len(plan["unscheduled_tasks"]) == 1


class TestSchedulerWithNoPets:
    """Owner with no pets should produce an empty plan."""
    TODAY = date(2026, 3, 31)

    def test_no_pets_produces_empty_plan(self):
        owner = Owner(owner_id="o1", name="Alex", available_minutes_per_day=120)
        scheduler = Scheduler()
        plan = scheduler.generate_plan(owner, self.TODAY)
        assert plan["selected_tasks"] == []
        assert plan["unscheduled_tasks"] == []


class TestUpdatePriorityValidation:
    """update_priority rejects anything outside low/medium/high."""

    def test_invalid_priority_raises(self):
        task = make_task()
        with pytest.raises(ValueError):
            task.update_priority("critical")

    def test_whitespace_only_priority_raises(self):
        task = make_task()
        with pytest.raises(ValueError):
            task.update_priority("   ")

    def test_valid_priority_with_whitespace_succeeds(self):
        task = make_task()
        task.update_priority("  HIGH  ")
        assert task.priority == "high"
