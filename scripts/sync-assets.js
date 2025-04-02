const { EC2Client, DescribeInstancesCommand, DescribeVpcsCommand, DescribeSubnetsCommand, DescribeSecurityGroupsCommand, DescribeInternetGatewaysCommand } = require('@aws-sdk/client-ec2');
const { S3Client, ListBucketsCommand, GetBucketLocationCommand } = require('@aws-sdk/client-s3');
const { IAMClient, ListRolesCommand, ListUsersCommand, ListPoliciesCommand } = require('@aws-sdk/client-iam');
const { CloudWatchClient, ListMetricsCommand } = require('@aws-sdk/client-cloudwatch');
const { KMSClient, ListKeysCommand } = require('@aws-sdk/client-kms');
const axios = require('axios');
const https = require('https');

// AWS Configuration
const region = 'eu-north-1';
const ec2Client = new EC2Client({ region });
const s3Client = new S3Client({ region });
const iamClient = new IAMClient({ region });
const cloudwatchClient = new CloudWatchClient({ region });
const kmsClient = new KMSClient({ region });

// API Configuration
const API_BASE_URL = 'https://a12c65672e20e491e83c7a13c5662714-1758004955.eu-north-1.elb.amazonaws.com';

// Create HTTPS agent with proper configuration
const httpsAgent = new https.Agent({
    rejectUnauthorized: false, // Accept self-signed certificates
    keepAlive: true,
    timeout: 60000
});

// Create axios instance with proper configuration
const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json'
    },
    httpsAgent
});

// Create a separate axios instance for authentication
const authClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
    },
    httpsAgent
});

let isAuthenticating = false;

// Authentication function
async function authenticate() {
    try {
        console.log('Authenticating with API...');
        const formData = new URLSearchParams();
        formData.append('username', 'development');
        formData.append('password', 'development');
        
        const response = await authClient.post('/token', formData);
        
        if (!response.data || !response.data.access_token) {
            throw new Error('Invalid authentication response');
        }
        
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${response.data.access_token}`;
        console.log('Authentication successful');
    } catch (error) {
        console.error('Authentication failed:', error.message);
        throw error;
    }
}

// Add request interceptor to handle 401 errors
apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        if (error.response?.status === 401 && !originalRequest._retry && !isAuthenticating) {
            originalRequest._retry = true;
            try {
                await authenticate();
                return apiClient(originalRequest);
            } catch (authError) {
                console.error('Re-authentication failed:', authError.message);
                throw authError;
            }
        }
        throw error;
    }
);

// Utility function to convert AWS tags to our format
const convertTags = (awsTags) => {
    if (!awsTags) return {};
    return awsTags.reduce((acc, tag) => {
        acc[tag.Key] = tag.Value;
        return acc;
    }, {});
};

// Asset Type Enum
const AssetType = {
    EC2: 'ec2',
    VPC: 'vpc',
    Subnet: 'subnet',
    SecurityGroup: 'sg',
    S3: 's3',
    IAMRole: 'iam_role',
    IAMUser: 'user',
    IAMPolicy: 'iam_policy',
    KMSKey: 'kms_key',
    CloudWatchMetric: 'cloudwatch_metric',
    IGW: 'igw'
};

// Generic sync function with pagination and chunking
async function syncAssets(assetType, getAwsAssets) {
    try {
        console.log(`[${assetType}] Starting sync process...`);
        
        // Get current assets from database first
        console.log(`[${assetType}] Fetching existing assets from database...`);
        const dbAssets = [];
        let page = 1;
        const pageSize = 100; 
        let hasMoreData = true;
        
        while (hasMoreData) {
            try {
                console.log(`[${assetType}] Fetching page ${page}...`);
                const response = await apiClient.get(`/api/data-access/assets/type/${assetType}`, {
                    params: { page, limit: pageSize },
                    timeout: 5000 // 5 second timeout per request
                });
                
                const responseData = response.data;
                if (!responseData || !Array.isArray(responseData) || responseData.length === 0) {
                    console.log(`[${assetType}] No more assets found on page ${page}`);
                    hasMoreData = false;
                    break;
                }
                
                console.log(`[${assetType}] Received ${responseData.length} assets on page ${page}`);
                dbAssets.push(...responseData);
                
                // If we received fewer assets than the page size, we've reached the end
                if (responseData.length < pageSize) {
                    hasMoreData = false;
                } else {
                    page++;
                }
            } catch (error) {
                // Error handling
                hasMoreData = false;
                break;
            }
        }

        console.log(`[${assetType}] Total assets from DB: ${dbAssets.length}`);

        // Create a map of existing assets by UniqueId
        const existingAssets = new Map(dbAssets.map(asset => [asset.UniqueId, asset]));

        // Process AWS assets as we get them
        let nextToken = null;
        let processedCount = 0;
        let allAwsAssets = [];
        let batchSize = 5; // Reduced batch size for debugging
        let currentBatch = [];
        
        do {
            const { assets, token } = await getAwsAssets(nextToken);
            nextToken = token;
            allAwsAssets = allAwsAssets.concat(assets);
            
            // Process this batch of assets
            for (const awsAsset of assets) {
                try {
                    currentBatch.push(awsAsset);
                    if (currentBatch.length >= batchSize) {
                        // The exact URL path is a problem - use the raw asset type value
                        const apiPath = `/api/data-access/assets/${assetType.toLowerCase()}/batch`;
                        
                        try {
                            const response = await apiClient.post(apiPath, {
                                assets: currentBatch
                            });
                            console.log(`[${assetType}] Processed batch of ${currentBatch.length} assets`);
                        } catch (error) {
                            console.error(`[${assetType}] Batch creation error:`, error.message);
                            if (error.response) {
                                console.error(`[${assetType}] Response status:`, error.response.status);
                                console.error(`[${assetType}] Response data:`, JSON.stringify(error.response.data, null, 2));
                            }
                            throw error;
                        }
                        
                        currentBatch = [];
                    }
                    processedCount++;
                } catch (error) {
                    console.error(`[${assetType}] Error processing batch:`, error.message);
                    throw error;
                }
            }
            
            console.log(`[${assetType}] Processed ${processedCount} assets from AWS...`);
        } while (nextToken);
        
        // Process any remaining assets in the last batch
        if (currentBatch.length > 0) {
            try {
                console.log(`[${assetType}] Sending final batch of ${currentBatch.length} assets to API`);
                
                // The exact URL path is a problem - use the raw asset type value
                const apiPath = `/api/data-access/assets/${assetType.toLowerCase()}/batch`;
                
                try {
                    await apiClient.post(apiPath, {
                        assets: currentBatch
                    });
                    console.log(`[${assetType}] Processed final batch of ${currentBatch.length} assets`);
                } catch (error) {
                    console.error(`[${assetType}] Final batch creation error:`, error.message);
                    if (error.response) {
                        console.error(`[${assetType}] Response status:`, error.response.status);
                        console.error(`[${assetType}] Response data:`, JSON.stringify(error.response.data, null, 2));
                    }
                    throw error;
                }
            } catch (error) {
                console.error(`[${assetType}] Error processing final batch:`, error.message);
                throw error;
            }
        }

        // Find and mark stale assets
        const staleAssets = Array.from(existingAssets.values()).filter(dbAsset => 
            !allAwsAssets.some(awsAsset => awsAsset.UniqueId === dbAsset.UniqueId)
        );

        if (staleAssets.length > 0) {
            const chunkSize = 50;
            for (let i = 0; i < staleAssets.length; i += chunkSize) {
                const chunk = staleAssets.slice(i, i + chunkSize);
                try {
                    await apiClient.post(`/api/data-access/${assetType}/stale`, 
                        chunk.map(asset => asset.UniqueId)
                    );
                    console.log(`Marked ${chunk.length} ${assetType} assets as stale`);
                } catch (error) {
                    console.error(`Error marking stale ${assetType} assets:`, error.message);
                    throw error;
                }
            }
        }

        console.log(`Completed sync for ${assetType}`);
    } catch (error) {
        console.error(`[${assetType}] Error in sync process:`, error.message);
        throw error;
    }
}

// AWS Asset Fetch Functions with pagination
async function getEC2Instances(nextToken = null) {
    const params = { MaxResults: 100 };
    if (nextToken) params.NextToken = nextToken;
    
    const data = await ec2Client.send(new DescribeInstancesCommand(params));
    
    const instances = data.Reservations.flatMap(reservation => 
        reservation.Instances.map(instance => {
            return {
                asset_type: 'ec2',
                unique_id: instance.InstanceId,
                name: instance.Tags?.find(tag => tag.Key === 'Name')?.Value || instance.InstanceId,
                description: `EC2 Instance ${instance.InstanceId}`,
                metadata: {
                    vpc_id: instance.VpcId || null,
                    VpcId: instance.VpcId || null,
                    subnet_id: instance.SubnetId || null,
                    SubnetId: instance.SubnetId || null,
                    security_groups: instance.SecurityGroups?.map(sg => sg.GroupId) || []
                },
                is_stale: false,
                tags: convertTags(instance.Tags),
                // EC2-specific fields at root level
                instance_id: instance.InstanceId,
                instance_type: instance.InstanceType,
                state: instance.State.Name,
                private_ip: instance.PrivateIpAddress,
                public_ip: instance.PublicIpAddress || null
            };
        })
    );
    
    return {
        assets: instances,
        token: data.NextToken
    };
}

async function getVPCs(nextToken = null) {
    const params = { MaxResults: 100 };
    if (nextToken) params.NextToken = nextToken;
    
    const data = await ec2Client.send(new DescribeVpcsCommand(params));
    
    const vpcs = data.Vpcs.map(vpc => {
        return {
            asset_type: 'vpc',
            unique_id: vpc.VpcId,
            name: vpc.Tags?.find(tag => tag.Key === 'Name')?.Value || vpc.VpcId,
            description: `VPC ${vpc.VpcId}`,
            metadata: {
                cidr_block: vpc.CidrBlock,
                state: vpc.State,
                is_default: vpc.IsDefault,
                unique_id: vpc.VpcId,
                vpc_id: vpc.VpcId
            },
            is_stale: false,
            tags: convertTags(vpc.Tags)
        };
    });
    
    return {
        assets: vpcs,
        token: data.NextToken
    };
}

async function getSubnets(nextToken = null) {
    const params = { MaxResults: 100 };
    if (nextToken) params.NextToken = nextToken;
    
    const data = await ec2Client.send(new DescribeSubnetsCommand(params));
    
    const subnets = data.Subnets.map(subnet => {
        return {
            asset_type: 'subnet',
            unique_id: subnet.SubnetId,
            name: subnet.Tags?.find(tag => tag.Key === 'Name')?.Value || subnet.SubnetId,
            description: `Subnet ${subnet.SubnetId}`,
            metadata: {
                vpc_id: subnet.VpcId,
                cidr_block: subnet.CidrBlock,
                availability_zone: subnet.AvailabilityZone,
                state: subnet.State,
                map_public_ip_on_launch: subnet.MapPublicIpOnLaunch
            },
            is_stale: false,
            tags: convertTags(subnet.Tags)
        };
    });
    
    return {
        assets: subnets,
        token: data.NextToken
    };
}

async function getSecurityGroups(nextToken = null) {
    const params = { MaxResults: 100 };
    if (nextToken) params.NextToken = nextToken;
    
    const data = await ec2Client.send(new DescribeSecurityGroupsCommand(params));
    
    const sgs = data.SecurityGroups.map(sg => {
        return {
            asset_type: 'sg',
            unique_id: sg.GroupId,
            name: sg.GroupName,
            description: sg.Description,
            metadata: {
                group_id: sg.GroupId,
                vpc_id: sg.VpcId
            },
            is_stale: false,
            tags: convertTags(sg.Tags)
        };
    });
    
    return {
        assets: sgs,
        token: data.NextToken
    };
}

async function getS3Buckets() {
    const data = await s3Client.send(new ListBucketsCommand({}));
    
    // Since S3 doesn't have pagination for bucket listing
    const buckets = await Promise.all(data.Buckets.map(async bucket => {
        let region = 'unknown';
        
        try {
            const locationResponse = await s3Client.send(
                new GetBucketLocationCommand({ Bucket: bucket.Name })
            );
            region = locationResponse.LocationConstraint || 'us-east-1';
        } catch (error) {
            console.warn(`Could not determine region for bucket ${bucket.Name}: ${error.message}`);
        }
        
        return {
            asset_type: 's3',
            unique_id: bucket.Name,
            name: bucket.Name,
            description: `S3 Bucket ${bucket.Name}`,
            metadata: {
                region: region,
                creation_date: bucket.CreationDate.toISOString()
            },
            is_stale: false,
            tags: {} // We would need to fetch tags separately per bucket
        };
    }));
    
    return {
        assets: buckets,
        token: null // No pagination for S3 bucket listing
    };
}

async function getIAMRoles(marker = null) {
    const params = { MaxItems: 100 };
    if (marker) params.Marker = marker;
    
    const data = await iamClient.send(new ListRolesCommand(params));
    
    const roles = data.Roles.map(role => {
        return {
            asset_type: 'iam_role',
            unique_id: role.RoleId,
            name: role.RoleName,
            description: `IAM Role ${role.RoleName}`,
            metadata: {
                path: role.Path,
                arn: role.Arn
            },
            is_stale: false,
            tags: convertTags(role.Tags)
        };
    });
    
    return {
        assets: roles,
        token: data.Marker
    };
}

async function getIAMUsers(marker = null) {
    const params = { MaxItems: 100 };
    if (marker) params.Marker = marker;
    
    const data = await iamClient.send(new ListUsersCommand(params));
    
    const users = data.Users.map(user => {
        return {
            asset_type: 'user',
            unique_id: user.UserId,
            name: user.UserName,
            description: `IAM User ${user.UserName}`,
            metadata: {
                path: user.Path,
                arn: user.Arn
            },
            is_stale: false,
            tags: convertTags(user.Tags)
        };
    });
    
    return {
        assets: users,
        token: data.Marker
    };
}

async function getIAMPolicies(marker = null) {
    const params = { MaxItems: 100, Scope: 'Local' }; // Only get customer managed policies
    if (marker) params.Marker = marker;
    
    const data = await iamClient.send(new ListPoliciesCommand(params));
    
    const policies = data.Policies.map(policy => {
        return {
            asset_type: 'iam_policy',
            unique_id: policy.PolicyId,
            name: policy.PolicyName,
            description: `IAM Policy ${policy.PolicyName}`,
            metadata: {
                path: policy.Path,
                arn: policy.Arn
            },
            is_stale: false,
            tags: {} // Would need to fetch tags separately
        };
    });
    
    return {
        assets: policies,
        token: data.Marker
    };
}

async function getKMSKeys(nextToken = null) {
    const params = { Limit: 100 };
    if (nextToken) params.Marker = nextToken;
    
    const data = await kmsClient.send(new ListKeysCommand(params));
    return {
        assets: data.Keys.map(key => ({
            asset_type: 'kms_key',
            unique_id: key.KeyId,
            name: key.KeyId,
            description: `KMS Key ${key.KeyId}`,
            metadata: {
                arn: key.KeyArn
            },
            is_stale: false,
            tags: {}
        })),
        token: data.NextMarker
    };
}

async function getCloudWatchMetrics(nextToken = null) {
    const params = {};
    if (nextToken) params.NextToken = nextToken;
    
    const data = await cloudwatchClient.send(new ListMetricsCommand(params));
    return {
        assets: data.Metrics.map(metric => ({
            asset_type: 'cloudwatch_metric',
            unique_id: `${metric.Namespace}-${metric.MetricName}`,
            name: metric.MetricName,
            description: `CloudWatch Metric ${metric.MetricName} in namespace ${metric.Namespace}`,
            metadata: {
                namespace: metric.Namespace,
                dimensions: metric.Dimensions,
                unit: metric.Unit,
                statistic: 'Average'
            },
            is_stale: false,
            tags: {}
        })),
        token: data.NextToken
    };
}

async function getIGWs(nextToken = null) {
    const params = { MaxResults: 100 };
    if (nextToken) params.NextToken = nextToken;
    
    const data = await ec2Client.send(new DescribeInternetGatewaysCommand(params));
    
    const igws = data.InternetGateways.map(igw => {
        return {
            asset_type: 'igw',
            unique_id: igw.InternetGatewayId,
            name: igw.Tags?.find(tag => tag.Key === 'Name')?.Value || igw.InternetGatewayId,
            description: `Internet Gateway ${igw.InternetGatewayId}`,
            metadata: {
                internet_gateway_id: igw.InternetGatewayId,
                state: igw.State,
                vpc_id: igw.Attachments?.[0]?.VpcId || null,
                VpcId: igw.Attachments?.[0]?.VpcId || null
            },
            is_stale: false,
            tags: convertTags(igw.Tags)
        };
    });
    
    return {
        assets: igws,
        token: data.NextToken
    };
}

// Main
async function main() {
    try {
        console.log('Starting main sync process...');
        await authenticate();
        
        await syncAssets(AssetType.VPC, getVPCs);
        await syncAssets(AssetType.Subnet, getSubnets);
        await syncAssets(AssetType.SecurityGroup, getSecurityGroups);
        await syncAssets(AssetType.EC2, getEC2Instances);
        await syncAssets(AssetType.S3, getS3Buckets);
        await syncAssets(AssetType.IAMRole, getIAMRoles);
        await syncAssets(AssetType.IAMUser, getIAMUsers);
        await syncAssets(AssetType.IAMPolicy, getIAMPolicies);
        await syncAssets(AssetType.IGW, getIGWs);
        
        console.log('All assets synced successfully');
    } catch (error) {
        console.error('Sync failed:', error.message);
        process.exit(1);
    }
}

// Start the sync process
console.log('Script starting...');
main().catch(error => {
    console.error('Unhandled error:', error);
    process.exit(1);
}); 