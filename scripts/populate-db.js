const axios = require('axios');

const API_BASE_URL = 'http://localhost:8080';

async function createEC2Asset() {
    try {
        const response = await axios.post(`${API_BASE_URL}/assets/EC2`, {
            UniqueId: "ec2-123",
            IsStale: false,
            Tags: {
                Name: "production-server",
                Environment: "prod"
            },
            InstanceId: "i-1234567890abcdef0",
            InstanceType: "t2.micro",
            State: "running",
            VpcId: "vpc-12345678",
            SubnetId: "subnet-12345678"
        });
        console.log('Created EC2 asset:', response.data);
    } catch (error) {
        console.error('Error creating EC2 asset:', error.message);
    }
}

async function createVPCAsset() {
    try {
        const response = await axios.post(`${API_BASE_URL}/assets/VPC`, {
            UniqueId: "vpc-123",
            IsStale: false,
            Tags: {
                Name: "main-vpc",
                Environment: "prod"
            },
            VpcId: "vpc-12345678",
            CidrBlock: "10.0.0.0/16",
            State: "available",
            IsDefault: false
        });
        console.log('Created VPC asset:', response.data);
    } catch (error) {
        console.error('Error creating VPC asset:', error.message);
    }
}

async function createS3Asset() {
    try {
        const response = await axios.post(`${API_BASE_URL}/assets/S3`, {
            UniqueId: "s3-123",
            IsStale: false,
            Tags: {
                Name: "data-bucket",
                Environment: "prod"
            },
            BucketName: "my-data-bucket",
            Region: "eu-north-1",
            CreationDate: new Date().toISOString(),
            VersioningEnabled: true
        });
        console.log('Created S3 asset:', response.data);
    } catch (error) {
        console.error('Error creating S3 asset:', error.message);
    }
}

async function createIAMRoleAsset() {
    try {
        const response = await axios.post(`${API_BASE_URL}/assets/IAMRole`, {
            UniqueId: "iam-role-123",
            IsStale: false,
            Tags: {
                Name: "lambda-execution-role",
                Environment: "prod"
            },
            RoleName: "lambda-execution-role",
            Arn: "arn:aws:iam::123456789012:role/lambda-execution-role",
            CreateDate: new Date().toISOString(),
            AssumeRolePolicyDocument: {
                Version: "2012-10-17",
                Statement: [
                    {
                        Effect: "Allow",
                        Principal: {
                            Service: "lambda.amazonaws.com"
                        },
                        Action: "sts:AssumeRole"
                    }
                ]
            }
        });
        console.log('Created IAM Role asset:', response.data);
    } catch (error) {
        console.error('Error creating IAM Role asset:', error.message);
    }
}

async function createCloudWatchMetricAsset() {
    try {
        const response = await axios.post(`${API_BASE_URL}/assets/CloudWatchMetric`, {
            UniqueId: "cw-metric-123",
            IsStale: false,
            Tags: {
                Name: "cpu-utilization",
                Environment: "prod"
            },
            MetricName: "CPUUtilization",
            Namespace: "AWS/EC2",
            Dimensions: [
                {
                    Name: "InstanceId",
                    Value: "i-1234567890abcdef0"
                }
            ],
            Unit: "Percent",
            Statistic: "Average"
        });
        console.log('Created CloudWatch Metric asset:', response.data);
    } catch (error) {
        console.error('Error creating CloudWatch Metric asset:', error.message);
    }
}

async function main() {
    console.log('Starting database population...');
    
    // Create assets in sequence
    await createEC2Asset();
    await createVPCAsset();
    await createS3Asset();
    await createIAMRoleAsset();
    await createCloudWatchMetricAsset();
    
    console.log('Database population completed!');
}

// Run the script
main().catch(console.error); 