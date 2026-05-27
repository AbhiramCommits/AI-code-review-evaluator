from app import db


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    due_date = db.Column(db.Date, nullable=True)

    def __repr__(self):
        return f"<Project id={self.id} name='{self.name}' due_date={self.due_date}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
        }
