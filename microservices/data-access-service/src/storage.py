import os
import json
import pandas as pd
import httpx
import logging
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field
from .schemas import AssetType, ASSET_TYPE_SCHEMAS
from .data_layer_client import DataLayerClient
from datetime import datetime
from fastapi import HTTPException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Storage:
    def __init__(self, data_layer_url: str):
        # Using a default token for development
        self.data_layer_client = DataLayerClient(data_layer_url, token="development")

    def read_assets(self, asset_type: AssetType) -> pd.DataFrame:
        """Read all assets of a specific type from the data layer."""
        try:
            return self.data_layer_client.read_assets(asset_type.value)
        except Exception as e:
            logger.error(f"Error reading assets: {str(e)}")
            raise

    def write_assets(self, asset_type: AssetType, assets: List[Dict[str, Any]]) -> None:
        """Write assets to the data layer."""
        try:
            self.data_layer_client.write_assets(asset_type.value, assets)
            logger.info(f"Successfully wrote {len(assets)} assets")
        except Exception as e:
            logger.error(f"Error writing assets: {str(e)}")
            raise

    def batch_create_assets(self, asset_type: AssetType, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple assets in a single operation."""
        try:
            return self.data_layer_client.batch_create_assets(asset_type.value, assets)
        except Exception as e:
            logger.error(f"Error in batch_create_assets: {str(e)}")
            raise

    def batch_update_assets(self, asset_type: AssetType, updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Update multiple assets in a single operation."""
        try:
            return self.data_layer_client.batch_update_assets(asset_type.value, updates)
        except Exception as e:
            logger.error(f"Error in batch_update_assets: {str(e)}")
            raise

    def batch_delete_assets(self, asset_type: AssetType, asset_ids: List[str]) -> List[str]:
        """Delete multiple assets in a single operation."""
        try:
            return self.data_layer_client.batch_delete_assets(asset_type.value, asset_ids)
        except Exception as e:
            logger.error(f"Error in batch_delete_assets: {str(e)}")
            raise 