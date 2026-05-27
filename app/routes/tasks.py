from flask import Blueprint, jsonify, request
from flask_babel import gettext as _

from app.repositories.task_repository import TaskRepository

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/tasks", methods=["GET"])
def list_tasks():
    """List all tasks.

    Endpoint: GET /tasks
    Method: GET
    Request body: None
    Response format: JSON array of task objects.
        [
            {
                "id": int,
                "title": str,
                "description": str | null,
                "done": bool
            }
        ]
    """
    tasks = TaskRepository.get_all()
    return jsonify([t.to_dict() for t in tasks]), 200


@tasks_bp.route("/tasks", methods=["POST"])
def create_task():
    """Create a new task.

    Endpoint: POST /tasks
    Method: POST
    Request body: JSON object with:
        - title (str, required)
        - description (str, optional)
    Response format: JSON object representing the created task.
        {
            "id": int,
            "title": str,
            "description": str | null,
            "done": bool
        }
    """
    data = request.get_json(silent=True)
    if not data or "title" not in data:
        return jsonify({"error": _("Title is required.")}), 400
    task = TaskRepository.create(
        title=data["title"],
        description=data.get("description"),
    )
    return jsonify(task.to_dict()), 201


@tasks_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    """Get a single task by ID.

    Endpoint: GET /tasks/<id>
    Method: GET
    Request body: None
    URL parameters: id (int) — the task ID
    Response format: JSON object representing the task.
        {
            "id": int,
            "title": str,
            "description": str | null,
            "done": bool
        }
    """
    task = TaskRepository.get_by_id(task_id)
    if not task:
        return jsonify({"error": _("Task not found.")}), 404
    return jsonify(task.to_dict()), 200


@tasks_bp.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    """Update an existing task.

    Endpoint: PUT /tasks/<id>
    Method: PUT
    Request body: JSON object with optional fields:
        - title (str, optional)
        - description (str, optional)
        - done (bool, optional)
    Response format: JSON object representing the updated task.
        {
            "id": int,
            "title": str,
            "description": str | null,
            "done": bool
        }
    """
    task = TaskRepository.get_by_id(task_id)
    if not task:
        return jsonify({"error": _("Task not found.")}), 404
    data = request.get_json(silent=True) or {}
    updated = TaskRepository.update(
        task=task,
        title=data.get("title"),
        description=data.get("description"),
        done=data.get("done"),
    )
    return jsonify(updated.to_dict()), 200


@tasks_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    """Delete a task by ID.

    Endpoint: DELETE /tasks/<id>
    Method: DELETE
    Request body: None
    URL parameters: id (int) — the task ID
    Response format: JSON object with a success message.
        {
            "message": str
        }
    """
    task = TaskRepository.get_by_id(task_id)
    if not task:
        return jsonify({"error": _("Task not found.")}), 404
    TaskRepository.delete(task)
    return jsonify({"message": _("Task deleted.")}), 200
