from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from prometheus_client import Counter, Histogram
import structlog
import boto3
import pyarrow.parquet as pq
from io import BytesIO
import time

# Configure logging
logger = structlog.get_logger()

# Metrics
REQUEST_COUNT = Counter('analytics_requests_total', 'Total analytics requests', ['endpoint', 'status'])
REQUEST_LATENCY = Histogram('analytics_request_duration_seconds', 'Analytics request latency', ['endpoint'])

app = FastAPI(title="FortifAI Analytics Service")

# OAuth2 scheme for authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# S3 client
s3_client = boto3.client('s3')

class AnalyticsRequest(BaseModel):
    data_id: str
    analysis_type: str
    parameters: dict = {}

@app.middleware("http")
async def add_metrics(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_LATENCY.labels(
        endpoint=request.url.path
    ).observe(duration)
    
    return response

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    return {"status": "ok"}

async def load_data_from_s3(data_id: str) -> pd.DataFrame:
    try:
        bucket_name = "fortifai-data"
        file_path = f"data/{data_id}.parquet"
        
        response = s3_client.get_object(Bucket=bucket_name, Key=file_path)
        parquet_file = BytesIO(response['Body'].read())
        
        return pq.read_table(parquet_file).to_pandas()
    except Exception as e:
        logger.error("data_load_failed", data_id=data_id, error=str(e))
        raise HTTPException(status_code=404, detail=f"Data not found: {data_id}")

@app.post("/analyze")
async def analyze_data(request: AnalyticsRequest, token: str = Depends(oauth2_scheme)):
    try:
        # Load data from S3
        df = await load_data_from_s3(request.data_id)
        
        # Perform analysis based on type
        if request.analysis_type == "basic_stats":
            result = {
                "mean": df.mean().to_dict(),
                "std": df.std().to_dict(),
                "min": df.min().to_dict(),
                "max": df.max().to_dict()
            }
        elif request.analysis_type == "correlation":
            result = df.corr().to_dict()
        elif request.analysis_type == "distribution":
            result = {
                column: df[column].value_counts().to_dict()
                for column in df.columns
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unknown analysis type: {request.analysis_type}")
        
        return {
            "data_id": request.data_id,
            "analysis_type": request.analysis_type,
            "result": result
        }
    except Exception as e:
        logger.error("analysis_failed", data_id=request.data_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) 