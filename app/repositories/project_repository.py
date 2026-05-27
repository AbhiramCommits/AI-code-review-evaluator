from app import db
from app.models.project import Project


class ProjectRepository:
    @staticmethod
    def get_all():
        return Project.query.all()

    @staticmethod
    def get_by_id(project_id):
        return db.session.get(Project, project_id)

    @staticmethod
    def create(name, description=None, due_date=None):
        project = Project(name=name, description=description, due_date=due_date)
        db.session.add(project)
        db.session.commit()
        return project

    @staticmethod
    def update(project, name=None, description=None, due_date=None):
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if due_date is not None:
            project.due_date = due_date
        db.session.commit()
        return project

    @staticmethod
    def delete(project):
        db.session.delete(project)
        db.session.commit()
