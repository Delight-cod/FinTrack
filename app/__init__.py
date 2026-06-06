from flask import Flask
from .models import engine, Base
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    Base.metadata.create_all(bind=engine)

    from .routes.pages import pages_bp
    from .routes.auth import auth_bp
    from .routes.transactions import transactions_bp
    from .routes.analytics import analytics_bp
    from .routes.budgets import budgets_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(budgets_bp)

    return app
