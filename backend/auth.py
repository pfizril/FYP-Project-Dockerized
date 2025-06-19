from datetime import timedelta, datetime,timezone
from typing import Annotated
from fastapi import APIRouter, Depends , HTTPException,Request
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status 
from database import session
from models import Users, APIEndpoint, APIKey, ThreatLog,ActivityLog
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError, jwt
from functools import wraps
import os
from dotenv import load_dotenv
from secrets import token_urlsafe
from collections import defaultdict
import requests
import logging
import asyncio
from csrf_protection import generate_csrf_token
load_dotenv()
from csrf_protection import csrf_protect
import re

router = APIRouter(
    prefix='/auth',
    tags=['Authentication']
)

logging.basicConfig(level=logging.INFO)


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"


api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)
class CreateUserRequest(BaseModel):
    user_name: str
    user_psw: str
    user_email: str
    user_role : str
    

class Token(BaseModel):
    access_token: str
    token_type: str 

def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()



db_dependecy = Annotated[Session, Depends(get_db)]

async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_name: str = payload.get('sub')
        user_id: int = int(payload.get('id'))
        user_role: str = payload.get('role')
        if user_name is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user.")
        return {"username": user_name, "id": user_id, "role": user_role}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user.")

user_dependency = Annotated[dict, Depends(get_current_user)]


def role_required(allowed_roles: list):
    def decorator(func):
        @wraps(func)
        async def async_wrapper(user: user_dependency, *args, **kwargs):
            if user.get('role') not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have the required permissions to access this resource."
                )
            return await func(user=user, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(user: user_dependency, *args, **kwargs):
            if user.get('role') not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have the required permissions to access this resource."
                )
            return func(user=user, *args, **kwargs)
        
        # Check if the function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator


@router.post("/users/create-user", status_code=status.HTTP_201_CREATED)
async def create_user(user:user_dependency, db: db_dependecy, create_user_request: CreateUserRequest,api_key: Annotated[str, Depends(api_key_header)]):
        create_user_model= Users(
            user_name=create_user_request.user_name,
            user_email = create_user_request.user_email,
            user_role = create_user_request.user_role,
            hashed_psw=bcrypt_context.hash(create_user_request.user_psw)
        )
        db.add(create_user_model)
        db.commit()


@router.post("/token")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    client_ip = request.client.host
    user = authenticate_user(form_data.username, form_data.password, db)

    if not user:
      # Log failed attempt to ThreatLog
        failed_log = ThreatLog(
            client_ip=client_ip,
            activity="Failed Login",
            detail=f"Invalid credentials for username: {form_data.username}"
        )
        db.add(failed_log)
        db.commit()

        # Brute-force detection: 5+ failures in 5 mins
        five_minutes_ago = datetime.now() - timedelta(minutes=5)

        fail_count = db.query(ThreatLog).filter(
            ThreatLog.client_ip == client_ip,
            ThreatLog.activity == "Failed Login",
            ThreatLog.created_at >= five_minutes_ago
        ).count()

        if fail_count >= 5:
            db.add(ThreatLog(
                client_ip=client_ip,
                activity="brute_force_detected",
                detail=f"{fail_count} failed login attempts within 5 minutes"
            ))
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    token = create_accesstoken(
        user.user_name, 
        user.user_id, 
        user.user_role, 
        timedelta(minutes=15)
    )
    
    # Create CSRF token
    csrf_token = generate_csrf_token()

    # Get or generate API key
    api_key_data = db.query(APIKey).filter(
        APIKey.user_id == user.user_id,
        APIKey.is_active == True
    ).first()

    if not api_key_data:
        # Generate new API key if none exists
        api_key = token_urlsafe(32)
        api_key_data = APIKey(key=api_key, user_id=user.user_id, is_active=True)
        db.add(api_key_data)
        db.commit()
    else:
        api_key = api_key_data.key

    # Set CSRF in cookie + return in response body (for frontend use)
    response = JSONResponse(content={
        "access_token": token,
        "token_type": "bearer",
        "csrf_token": csrf_token,
        "api_key": api_key
    })
    response.set_cookie(
        key="csrf_token", 
        value=csrf_token,
        httponly=False,
        samesite="Strict"
    )

    return response


@router.get("/show-current-users", status_code=status.HTTP_200_OK)
async def user(user:user_dependency, db:db_dependecy):
    if user is None: 
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed.")
    return {"User": user}


@router.get("/current-user", status_code=status.HTTP_200_OK)
async def show_current_user(api_key: Annotated[str, Depends(api_key_header)],db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    user_data = db.query(Users).filter(Users.user_id == user["id"]).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # Get the user's active API key
    api_key_data = db.query(APIKey).filter(
        APIKey.user_id == user["id"],
        APIKey.is_active == True
    ).first()

    return {
        "user_id": user_data.user_id,
        "user_name": user_data.user_name,
        "user_email": user_data.user_email,
        "user_role": user_data.user_role,
        "api_key": api_key_data.key if api_key_data else None
    }

@router.put("/update-user", status_code=status.HTTP_200_OK)
async def update_user_profile(
    user_update: dict, 
    db: Session = Depends(get_db), 
    user: dict = Depends(get_current_user)
):
    user_data = db.query(Users).filter(Users.user_id == user["id"]).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    # Update user details
    user_data.user_name = user_update.get("user_name", user_data.user_name)
    user_data.user_email = user_update.get("user_email", user_data.user_email)

    # Update password if provided
    if "password" in user_update and user_update["password"]:
        user_data.hashed_psw = bcrypt_context.hash(user_update["password"])

    db.commit()
    return {"message": "Profile updated successfully"}


@router.post("/api-keys/generate/{user_id}", status_code=status.HTTP_201_CREATED)
async def generate_api_key(api_key: Annotated[str, Depends(api_key_header)],user_id: int, user:user_dependency, db: Session = Depends(get_db)):
    user = db.query(Users).filter(Users.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    api_key = token_urlsafe(32)  # Generate a secure random key
    new_key = APIKey(key=api_key, user_id=user_id, is_active=True)
    db.add(new_key)
    db.commit()
    
    return {"api_key": api_key}


@router.post("/api-keys/revoke/{key_id}")
async def revoke_api_key(api_key: Annotated[str, Depends(api_key_header)],key_id: int, user: user_dependency, db: db_dependecy):
    if user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Only Admins can revoke API keys.")
    
    api_key = db.query(APIKey).filter(APIKey.key_id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found.")

    api_key.is_active = False
    db.commit()
    return {"message": "API key revoked successfully."}

@router.get("/api-keys/list")
async def list_api_keys(api_key: Annotated[str, Depends(api_key_header)],user: user_dependency, db: db_dependecy):
    keys = db.query(APIKey).filter(APIKey.user_id == user['id']).all()
    
    return [{"key_id": k.key_id, "key": k.key, "is_active": k.is_active, "user_id":k.user_id} for k in keys]


@router.get("/api-keys/{user_id}")
async def get_api_key(api_key: Annotated[str, Depends(api_key_header)],user_id: int, user:user_dependency,db: Session = Depends(get_db)):
    api_key = db.query(APIKey).filter(APIKey.user_id == user_id, APIKey.is_active == True).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key not found.")

    return {"api_key": api_key.key}


@router.get("/protected")
async def protected_endpoint(api_key: Annotated[str, Depends(api_key_header)], db: db_dependecy, user:user_dependency,):
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required.")
    await validate_api_key(api_key, db)
    return {"message": "Access granted"}


@router.get("/users/list", status_code=status.HTTP_200_OK)
async def list_users(api_key: Annotated[str, Depends(api_key_header)],user: user_dependency, db: db_dependecy, req: Request):
    if user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Only Admins can view users.") 

    users = db.query(Users).all()

    log_activity(user['id'], "Listed down all users", db, req) #test recording the log activity 
    
    return [
        {
            "user_id": u.user_id,
            "user_name": u.user_name,
            "user_email": u.user_email,
            "user_role": u.user_role
        } 
        for u in users
    ]

     

@router.put("/users/update-role/{user_id}")
async def update_user_role(api_key: Annotated[str, Depends(api_key_header)],user_id: int, new_role: str, user: user_dependency, db: db_dependecy):
    if user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Only Admins can modify roles.")

    user_to_update = db.query(Users).filter(Users.user_id == user_id).first()
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found.")

    user_to_update.user_role = new_role
    db.commit()
    return {"message": f"User {user_to_update.user_name} role updated to {new_role}."}

@router.put("/users/update/{user_id}")
async def update_user(
    api_key: Annotated[str, Depends(api_key_header)],
    user_id: int, 
    user_update: dict, 
    user: user_dependency, 
    db: db_dependecy
):
    if user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Only Admins can modify users.")

    user_to_update = db.query(Users).filter(Users.user_id == user_id).first()
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found.")

    # Update user information
    if "user_name" in user_update:
        user_to_update.user_name = user_update["user_name"]
    if "user_email" in user_update:
        user_to_update.user_email = user_update["user_email"]
    if "user_role" in user_update:
        user_to_update.user_role = user_update["user_role"]

    db.commit()
    return {"message": f"User {user_to_update.user_name} information updated successfully."}

async def check_endpoint_status(request: Request, call_next):
    db: Session = next(get_db())
    
    # Extract requested path and method
    requested_url = request.url.path
    requested_method = request.method

    # Get all disabled endpoints
    disabled_endpoints = db.query(APIEndpoint).filter(
        APIEndpoint.status == False
    ).all()

    # Check if the requested URL matches any disabled endpoint pattern
    for disabled_endpoint in disabled_endpoints:
        # Convert FastAPI path parameter format to regex pattern
        # Replace {param} with regex pattern that matches any value
        pattern = re.escape(disabled_endpoint.url).replace('\\{', '{').replace('\\}', '}')
        pattern = re.sub(r'\{[^}]+\}', r'[^/]+', pattern)
        
        # Add start and end anchors to ensure full match
        pattern = f'^{pattern}$'
        
        # Check if requested URL matches this pattern
        if re.match(pattern, requested_url):
            raise HTTPException(status_code=403, detail="This API is currently down.")

    return await call_next(request)


async def validate_api_key(api_key: str, db: Session):
    key = db.query(APIKey).filter(APIKey.key == api_key, APIKey.is_active == True).first()
    if not key:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key.")
    return key

def authenticate_user(user_name : str, psw: str , db):
    user = db.query(Users).filter(Users.user_name == user_name).first()
    if not user:
        return False
    if not bcrypt_context.verify(psw, user.hashed_psw):
        return False
    return user


def create_accesstoken(user_name: str, user_id: int, user_role: str, expires_delta: timedelta):
    encode = {'sub': user_name, 'id': user_id, 'role': user_role}
    expire = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp':expire})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


def log_activity(user_id: int, action: str, db: Session,request: Request):
    log_entry = ActivityLog(user_id=user_id, action=action, client_ip= request.client.host)
    db.add(log_entry)
    db.commit()

def verify_health_check_key(api_key: str = Depends(APIKeyHeader(name="X-API-KEY", auto_error=False))):
    """
    Verify the health check API key for internal health monitoring
    """
    health_check_api_key = os.getenv("HEALTH_CHECK_API_KEY", "health-monitor-key")
    
    if api_key == health_check_api_key:
        return True
    return False

# Optional user authentication - doesn't raise exception if no user
async def get_current_user_optional(token: str = Depends(oauth2_scheme_optional)):
    if not token:
        return None
    return await get_current_user(token)

