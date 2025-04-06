#!/usr/bin/env python3
import requests
import json
import sys
import urllib3

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API Gateway URL
API_GATEWAY_URL = "https://a12c65672e20e491e83c7a13c5662714-1758004955.eu-north-1.elb.amazonaws.com"

def test_sandbox_enforcer():
    """
    Test the sandbox-enforcer endpoint with a bogus instance ID.
    """
    # Bogus instance ID
    instance_id = "i-1234567890abcdef0"
    
    # Endpoint URL
    url = f"{API_GATEWAY_URL}/api/sandbox-enforcer/relocate-ec2"
    
    # Request payload
    payload = {
        "instance_id": instance_id
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer development_token"
    }
    
    print(f"Making request to: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    
    try:
        # Make the request with SSL verification disabled
        response = requests.post(url, json=payload, headers=headers, verify=False)
        
        # Print response details
        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {json.dumps(dict(response.headers), indent=2)}")
        
        try:
            print(f"Response body: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response body: {response.text}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_sandbox_enforcer() 