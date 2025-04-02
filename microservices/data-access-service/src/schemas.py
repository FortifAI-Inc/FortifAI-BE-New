from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

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

class StorageLocationBase(BaseModel):
    s3_bucket: str
    s3_key: str
    file_format: str

class StorageLocationCreate(StorageLocationBase):
    pass

class StorageLocation(StorageLocationBase):
    id: int
    asset_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AssetBase(BaseModel):
    """Base model for asset attributes."""
    asset_type: AssetType
    unique_id: str
    name: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_stale: bool = False
    tags: Dict[str, str] = Field(default_factory=dict)

class AssetCreate(AssetBase):
    """Schema for creating a new asset."""
    pass

class AssetUpdate(BaseModel):
    """Schema for updating an existing asset."""
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    is_stale: Optional[bool] = None
    tags: Optional[Dict[str, str]] = None

class Asset(AssetBase):
    """Schema for an asset with additional fields."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Asset-specific schemas
class VPC(BaseModel):
    """Schema for VPC asset data."""
    vpc_id: str
    cidr_block: str
    state: str
    is_default: bool = False
    tags: Dict[str, str] = Field(default_factory=dict)

class Subnet(BaseModel):
    """Schema for Subnet asset data."""
    subnet_id: str
    vpc_id: str
    cidr_block: str
    availability_zone: str
    state: str
    map_public_ip_on_launch: bool = False
    tags: Dict[str, str] = Field(default_factory=dict)

class EC2(BaseModel):
    """Schema for EC2 instance asset data."""
    instance_id: str
    instance_type: str
    state: str
    private_ip: str
    public_ip: Optional[str] = None
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    security_groups: List[str] = Field(default_factory=list)
    tags: Dict[str, str] = Field(default_factory=dict)

class S3(BaseModel):
    """Schema for S3 bucket asset data."""
    bucket_name: str
    region: str
    creation_date: datetime
    tags: Dict[str, str] = Field(default_factory=dict)

class IAMRole(BaseModel):
    """Schema for IAM role asset data."""
    role_name: str
    role_id: str
    arn: str
    path: str
    assume_role_policy: Dict[str, Any]
    tags: Dict[str, str] = Field(default_factory=dict)

class SecurityGroup(BaseModel):
    """Schema for Security Group asset data."""
    group_id: str
    group_name: str
    vpc_id: str
    description: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)

class User(BaseModel):
    """Schema for IAM user asset data."""
    user_name: str
    user_id: str
    arn: str
    path: str
    tags: Dict[str, str] = Field(default_factory=dict)

class IGW(BaseModel):
    """Schema for Internet Gateway asset data."""
    internet_gateway_id: str
    vpc_id: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)

class NI(BaseModel):
    """Schema for Network Interface asset data."""
    network_interface_id: str
    vpc_id: str
    subnet_id: Optional[str] = None
    description: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)

class Lambda(BaseModel):
    """Schema for Lambda function asset data."""
    function_name: str
    runtime: str
    handler: str
    role: str
    last_modified: str
    tags: Dict[str, str] = Field(default_factory=dict)

class IAMPolicy(BaseModel):
    """Schema for IAM policy asset data."""
    policy_id: str
    policy_name: str
    path: str
    arn: str
    tags: Dict[str, str] = Field(default_factory=dict)

# Mapping of asset types to their corresponding schema classes
ASSET_TYPE_SCHEMAS = {
    AssetType.VPC: VPC,
    AssetType.SUBNET: Subnet,
    AssetType.EC2: EC2,
    AssetType.S3: S3,
    AssetType.IAM_ROLE: IAMRole,
    AssetType.SECURITY_GROUP: SecurityGroup,
    AssetType.USER: User,
    AssetType.IGW: IGW,
    AssetType.NI: NI,
    AssetType.LAMBDA: Lambda,
    AssetType.IAM_POLICY: IAMPolicy
} 