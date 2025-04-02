from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException
from .schemas import Asset, AssetType, StorageLocation, AssetCreate, AssetUpdate
from .data_layer_client import DataLayerClient
import logging
import httpx
from httpx import AsyncClient

logger = logging.getLogger(__name__)

class DataAccessService:
    def __init__(self, data_layer_url: str, data_layer_token: str):
        self.data_layer_url = data_layer_url
        self.data_layer_token = data_layer_token
        self.client = AsyncClient(
            base_url=data_layer_url,
            headers={"Authorization": f"Bearer {data_layer_token}"}
        )
        self._assets: Dict[str, Asset] = {}  # In-memory storage for development

    async def create_asset(self, asset: AssetCreate) -> Asset:
        """Create a new asset."""
        response = await self.client.post(f"/assets/{asset.asset_type}", json=asset.model_dump())
        response.raise_for_status()
        return Asset(**response.json())

    async def update_asset(self, asset_id: int, asset_update: AssetUpdate) -> Asset:
        """Update an existing asset."""
        response = await self.client.put(f"/assets/{asset_id}", json=asset_update.model_dump())
        response.raise_for_status()
        return Asset(**response.json())

    async def get_asset(self, asset_id: int) -> Asset:
        """Get an asset by ID."""
        response = await self.client.get(f"/assets/{asset_id}")
        response.raise_for_status()
        return Asset(**response.json())

    async def delete_asset(self, asset_id: int):
        """Delete an asset."""
        response = await self.client.delete(f"/assets/{asset_id}")
        response.raise_for_status()

    async def list_assets(self, asset_type: Optional[AssetType] = None) -> List[Asset]:
        """List all assets, optionally filtered by type."""
        try:
            # Construct the appropriate URL and parameters
            params = {}
            if asset_type:
                # Convert asset_type to lowercase string
                asset_type_str = asset_type.value.lower()
                params["asset_type"] = asset_type_str
                logger.debug(f"Listing assets with type parameter: {asset_type_str}")
            else:
                logger.debug("Listing all assets")
            
            response = await self.client.get("/assets", params=params)
            response.raise_for_status()
            
            # Convert response to Asset objects
            assets_data = response.json()
            if not assets_data:
                logger.debug("No assets found")
                return []
                
            logger.debug(f"Retrieved {len(assets_data)} assets from data layer")
            return [Asset(**asset) for asset in assets_data]
        except Exception as e:
            logger.error(f"Error listing assets: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to list assets: {str(e)}")

    async def store_asset_data(self, asset_id: int, data: List[Dict[str, Any]], schema: Dict[str, str]):
        """Store data for an asset."""
        response = await self.client.post(
            f"/assets/{asset_id}/data",
            json={"data": data, "schema": schema}
        )
        response.raise_for_status()

    async def get_asset_data(self, asset_id: int) -> List[Dict[str, Any]]:
        """Get data for an asset."""
        response = await self.client.get(f"/assets/{asset_id}/data")
        response.raise_for_status()
        return response.json()

    async def create_assets_batch(self, asset_type: AssetType, assets: List[Dict[str, Any]]) -> List[Asset]:
        """Create multiple assets in a batch."""
        # Use lowercase string representation of asset_type for the endpoint URL
        asset_type_str = asset_type.value.lower()
        logger.debug(f"Creating batch of {len(assets)} assets of type {asset_type_str}")
        
        # Format batch data according to API expectations
        batch_data = {
            "assets": assets
        }
        
        try:
            # Try batch creation first
            response = await self.client.post(f"/assets/{asset_type_str}/batch", json=batch_data)
            response.raise_for_status()
            return [Asset(**asset) for asset in response.json()]
        except httpx.HTTPStatusError as e:
            logger.error(f"Batch creation failed: {e}")
            if e.response.status_code == 422:
                try:
                    error_data = e.response.json()
                    logger.error(f"Validation error: {error_data}")
                except Exception:
                    pass
            
            # Fall back to individual creation
            logger.info(f"Falling back to individual asset creation for {len(assets)} assets")
            created_assets = []
            
            for i, asset in enumerate(assets):
                try:
                    # Format single asset according to AssetCreate schema
                    formatted_asset = {
                        "unique_id": asset.get("unique_id", ""),
                        "name": asset.get("name", ""),
                        "description": asset.get("description", ""),
                        "metadata": asset.get("metadata", {}),
                        "tags": asset.get("tags", {}),
                        "is_stale": asset.get("is_stale", False)
                    }
                    
                    individual_response = await self.client.post(f"/assets/{asset_type_str}", json=formatted_asset)
                    individual_response.raise_for_status()
                    created_asset = Asset(**individual_response.json())
                    created_assets.append(created_asset)
                    logger.debug(f"Successfully created individual asset {i}")
                except Exception as inner_e:
                    logger.error(f"Failed to create individual asset {i}: {str(inner_e)}")
            
            return created_assets
        except Exception as e:
            logger.error(f"Error in create_assets_batch: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def create_asset_in_service(self, asset: AssetCreate) -> Asset:
        """Create a new asset and store its data in the data layer."""
        try:
            # Create asset in data layer
            data_layer_id = self.data_layer.create_asset(
                asset_type=asset.asset_type,
                data=[],  # Empty data for now
                schema={}  # Empty schema for now
            )

            # Create asset in our service
            new_asset = Asset(
                id=len(self._assets) + 1,
                name=asset.name,
                description=asset.description,
                asset_type=asset.asset_type,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                storage_locations=[
                    StorageLocation(
                        id=1,
                        asset_id=len(self._assets) + 1,
                        s3_bucket="fortifai-data",  # This is hidden from the client
                        s3_key=f"data/{data_layer_id}.parquet",  # This is hidden from the client
                        file_format="parquet",  # This is hidden from the client
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                ]
            )

            self._assets[new_asset.id] = new_asset
            return new_asset
        except Exception as e:
            logger.error(f"Failed to create asset: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_asset_in_service(self, asset_id: int) -> Asset:
        """Get an asset by ID."""
        if asset_id not in self._assets:
            raise HTTPException(status_code=404, detail="Asset not found")
        return self._assets[asset_id]

    async def update_asset_in_service(self, asset_id: int, asset_update: AssetUpdate) -> Asset:
        """Update an existing asset."""
        if asset_id not in self._assets:
            raise HTTPException(status_code=404, detail="Asset not found")

        asset = self._assets[asset_id]
        
        # Update fields if provided
        if asset_update.name is not None:
            asset.name = asset_update.name
        if asset_update.description is not None:
            asset.description = asset_update.description
        if asset_update.asset_type is not None:
            asset.asset_type = asset_update.asset_type
        
        asset.updated_at = datetime.utcnow()
        self._assets[asset_id] = asset
        return asset

    async def delete_asset_in_service(self, asset_id: int) -> None:
        """Delete an asset and its data."""
        if asset_id not in self._assets:
            raise HTTPException(status_code=404, detail="Asset not found")

        try:
            # Get the data layer ID from storage location
            storage_location = self._assets[asset_id].storage_locations[0]
            data_layer_id = storage_location.s3_key.split('/')[-1].replace('.parquet', '')

            # Delete from data layer
            self.data_layer.delete_asset(data_layer_id)

            # Delete from our service
            del self._assets[asset_id]
        except Exception as e:
            logger.error(f"Failed to delete asset: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def list_assets_in_service(self, asset_type: Optional[AssetType] = None) -> List[Asset]:
        """List all assets, optionally filtered by type."""
        assets = list(self._assets.values())
        if asset_type:
            assets = [a for a in assets if a.asset_type == asset_type]
        return assets

    async def store_asset_data_in_service(self, asset_id: int, data: List[Dict[str, Any]], schema: Dict[str, str]) -> None:
        """Store data for an asset in the data layer."""
        if asset_id not in self._assets:
            raise HTTPException(status_code=404, detail="Asset not found")

        try:
            # Get the data layer ID from storage location
            storage_location = self._assets[asset_id].storage_locations[0]
            data_layer_id = storage_location.s3_key.split('/')[-1].replace('.parquet', '')

            # Update data in data layer
            self.data_layer.update_asset(data_layer_id, data, schema)
        except Exception as e:
            logger.error(f"Failed to store asset data: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_asset_data_in_service(self, asset_id: int) -> Dict[str, Any]:
        """Get data for an asset from the data layer."""
        if asset_id not in self._assets:
            raise HTTPException(status_code=404, detail="Asset not found")

        try:
            # Get the data layer ID from storage location
            storage_location = self._assets[asset_id].storage_locations[0]
            data_layer_id = storage_location.s3_key.split('/')[-1].replace('.parquet', '')

            # Get data from data layer
            return self.data_layer.get_asset(data_layer_id)
        except Exception as e:
            logger.error(f"Failed to get asset data: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) 