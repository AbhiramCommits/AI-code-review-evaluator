from app import db
from app.models.task import Task


class TaskRepository:
    @staticmethod
    def get_all():
        return Task.query.all()

    @staticmethod
    def get_by_id(task_id):
        return db.session.get(Task, task_id)

    @staticmethod
    def create(title, description=None):
        task = Task(title=title, description=description)
        db.session.add(task)
        db.session.commit()
        return task

    @staticmethod
    def update(task, title=None, description=None, done=None):
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if done is not None:
            task.done = done
        db.session.commit()
        return task

    @staticmethod
    def delete(task):
        db.session.delete(task)
        db.session.commit()
