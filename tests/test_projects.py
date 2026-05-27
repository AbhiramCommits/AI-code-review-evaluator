from datetime import date

import pytest
from app import create_app, db
from app.models.project import Project
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


def test_list_projects_empty(client):
    """GET /projects returns an empty list."""
    resp = client.get("/projects")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_create_project(client):
    """POST /projects creates a project and returns it."""
    resp = client.post("/projects", json={
        "name": "Website Redesign",
        "description": "Redesign the company homepage",
        "due_date": "2026-06-15",
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "Website Redesign"
    assert data["description"] == "Redesign the company homepage"
    assert data["due_date"] == "2026-06-15"
    assert "id" in data


def test_create_project_missing_name(client):
    """POST /projects without name returns 400."""
    resp = client.post("/projects", json={})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_create_project_invalid_date(client):
    """POST /projects with invalid date returns 400."""
    resp = client.post("/projects", json={"name": "Bad", "due_date": "not-a-date"})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_create_project_minimal(client):
    """POST /projects with only name creates a project with defaults."""
    resp = client.post("/projects", json={"name": "Minimal"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "Minimal"
    assert data["description"] is None
    assert data["due_date"] is None


def test_get_project(client, app):
    """GET /projects/<id> returns the project."""
    with app.app_context():
        project = Project(name="Test Project")
        db.session.add(project)
        db.session.commit()
        project_id = project.id

    resp = client.get(f"/projects/{project_id}")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Test Project"


def test_get_project_not_found(client):
    """GET /projects/<id> with unknown id returns 404."""
    resp = client.get("/projects/9999")
    assert resp.status_code == 404


def test_list_project_tasks_empty(client, app):
    """GET /projects/<id>/tasks returns empty list when project has no tasks."""
    with app.app_context():
        project = Project(name="Empty Project")
        db.session.add(project)
        db.session.commit()
        project_id = project.id

    resp = client.get(f"/projects/{project_id}/tasks")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_project_tasks(client, app):
    """GET /projects/<id>/tasks returns all tasks for the project."""
    with app.app_context():
        project = Project(name="With Tasks")
        db.session.add(project)
        db.session.commit()
        task1 = Task(title="Task 1", project_id=project.id)
        task2 = Task(title="Task 2", project_id=project.id)
        db.session.add_all([task1, task2])
        db.session.commit()
        project_id = project.id

    resp = client.get(f"/projects/{project_id}/tasks")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2
    assert data[0]["title"] == "Task 1"
    assert data[0]["project_id"] == project_id
    assert data[1]["title"] == "Task 2"


def test_list_project_tasks_not_found(client):
    """GET /projects/<id>/tasks with unknown id returns 404."""
    resp = client.get("/projects/9999/tasks")
    assert resp.status_code == 404


def test_create_task_with_project(client, app):
    """POST /tasks with project_id assigns task to that project."""
    with app.app_context():
        project = Project(name="Test Project")
        db.session.add(project)
        db.session.commit()
        project_id = project.id

    resp = client.post("/tasks", json={"title": "Task for project", "project_id": project_id})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["project_id"] == project_id


def test_update_task_project_id(client, app):
    """PUT /tasks/<id> can reassign a task to a different project."""
    with app.app_context():
        p1 = Project(name="Project 1")
        p2 = Project(name="Project 2")
        db.session.add_all([p1, p2])
        db.session.commit()
        task = Task(title="Movable", project_id=p1.id)
        db.session.add(task)
        db.session.commit()
        task_id = task.id
        p2_id = p2.id

    resp = client.put(f"/tasks/{task_id}", json={"project_id": p2_id})
    assert resp.status_code == 200
    assert resp.get_json()["project_id"] == p2_id


def test_project_repr(app):
    """Project model has a __repr__ method."""
    project = Project(id=1, name="Test", due_date=date(2026, 6, 15))
    assert repr(project) == "<Project id=1 name='Test' due_date=2026-06-15>"


def test_project_to_dict(app):
    """Project model to_dict serializes correctly."""
    project = Project(id=1, name="Test", description="Desc", due_date=date(2026, 6, 15))
    assert project.to_dict() == {
        "id": 1,
        "name": "Test",
        "description": "Desc",
        "due_date": "2026-06-15",
    }


def test_project_to_dict_none_due_date(app):
    """Project model to_dict handles None due_date."""
    project = Project(id=1, name="Test", description=None, due_date=None)
    assert project.to_dict() == {
        "id": 1,
        "name": "Test",
        "description": None,
        "due_date": None,
    }
