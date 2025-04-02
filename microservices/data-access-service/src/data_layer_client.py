import httpx
import pandas as pd
from typing import Dict, Any, List, Optional
import logging
from io import BytesIO
import json
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class DataLayerClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"}
        )

    def create_asset(self, asset_type: str, data: List[Dict[str, Any]], schema: Dict[str, str]) -> str:
        """Create a new asset in the data layer."""
        response = self.client.post(
            "/assets",
            json={
                "asset_type": asset_type,
                "data": data,
                "schema": schema
            }
        )
        response.raise_for_status()
        return response.json()["asset_id"]

    def get_asset(self, asset_id: str) -> Dict[str, Any]:
        """Get an asset from the data layer."""
        response = self.client.get(f"/assets/{asset_id}")
        response.raise_for_status()
        return response.json()

    def update_asset(self, asset_id: str, data: List[Dict[str, Any]], schema: Optional[Dict[str, str]] = None) -> None:
        """Update an existing asset in the data layer."""
        payload = {"data": data}
        if schema is not None:
            payload["schema"] = schema
            
        response = self.client.put(
            f"/assets/{asset_id}",
            json=payload
        )
        response.raise_for_status()

    def delete_asset(self, asset_id: str) -> None:
        """Delete an asset from the data layer."""
        response = self.client.delete(f"/assets/{asset_id}")
        response.raise_for_status()

    def list_assets_by_type(self, asset_type: str) -> List[Dict[str, Any]]:
        """List all assets of a specific type."""
        response = self.client.get(f"/assets/type/{asset_type}")
        response.raise_for_status()
        return response.json()["assets"]

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def _ensure_authenticated(self):
        if not self.token:
            response = self.client.post("/token", params={
                "username": "development",
                "password": "development"
            })
            response.raise_for_status()
            self.token = response.json()["access_token"]
            self.client.headers["Authorization"] = f"Bearer {self.token}"

    def read_assets(self, asset_type: str) -> pd.DataFrame:
        """Read assets from the data layer."""
        try:
            self._ensure_authenticated()
            response = self.client.get(f"/data/type/{asset_type}")
            response.raise_for_status()
            data = response.json()
            return pd.DataFrame(data["data"])
        except Exception as e:
            logger.error(f"Error reading assets from data layer: {str(e)}")
            raise

    def write_assets(self, asset_type: str, assets: List[Dict[str, Any]]) -> None:
        """Write assets to the data layer."""
        try:
            self._ensure_authenticated()
            
            # Convert assets to DataFrame
            df = pd.DataFrame(assets)
            
            # Convert DataFrame to CSV for upload
            csv_buffer = BytesIO()
            
            # Convert any ObjectDType columns to string
            for col in df.columns:
                if pd.api.types.is_object_dtype(df[col]):
                    df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, (dict, list)) else str(x) if x is not None else None)
            
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            
            # Prepare metadata
            metadata = {
                "data_id": asset_type,
                "schema": {k: str(v) for k, v in df.dtypes.to_dict().items()},  # Convert dtypes to strings
                "row_count": len(df),
                "created_at": pd.Timestamp.now().isoformat(),
                "updated_at": pd.Timestamp.now().isoformat()
            }
            
            # Upload data
            files = {"file": ("data.csv", csv_buffer, "text/csv")}
            response = self.client.post(
                f"/data/type/{asset_type}",
                files=files,
                data={"metadata": json.dumps(metadata)}
            )
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Error writing assets to data layer: {str(e)}")
            raise

    def batch_create_assets(self, asset_type: str, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple assets in a single operation."""
        try:
            # Read existing assets
            existing_df = self.read_assets(asset_type)
            
            # Convert new assets to DataFrame
            new_df = pd.DataFrame(assets)
            
            # Check for duplicate UniqueIds
            if not existing_df.empty and not new_df.empty:
                duplicate_ids = set(new_df['UniqueId']) & set(existing_df['UniqueId'])
                if duplicate_ids:
                    raise ValueError(f"Duplicate UniqueIds found: {duplicate_ids}")
            
            # Combine existing and new assets
            if existing_df.empty:
                combined_df = new_df
            elif new_df.empty:
                combined_df = existing_df
            else:
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            
            # Write the combined DataFrame back
            self.write_assets(asset_type, combined_df.to_dict('records'))
            
            return new_df.to_dict('records')
            
        except Exception as e:
            logger.error(f"Error in batch_create_assets: {str(e)}")
            raise

    def batch_update_assets(self, asset_type: str, updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Update multiple assets in a single operation."""
        try:
            # Read existing assets
            existing_df = self.read_assets(asset_type)
            
            # Create a new DataFrame for the updates
            update_df = pd.DataFrame(updates)
            
            # Check if all assets exist
            if not existing_df.empty and not update_df.empty:
                missing_ids = set(update_df['UniqueId']) - set(existing_df['UniqueId'])
                if missing_ids:
                    raise ValueError(f"Assets not found: {missing_ids}")
            
            # If either DataFrame is empty, handle appropriately
            if existing_df.empty:
                return updates
            elif update_df.empty:
                return []
            
            # Create a mask for rows to update
            mask = existing_df['UniqueId'].isin(update_df['UniqueId'])
            
            # Create a new DataFrame with non-matching rows
            non_matching_df = existing_df[~mask].copy()
            
            # Update matching rows
            for idx, row in update_df.iterrows():
                existing_df.loc[existing_df['UniqueId'] == row['UniqueId']] = row
            
            # Combine updated and non-matching rows
            combined_df = pd.concat([non_matching_df, existing_df[mask]], ignore_index=True)
            
            # Write the combined DataFrame back
            self.write_assets(asset_type, combined_df.to_dict('records'))
            
            return update_df.to_dict('records')
            
        except Exception as e:
            logger.error(f"Error in batch_update_assets: {str(e)}")
            raise

    def batch_delete_assets(self, asset_type: str, asset_ids: List[str]) -> List[str]:
        """Delete multiple assets in a single operation."""
        try:
            # Read existing assets
            existing_df = self.read_assets(asset_type)
            
            # Check if all assets exist
            if not existing_df.empty:
                missing_ids = set(asset_ids) - set(existing_df['UniqueId'])
                if missing_ids:
                    raise ValueError(f"Assets not found: {missing_ids}")
            
            # Create a new DataFrame without the deleted assets
            remaining_df = existing_df[~existing_df['UniqueId'].isin(asset_ids)]
            
            # Write the remaining DataFrame back
            self.write_assets(asset_type, remaining_df.to_dict('records'))
            
            return asset_ids
            
        except Exception as e:
            logger.error(f"Error in batch_delete_assets: {str(e)}")
            raise 