#!/bin/bash

# Create policy document
cat > flow-logs-policy.json << 'EOL'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:CreateFlowLogs",
                "ec2:DeleteFlowLogs",
                "ec2:DescribeFlowLogs",
                "ec2:DescribeNetworkInterfaces",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "iam:GetRole",
                "iam:CreateRole",
                "iam:PutRolePolicy",
                "iam:PassRole"
            ],
            "Resource": "*"
        }
    ]
}
EOL

# Put the inline policy
aws iam put-role-policy \
    --role-name fortifai-data-layer-s3-access \
    --policy-name FlowLogsAccess \
    --policy-document file://flow-logs-policy.json

# Clean up
rm flow-logs-policy.json 