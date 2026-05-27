from datetime import date

from flask import Blueprint, jsonify, request
from flask_babel import gettext as _

from app.repositories.project_repository import ProjectRepository

projects_bp = Blueprint("projects", __name__)


@projects_bp.route("/projects", methods=["GET"])
def list_projects():
    """List all projects.

    Endpoint: GET /projects
    Method: GET
    Request body: None
    Response format: JSON array of project objects.
        [
            {
                "id": int,
                "name": str,
                "description": str | null,
                "due_date": str | null
            }
        ]
    """
    projects = ProjectRepository.get_all()
    return jsonify([p.to_dict() for p in projects]), 200


@projects_bp.route("/projects", methods=["POST"])
def create_project():
    """Create a new project.

    Endpoint: POST /projects
    Method: POST
    Request body: JSON object with:
        - name (str, required)
        - description (str, optional)
        - due_date (str, ISO date YYYY-MM-DD, optional)
    Response format: JSON object representing the created project.
        {
            "id": int,
            "name": str,
            "description": str | null,
            "due_date": str | null
        }
    """
    data = request.get_json(silent=True)
    if not data or "name" not in data:
        return jsonify({"error": _("Name is required.")}), 400
    due_date_raw = data.get("due_date")
    try:
        due_date = date.fromisoformat(due_date_raw) if due_date_raw else None
    except (ValueError, TypeError):
        return jsonify({"error": _("Invalid date format. Use YYYY-MM-DD.")}), 400
    project = ProjectRepository.create(
        name=data["name"],
        description=data.get("description"),
        due_date=due_date,
    )
    return jsonify(project.to_dict()), 201


@projects_bp.route("/projects/<int:project_id>", methods=["GET"])
def get_project(project_id):
    """Get a single project by ID.

    Endpoint: GET /projects/<id>
    Method: GET
    Request body: None
    URL parameters: id (int) — the project ID
    Response format: JSON object representing the project.
        {
            "id": int,
            "name": str,
            "description": str | null,
            "due_date": str | null
        }
    """
    project = ProjectRepository.get_by_id(project_id)
    if not project:
        return jsonify({"error": _("Project not found.")}), 404
    return jsonify(project.to_dict()), 200


@projects_bp.route("/projects/<int:project_id>/tasks", methods=["GET"])
def list_project_tasks(project_id):
    """List all tasks belonging to a project.

    Endpoint: GET /projects/<id>/tasks
    Method: GET
    Request body: None
    URL parameters: id (int) — the project ID
    Response format: JSON array of task objects.
        [
            {
                "id": int,
                "title": str,
                "description": str | null,
                "done": bool,
                "project_id": int | null
            }
        ]
    """
    project = ProjectRepository.get_by_id(project_id)
    if not project:
        return jsonify({"error": _("Project not found.")}), 404
    return jsonify([t.to_dict() for t in project.tasks]), 200
