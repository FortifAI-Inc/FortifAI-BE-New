from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional, Dict, Any, Union
from .schemas import (
    Asset, AssetCreate, AssetUpdate, AssetType,
    ASSET_TYPE_SCHEMAS
)
from .service import DataAccessService
import os
import logging
from httpx import AsyncClient
import httpx

logger = logging.getLogger(__name__)

app = FastAPI(title="FortifAI Data Access Service")

# OAuth2 scheme for authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize service
service = DataAccessService(
    data_layer_url=os.getenv("DATA_LAYER_URL", "http://data-layer"),
    data_layer_token=os.getenv("DATA_LAYER_TOKEN", "development_token")
)

@app.post("/assets/{asset_type}", response_model=Asset)
async def create_asset(
    asset_type: AssetType,
    asset: AssetCreate,
    token: str = Depends(oauth2_scheme)
):
    """Create a new asset."""
    try:
        # Ensure asset_type matches the path parameter
        if asset.asset_type != asset_type:
            raise HTTPException(
                status_code=400,
                detail="Asset type in path does not match asset type in body"
            )
        result = await service.create_asset(asset)
        return result
    except Exception as e:
        logger.error(f"Error creating asset: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/assets/{asset_id}", response_model=Asset)
async def get_asset(
    asset_id: int,
    token: str = Depends(oauth2_scheme)
):
    """Get an asset by ID."""
    return await service.get_asset(asset_id)

@app.put("/assets/{asset_id}", response_model=Asset)
async def update_asset(
    asset_id: int,
    asset_update: AssetUpdate,
    token: str = Depends(oauth2_scheme)
):
    """Update an existing asset."""
    return await service.update_asset(asset_id, asset_update)

@app.delete("/assets/{asset_id}")
async def delete_asset(
    asset_id: int,
    token: str = Depends(oauth2_scheme)
):
    """Delete an asset."""
    await service.delete_asset(asset_id)
    return {"status": "success"}

@app.get("/assets", response_model=List[Asset])
async def list_assets(
    asset_type: Optional[AssetType] = None,
    token: str = Depends(oauth2_scheme)
):
    """List all assets, optionally filtered by type."""
    return await service.list_assets(asset_type)

@app.get("/assets/type/{asset_type}", response_model=List[Asset])
async def list_assets_by_type(
    asset_type: AssetType,
    page: int = 1,
    limit: int = 100,
    token: str = Depends(oauth2_scheme)
):
    """List assets by type using the data layer's type-specific endpoint."""
    try:
        logger.info(f"Getting assets of type: {asset_type}")
        
        # Make a direct request to data layer's type-specific endpoint with a timeout
        async with AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(
                    f"{service.data_layer_url}/assets/{asset_type.value.lower()}",
                    headers={"Authorization": f"Bearer {service.data_layer_token}"}
                )
                
                if response.status_code == 404:
                    logger.warning(f"No assets found for type {asset_type}")
                    return []
                    
                response.raise_for_status()
                assets_data = response.json()
                logger.info(f"Retrieved {len(assets_data)} assets from data layer")
                
                # Convert response to Asset objects
                return [Asset(**asset) for asset in assets_data]
            except httpx.TimeoutException:
                logger.error(f"Timeout when requesting assets of type {asset_type} from data layer")
                return []
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} when requesting assets of type {asset_type}")
                return []
    except Exception as e:
        logger.error(f"Error listing assets by type {asset_type}: {str(e)}")
        # Don't raise exception, return empty list to prevent hanging
        return []

@app.post("/assets/{asset_id}/data")
async def store_asset_data(
    asset_id: int,
    data: List[Dict[str, Any]],
    token: str = Depends(oauth2_scheme)
):
    """Store data for an asset."""
    # Get the asset to determine its type
    asset = await service.get_asset(asset_id)
    
    # Get the schema for the asset type
    schema_class = ASSET_TYPE_SCHEMAS.get(asset.asset_type)
    if not schema_class:
        raise HTTPException(
            status_code=400,
            detail=f"No schema defined for asset type: {asset.asset_type}"
        )
    
    # Validate data against schema
    try:
        for item in data:
            schema_class(**item)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data format: {str(e)}"
        )
    
    # Get schema information
    schema = {
        field: field_info.annotation.__name__
        for field, field_info in schema_class.model_fields.items()
    }
    
    await service.store_asset_data(asset_id, data, schema)
    return {"status": "success"}

@app.get("/assets/{asset_id}/data")
async def get_asset_data(
    asset_id: int,
    token: str = Depends(oauth2_scheme)
):
    """Get data for an asset."""
    return await service.get_asset_data(asset_id)

@app.post("/assets/{asset_type}", response_model=List[Asset])
async def create_assets_by_type(
    asset_type: AssetType,
    assets: Union[Dict[str, Any], List[Dict[str, Any]]],
    token: str = Depends(oauth2_scheme)
):
    """Create multiple assets of a specific type."""
    try:
        # Convert single object to list if needed
        if isinstance(assets, dict):
            assets = [assets]
            
        logger.info(f"Received request to create {len(assets)} assets of type {asset_type}")
        logger.debug(f"Asset data: {assets}")
        
        # Get the schema for the asset type
        schema_class = ASSET_TYPE_SCHEMAS.get(asset_type)
        if not schema_class:
            raise HTTPException(
                status_code=400,
                detail=f"No schema defined for asset type: {asset_type}"
            )
        
        # Validate data against schema
        validated_assets = []
        for asset_data in assets:
            try:
                # Validate data against schema
                validated_data = schema_class(**asset_data)
                
                # Create asset with type-specific fields in metadata
                asset_create = {
                    "asset_type": asset_type,
                    "unique_id": asset_data.get('unique_id', ''),
                    "name": asset_data.get('name', ''),
                    "description": asset_data.get('description'),
                    "metadata": validated_data.model_dump(),
                    "tags": asset_data.get('tags', {}),
                    "is_stale": asset_data.get('is_stale', False)
                }
                
                validated_assets.append(asset_create)
            except Exception as e:
                logger.warning(f"Invalid data for {asset_type}: {str(e)}")
                continue
        
        if not validated_assets:
            raise HTTPException(
                status_code=400,
                detail="No valid assets to create"
            )
        
        # Create assets in batch
        created_assets = await service.create_assets_batch(asset_type, validated_assets)
        logger.info(f"Successfully created {len(created_assets)} assets")
        return created_assets
    except Exception as e:
        logger.error(f"Error in create_assets_by_type: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/assets/{asset_type}/batch", response_model=List[Asset])
async def batch_create_assets(
    asset_type: AssetType,
    batch_data: Dict[str, Any],
    token: str = Depends(oauth2_scheme)
):
    """Create multiple assets of a specific type in batch."""
    try:
        # Extract assets from the batch data
        if not batch_data or "assets" not in batch_data or not batch_data["assets"]:
            error_msg = "Request must include 'assets' field with a non-empty list of assets"
            logger.error(f"Batch request validation failed: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
            
        assets = batch_data["assets"]
        if not isinstance(assets, list):
            assets = [assets]
            
        logger.info(f"Received batch request to create {len(assets)} assets of type {asset_type}")
        
        # Log each asset in the batch
        for i, asset in enumerate(assets):
            logger.info(f"Batch asset {i} details: {asset}")
        
        # Get the schema for the asset type
        schema_class = ASSET_TYPE_SCHEMAS.get(asset_type)
        if not schema_class:
            error_msg = f"No schema defined for asset type: {asset_type}"
            logger.error(f"Batch request schema validation failed: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
        
        # Validate data against schema
        validated_assets = []
        for i, asset_data in enumerate(assets):
            try:
                # Make sure asset_type is set for each asset
                asset_data["asset_type"] = asset_type
                
                logger.info(f"Validating asset {i} against schema: {asset_data}")
                
                # Create asset with type-specific fields in metadata
                asset_create = {
                    "asset_type": asset_type,
                    "unique_id": asset_data.get('unique_id', ''),
                    "name": asset_data.get('name', ''),
                    "description": asset_data.get('description', ''),
                    "metadata": asset_data.get('metadata', {}),
                    "tags": asset_data.get('tags', {}),
                    "is_stale": asset_data.get('is_stale', False)
                }
                
                logger.info(f"Formatted asset {i}: {asset_create}")
                validated_assets.append(asset_create)
            except Exception as e:
                logger.warning(f"Invalid data for asset {i} of type {asset_type} in batch: {str(e)}")
                logger.warning(f"Asset data: {asset_data}")
                continue
        
        if not validated_assets:
            error_msg = "No valid assets to create in batch"
            logger.error(f"Batch validation failed: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
        
        logger.info(f"Sending {len(validated_assets)} validated assets to service.create_assets_batch")
        
        # Create assets in batch using the same service method
        created_assets = await service.create_assets_batch(asset_type, validated_assets)
        logger.info(f"Successfully created {len(created_assets)} assets in batch")
        return created_assets
    except Exception as e:
        logger.error(f"Error in batch_create_assets: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes."""
    try:
        # First check if our service is up
        if not service:
            raise HTTPException(status_code=503, detail="Service not initialized")
            
        # Try to connect to the data layer, but don't fail if it's not available
        try:
            async with AsyncClient() as client:
                response = await client.get(f"{os.getenv('DATA_LAYER_URL', 'http://data-layer')}/health", timeout=2.0)
                if response.status_code != 200:
                    logger.warning("Data layer health check failed, but continuing")
        except Exception as e:
            logger.warning(f"Data layer health check failed: {str(e)}, but continuing")
            
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=str(e))

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    try:
        await service.close()
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}") 