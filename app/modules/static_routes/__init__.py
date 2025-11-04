from flask import Blueprint

static_routes_bp = Blueprint('static_routes', __name__, url_prefix='/static-routes')

from app.modules.static_routes import views
