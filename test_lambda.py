import json
import os
import traceback
import sys
from dotenv import load_dotenv
from lambda_function import lambda_handler
import requests

def test_connectivity(api_key):

    try:
        print("Testing API connectivity...")
        url = "https://api.twelvelabs.io/v1.3/indexes"
        headers = {"x-api-key": api_key}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("API connectivity test successful!")
            return True, "API connectivity successful"
        else:
            error_msg = f"API test failed with status code {response.status_code}: {response.text}"
            print(error_msg)
            return False, error_msg
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Connection error: {str(e)}"
        print(error_msg)
        return False, error_msg

def test_video_exists(api_key, video_id):

    try:
        print(f"Checking if video {video_id} exists...")
        url = f"https://api.twelvelabs.io/v1.3/indexes"
        headers = {"x-api-key": api_key}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return False, f"Failed to retrieve indexes: {response.status_code}"
        
        indexes = response.json().get('data', [])
        
        for index in indexes:
            index_id = index.get('_id')
            
            video_url = f"https://api.twelvelabs.io/v1.3/indexes/{index_id}/videos/{video_id}"
            video_response = requests.get(video_url, headers=headers, timeout=10)
            
            if video_response.status_code == 200:
                print(f"Video found in index: {index_id}")
                return True, f"Video exists in index {index_id}"
        
        error_msg = f"Video {video_id} not found in any index"
        print(error_msg)
        return False, error_msg
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Error checking video existence: {str(e)}"
        print(error_msg)
        return False, error_msg

def print_structured_data(data):

    print("\nStructured Data Summary")
    print("-" * 50)

    for key in ["Shot", "Action"]:
        if key in data:
            print(f"{key}: {data[key]}")
    

    if "Subject" in data:
        subject = data["Subject"]
        print("\nSubject:")
        for subkey, value in subject.items():
            if value: 
                print(f"  - {subkey}: {value}")
    
    if "Environment" in data:
        env = data["Environment"]
        print("\nEnvironment:")
        for subkey, value in env.items():
            if value: 
                print(f"  - {subkey}: {value}")
    
    if "Narrative Flow" in data:
        print("\nNarrative Flow:")
        print(f"  {data['Narrative Flow']}")
    
    if "Additional Details" in data:
        print("\nAdditional Details:")
        print(f"  {data['Additional Details']}")
    
    print("-" * 50)

def test_lambda():

    load_dotenv()
    
    api_key = os.getenv("API_KEY")
    video_id = os.getenv("VIDEO_ID")
    
    if not api_key:
        print("Error: API_KEY not found in .env file")
        return
    
    if not video_id:
        print("Please add VIDEO_ID=your_video_id to your .env file")
        return
    
    print(f"API key length: {len(api_key)} characters")
    print(f"Video ID: {video_id} ({len(video_id)} characters)")
    
    conn_success, conn_msg = test_connectivity(api_key)
    if not conn_success:
        print("\nAPI connectivity test failed. Please check your internet connection and API key.")
        return
    
    video_success, video_msg = test_video_exists(api_key, video_id)
    if not video_success:
        print("\nVideo ID check failed. The video might not exist or might be in a different index.")
        return
    
    event = {
        "video_id": video_id,
        "api_key": api_key
    }
    
    print(f"\nTesting lambda_handler with video_id: {video_id}")

    try:
        print("Calling lambda_handler function...")
        response = lambda_handler(event, None)
        
        print("\nResponse:")
        print(json.dumps(response, indent=2))
        
        if 'error' in response:
            print(f"\n Error encountered: {response['error']}")
            
            if 'details' in response:
                print("\nError details:")
                print(response['details'])
            

        else:
            print("\nTest completed successfully!")
            
            if 'structured_data' in response:
                print_structured_data(response['structured_data'])
            else:
                print("\nNo structured data found in the response")
    
    except Exception as e:
        print(f"\n Exception occurred during testing: {str(e)}")


if __name__ == "__main__":
    test_lambda()