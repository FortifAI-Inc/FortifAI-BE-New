import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from fastapi import HTTPException
from ..src.service import DataAccessService
from ..src.schemas import AssetCreate, AssetUpdate, AssetType, EC2Schema, Asset, StorageLocation

@pytest.fixture
def mock_data_layer():
    with patch('data_access_service.service.DataLayerClient') as mock:
        client = Mock()
        client.create_asset.return_value = "asset_123"
        client.get_asset.return_value = {
            "data": [
                {
                    "UniqueId": "i-123",
                    "InstanceId": "i-123",
                    "InstanceType": "t2.micro",
                    "State": "running",
                    "VpcId": "vpc-123",
                    "SubnetId": "subnet-123",
                    "SecurityGroups": ["sg-123"],
                    "Tags": {"Name": "test"}
                }
            ],
            "metadata": {
                "asset_id": "asset_123",
                "asset_type": "ec2",
                "schema": {"InstanceId": "str", "InstanceType": "str"},
                "row_count": 1,
                "created_at": "2024-03-30 12:00:00",
                "updated_at": "2024-03-30 12:00:00"
            }
        }
        mock.return_value = client
        yield client

@pytest.fixture
def service(mock_data_layer):
    return DataAccessService(
        data_layer_url="http://data-layer",
        data_layer_token="test_token"
    )

@pytest.fixture
def sample_ec2_asset():
    return Asset(
        id=1,
        name="Test EC2",
        description="Test EC2 instance",
        asset_type=AssetType.EC2,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        storage_locations=[
            StorageLocation(
                id=1,
                asset_id=1,
                s3_bucket="fortifai-data",
                s3_key="data/asset_123.parquet",
                file_format="parquet",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
    )

async def test_create_asset(service, mock_data_layer):
    asset_create = AssetCreate(
        name="Test EC2",
        description="Test EC2 instance",
        asset_type=AssetType.EC2
    )
    
    asset = await service.create_asset(asset_create)
    
    assert asset.name == "Test EC2"
    assert asset.description == "Test EC2 instance"
    assert asset.asset_type == AssetType.EC2
    assert len(asset.storage_locations) == 1
    assert asset.storage_locations[0].s3_key == "data/asset_123.parquet"
    
    mock_data_layer.create_asset.assert_called_once_with(
        asset_type=AssetType.EC2,
        data=[],
        schema={}
    )

async def test_get_asset(service, sample_ec2_asset):
    service._assets[1] = sample_ec2_asset
    
    asset = await service.get_asset(1)
    assert asset == sample_ec2_asset

async def test_get_asset_not_found(service):
    with pytest.raises(HTTPException) as exc_info:
        await service.get_asset(1)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Asset not found"

async def test_update_asset(service, sample_ec2_asset):
    service._assets[1] = sample_ec2_asset
    
    asset_update = AssetUpdate(
        name="Updated EC2",
        description="Updated description"
    )
    
    updated_asset = await service.update_asset(1, asset_update)
    
    assert updated_asset.name == "Updated EC2"
    assert updated_asset.description == "Updated description"
    assert updated_asset.asset_type == AssetType.EC2

async def test_delete_asset(service, sample_ec2_asset, mock_data_layer):
    service._assets[1] = sample_ec2_asset
    
    await service.delete_asset(1)
    
    assert 1 not in service._assets
    mock_data_layer.delete_asset.assert_called_once_with("asset_123")

async def test_list_assets(service, sample_ec2_asset):
    service._assets[1] = sample_ec2_asset
    
    assets = await service.list_assets()
    assert len(assets) == 1
    assert assets[0] == sample_ec2_asset
    
    assets = await service.list_assets(asset_type=AssetType.EC2)
    assert len(assets) == 1
    assert assets[0] == sample_ec2_asset
    
    assets = await service.list_assets(asset_type=AssetType.VPC)
    assert len(assets) == 0

async def test_store_asset_data(service, sample_ec2_asset, mock_data_layer):
    service._assets[1] = sample_ec2_asset
    
    data = [
        {
            "UniqueId": "i-123",
            "InstanceId": "i-123",
            "InstanceType": "t2.micro",
            "State": "running",
            "VpcId": "vpc-123",
            "SubnetId": "subnet-123",
            "SecurityGroups": ["sg-123"],
            "Tags": {"Name": "test"}
        }
    ]
    schema = {"InstanceId": "str", "InstanceType": "str"}
    
    await service.store_asset_data(1, data, schema)
    
    mock_data_layer.update_asset.assert_called_once_with(
        "asset_123",
        data,
        schema
    )

async def test_get_asset_data(service, sample_ec2_asset, mock_data_layer):
    service._assets[1] = sample_ec2_asset
    
    data = await service.get_asset_data(1)
    
    assert data["data"][0]["InstanceId"] == "i-123"
    assert data["metadata"]["asset_type"] == "ec2"
    
    mock_data_layer.get_asset.assert_called_once_with("asset_123") 