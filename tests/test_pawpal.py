from pawpal_system import Task, Pet

#test completion
def test_mark_completed_changes_status():
    task = Task(task_id="t1", pet_id="p1", title="Feed", category="nutrition",
                duration_minutes=10, priority="medium")
    assert task.completed is False
    task.mark_completed()
    assert task.completed is True

#test addition
def test_add_task_increases_pet_task_count():
    pet = Pet(pet_id="p1", name="Buddy", species="dog", age=3, health_notes="")
    task = Task(task_id="t1", pet_id="p1", title="Walk", category="exercise",
                duration_minutes=30, priority="high")
    assert len(pet.task_list) == 0
    pet.add_task(task)
    assert len(pet.task_list) == 1
