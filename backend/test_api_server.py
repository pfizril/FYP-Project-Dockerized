from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
import time
import random
from typing import List, Dict, Any
import uvicorn
import secrets
from datetime import datetime

app = FastAPI(title="Test API Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic authentication
security = HTTPBasic()

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "test")
    correct_password = secrets.compare_digest(credentials.password, "test")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Simulate some data
users = [
    {"id": 1, "username": "user1", "email": "user1@example.com"},
    {"id": 2, "username": "user2", "email": "user2@example.com"},
]

products = [
    {"id": 1, "name": "Product 1", "price": 100},
    {"id": 2, "name": "Product 2", "price": 200},
]

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Users endpoints
@app.get("/users", response_model=List[Dict[str, Any]])
async def get_users(username: str = Depends(get_current_username)):
    # Simulate random delay
    await asyncio.sleep(random.uniform(0.1, 0.5))
    return users

@app.get("/users/{user_id}")
async def get_user(user_id: int, username: str = Depends(get_current_username)):
    # Simulate random delay
    await asyncio.sleep(random.uniform(0.1, 0.5))
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Products endpoints
@app.get("/products", response_model=List[Dict[str, Any]])
async def get_products(username: str = Depends(get_current_username)):
    # Simulate random delay
    await asyncio.sleep(random.uniform(0.1, 0.5))
    return products

@app.get("/products/{product_id}")
async def get_product(product_id: int, username: str = Depends(get_current_username)):
    # Simulate random delay
    await asyncio.sleep(random.uniform(0.1, 0.5))
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

# Error simulation endpoints
@app.get("/error/500")
async def simulate_500():
    raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/error/404")
async def simulate_404():
    raise HTTPException(status_code=404, detail="Not found")

@app.get("/error/403")
async def simulate_403():
    raise HTTPException(status_code=403, detail="Forbidden")

@app.get("/error/401")
async def simulate_401():
    raise HTTPException(status_code=401, detail="Unauthorized")

# Slow endpoint
@app.get("/slow")
async def slow_endpoint():
    await asyncio.sleep(2)  # Simulate slow response
    return {"message": "This is a slow endpoint"}

if __name__ == "__main__":
    import asyncio
    uvicorn.run(app, host="0.0.0.0", port=8000) 