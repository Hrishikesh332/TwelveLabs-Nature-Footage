import requests
import json
import logging
import traceback
from twelvelabs import TwelveLabs
import time

from config.settings import API_KEY, INDEX_ID

logger = logging.getLogger(__name__)


# List videos from the TwelveLabs index
def list_videos(page=1, page_limit=50, sort_by="created_at", sort_option="desc", filename=None):


    url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos"
    
    querystring = {
        "page": page,
        "page_limit": page_limit,
        "sort_by": sort_by,
        "sort_option": sort_option
    }
    
    if filename:
        querystring["filename"] = filename
    
    headers = {"x-api-key": API_KEY}
    
    try:
        logger.info(f"Listing videos: page {page}, limit {page_limit}")
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error listing videos: {str(e)}")
        return None


# Information about the TwelveLabs index
def get_index_info():

    url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}"
    headers = {"x-api-key": API_KEY}
    
    try:
        logger.info(f"Getting index information for {INDEX_ID}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching index information: {str(e)}")
        return None


# Get information about a specific video
def get_video_info(video_id, include_embeddings=False):

    url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos/{video_id}"
    headers = {"x-api-key": API_KEY}
    
    params = {}
    if include_embeddings:
        params["embedding_option"] = ["visual-text", "audio"]
    
    try:
        logger.info(f"Getting video information for {video_id}")
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching video information: {str(e)}")
        return None

# Get metadata for a specific video
def get_video_metadata(video_id):

    video_info = get_video_info(video_id)
    if video_info:
        return video_info.get("user_metadata", {})
    return {}

# Update metadata for a specific video
def update_video_metadata(video_id, metadata):

    url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos/{video_id}"
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "user_metadata": metadata
    }
    
    try:
        logger.info(f"Updating metadata for video {video_id}")
        response = requests.put(url, json=payload, headers=headers)
        response.raise_for_status()
        
        try:
            response_data = response.json()
            return True, response_data
        except json.JSONDecodeError:
            if response.status_code in (200, 201, 204):
                return True, "Success (no JSON response)"
            else:
                error_msg = f"Invalid JSON response: {response.text}"
                logger.error(error_msg)
                return False, error_msg
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP Error: {e}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Error updating metadata: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


# Update a single field in the user metadata
def update_single_field_metadata(video_id, field_name, field_value):

    try:
        logger.info(f"Updating single field '{field_name}' for video {video_id}")
        
        url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos/{video_id}"
        headers = {
            "x-api-key": API_KEY,
            "Content-Type": "application/json"
        }
        
        if isinstance(field_value, (list, dict)):
            field_value_str = json.dumps(field_value)
            logger.debug(f"Converting complex value to string: {field_value_str[:100]}...")
            
            # Simple payload with just the one field we want to update
            payload = {
                "user_metadata": {
                    field_name: field_value_str
                }
            }
        else:
            payload = {
                "user_metadata": {
                    field_name: field_value
                }
            }
        
        response = requests.put(url, json=payload, headers=headers)
        logger.info(f"API response status: {response.status_code}")
        
        response.raise_for_status()
        
        try:
            response_data = response.json()
            return True, response_data
        except json.JSONDecodeError:
            if response.status_code in (200, 201, 204):
                return True, "Success (no JSON response)"
            else:
                error_msg = f"Invalid JSON response: {response.text}"
                logger.error(error_msg)
                return False, error_msg
    
    except Exception as e:
        error_msg = f"Error updating metadata field: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False, error_msg


# Get embedding for a video
def get_video_embedding(video_id):

    try:
        logger.info(f"Retrieving embeddings for video_id: {video_id}")
        
        video_url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos/{video_id}"
        headers = {"x-api-key": API_KEY}
        
        params = {
            "embedding_option": ["visual-text", "audio"]
        }
        
        logger.debug(f"Making API request to {video_url} with params: {params}")
        video_response = requests.get(video_url, headers=headers, params=params)

        if video_response.status_code == 404 and "embed_no_embeddings_found" in video_response.text and "audio" in video_response.text:
            logger.warning(f"No audio embeddings found for video {video_id}, retrying with visual-text only")
            
            params = {
                "embedding_option": ["visual-text"]
            }
            
            video_response = requests.get(video_url, headers=headers, params=params)
        
        if video_response.status_code != 200:
            error_msg = f"API error: {video_response.status_code} - {video_response.text}"
            logger.error(f"Error retrieving video with embeddings: {error_msg}")
            return {"status": "failed", "error": error_msg}
        
        video_data = video_response.json()
        
        if "embedding" not in video_data or "video_embedding" not in video_data.get("embedding", {}):
            error_msg = "No embeddings available for this video"
            logger.warning(f"No embeddings for video {video_id}: {error_msg}")
            return {"status": "failed", "error": error_msg}
        
        embedding_data = {
            "status": "ready",
            "_id": video_id,
            "model_name": video_data.get("embedding", {}).get("model_name", "unknown"),
            "video_embedding": video_data.get("embedding", {}).get("video_embedding", {})
        }
        
        logger.info(f"Successfully retrieved embeddings for video {video_id}")
        return embedding_data
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error getting video embedding: {error_msg}")
        logger.error(traceback.format_exc())
        return {"status": "error", "error": error_msg}


# Search for videos using TwelveLabs API
def search_videos(query_text, search_options=None, page_limit=15, threshold="high"):

    try:
        logger.info(f"Searching videos with query: {query_text}")
        if search_options is None:
            search_options = ['visual']
            
        client = TwelveLabs(api_key=API_KEY)
        
        search_params = {
            "index_id": INDEX_ID,
            "query_text": query_text,
            "threshold": threshold,
            "page_limit": page_limit,
            "group_by": "video", 
            "sort_option": "score"
        }
        
        # Add search options to the search parameters
        if search_options:
            search_params["options"] = search_options
        
        logger.info(f"Searching with params: {search_params}")
        search_results = client.search.query(**search_params)
        
        return search_results
    except Exception as e:
        logger.error(f"Error searching videos: {str(e)}")
        logger.error(traceback.format_exc())
        return None

# Next page of search results using a page token
def search_by_page_token(page_token):

    try:
        logger.info(f"Fetching next page with token: {page_token[:10]}...")
        client = TwelveLabs(api_key=API_KEY)
        search_results = client.search.by_page_token(page_token=page_token)
        return search_results
    except Exception as e:
        logger.error(f"Error fetching next page: {str(e)}")
        logger.error(traceback.format_exc())
        return None


def normalize_structured_data(data):

    normalized = {}
    
    if "Shot" in data:
        normalized["Shot"] = data["Shot"]
    elif "shot" in data:
        normalized["Shot"] = data["shot"]
    
    if "Subject" in data:
        subject = data["Subject"]
        if isinstance(subject, dict):
            normalized["Subject"] = subject
        else:
            normalized["Subject"] = {"Identification": subject}
    elif "subject" in data:
        subject = data["subject"]
        if isinstance(subject, dict):
            normalized["Subject"] = subject
        else:
            normalized["Subject"] = {"Identification": subject}
    
    if "Action" in data:
        normalized["Action"] = data["Action"]
    elif "action" in data:
        normalized["Action"] = data["action"]
    
    if "Environment" in data:
        env = data["Environment"]
        if isinstance(env, dict):
            normalized["Environment"] = env
        else:
            normalized["Environment"] = {"Description": env}
    elif "environment" in data:
        env = data["environment"]
        if isinstance(env, dict):
            normalized["Environment"] = env
        else:
            normalized["Environment"] = {"Description": env}
    
    if "Narrative Flow" in data:
        normalized["Narrative Flow"] = data["Narrative Flow"]
    elif "narrative flow" in data:
        normalized["Narrative Flow"] = data["narrative flow"]
    elif "NarrativeFlow" in data:
        normalized["Narrative Flow"] = data["NarrativeFlow"]
    
    if "Additional Details" in data:
        normalized["Additional Details"] = data["Additional Details"]
    elif "additional details" in data:
        normalized["Additional Details"] = data["additional details"]
    elif "AdditionalDetails" in data:
        normalized["Additional Details"] = data["AdditionalDetails"]
    
    return normalized

def parse_unstructured_response(text):

    result = {
        "Shot": "",
        "Subject": {
            "Type": "",
            "Classification": "",
            "Species": "",
            "Count": "",
            "Identification": "",
            "Color": ""
        },
        "Action": "",
        "Environment": {
            "Time": "",
            "Location": "",
            "Weather": "",
            "Position": "",
            "Climate": ""
        },
        "Narrative Flow": "",
        "Additional Details": ""
    }

    if not text:
        return result

    if "shot:" in text.lower():
        shot_section = text.lower().split("shot:")[1].split("\n")[0]
        result["Shot"] = shot_section.strip()

    if "subject:" in text.lower():
        subject_section = text.lower().split("subject:")[1].split("\n")[0]
        parts = subject_section.split()
        
        for type_key in ["animal", "human", "object"]:
            if type_key in parts:
                result["Subject"]["Type"] = type_key.capitalize()
        
        for class_key in ["mammal", "bird", "reptile", "amphibian", "fish", "insect"]:
            if class_key in parts:
                result["Subject"]["Classification"] = class_key.capitalize()
        
        for species_key in ["primate", "feline", "canine", "bovine", "equine"]:
            if species_key in parts:
                result["Subject"]["Species"] = species_key.capitalize()
        
        for count_key in ["single", "multiple", "pair", "group"]:
            if count_key in parts:
                result["Subject"]["Count"] = count_key.capitalize()
        
        result["Subject"]["Identification"] = subject_section.strip()
        
        for color in ["black", "white", "brown", "grey", "gray", "red", "blue", "green", "yellow"]:
            if color in parts:
                result["Subject"]["Color"] = color.capitalize()
    
    if "action:" in text.lower():
        action_section = text.lower().split("action:")[1].split("\n")[0]
        result["Action"] = action_section.strip()
    
    if "environment:" in text.lower():
        env_section = text.lower().split("environment:")[1].split("\n")[0]
        parts = env_section.split()
        
        for time_key in ["day", "night", "dusk", "dawn", "morning", "evening"]:
            if time_key in parts:
                result["Environment"]["Time"] = time_key.capitalize()

        for loc_key in ["forest", "urban", "indoor", "outdoor", "rural", "jungle", "desert", "mountain", "beach", "ocean", "river", "lake", "rainforest"]:
            if loc_key in parts:
                result["Environment"]["Location"] = loc_key.capitalize()
        
        for weather_key in ["sunny", "rainy", "cloudy", "snowy", "foggy", "clear"]:
            if weather_key in parts:
                result["Environment"]["Weather"] = weather_key.capitalize()
        
        for pos_key in ["topside", "underwater", "aerial", "ground"]:
            if pos_key in parts:
                result["Environment"]["Position"] = pos_key.capitalize()
        
        for climate_key in ["tropical", "temperate", "arctic", "desert", "mediterranean"]:
            if climate_key in parts:
                result["Environment"]["Climate"] = climate_key.capitalize()
    
    if "narrative flow:" in text.lower():
        narrative_section = text.lower().split("narrative flow:")[1]
        if "\n" in narrative_section:
            narrative_section = narrative_section.split("\n")[0]
        result["Narrative Flow"] = narrative_section.strip()
    
    if "additional details:" in text.lower():
        details_section = text.lower().split("additional details:")[1]
        if "\n" in details_section:
            details_section = details_section.split("\n")[0]
        result["Additional Details"] = details_section.strip()
    
    return result