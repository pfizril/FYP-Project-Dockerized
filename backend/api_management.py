from typing import Union, List, Annotated
from pydantic import BaseModel 
from fastapi import FastAPI, HTTPException, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import models
from database import engine, session
from sqlalchemy.orm import Session
from datetime import datetime
import auth
from starlette import status 
from auth import get_current_user
from models import EndpointHealth, APIEndpoint
from sqlalchemy.sql import func  
from fastapi.security import APIKeyHeader

from urllib.parse import urlparse
from dotenv import load_dotenv


load_dotenv()
router = APIRouter(
    prefix='/api-management',
    tags=['Api Management']
)

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)


class EndpointBaseDisplay(BaseModel):
    endpoint_id: int
    name: str
    url: str
    method: str
    status: bool
    description: str

class CreateEndpoint(BaseModel):
    name: str
    url: str
    method: str
    status: bool
    description: str

class UpdateEndpointBase(BaseModel):
    name: str = None
    url: str = None
    method: str = None
    status: bool = None
    updated_at: datetime = None
    requires_auth: bool = None
    description: str = None


def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()



db_dependecy = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.put("/endpoints-update/{endpoint_id}")
def update_endpoint(api_key: Annotated[str, Depends(api_key_header)],endpoint_id: int, data: UpdateEndpointBase,user:user_dependency, db: Session = Depends(get_db)):
    endpoint = db.query(models.APIEndpoint).filter(models.APIEndpoint.endpoint_id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(endpoint, key, value)
    
    db.commit()
    db.refresh(endpoint)
    return {"message": "Endpoint updated successfully", "data": endpoint}


@router.delete("/delete-endpoints/{endpoint_id}")
def delete_endpoint(api_key: Annotated[str, Depends(api_key_header)],endpoint_id: int,user:user_dependency, db: Session = Depends(get_db)):
    endpoint = db.query(models.APIEndpoint).filter(models.APIEndpoint.endpoint_id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    db.delete(endpoint)
    db.commit()
    return {"message": "Endpoint deleted successfully"}


@router.post("/endpoints/create")
def create_endpoint(api_key: Annotated[str, Depends(api_key_header)],data: CreateEndpoint,user:user_dependency, db: Session = Depends(get_db)):
    new_endpoint = models.APIEndpoint(
        name=data.name,
        url=data.url,
        method=data.method,
        description=data.description,
    )
    db.add(new_endpoint)
    db.commit()
    db.refresh(new_endpoint)
    return {"message": "Endpoint created successfully", "data": new_endpoint}


@router.get("/endpoints", response_model=List[EndpointBaseDisplay])
async def list_endpoints(api_key: Annotated[str, Depends(api_key_header)],user:user_dependency, db: Session = Depends(get_db)):
    endpoints = db.query(models.APIEndpoint).all()
    return endpoints

@router.put("/endpoints/toggle_status/{endpoint_id}")
def toggle_endpoint_status(api_key: Annotated[str, Depends(api_key_header)],endpoint_id: int, user:user_dependency,status: bool, db: Session = Depends(get_db)):
    endpoint = db.query(models.APIEndpoint).filter(models.APIEndpoint.endpoint_id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    endpoint.status = status
    db.commit()
    db.refresh(endpoint)
    return {"message": "Endpoint status updated", "data": endpoint}




    