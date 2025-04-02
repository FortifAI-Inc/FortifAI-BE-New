from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Body, Header, Query
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field, ValidationError
import boto3
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
from io import BytesIO
import structlog
from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST
import time
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from enum import Enum
from fastapi.responses import Response, JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Metrics
REQUEST_COUNT = Counter('data_layer_requests_total', 'Total data layer requests', ['operation', 'status'])
REQUEST_LATENCY = Histogram('data_layer_request_duration_seconds', 'Data layer request latency', ['operation'])

app = FastAPI(title="FortifAI Data Layer")

# OAuth2 scheme for authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# S3 client
s3_client = boto3.client('s3')
BUCKET_NAME = "fortifai-data"

class AssetType(str, Enum):
    """Enumeration of supported asset types."""
    VPC = "vpc"
    SUBNET = "subnet"
    EC2 = "ec2"
    S3 = "s3"
    IAM_ROLE = "iam_role"
    SECURITY_GROUP = "sg"
    USER = "user"
    IGW = "igw"
    NI = "ni"
    LAMBDA = "lambda"
    IAM_POLICY = "iam_policy"

# Asset schemas
class AssetMetadata(BaseModel):
    asset_id: str
    asset_type: AssetType
    schema: Dict[str, str]
    row_count: int
    created_at: datetime
    updated_at: datetime

class AssetData(BaseModel):
    data: List[Dict[str, Any]]
    metadata: AssetMetadata

class AssetCreate(BaseModel):
    unique_id: str
    name: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: Dict[str, str] = Field(default_factory=dict)
    is_stale: bool = False

class AssetBatchCreate(BaseModel):
    assets: List[AssetCreate]

class AssetUpdate(BaseModel):
    data: List[Dict[str, Any]]
    schema: Optional[Dict[str, str]] = None

class Asset(AssetCreate):
    id: str
    asset_type: AssetType
    created_at: datetime
    updated_at: datetime
    last_synced_at: Optional[datetime] = None
    data_file_key: Optional[str] = None
    metadata_file_key: Optional[str] = None

    class Config:
        from_attributes = True

@app.middleware("http")
async def add_metrics(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(
        operation=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_LATENCY.labels(
        operation=request.url.path
    ).observe(duration)
    
    return response

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    return {"status": "ok"}

@app.post("/assets/{asset_type}")
async def create_asset(
    asset_type: AssetType,
    asset: AssetCreate,
    token: str = Depends(oauth2_scheme)
):
    """Create a new asset."""
    try:
        logger.debug(f"Received asset creation request: {asset}")
        
        # Generate a unique asset ID
        asset_id = f"AssetType.{asset_type.value}_{asset.unique_id}"
        logger.debug(f"Generated asset ID: {asset_id}")
        
        # Create metadata
        metadata = {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "unique_id": asset.unique_id,
            "name": asset.name,
            "description": asset.description,
            "metadata": asset.metadata,
            "tags": asset.tags,
            "is_stale": asset.is_stale,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        logger.debug(f"Created metadata: {metadata}")
        
        # Store metadata
        metadata_key = f"metadata/{asset_id}.json"
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=metadata_key,
            Body=json.dumps(metadata)
        )
        logger.debug(f"Stored metadata in S3: {metadata_key}")
        
        # Get existing data file for this asset type
        data_key = f"data/{asset_type.value}.parquet"
        try:
            response = s3_client.get_object(Bucket=BUCKET_NAME, Key=data_key)
            existing_data = BytesIO(response['Body'].read())
            df = pd.read_parquet(existing_data)
        except s3_client.exceptions.NoSuchKey:
            df = pd.DataFrame()
        
        # Add new asset to dataframe
        new_row = pd.DataFrame([{
            "asset_id": asset_id,
            "unique_id": asset.unique_id,
            "name": asset.name,
            "description": asset.description,
            "metadata": json.dumps(asset.metadata),
            "tags": json.dumps(asset.tags),
            "is_stale": asset.is_stale,
            "created_at": metadata["created_at"],
            "updated_at": metadata["updated_at"]
        }])
        
        df = pd.concat([df, new_row], ignore_index=True)
        
        # Store updated dataframe
        parquet_buffer = BytesIO()
        pq.write_table(pa.Table.from_pandas(df), parquet_buffer)
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=data_key,
            Body=parquet_buffer.getvalue()
        )
        logger.debug(f"Updated data file in S3: {data_key}")
        
        return {
            "id": asset_id,
            "asset_type": asset_type,
            "unique_id": asset.unique_id,
            "name": asset.name,
            "description": asset.description,
            "metadata": asset.metadata,
            "tags": asset.tags,
            "is_stale": asset.is_stale,
            "created_at": metadata["created_at"],
            "updated_at": metadata["updated_at"]
        }
    except Exception as e:
        logger.error(f"Error creating asset: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/assets/{asset_type}")
async def update_asset(
    asset_type: AssetType,
    asset: AssetUpdate,
    token: str = Depends(oauth2_scheme)
):
    """Update assets of a specific type."""
    try:
        logger.debug(f"Received asset update request for type {asset_type}")
        
        # Get existing data file for this asset type
        data_key = f"data/{asset_type.value}.parquet"
        try:
            response = s3_client.get_object(Bucket=BUCKET_NAME, Key=data_key)
            existing_data = BytesIO(response['Body'].read())
            df = pd.read_parquet(existing_data)
        except s3_client.exceptions.NoSuchKey:
            df = pd.DataFrame()
        
        # Convert new data to DataFrame
        new_data = pd.DataFrame(asset.data)
        
        # Update existing rows and add new ones
        for _, row in new_data.iterrows():
            mask = df['unique_id'] == row['unique_id']
            if mask.any():
                df.loc[mask] = row
            else:
                df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        
        # Store updated dataframe
        parquet_buffer = BytesIO()
        pq.write_table(pa.Table.from_pandas(df), parquet_buffer)
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=data_key,
            Body=parquet_buffer.getvalue()
        )
        logger.debug(f"Updated data file in S3: {data_key}")
        
        return {"message": f"Successfully updated {len(asset.data)} assets"}
    except Exception as e:
        logger.error(f"Error updating assets: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/assets/{asset_type}")
async def list_assets_by_type(
    asset_type: AssetType,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    token: str = Depends(oauth2_scheme)
):
    """List all assets of a specific type with pagination."""
    try:
        logger.info(f"Listing assets of type: {asset_type}, page: {page}, limit: {limit}")
        
        # Get data file for this asset type
        data_key = f"data/{asset_type.value}.parquet"
        try:
            response = s3_client.get_object(Bucket=BUCKET_NAME, Key=data_key)
            existing_data = BytesIO(response['Body'].read())
            df = pd.read_parquet(existing_data)
            total_count = len(df)
            logger.debug(f"Found {total_count} assets of type {asset_type}")
            
            # Apply pagination
            skip = (page - 1) * limit
            if skip >= total_count:
                logger.debug(f"Page {page} exceeds available data, returning empty list")
                return []
                
            # Get the subset of rows for this page
            end_idx = min(skip + limit, total_count)
            df_page = df.iloc[skip:end_idx]
            logger.debug(f"Paginated data: {len(df_page)} rows from index {skip} to {end_idx-1}")
            
        except s3_client.exceptions.NoSuchKey:
            logger.debug(f"No data file found for asset type {asset_type}")
            return []
        except Exception as e:
            logger.error(f"Error accessing S3 for asset type {asset_type}: {str(e)}")
            return []
        
        # Convert dataframe to list of dictionaries
        assets = []
        for _, row in df_page.iterrows():
            asset = {
                "id": row["asset_id"],
                "asset_type": asset_type,
                "unique_id": row["unique_id"],
                "name": row["name"],
                "description": row["description"],
                "is_stale": row["is_stale"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
            
            # Parse JSON strings for metadata and tags
            try:
                asset["metadata"] = json.loads(row["metadata"])
            except:
                asset["metadata"] = {}
                
            try:
                asset["tags"] = json.loads(row["tags"])
            except:
                asset["tags"] = {}
                
            assets.append(asset)
        
        logger.debug(f"Returning {len(assets)} assets for page {page} (limit: {limit})")
        return assets
    except Exception as e:
        logger.error(f"Error listing assets by type: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/assets/{asset_type}/batch")
async def create_assets_batch(
    asset_type: AssetType,
    batch: AssetBatchCreate,
    token: str = Depends(oauth2_scheme)
):
    """Create or update multiple assets in a batch."""
    try:
        logger.debug(f"Received batch asset creation request for type: {asset_type} with {len(batch.assets)} assets")
        
        # Log detailed information about the batch
        for i, asset in enumerate(batch.assets):
            # Check if asset is valid
            try:
                # Validate the asset explicitly
                asset_dict = asset.model_dump()
                AssetCreate(**asset_dict)
            except ValidationError as ve:
                logger.error(f"Asset {i} validation failed: {ve.errors()}")
                raise
        
        # Get existing data file for this asset type
        data_key = f"data/{asset_type.value}.parquet"
        try:
            response = s3_client.get_object(Bucket=BUCKET_NAME, Key=data_key)
            existing_data = BytesIO(response['Body'].read())
            df = pd.read_parquet(existing_data)
            logger.debug(f"Found existing data file with {len(df)} rows")
        except s3_client.exceptions.NoSuchKey:
            logger.debug("No existing data file found, creating new DataFrame")
            df = pd.DataFrame()
        
        # Process each asset
        new_rows = []
        updated_count = 0
        created_count = 0
        
        for asset in batch.assets:
            # Generate a unique asset ID
            asset_id = f"AssetType.{asset_type.value}_{asset.unique_id}"
            
            # Create metadata
            now = datetime.utcnow().isoformat()
            
            # Check if this asset already exists in the dataframe
            existing_mask = df['unique_id'] == asset.unique_id
            
            if len(df) > 0 and existing_mask.any():
                # Update existing asset
                logger.debug(f"Updating existing asset with unique_id: {asset.unique_id}")
                updated_count += 1
                
                # Get the original creation date
                created_at = df.loc[existing_mask, 'created_at'].iloc[0]
                
                # Update the row
                df.loc[existing_mask, 'name'] = asset.name
                df.loc[existing_mask, 'description'] = asset.description
                df.loc[existing_mask, 'metadata'] = json.dumps(asset.metadata)
                df.loc[existing_mask, 'tags'] = json.dumps(asset.tags)
                df.loc[existing_mask, 'is_stale'] = asset.is_stale
                df.loc[existing_mask, 'updated_at'] = now
                
                # Also add to new_rows for response
                new_rows.append({
                    "asset_id": asset_id,
                    "unique_id": asset.unique_id,
                    "name": asset.name,
                    "description": asset.description,
                    "metadata": json.dumps(asset.metadata),
                    "tags": json.dumps(asset.tags),
                    "is_stale": asset.is_stale,
                    "created_at": created_at,
                    "updated_at": now
                })
            else:
                # Add new asset
                logger.debug(f"Creating new asset with unique_id: {asset.unique_id}")
                created_count += 1
                
                new_row = {
                    "asset_id": asset_id,
                    "unique_id": asset.unique_id,
                    "name": asset.name,
                    "description": asset.description,
                    "metadata": json.dumps(asset.metadata),
                    "tags": json.dumps(asset.tags),
                    "is_stale": asset.is_stale,
                    "created_at": now,
                    "updated_at": now
                }
                
                # Add to dataframe
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                
                # Add to new_rows for response
                new_rows.append(new_row)
        
        logger.debug(f"Processed {len(batch.assets)} assets: {created_count} created, {updated_count} updated")
        
        # Store updated dataframe
        parquet_buffer = BytesIO()
        pq.write_table(pa.Table.from_pandas(df), parquet_buffer)
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=data_key,
            Body=parquet_buffer.getvalue()
        )
        logger.debug(f"Stored updated data file with {len(df)} rows")
        
        # Create response
        response_data = [{
            "id": row["asset_id"],
            "asset_type": asset_type,
            "unique_id": row["unique_id"],
            "name": row["name"],
            "description": row["description"],
            "metadata": json.loads(row["metadata"]),
            "tags": json.loads(row["tags"]),
            "is_stale": row["is_stale"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        } for row in new_rows]
        
        return response_data
    except ValidationError as ve:
        logger.error(f"Validation error in batch creation: {str(ve)}")
        # Get detailed validation errors
        error_details = []
        for error in ve.errors():
            error_details.append({
                "loc": error.get("loc", []),
                "msg": error.get("msg", ""),
                "type": error.get("type", "")
            })
        logger.error(f"Validation error details: {error_details}")
        raise HTTPException(status_code=422, detail={"message": "Validation error", "errors": error_details})
    except Exception as e:
        logger.error(f"Error creating assets batch: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/assets")
async def list_all_assets(
    asset_type: Optional[AssetType] = None,
    token: str = Depends(oauth2_scheme)
):
    """List all assets with optional filtering by type."""
    try:
        # If asset_type is specified, use the existing list_assets_by_type function
        if asset_type:
            return await list_assets_by_type(asset_type, token)
        
        # Otherwise, retrieve all asset types and combine results
        all_assets = []
        for current_type in AssetType:
            try:
                assets = await list_assets_by_type(current_type, token)
                all_assets.extend(assets)
            except Exception as e:
                # Log but continue if one type fails
                logger.error(f"Error listing assets of type {current_type}: {str(e)}")
                
        return all_assets
    except Exception as e:
        logger.error(f"Error listing all assets: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 