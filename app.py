import os
import requests
import json
import time
import csv
import io
import boto3
from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
from twelvelabs import TwelveLabs
from botocore.exceptions import ClientError
from flask_cors import CORS

from weaviate.util import generate_uuid5

import time

import weaviate
from weaviate.auth import AuthApiKey
from weaviate.classes.config import Configure, Property, DataType, VectorDistances
# from weaviate.collections import Collection


import weaviate
from weaviate.classes.query import Filter

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import atexit

import logging


load_dotenv()
INDEX_ID = os.getenv("INDEX_ID")
API_KEY = os.getenv("API_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

lambda_client = boto3.client(
    'lambda', 
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

weaviate_client = None

@app.route('/')
def home():
    return "Server is running! Current time: " + str(datetime.now())


def init_weaviate_client():
    global weaviate_client
    
    if not WEAVIATE_URL or not WEAVIATE_API_KEY:
        app.logger.error("WEAVIATE_URL or WEAVIATE_API_KEY environment variables not set")
        return False
    
    try:
        weaviate_client = weaviate.connect_to_weaviate_cloud(
            cluster_url=WEAVIATE_URL,
            auth_credentials=AuthApiKey(WEAVIATE_API_KEY),
        )
        
        if not weaviate_client.is_ready():
            app.logger.error("Weaviate client is not ready")
            return False
            
        app.logger.info("Weaviate client initialized successfully")
        return True
    except Exception as e:
        app.logger.error(f"Error initializing Weaviate client: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return False


init_weaviate_client()


def create_videos_schema():
    if not weaviate_client:
        app.logger.error("Weaviate client not initialized")
        return False

    try:
        collections = weaviate_client.collections.list_all()
        if "NatureVideo" not in collections:

            weaviate_client.collections.create(
                name="NatureVideo",
                description="Nature video embeddings from Twelve Labs",
                vectorizer="none", 
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=VectorDistances.COSINE,
                    ef_construction=128,
                    max_connections=16,
                    vector_cache_max_objects=1000000
                ),
                properties=[
                    Property(name="video_id", data_type=DataType.TEXT, description="Twelve Labs video ID"),
                    Property(name="filename", data_type=DataType.TEXT, description="Original filename"),
                    Property(name="duration", data_type=DataType.NUMBER, description="Video duration in seconds"),
                    Property(name="embedding_type", data_type=DataType.TEXT, description="Type of embedding (visual-text, audio)"),
                    Property(name="scope", data_type=DataType.TEXT, description="Scope of embedding (clip, video)"),
                    Property(name="start_time", data_type=DataType.NUMBER, description="Start time of the clip"),
                    Property(name="end_time", data_type=DataType.NUMBER, description="End time of the clip"),
                ]
            )
            app.logger.info("Created NatureVideo collection in Weaviate")
        else:
            app.logger.info("NatureVideo collection already exists in Weaviate")
        return True
    except Exception as e:
        app.logger.error(f"Failed to create collection: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return False

if weaviate_client:
    create_videos_schema()



def get_video_embedding(video_id):
    try:
        video_url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos/{video_id}"
        headers = {"x-api-key": API_KEY}
        
        params = {
            "embedding_option": ["visual-text", "audio"]
        }
        
        app.logger.info(f"Retrieving video information with both visual-text and audio embeddings for {video_id}")
        video_response = requests.get(video_url, headers=headers, params=params)

        if video_response.status_code == 404 and "embed_no_embeddings_found" in video_response.text and "audio" in video_response.text:
            app.logger.warning(f"No audio embeddings found for video {video_id}, retrying with visual-text only")
            
            params = {
                "embedding_option": ["visual-text"]
            }
            
            video_response = requests.get(video_url, headers=headers, params=params)
        
        if video_response.status_code != 200:
            error_msg = f"API error: {video_response.status_code} - {video_response.text}"
            app.logger.error(f"Error retrieving video with embeddings: {error_msg}")
            track_embedding_status(video_id, "failed", None, error_msg)
            return {"status": "failed", "error": error_msg}
        
        video_data = video_response.json()
        
        if "embedding" not in video_data or "video_embedding" not in video_data.get("embedding", {}):
            error_msg = "No embeddings available for this video"
            app.logger.warning(f"No embeddings for video {video_id}: {error_msg}")
            track_embedding_status(video_id, "failed", None, error_msg)
            return {"status": "failed", "error": error_msg}
        
        embedding_data = {
            "status": "ready",
            "_id": video_id,
            "model_name": video_data.get("embedding", {}).get("model_name", "unknown"),
            "video_embedding": video_data.get("embedding", {}).get("video_embedding", {})
        }
        
        track_embedding_status(video_id, "retrieved", video_id)
        return embedding_data
        
    except Exception as e:
        error_msg = str(e)
        app.logger.error(f"Error getting video embedding: {error_msg}")
        track_embedding_status(video_id, "error", None, error_msg)
        return {"status": "error", "error": error_msg}

def track_embedding_status(video_id, status, task_id=None, error=None):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    csv_path = "embedding_status.csv"
    file_exists = os.path.isfile(csv_path)
    
    with open(csv_path, 'a', newline='') as csvfile:
        fieldnames = ['timestamp', 'video_id', 'status', 'task_id', 'error']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow({
            'timestamp': timestamp,
            'video_id': video_id,
            'status': status,
            'task_id': task_id or '',
            'error': error or ''
        })
    
    log_message = f"Embedding status: {status} for video {video_id}"
    if error:
        log_message += f" - Error: {error}"
    
    if status == 'failed' or status == 'error':
        app.logger.error(log_message)
    else:
        app.logger.info(log_message)

@app.route('/api/recreate-schema', methods=['POST'])
def api_recreate_schema():
    try:
        if not weaviate_client:
            return jsonify({"error": "Weaviate client not initialized"}), 500
        
        videos_response = list_videos(page=1, page_limit=1)
        if not videos_response or 'data' not in videos_response or not videos_response['data']:
            return jsonify({"error": "No videos found to determine vector dimensions"}), 500
        
        sample_video_id = videos_response['data'][0]['_id']
        
        video_url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos/{sample_video_id}"
        headers = {"x-api-key": API_KEY}
        params = {
            "embedding_option": ["visual-text", "audio"]
        }
        
        video_response = requests.get(video_url, headers=headers, params=params)
        video_response.raise_for_status()
        video_data = video_response.json()

        vector_dimensions = None
        embedding_info = video_data.get("embedding", {})
        
        if embedding_info and "video_embedding" in embedding_info:
            segments = embedding_info.get("video_embedding", {}).get("segments", [])
            if segments:
                first_vector = segments[0].get("float", [])
                vector_dimensions = len(first_vector)
        
        if not vector_dimensions:
            return jsonify({"error": "Could not determine vector dimensions from sample video"}), 500
        
        app.logger.info(f"Detected vector dimensions: {vector_dimensions}")
        
        all_collections = weaviate_client.collections.list_all()
        if "NatureVideo" in all_collections:
            try:
                weaviate_client.collections.delete("NatureVideo")
                app.logger.info("Deleted existing NatureVideo collection")
            except Exception as e:
                app.logger.error(f"Error deleting NatureVideo collection: {str(e)}")
        
        try:

            weaviate_client.collections.create(
                name="NatureVideo",
                description="Nature video embeddings from Twelve Labs",
                vectorizer_config=None,  
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=VectorDistances.COSINE,
                    ef_construction=128,
                    max_connections=16,
                    vector_cache_max_objects=1000000
                ),
                properties=[
                    Property(name="video_id", data_type=DataType.TEXT, description="Twelve Labs video ID"),
                    Property(name="filename", data_type=DataType.TEXT, description="Original filename"),
                    Property(name="duration", data_type=DataType.NUMBER, description="Video duration in seconds"),
                    Property(name="embedding_type", data_type=DataType.TEXT, description="Type of embedding (visual-text, audio)"),
                    Property(name="scope", data_type=DataType.TEXT, description="Scope of embedding (clip, video)"),
                    Property(name="start_time", data_type=DataType.NUMBER, description="Start time of the clip"),
                    Property(name="end_time", data_type=DataType.NUMBER, description="End time of the clip"),
                ]
            )
            
            app.logger.info(f"Created NatureVideo collection successfully with {vector_dimensions} dimensions")
            
            return jsonify({
                "success": True, 
                "message": f"Schema recreated successfully with {vector_dimensions} dimensions"
            })
        
        except Exception as e:
            app.logger.error(f"Error creating collection: {str(e)}")
            import traceback
            app.logger.error(traceback.format_exc())
            return jsonify({"error": f"Error creating collection: {str(e)}"}), 500
            
    except Exception as e:
        app.logger.error(f"Error in recreate schema process: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Error recreating schema: {str(e)}"}), 500



def store_video_embedding_in_weaviate(video_id, embedding_data):

    app.logger.info(f"Storing embeddings for video {video_id}")
    
    if not weaviate_client:
        app.logger.error("Weaviate client not initialized")
        return False
    
    try:
        collections = weaviate_client.collections.list_all()
        if "NatureVideo" not in collections:
            app.logger.warning("NatureVideo collection does not exist, creating it...")
            create_videos_schema()
        
        try:
            collection = weaviate_client.collections.get("NatureVideo")
            app.logger.info("Successfully accessed NatureVideo collection")
        except Exception as e:
            app.logger.error(f"Failed to access NatureVideo collection: {str(e)}")
            return False
        
        try:
            video_url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos/{video_id}"
            headers = {"x-api-key": API_KEY}
            
            video_response = requests.get(video_url, headers=headers)
            video_response.raise_for_status()
            video_data = video_response.json()
            
            filename = video_data.get("system_metadata", {}).get("filename", "unknown")
            duration = video_data.get("system_metadata", {}).get("duration", 0)
            
            if isinstance(duration, str):
                duration = float(duration)
            
            app.logger.info(f"Video metadata: filename={filename}, duration={duration}")
            
        except Exception as e:
            app.logger.error(f"Error retrieving video metadata: {str(e)}")
            return False
        
        segments = []
        
        if embedding_data and embedding_data.get("video_embedding"):
            segments = embedding_data.get("video_embedding", {}).get("segments", [])
        
        if not segments and video_data:
            embedding_info = video_data.get("embedding", {})
            if embedding_info and "video_embedding" in embedding_info:
                segments = embedding_info.get("video_embedding", {}).get("segments", [])
        
        if not segments:
            app.logger.warning(f"No embedding segments found for video {video_id}")
            return successful_inserts > 0
        
        app.logger.info(f"Found {len(segments)} embedding segments")
        
        if segments:
            first_segment = segments[0]
            vector = first_segment.get("float", [])
            vector_dimensions = len(vector)
            app.logger.info(f"First segment has {vector_dimensions} dimensions")
        
        successful_inserts = 0
        failed_inserts = 0
        
        for segment in segments:
            try:
                vector = segment.get("float", [])
                embedding_type = segment.get("embedding_option", "unknown")
                scope = segment.get("embedding_scope", "unknown")
                start_time = segment.get("start_offset_sec", 0)
                end_time = segment.get("end_offset_sec", duration)
                
                if isinstance(start_time, str):
                    start_time = float(start_time)
                if isinstance(end_time, str):
                    end_time = float(end_time)
                
                if not vector:
                    app.logger.warning(f"Empty vector for {embedding_type}/{scope} segment")
                    continue
                
                properties = {
                    "video_id": video_id,
                    "filename": filename,
                    "duration": float(duration),
                    "embedding_type": embedding_type,
                    "scope": scope,
                    "start_time": float(start_time),
                    "end_time": float(end_time)
                }
                
                object_id = f"{video_id}_{embedding_type}_{scope}"
                object_uuid = generate_uuid5(object_id)
                
                app.logger.info(f"Inserting {embedding_type}/{scope} vector with {len(vector)} dimensions")
                
                collection.data.insert(
                    properties=properties,
                    vector=vector,
                    uuid=object_uuid
                )
                
                app.logger.info(f"Successfully inserted {embedding_type}/{scope} embedding")
                successful_inserts += 1
                
            except Exception as e:
                app.logger.error(f"Failed to insert {embedding_type}/{scope} embedding: {str(e)}")
                failed_inserts += 1
        

        app.logger.info(f"Inserted {successful_inserts} embeddings, failed {failed_inserts} embeddings")
        
        if successful_inserts > 0:
            return True
        else:
            app.logger.error("Failed to insert any embeddings")
            return False
        
    except Exception as e:
        app.logger.error(f"Error in store_video_embedding_in_weaviate: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return False
    
@app.route('/api/debug-similar-videos/<video_id>', methods=['GET'])
def api_debug_similar_videos(video_id):

    debug_info = {
        "video_id": video_id,
        "steps": []
    }
    
    try:
        if not weaviate_client:
            debug_info["error"] = "Weaviate client not initialized"
            return jsonify(debug_info), 500
        
        debug_info["steps"].append("Weaviate client is initialized")
        
        video_url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos/{video_id}"
        headers = {"x-api-key": API_KEY}
        
        video_response = requests.get(video_url, headers=headers)
        debug_info["steps"].append(f"Twelve Labs API response status: {video_response.status_code}")
        
        if video_response.status_code != 200:
            debug_info["error"] = f"Failed to get video info: {video_response.text}"
            return jsonify(debug_info), 400
            
        video_data = video_response.json()
        debug_info["video_info"] = {
            "filename": video_data.get("system_metadata", {}).get("filename", "unknown"),
            "has_user_metadata": "user_metadata" in video_data
        }
        
        embedding_data = get_video_embedding(video_id)
        debug_info["embedding_status"] = embedding_data.get("status")
        
        if embedding_data.get("status") != "ready":
            debug_info["error"] = f"Embedding not ready: {embedding_data.get('error', 'Unknown error')}"
            return jsonify(debug_info), 400
        
        segments = embedding_data.get("video_embedding", {}).get("segments", [])
        debug_info["total_segments"] = len(segments)
        
        visual_embedding = None
        segment_info = []
        
        for segment in segments:
            seg_info = {
                "embedding_option": segment.get("embedding_option"),
                "embedding_scope": segment.get("embedding_scope"),
                "has_float_vector": "float" in segment and len(segment.get("float", [])) > 0
            }
            segment_info.append(seg_info)
            
            if segment.get("embedding_option") == "visual-text" and segment.get("embedding_scope") == "video":
                visual_embedding = segment.get("float", [])
        
        debug_info["segments_info"] = segment_info
        
        if not visual_embedding:
            for segment in segments:
                if segment.get("embedding_option") == "visual-text":
                    visual_embedding = segment.get("float", [])
                    debug_info["fallback"] = f"Using {segment.get('embedding_scope')} scope visual-text embedding"
                    break
        
        if not visual_embedding:
            debug_info["error"] = "No visual-text embedding found"
            return jsonify(debug_info), 400
        
        debug_info["visual_embedding_found"] = True
        debug_info["embedding_vector_length"] = len(visual_embedding)
        
        try:
            collection = weaviate_client.collections.get("NatureVideo")
            
            existing_check = collection.query.fetch_objects(
                filters=weaviate.classes.query.Filter.by_property("video_id").equal(video_id),
                limit=1
            )
            
            debug_info["video_in_weaviate"] = len(existing_check.objects) > 0
            
            similar_results = collection.query.near_vector(
                near_vector=visual_embedding,
                limit=11,
                return_properties=["video_id", "filename", "embedding_type", "scope"]
            )
            
            debug_info["similar_results_count"] = len(similar_results.objects)
            
            similar_videos = []
            for obj in similar_results.objects:
                props = obj.properties
                if props.get("video_id") != video_id:
                    similar_videos.append({
                        "video_id": props.get("video_id"),
                        "filename": props.get("filename"),
                        "embedding_type": props.get("embedding_type"),
                        "scope": props.get("scope")
                    })
            
            debug_info["similar_videos_found"] = len(similar_videos)
            debug_info["similar_videos_preview"] = similar_videos[:3]
            
        except Exception as e:
            debug_info["weaviate_error"] = str(e)
            
        return jsonify(debug_info)
        
    except Exception as e:
        debug_info["error"] = f"Unexpected error: {str(e)}"
        import traceback
        debug_info["traceback"] = traceback.format_exc()
        return jsonify(debug_info), 500

        




def update_video_metadata(video_id, metadata):

    try:
        url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos/{video_id}"
        headers = {
            "x-api-key": API_KEY,
            "Content-Type": "application/json"
        }
        
        data = {
            "user_metadata": metadata
        }
        
        response = requests.put(url, headers=headers, json=data)
        
        if response.status_code == 200:
            app.logger.info(f"Successfully updated metadata for video {video_id}")
            return True
        else:
            app.logger.error(f"Failed to update metadata for video {video_id}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        app.logger.error(f"Error updating video metadata: {str(e)}")
        return False


def find_similar_videos(video_id, limit=10):

    result = {
        "videos": [],
        "source": "weaviate",
        "cache_age": None,
        "embedding_scope": None
    }
    
    if not weaviate_client:
        app.logger.error("Weaviate client not initialized")
        return result
    
    try:
        app.logger.info(f"Finding similar videos for video_id: {video_id}")
        
        video_url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos/{video_id}"
        headers = {"x-api-key": API_KEY}
        
        video_response = requests.get(video_url, headers=headers)
        video_response.raise_for_status()
        video_data = video_response.json()
        
        user_metadata = video_data.get("user_metadata", {})
        
        if "similar_videos" in user_metadata and "similar_videos_timestamp" in user_metadata:
            timestamp = user_metadata.get("similar_videos_timestamp", 0)
            current_time = int(time.time())
            cache_age = current_time - timestamp
            
            app.logger.info(f"Found cached results. Cache age: {cache_age} seconds")
            
            if cache_age < 86400:
                cached_videos = user_metadata.get("similar_videos", [])
                app.logger.info(f"Returning {len(cached_videos)} similar videos from CACHE (age: {cache_age} seconds)")
                result["videos"] = cached_videos
                result["source"] = "cache"
                result["cache_age"] = cache_age
                return result
            else:
                app.logger.info(f"Cache expired (age: {cache_age} seconds > 86400). Fetching fresh results...")
        else:
            app.logger.info("No cached results found. Fetching fresh results...")
        
        app.logger.info(f"Retrieving embeddings for video_id: {video_id}")
        embedding_data = get_video_embedding(video_id)
        
        if embedding_data.get("status") != "ready":
            app.logger.error(f"Embedding not ready for video_id: {video_id}")
            return result
        
        segments = embedding_data.get("video_embedding", {}).get("segments", [])
        visual_embedding = None
        embedding_scope = None
        
        for segment in segments:
            if segment.get("embedding_option") == "visual-text" and segment.get("embedding_scope") == "video":
                visual_embedding = segment.get("float", [])
                embedding_scope = "video"
                app.logger.info("Found video scope visual-text embedding")
                break
        
        if not visual_embedding:
            for segment in segments:
                if segment.get("embedding_option") == "visual-text":
                    visual_embedding = segment.get("float", [])
                    embedding_scope = "clip"
                    app.logger.info("Using clip scope visual-text embedding (fallback)")
                    break
        
        if not visual_embedding:
            app.logger.error("No visual-text embedding found")
            return result
        
        app.logger.info(f"Storing/updating embedding in Weaviate for video_id: {video_id}")
        store_video_embedding_in_weaviate(video_id, embedding_data)
        
        collection = weaviate_client.collections.get("NatureVideo")
        
        app.logger.info(f"Searching Weaviate for similar videos (limit: {limit + 1})")
        results = collection.query.near_vector(
            near_vector=visual_embedding,
            limit=limit + 1, 
            return_properties=["video_id", "filename"]
        )
        
        similar_videos = []
        
        app.logger.info(f"Weaviate returned {len(results.objects)} results")
        
        for result_obj in results.objects:
            result_video_id = result_obj.properties.get("video_id")
            
            if result_video_id != video_id:
                video_detail_url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos/{result_video_id}"
                video_detail_response = requests.get(video_detail_url, headers=headers)
                
                if video_detail_response.status_code == 200:
                    video_detail = video_detail_response.json()
                    
                    video_url = None
                    thumbnail_url = None
                    
                    if "hls" in video_detail:
                        video_url = video_detail.get("hls", {}).get("video_url")
                        if "thumbnail_urls" in video_detail.get("hls", {}) and video_detail.get("hls", {}).get("thumbnail_urls"):
                            thumbnail_url = video_detail.get("hls", {}).get("thumbnail_urls")[0]
                    
                    similar_videos.append({
                        "video_id": result_video_id,
                        "filename": result_obj.properties.get("filename"),
                        "video_url": video_url,
                        "thumbnail_url": thumbnail_url
                    })
                    
                    if len(similar_videos) >= limit:
                        break
        
        app.logger.info(f"Found {len(similar_videos)} similar videos from WEAVIATE")
        
        if similar_videos:
            metadata = {
                "similar_videos": similar_videos,
                "similar_videos_timestamp": int(time.time())
            }
            
            success = update_video_metadata(video_id, metadata)
            
            if success:
                app.logger.info(f"Successfully cached {len(similar_videos)} similar videos for video_id: {video_id}")
            else:
                app.logger.warning(f"Failed to cache similar videos for video_id: {video_id}")
        else:
            app.logger.warning(f"No similar videos found for video_id: {video_id}")
        
        result["videos"] = similar_videos
        result["embedding_scope"] = embedding_scope
        return result
        
    except Exception as e:
        app.logger.error(f"Error finding similar videos: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return result


@app.route('/api/similar-videos/<video_id>', methods=['GET'])
def api_get_similar_videos(video_id):
    limit = request.args.get('limit', 6, type=int)
    
    result = find_similar_videos(video_id, limit)
    
    response = {
        "success": True,
        "video_id": video_id,
        "similar_videos": result["videos"],
        "source": result["source"],
        "embedding_scope": result.get("embedding_scope")
    }
    
    if result["source"] == "cache" and result["cache_age"] is not None:
        response["cache_age_seconds"] = result["cache_age"]
        response["cache_age_readable"] = f"{result['cache_age'] // 3600} hours {(result['cache_age'] % 3600) // 60} minutes"
    
    return jsonify(response)


@app.route('/api/batch-embed', methods=['POST'])
def api_batch_embed_videos():
    try:
        data = request.get_json() or {}
        page_size = min(50, data.get('page_size', 50))  
        max_pages = data.get('max_pages', 0)  # 0 means process all pages
        delay_between_pages = data.get('delay_seconds', 2) 
        

        initial_response = list_videos(page=1, page_limit=page_size)
        if not initial_response or 'page_info' not in initial_response:
            return jsonify({"error": "Failed to retrieve videos"}), 500
        
        total_pages = initial_response['page_info']['total_page']
        total_videos = initial_response['page_info']['total_results']
        
        if max_pages > 0:
            total_pages = min(total_pages, max_pages)
            
        app.logger.info(f"Starting batch embedding for {total_videos} videos across {total_pages} pages")
        
        already_embedded = set()
        if weaviate_client:
            try:
                response = weaviate_client.query.get(
                    "NatureVideo", 
                    ["video_id"]
                ).with_limit(1000).do()
                
                for item in response.get("data", {}).get("Get", {}).get("NatureVideo", []):
                    already_embedded.add(item.get("video_id"))
                
                app.logger.info(f"Found {len(already_embedded)} videos already embedded in Weaviate")
            except Exception as e:
                app.logger.error(f"Error checking existing embeddings: {str(e)}")
        
        all_results = []
        summary_report = {
            "total": 0,
            "skipped": 0,
            "stored": 0,
            "processing": 0,
            "failed": 0,
        }
        
        for current_page in range(1, total_pages + 1):
            app.logger.info(f"Processing page {current_page} of {total_pages}")
            
            if current_page == 1:
                videos_response = initial_response
            else:
                if current_page > 1 and delay_between_pages > 0:
                    time.sleep(delay_between_pages)
                
                videos_response = list_videos(page=current_page, page_limit=page_size)
            
            if not videos_response or 'data' not in videos_response:
                app.logger.error(f"Failed to retrieve videos for page {current_page}")
                continue
            
            video_ids = [video['_id'] for video in videos_response['data']]
            page_results = []
            
            for video_id in video_ids:
                summary_report["total"] += 1
                
                if video_id in already_embedded:
                    app.logger.info(f"Skipping video {video_id} - already embedded")
                    track_embedding_status(video_id, "skipped", None, "Already embedded")
                    page_results.append({
                        "video_id": video_id,
                        "status": "skipped",
                        "reason": "Already embedded"
                    })
                    summary_report["skipped"] += 1
                    continue
                    
                try:
                    embedding_data = get_video_embedding(video_id)
                    
                    if embedding_data.get("status") == "ready":
                        success = store_video_embedding_in_weaviate(video_id, embedding_data)
                        
                        status = "stored" if success else "failed"
                        track_embedding_status(
                            video_id, 
                            status, 
                            video_id, 
                            None if success else "Failed to store in Weaviate"
                        )
                        
                        page_results.append({
                            "video_id": video_id,
                            "status": status
                        })
                        
                        if success:
                            summary_report["stored"] += 1
                        else:
                            summary_report["failed"] += 1
                            
                    else:
                        track_embedding_status(
                            video_id, 
                            embedding_data.get("status", "unknown"), 
                            None, 
                            embedding_data.get("error")
                        )
                        
                        page_results.append({
                            "video_id": video_id,
                            "status": embedding_data.get("status", "unknown"),
                            "error": embedding_data.get("error")
                        })
                        
                        if embedding_data.get("status") == "processing":
                            summary_report["processing"] += 1
                        else:
                            summary_report["failed"] += 1
                            
                except Exception as e:
                    error_msg = str(e)
                    app.logger.error(f"Error processing video {video_id}: {error_msg}")
                    track_embedding_status(video_id, "error", None, error_msg)
                    page_results.append({
                        "video_id": video_id,
                        "status": "error",
                        "error": error_msg
                    })
                    summary_report["failed"] += 1
            
            all_results.extend(page_results)
            
            app.logger.info(f"Completed page {current_page}/{total_pages}: " +
                           f"Processed {len(page_results)} videos, " +
                           f"Total progress: {summary_report['stored']} stored, " +
                           f"{summary_report['skipped']} skipped, " +
                           f"{summary_report['processing']} processing, " +
                           f"{summary_report['failed']} failed")
        
        return jsonify({
            "success": True,
            "summary": summary_report,
            "pages_processed": total_pages,
            "results": all_results
        })
        
    except Exception as e:
        app.logger.error(f"Batch embedding failed: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Batch embedding failed: {str(e)}"}), 500



def update_embeddings():
    app.logger.info("Starting scheduled embedding update")
    
    try:
        videos_response = list_videos(page=1, page_limit=50)
        if not videos_response or 'data' not in videos_response:
            app.logger.error("Failed to retrieve videos for embedding update")
            return
        
        video_ids = [video['_id'] for video in videos_response['data']]
        
        for video_id in video_ids:
            try:

                embedding_data = get_video_embedding(video_id)
                
                if embedding_data.get("status") == "ready":
                    store_video_embedding_in_weaviate(video_id, embedding_data)
                    app.logger.info(f"Updated embeddings for video {video_id}")
            except Exception as e:
                app.logger.error(f"Error updating embeddings for video {video_id}: {str(e)}")
    
    except Exception as e:
        app.logger.error(f"Scheduled embedding update failed: {str(e)}")



def track_embedding_status(video_id, status, task_id=None, error=None):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    csv_path = "embedding_status.csv"
    file_exists = os.path.isfile(csv_path)
    
    with open(csv_path, 'a', newline='') as csvfile:
        fieldnames = ['timestamp', 'video_id', 'status', 'task_id', 'error']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow({
            'timestamp': timestamp,
            'video_id': video_id,
            'status': status,
            'task_id': task_id or '',
            'error': error or ''
        })

@app.route('/api/embedding-status', methods=['GET'])
def api_embedding_status():

    try:

        csv_path = "embedding_status.csv"
        if not os.path.isfile(csv_path):
            return jsonify({
                "success": True,
                "message": "No embedding status data available",
                "status": {}
            })
        

        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            
            status_by_video = {}
            for row in reader:
                video_id = row.get('video_id')
                if video_id:
                    status_by_video[video_id] = {
                        "status": row.get('status'),
                        "timestamp": row.get('timestamp'),
                        "task_id": row.get('task_id'),
                        "error": row.get('error')
                    }
            

            status_counts = {
                "total": len(status_by_video),
                "stored": sum(1 for s in status_by_video.values() if s.get("status") == "stored"),
                "processing": sum(1 for s in status_by_video.values() if s.get("status") == "processing"),
                "failed": sum(1 for s in status_by_video.values() if s.get("status") == "failed" or s.get("status") == "error"),
                "skipped": sum(1 for s in status_by_video.values() if s.get("status") == "skipped")
            }
            
            return jsonify({
                "success": True,
                "summary": status_counts,
                "status": status_by_video
            })
            
    except Exception as e:
        app.logger.error(f"Error getting embedding status: {str(e)}")
        return jsonify({"error": f"Error getting embedding status: {str(e)}"}), 500
    
@app.route('/api/download/embedding-status', methods=['GET'])
def download_embedding_status():
    csv_path = "embedding_status.csv"
    
    if not os.path.isfile(csv_path):
        return jsonify({"error": "Embedding status CSV not found"}), 404
    
    return send_file(
        csv_path,
        mimetype='text/csv',
        as_attachment=True,
        download_name='embedding_status.csv'
    )





def get_index_info():
    url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}"
    headers = {"x-api-key": API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        app.logger.error(f"Error fetching index information: {str(e)}")
        return None

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
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        app.logger.error(f"Error listing videos: {str(e)}")
        return None

def analyze_video_with_lambda(video_id, prompt="Describe this video in detail."):
    try:
        payload = {
            "video_id": video_id,
            "prompt": prompt,
            "api_key": API_KEY
        }
        
        response = lambda_client.invoke(
            FunctionName='pegasus-video-analysis',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read().decode('utf-8'))
        
        if 'error' in result:
            app.logger.error(f"Lambda function error: {result['error']}")
            return None
        
        return result
    except ClientError as e:
        app.logger.error(f"Error invoking Lambda function: {str(e)}")
        return None
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return None

def analyze_video_directly(video_id, prompt="Describe this video in detail."):
    # Generate analysis of a video using Pegasus model directly
    try:
        client = TwelveLabs(api_key=API_KEY)
        response = client.generate.text(
            video_id=video_id,
            prompt=prompt
        )
        return {"data": response.data}
    except Exception as e:
        app.logger.error(f"Error analyzing video: {str(e)}")
        return None

def update_video_metadata(video_id, metadata):

    url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos/{video_id}"
    
    payload = {
        "user_metadata": metadata
    }
    
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.put(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        app.logger.error(f"Error updating video metadata: {str(e)}")
        return None

def generate_structured_csv_report(results):

    csv_data = io.StringIO()
    csv_writer = csv.writer(csv_data)
    
    csv_writer.writerow([
        'Video ID', 'Filename', 'Analysis Timestamp', 
        'Shot', 'Subject', 'Action', 'Environment', 
        'Status', 'Raw Analysis'
    ])
    

    for result in results:
        video_id = result.get('video_id', 'N/A')
        status = 'Success' if result.get('success', False) else 'Failed'
        
        video_info = result.get('video_info', {})
        filename = video_info.get('system_metadata', {}).get('filename', 'N/A')
        
        raw_analysis = result.get('analysis', {}).get('data', 'No analysis data')
        timestamp = result.get('timestamp', time.time())
        
        structured_data = result.get('analysis', {}).get('structured_data', {})
        
        shot = structured_data.get('Shot', '')
        
        if 'condensed_format' in structured_data:
            subject = structured_data.get('condensed_format', {}).get('Subject', '')
            action = structured_data.get('condensed_format', {}).get('Action', '')
            environment = structured_data.get('condensed_format', {}).get('Environment', '')
        else:
            subject_data = structured_data.get('Subject', {})
            subject = ''.join([
                subject_data.get('Type', ''),
                subject_data.get('Classification', ''),
                subject_data.get('Species', ''),
                subject_data.get('Count', ''),
                subject_data.get('Identification', ''),
                subject_data.get('Color', '')
            ])
            
            action = structured_data.get('Action', '')
            
            env_data = structured_data.get('Environment', {})
            environment = ''.join([
                env_data.get('Time', ''),
                env_data.get('Location', ''),
                env_data.get('Weather', ''),
                env_data.get('Position', ''),
                env_data.get('Climate', '')
            ])
        
        csv_writer.writerow([
            video_id, filename, timestamp,
            shot, subject, action, environment,
            status, raw_analysis
        ])
    
    csv_data.seek(0)
    return csv_data

@app.route('/api/index', methods=['GET'])
def api_get_index_info():

    index_info = get_index_info()
    if index_info:
        return jsonify(index_info)
    return jsonify({"error": "Failed to retrieve index information"}), 500

@app.route('/api/videos', methods=['GET'])
def api_list_videos():

    page = request.args.get('page', 1, type=int)
    page_limit = request.args.get('limit', 100, type=int)
    sort_by = request.args.get('sort_by', 'created_at')
    sort_option = request.args.get('sort_option', 'desc')
    filename = request.args.get('filename')
    
    videos = list_videos(page, page_limit, sort_by, sort_option, filename)
    if videos:
        return jsonify(videos)
    return jsonify({"error": "Failed to retrieve videos"}), 500

@app.route('/api/analyze/<video_id>', methods=['POST'])
def api_analyze_video(video_id):

    data = request.get_json() or {}
    prompt = data.get('prompt', 'Describe this video in detail.')
    use_lambda = data.get('use_lambda', True)
    
    if use_lambda:
        result = analyze_video_with_lambda(video_id, prompt)
    else:
        result = analyze_video_directly(video_id, prompt)
    
    if result:
        structured_data = result.get('structured_data', {})
        
        if 'condensed_format' in structured_data:
            metadata = {
                "analysis_timestamp": int(time.time()),
                "analysis_prompt": prompt,
                "shot": structured_data.get('condensed_format', {}).get('Shot', ''),
                "subject": structured_data.get('condensed_format', {}).get('Subject', ''),
                "action": structured_data.get('condensed_format', {}).get('Action', ''),
                "environment": structured_data.get('condensed_format', {}).get('Environment', ''),
                "raw_analysis": str(result.get('data', ''))[:1000]  # Limit the size to avoid issues
            }
        else:
            metadata = {
                "analysis_timestamp": int(time.time()),
                "analysis_prompt": prompt,
                "shot": structured_data.get('Shot', ''),
                "subject": json.dumps(structured_data.get('Subject', {})),
                "action": structured_data.get('Action', ''),
                "environment": json.dumps(structured_data.get('Environment', {})),
                "raw_analysis": str(result.get('data', ''))[:1000]  # Limit the size to avoid issues
            }
        
        update_result = update_video_metadata(video_id, metadata)
        
        if update_result:
            return jsonify({
                "success": True,
                "analysis": result,
                "metadata_update": update_result
            })
        else:
            return jsonify({
                "success": True,
                "analysis": result,
                "metadata_update": "Failed to update metadata"
            })
    
    return jsonify({"error": "Failed to analyze video"}), 500





@app.route('/api/search', methods=['POST'])
def api_search_videos():
    data = request.get_json() or {}
    
    query_text = data.get('query_text', '')
    search_options = data.get('options', ['visual'])
    page_limit = data.get('page_limit', 15)  
    threshold = data.get('threshold', 'high')
    
    if not query_text:
        return jsonify({"error": "Search query text is required"}), 400
    
    try:
        app.logger.info(f"Search request received: query={query_text}, options={search_options}")
        
        client = TwelveLabs(api_key=API_KEY)
        
        search_params = {
            "index_id": INDEX_ID,
            "query_text": query_text,
            "options": search_options,
            "threshold": threshold,
            "page_limit": page_limit,
            "group_by": "video", 
            "sort_option": "score"
        }
        
        app.logger.info(f"Searching with params: {search_params}")
        search_results = client.search.query(**search_params)
        
        results = []
        for video in search_results.data:
            video_id = getattr(video, 'id', None) or getattr(video, 'video_id', None)
            
            if not video_id:
                continue
            
            video_url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos/{video_id}"
            headers = {"x-api-key": API_KEY}
            
            try:
                video_response = requests.get(video_url, headers=headers)
                video_data = video_response.json()
                
                video_stream_url = None
                if "hls" in video_data and "video_url" in video_data["hls"]:
                    video_stream_url = video_data["hls"]["video_url"]
                
                thumbnail_url = getattr(video, 'thumbnail_url', None)
                if not thumbnail_url and "hls" in video_data and "thumbnail_urls" in video_data["hls"] and video_data["hls"]["thumbnail_urls"]:
                    thumbnail_url = video_data["hls"]["thumbnail_urls"][0]
                
                filename = video_data.get("system_metadata", {}).get("filename", "Unknown")
                
                clips = []
                highest_clip_score = None
                
                for clip in getattr(video, 'clips', []):
                    clip_score = getattr(clip, 'score', None)
                    
                    if clip_score is not None:
                        if highest_clip_score is None or clip_score > highest_clip_score:
                            highest_clip_score = clip_score
                    
                    clips.append({
                        "start": getattr(clip, 'start', None),
                        "end": getattr(clip, 'end', None),
                        "score": clip_score,
                        "confidence": getattr(clip, 'confidence', None),
                        "thumbnail_url": getattr(clip, 'thumbnail_url', None)
                    })

                video_score = getattr(video, 'score', None)
                if video_score is None and highest_clip_score is not None:
                    video_score = highest_clip_score
                
                video_result = {
                    "video_id": video_id,
                    "score": video_score,
                    "filename": filename,
                    "video_url": video_stream_url,
                    "thumbnail_url": thumbnail_url,
                    "clips": clips
                }
                
                results.append(video_result)
                
            except Exception as e:
                app.logger.error(f"Error fetching video details: {str(e)}")
                results.append({
                    "video_id": video_id,
                    "score": getattr(video, 'score', None),
                    "thumbnail_url": getattr(video, 'thumbnail_url', None)
                })
        
        page_info = search_results.page_info
        pagination = {
            "total_results": getattr(page_info, 'total_results', 0),
            "limit_per_page": getattr(page_info, 'limit_per_page', 0),
            "next_page_token": getattr(page_info, 'next_page_token', None),
            "prev_page_token": getattr(page_info, 'prev_page_token', None),
            "has_more": getattr(page_info, 'next_page_token', None) is not None
        }
        

        if pagination["total_results"] > 0 and pagination["limit_per_page"] > 0:
            pagination["total_pages"] = (pagination["total_results"] + pagination["limit_per_page"] - 1) // pagination["limit_per_page"]
        else:
            pagination["total_pages"] = 1
        
        return jsonify({
            "success": True,
            "query": query_text,
            "options": search_options,
            "results": results,
            "pagination": pagination
        })
        
    except Exception as e:
        app.logger.error(f"Error searching videos: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Failed to search videos: {str(e)}"}), 500


@app.route('/api/search/next', methods=['POST'])
def api_search_next_page():
    data = request.get_json() or {}
    
    page_token = data.get('page_token')
    
    if not page_token:
        return jsonify({"error": "Page token is required"}), 400
    
    try:

        client = TwelveLabs(api_key=API_KEY)
        search_results = client.search.by_page_token(page_token=page_token)
        
        results = []
        for video in search_results.data:
            video_id = getattr(video, 'id', None) or getattr(video, 'video_id', None)
            
            if not video_id:
                continue
            
            video_url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos/{video_id}"
            headers = {"x-api-key": API_KEY}
            
            try:
                video_response = requests.get(video_url, headers=headers)
                video_data = video_response.json()
                
                video_stream_url = None
                if "hls" in video_data and "video_url" in video_data["hls"]:
                    video_stream_url = video_data["hls"]["video_url"]
                
                thumbnail_url = getattr(video, 'thumbnail_url', None)
                if not thumbnail_url and "hls" in video_data and "thumbnail_urls" in video_data["hls"] and video_data["hls"]["thumbnail_urls"]:
                    thumbnail_url = video_data["hls"]["thumbnail_urls"][0]
                
                filename = video_data.get("system_metadata", {}).get("filename", "Unknown")
                
                clips = []
                for clip in getattr(video, 'clips', []):
                    clips.append({
                        "start": getattr(clip, 'start', None),
                        "end": getattr(clip, 'end', None),
                        "score": getattr(clip, 'score', None),
                        "confidence": getattr(clip, 'confidence', None),
                        "thumbnail_url": getattr(clip, 'thumbnail_url', None)
                    })
                
                video_result = {
                    "video_id": video_id,
                    "score": getattr(video, 'score', None),
                    "filename": filename,
                    "video_url": video_stream_url,
                    "thumbnail_url": thumbnail_url, 
                    "clips": clips
                }
                
                results.append(video_result)
                
            except Exception as e:
                app.logger.error(f"Error fetching video details: {str(e)}")
                results.append({
                    "video_id": video_id,
                    "score": getattr(video, 'score', None),
                    "thumbnail_url": getattr(video, 'thumbnail_url', None)
                })
        
        page_info = search_results.page_info
        pagination = {
            "total_results": getattr(page_info, 'total_results', 0),
            "limit_per_page": getattr(page_info, 'limit_per_page', 0),
            "next_page_token": getattr(page_info, 'next_page_token', None),
            "prev_page_token": getattr(page_info, 'prev_page_token', None),
            "has_more": getattr(page_info, 'next_page_token', None) is not None
        }
        
        if pagination["total_results"] > 0 and pagination["limit_per_page"] > 0:
            pagination["total_pages"] = (pagination["total_results"] + pagination["limit_per_page"] - 1) // pagination["limit_per_page"]
        else:
            pagination["total_pages"] = 1
        
        return jsonify({
            "success": True,
            "results": results,
            "pagination": pagination
        })
        
    except Exception as e:
        app.logger.error(f"Error fetching next page: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Failed to fetch next page: {str(e)}"}), 500
    



@app.route('/api/batch-analyze', methods=['POST'])
def api_batch_analyze():

    data = request.get_json() or {}
    video_ids = data.get('video_ids', [])
    prompt = data.get('prompt', 'Describe this video in detail.')
    use_lambda = data.get('use_lambda', True)
    
    if not video_ids:

        videos_response = list_videos(page=1, page_limit=50)
        if not videos_response or 'data' not in videos_response:
            return jsonify({"error": "Failed to retrieve videos"}), 500
        
        video_ids = [video['_id'] for video in videos_response['data']]
    
    results = []
    successful_results = []
    
    for video_id in video_ids:
        video_url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos/{video_id}"
        headers = {"x-api-key": API_KEY}
        
        try:
            video_response = requests.get(video_url, headers=headers)
            video_response.raise_for_status()
            video_info = video_response.json()
        except:
            video_info = {"_id": video_id}
        
        if use_lambda:
            result = analyze_video_with_lambda(video_id, prompt)
        else:
            result = analyze_video_directly(video_id, prompt)
        
        if result:
            structured_data = result.get('structured_data', {})
            
            if 'condensed_format' in structured_data:
                metadata = {
                    "analysis_timestamp": int(time.time()),
                    "analysis_prompt": prompt,
                    "shot": structured_data.get('condensed_format', {}).get('Shot', ''),
                    "subject": structured_data.get('condensed_format', {}).get('Subject', ''),
                    "action": structured_data.get('condensed_format', {}).get('Action', ''),
                    "environment": structured_data.get('condensed_format', {}).get('Environment', ''),
                    "raw_analysis": str(result.get('data', ''))[:1000] 
                }
            else:

                metadata = {
                    "analysis_timestamp": int(time.time()),
                    "analysis_prompt": prompt,
                    "shot": structured_data.get('Shot', ''),
                    "subject": json.dumps(structured_data.get('Subject', {})),
                    "action": structured_data.get('Action', ''),
                    "environment": json.dumps(structured_data.get('Environment', {})),
                    "raw_analysis": str(result.get('data', ''))[:1000]  # Limit the size to avoid issues
                }
            
            update_result = update_video_metadata(video_id, metadata)
            
            current_result = {
                "video_id": video_id,
                "video_info": video_info,
                "success": True,
                "analysis": result,
                "timestamp": int(time.time()),
                "metadata_update": update_result if update_result else "Failed"
            }
            
            results.append(current_result)
            successful_results.append(current_result)
        else:
            results.append({
                "video_id": video_id,
                "video_info": video_info,
                "success": False,
                "timestamp": int(time.time()),
                "error": "Failed to analyze video"
            })
    
    if successful_results:
        try:
            successful_csv = generate_structured_csv_report(successful_results)
            
            timestamp = int(time.time())
            with open(f"successful_analyses_{timestamp}.csv", "w") as f:
                f.write(successful_csv.getvalue())
        except Exception as e:
            app.logger.error(f"Error generating CSV for successful analyses: {str(e)}")
    
    try:
        all_csv = generate_structured_csv_report(results)

        timestamp = int(time.time())
        with open(f"all_analyses_{timestamp}.csv", "w") as f:
            f.write(all_csv.getvalue())
    except Exception as e:
        app.logger.error(f"Error generating complete CSV report: {str(e)}")
    
    return jsonify({
        "success": True,
        "total": len(video_ids),
        "processed": len(results),
        "successful": len(successful_results),
        "results": results
    })

@app.route('/api/download/report', methods=['GET'])
def download_latest_report():

    report_type = request.args.get('type', 'all')

    if report_type == 'successful':
        prefix = 'successful_analyses_'
    else:
        prefix = 'all_analyses_'
    
    report_files = [f for f in os.listdir('.') if f.startswith(prefix) and f.endswith('.csv')]
    
    if not report_files:
        return jsonify({"error": "No report files found"}), 404
    
    latest_report = sorted(report_files, reverse=True)[0]

    return send_file(
        latest_report,
        mimetype='text/csv',
        as_attachment=True,
        download_name=latest_report
    )

@app.route('/api/metadata/<video_id>', methods=['PUT'])
def api_update_metadata(video_id):

    data = request.get_json() or {}
    
    if not data:
        return jsonify({"error": "No metadata provided"}), 400
    
    result = update_video_metadata(video_id, data)
    
    if result:
        return jsonify({
            "success": True,
            "result": result
        })
    
    return jsonify({"error": "Failed to update metadata"}), 500


def wake_up_app():
    try:
        app_url = os.getenv('APP_URL')
        if app_url:
            response = requests.get(app_url)
            if response.status_code == 200:
                print(f"Successfully pinged {app_url} at {datetime.now()}")
            else:
                print(f"Failed to ping {app_url} (status code: {response.status_code}) at {datetime.now()}")
        else:
            print("APP_URL environment variable not set.")
    except Exception as e:
        print(f"Error occurred while pinging app: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(wake_up_app, 'interval', minutes=9)
scheduler.start()
# scheduler.add_job(update_embeddings, 'interval', hours=24)

atexit.register(lambda: scheduler.shutdown())



if __name__ == '__main__':
    app.run(debug=True)