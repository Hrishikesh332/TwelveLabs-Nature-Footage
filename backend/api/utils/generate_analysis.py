import json
import logging
import traceback
import boto3
from twelvelabs import TwelveLabs
import time


from config.settings import (
    API_KEY, 
    AWS_REGION, 
    AWS_ACCESS_KEY_ID, 
    AWS_SECRET_ACCESS_KEY,
    LAMBDA_FUNCTION_NAME
)

from api.utils.twelvelabs_api import normalize_structured_data, parse_unstructured_response

logger = logging.getLogger(__name__)


# Initialize Lambda client if credentials are available
if all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION]):
    lambda_client = boto3.client(
        'lambda', 
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
else:
    lambda_client = None
    logger.warning("AWS credentials not set, Lambda client will not be available")


def load_prompt(path="config/prompt.txt"):
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except FileNotFoundError:
        return None
    

def analyze_video(video_id, prompt=None, use_lambda=True):

    try:
        logger.info(f"Analyzing video {video_id}")
        
        if use_lambda and lambda_client:
            return analyze_video_with_lambda(video_id, prompt)
        
        return analyze_video_directly(video_id, prompt)
        
    except Exception as e:
        error_msg = f"Error analyzing video: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {
            'statusCode': 500,
            'error': error_msg,
            'details': traceback.format_exc()
        }

def analyze_video_with_lambda(video_id, prompt=None):

    try:
        logger.info(f"Analyzing video {video_id} with Lambda function")
        
        payload = {
            "video_id": video_id,
            "api_key": API_KEY
        }
        
        if prompt:
            payload["prompt"] = prompt
        
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        
        if 'error' in result:
            logger.error(f"Lambda function error: {result['error']}")
        
        return result
        
    except Exception as e:
        error_msg = f"Error invoking Lambda function: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {
            'statusCode': 500,
            'error': error_msg,
            'details': traceback.format_exc()
        }

def analyze_video_directly(video_id, prompt=None):
    try:
        logger.info(f"Analyzing video {video_id} directly with Pegasus model")
        prompt = load_prompt()
        if not prompt:
            raise ValueError("Prompt is not provided or not loaded")
        
        client = TwelveLabs(api_key=API_KEY)
        
        logger.info(f"Sending generation request for video {video_id}")
        response = client.generate.text(
            video_id=video_id,
            prompt=prompt
        )
        
        raw_analysis = response.data
        logger.info(f"Received response with length: {len(raw_analysis) if raw_analysis else 0}")
        
        try:
            structured_data = json.loads(raw_analysis)
            logger.info("Successfully parsed response as JSON")
            
            structured_data = normalize_structured_data(structured_data)
            
        except json.JSONDecodeError:
            logger.warning("JSON parsing failed, using structured parsing")
            structured_data = parse_unstructured_response(raw_analysis)
        
        return {
            'statusCode': 200,
            'data': raw_analysis,
            'structured_data': structured_data
        }
        
    except Exception as e:
        error_msg = f"Error analyzing video directly: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {
            'statusCode': 500,
            'error': error_msg,
            'details': traceback.format_exc()
        }

def process_analysis_result(video_id, result, update_metadata=True):

    try:
        if result.get('statusCode') == 200 and 'structured_data' in result:
            structured_data = result['structured_data']
            
            if update_metadata:
                from api.utils.twelvelabs_api import update_video_metadata, get_video_metadata
                
                # Get current metadata
                current_metadata = get_video_metadata(video_id)
                
                # Create new metadata
                new_metadata = current_metadata.copy()
                
                # Main analysis fields
                new_metadata.update({
                    'analysis_complete': True,
                    'analysis_timestamp': int(time.time()),
                    'analysis_version': '1.0'
                })
                
                # Shot field
                if 'Shot' in structured_data:
                    new_metadata['analysis_shot'] = structured_data['Shot']
                
                # Add Action field
                if 'Action' in structured_data:
                    new_metadata['analysis_action'] = structured_data['Action']
                
                # Handle Subject 
                if 'Subject' in structured_data:
                    subject = structured_data['Subject']
                    if isinstance(subject, dict):
                
                        subject_json = json.dumps(subject)
                        new_metadata['analysis_subject'] = subject_json
                        
                        for key, value in subject.items():
                            if value:  
                                from api.utils.csv_utils import normalize_metadata_key
                                meta_key = f"analysis_subject_{normalize_metadata_key(key)}"
                                new_metadata[meta_key] = value
                    else:
 
                        new_metadata['analysis_subject'] = json.dumps({"Identification": subject})
                        new_metadata['analysis_subject_identification'] = subject
                
                # Handle Environment 
                if 'Environment' in structured_data:
                    environment = structured_data['Environment']
                    if isinstance(environment, dict):

                        env_json = json.dumps(environment)
                        new_metadata['analysis_environment'] = env_json
                        
                        for key, value in environment.items():
                            if value:  
                                from api.utils.csv_utils import normalize_metadata_key
                                meta_key = f"analysis_environment_{normalize_metadata_key(key)}"
                                new_metadata[meta_key] = value
                    else:
                        new_metadata['analysis_environment'] = json.dumps({"Description": environment})
                        new_metadata['analysis_environment_description'] = environment
                
                # Narrative Flow
                if 'Narrative Flow' in structured_data:
                    value = structured_data['Narrative Flow']
                    if isinstance(value, str) and len(value) > 1000:
                        value = value[:1000] + "..."
                    new_metadata['analysis_narrativeflow'] = value
                
                # Additional Details field
                if 'Additional Details' in structured_data:
                    value = structured_data['Additional Details']
                    if isinstance(value, str) and len(value) > 1000:
                        value = value[:1000] + "..."
                    new_metadata['analysis_additionaldetails'] = value
                
                # Summary field
                summary = []
                if structured_data.get('Shot'):
                    summary.append(f"Shot: {structured_data['Shot']}")
                if structured_data.get('Action'):
                    summary.append(f"Action: {structured_data['Action']}")
                
                if isinstance(structured_data.get('Subject'), dict):

                    for id_key in ['Identification', 'Specific identification', 'Species/Category', 'Type']:
                        if id_key in structured_data['Subject'] and structured_data['Subject'][id_key]:
                            summary.append(f"Subject: {structured_data['Subject'][id_key]}")
                            break
                elif structured_data.get('Subject'):
                    summary.append(f"Subject: {structured_data['Subject']}")
                
                new_metadata['analysis_summary'] = " | ".join(summary)
                
                # Update the video metadata
                success, result = update_video_metadata(video_id, new_metadata)
                
                if success:
                    logger.info(f"Successfully updated metadata for video {video_id}")
                    return True, new_metadata
                else:
                    error_msg = f"Failed to update metadata: {result}"
                    logger.error(error_msg)
                    return False, error_msg
            
            return True, structured_data
        else:

            error_message = result.get('error', 'Unknown error')
            logger.error(f"Analysis failed: {error_message}")
            
            if update_metadata:
                from api.utils.twelvelabs_api import update_video_metadata, get_video_metadata
                

                current_metadata = get_video_metadata(video_id)
                
                new_metadata = current_metadata.copy()
                
                new_metadata.update({
                    'analysis_complete': False,
                    'analysis_timestamp': int(time.time()),
                    'analysis_error': error_message[:500],  
                    'analysis_version': '1.0'
                })
                
                # Update the video metadata
                update_video_metadata(video_id, new_metadata)
            
            return False, error_message
    
    except Exception as e:
        error_msg = f"Error processing analysis result: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False, error_msg