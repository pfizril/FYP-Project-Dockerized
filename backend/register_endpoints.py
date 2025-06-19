# RUN MANUALLY IN CMD AND RUN IF ADD NEW ENDPOINTS
from main import app
from models import APIEndpoint
from database import session
from fastapi.routing import APIRoute
from sqlalchemy.exc import IntegrityError
from datetime import datetime

def register_routes_to_db():
    db = session()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue  # skip non-API routes (e.g. static files)

        path = route.path
        name = route.name or "Unnamed"
        description = getattr(route.endpoint, '__doc__', '') or ""
        requires_auth = any(
            hasattr(dep.call, '__name__') and dep.call.__name__ in ["get_current_user", "require_api_key", "require_jwt", "get_current_admin"]
            for dep in route.dependant.dependencies
        )

        for method in route.methods:
            if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                continue

            # Check if URL+method combo already exists
            exists = db.query(APIEndpoint).filter_by(url=path, method=method).first()
            if not exists:
                endpoint = APIEndpoint(
                    name=name,
                    url=path,
                    method=method,
                    status=True,
                    description=description.strip(),
                    requires_auth=requires_auth,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(endpoint)

    try:
        db.commit()
        print("All API endpoints registered successfully.")
    except IntegrityError:
        db.rollback()
        print("Duplicate entries skipped.")
    finally:
        db.close()

if __name__ == "__main__":
    register_routes_to_db()
