import pytest
from app import create_app, db
from app.models.task import Task


@pytest.fixture
def app():
    app = create_app("config.TestConfig")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_list_tasks_empty(client):
    """GET /tasks returns an empty list."""
    resp = client.get("/tasks")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_create_task(client):
    """POST /tasks creates a task and returns it."""
    resp = client.post("/tasks", json={"title": "Buy milk"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["title"] == "Buy milk"
    assert data["done"] is False
    assert data["project_id"] is None
    assert "id" in data


def test_create_task_missing_title(client):
    """POST /tasks without title returns 400."""
    resp = client.post("/tasks", json={})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_get_task(client, app):
    """GET /tasks/<id> returns the task."""
    with app.app_context():
        task = Task(title="Test task")
        db.session.add(task)
        db.session.commit()
        task_id = task.id

    resp = client.get(f"/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Test task"


def test_get_task_not_found(client):
    """GET /tasks/<id> with unknown id returns 404."""
    resp = client.get("/tasks/9999")
    assert resp.status_code == 404


def test_update_task(client, app):
    """PUT /tasks/<id> updates the task."""
    with app.app_context():
        task = Task(title="Original")
        db.session.add(task)
        db.session.commit()
        task_id = task.id

    resp = client.put(f"/tasks/{task_id}", json={"title": "Updated", "done": True})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "Updated"
    assert data["done"] is True


def test_update_task_not_found(client):
    """PUT /tasks/<id> with unknown id returns 404."""
    resp = client.put("/tasks/9999", json={"title": "Nope"})
    assert resp.status_code == 404


def test_delete_task(client, app):
    """DELETE /tasks/<id> deletes the task."""
    with app.app_context():
        task = Task(title="To delete")
        db.session.add(task)
        db.session.commit()
        task_id = task.id

    resp = client.delete(f"/tasks/{task_id}")
    assert resp.status_code == 200
    assert "message" in resp.get_json()


def test_delete_task_not_found(client):
    """DELETE /tasks/<id> with unknown id returns 404."""
    resp = client.delete("/tasks/9999")
    assert resp.status_code == 404


def test_task_repr(app):
    """Task model has a __repr__ method."""
    task = Task(id=1, title="Hello", done=True)
    assert repr(task) == "<Task id=1 title='Hello' done=True project_id=None>"


def test_task_to_dict(app):
    """Task model to_dict serializes correctly."""
    task = Task(id=1, title="Hello", description="World", done=False)
    assert task.to_dict() == {
        "id": 1,
        "title": "Hello",
        "description": "World",
        "done": False,
        "project_id": None,
    }
