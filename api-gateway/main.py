from fastapi import FastAPI, HTTPException, Depends, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import httpx
import structlog
from prometheus_client import Counter, Histogram
import time
from typing import Union

# Configure logging
logger = structlog.get_logger()

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])

app = FastAPI(title="FortifAI API Gateway")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 scheme for authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Service routing configuration
SERVICE_ROUTES = {
    "analytics": "http://analytics-service:80",
    "processing": "http://processing-service:80",
    "storage": "http://storage-service:80",
    "data-access": "http://data-access-service.microservices:8000"
}

class ServiceResponse(BaseModel):
    service: str
    data: Union[dict, list]  # Allow both dict and list responses
    status: int

@app.middleware("http")
async def add_metrics(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    # This endpoint will be used by Prometheus to scrape metrics
    return {"status": "ok"}

@app.post("/token")
async def login(request: Request):
    # Log the raw request data for debugging
    body = await request.body()
    logger.info("token_request", body=body.decode(), headers=dict(request.headers))
    
    # Parse form data manually
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")
    
    logger.info("token_credentials", username=username, password=password)
    
    # For development, accept any credentials
    return {"access_token": "development_token", "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    logger.info("get_current_user_called", token=token)
    if not token:
        logger.warning("no_token_provided")
        return None
    # For development, accept any token
    return {"username": "development"}

async def forward_request(request: Request, service: str, path: str):
    """Forward request to appropriate service."""
    if service not in SERVICE_ROUTES:
        raise HTTPException(status_code=404, detail=f"Service {service} not found")
    
    # Remove leading slashes from path
    path = path.lstrip('/')
    
    # Handle data-access service paths
    if service == "data-access":
        # Map /api/data-access/ec2 to /assets/ec2
        if path in ["ec2", "vpc", "subnet", "sg", "s3", "iam_role", "user", "iam_policy", "kms_key", "cloudwatch_metric"]:
            path = f"assets/{path}"
        logger.info("data_access_path_mapped", path=path)
    
    target_url = f"{SERVICE_ROUTES[service]}/{path}"
    logger.info("forwarding_request", service=service, path=path, target_url=target_url, method=request.method)
    
    # Get request body for non-GET requests
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=dict(request.headers),
                content=body,
                params=request.query_params,
                timeout=30.0
            )
            return response.json()
        except httpx.HTTPError as e:
            logger.error("request_failed", error=str(e), service=service, path=path, method=request.method)
            raise HTTPException(status_code=500, detail=f"Request to {service} failed: {str(e)}")

@app.get("/api/{service}/{path:path}")
async def route_get(service: str, path: str, request: Request, user: dict = Depends(get_current_user)):
    logger.info("route_get_called", service=service, path=path, user=user)
    try:
        return await forward_request(request, service, path)
    except Exception as e:
        logger.error("route_get_error", service=service, path=path, error=str(e))
        raise

@app.post("/api/{service}/{path:path}")
async def route_post(service: str, path: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    logger.info("route_post_called", service=service, path=path, data=data, user=user)
    try:
        return await forward_request(request, service, path)
    except Exception as e:
        logger.error("route_post_error", service=service, path=path, error=str(e))
        raise

@app.put("/api/{service}/{path:path}")
async def route_put(service: str, path: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    logger.info("route_put_called", service=service, path=path, data=data, user=user)
    try:
        return await forward_request(request, service, path)
    except Exception as e:
        logger.error("route_put_error", service=service, path=path, error=str(e))
        raise

@app.delete("/api/{service}/{path:path}")
async def route_delete(service: str, path: str, request: Request, user: dict = Depends(get_current_user)):
    logger.info("route_delete_called", service=service, path=path, user=user)
    try:
        return await forward_request(request, service, path)
    except Exception as e:
        logger.error("route_delete_error", service=service, path=path, error=str(e))
        raise

# Add a catch-all route for debugging - moved to the end to not interfere with /api routes
@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(full_path: str, request: Request):
    logger.info("catch_all_route", 
                full_path=full_path,
                method=request.method,
                headers=dict(request.headers),
                query_params=dict(request.query_params))
    raise HTTPException(status_code=404, detail=f"Route not found: {full_path}") 