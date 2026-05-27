from flask import Flask
from flask_babel import Babel
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
babel = Babel()


def create_app(config_object="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    babel.init_app(app)

    from app.routes.tasks import tasks_bp

    app.register_blueprint(tasks_bp)

    with app.app_context():
        db.create_all()

    return app
