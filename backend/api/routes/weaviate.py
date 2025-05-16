from flask import Blueprint, jsonify, request
import logging
import time

# Create blueprint
weaviate_bp = Blueprint('weaviate', __name__)

logger = logging.getLogger(__name__)


# Recreate the Weaviate schema for video embeddings
@weaviate_bp.route('/recreate-schema', methods=['POST'])
def api_recreate_schema():

    try:
        from api.utils.twelvelabs_api import list_videos, get_video_embedding
        from api.utils.weaviate_api import recreate_videos_schema
        
        # Get sample video
        videos_response = list_videos(page=1, page_limit=1)
        
        if not videos_response or 'data' not in videos_response or not videos_response['data']:
            return jsonify({"error": "No videos found to determine vector dimensions"}), 500
        
        sample_video_id = videos_response['data'][0]['_id']
        embedding_data = get_video_embedding(sample_video_id)
        
        vector_dimensions = None
        if embedding_data.get("status") == "ready":
            segments = embedding_data.get("video_embedding", {}).get("segments", [])
            if segments:
                first_vector = segments[0].get("float", [])
                vector_dimensions = len(first_vector)
        
        if not vector_dimensions:
            return jsonify({"error": "Could not determine vector dimensions from sample video"}), 500
        
        logger.info(f"Detected vector dimensions: {vector_dimensions}")
        
        # Recreate schema
        success = recreate_videos_schema(vector_dimensions)
        
        if success:
            return jsonify({
                "success": True, 
                "message": f"Schema recreated successfully with {vector_dimensions} dimensions"
            })
        else:
            return jsonify({"error": "Failed to recreate schema"}), 500
            
    except Exception as e:
        logger.error(f"Error in recreate schema process: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Error recreating schema: {str(e)}"}), 500


@weaviate_bp.route('/similar-videos/<video_id>', methods=['GET'])
def api_get_similar_videos(video_id):
    import json
    from api.utils.twelvelabs_api import get_video_info, update_video_metadata
    from api.utils.weaviate_api import find_similar_videos


    limit = request.args.get('limit', 6, type=int)

    # Step 1 - Check metadata cache (using `similar_videos_str` which is a key)
    video_info = get_video_info(video_id)
    if video_info and 'user_metadata' in video_info:
        user_metadata = video_info['user_metadata']
        if 'similar_videos_str' in user_metadata:
            try:
                similar_videos = json.loads(user_metadata['similar_videos_str'])

                # Append video URLs
                for video in similar_videos:
                    if isinstance(video, dict):
                        vid_id = video.get('video_id')
                        if vid_id:
                            filename = video.get("filename")
                            if filename:
                                video['video_url'] = f"/api/video/{filename}"

                return jsonify({
                    "success": True,
                    "video_id": video_id,
                    "similar_videos": similar_videos,
                    "source": "metadata"
                })
            except Exception as e:
                logger.warning(f"Failed to parse similar_videos_str from metadata: {str(e)}")

    # Step 2 - Cache miss or error — do Weaviate search
    similar_videos = find_similar_videos(video_id, limit=limit)

    for video in similar_videos:
        if isinstance(video, dict):
            vid_id = video.get('video_id')
            if vid_id:
                filename = video.get("filename")
                if filename:
                    video['video_url'] = f"/api/video/{filename}"

    # Step 3 - Store results as JSON string in metadata
    if similar_videos:
        try:
            similar_videos_str = json.dumps(similar_videos)
            update_video_metadata(video_id, {
                "similar_videos_str": similar_videos_str
            })
        except Exception as e:
            logger.warning(f"Failed to store similar_videos_str in metadata: {str(e)}")

    return jsonify({
        "success": True,
        "video_id": video_id,
        "similar_videos": similar_videos,
        "source": "weaviate"
    })

@weaviate_bp.route('/debug-similar-videos/<video_id>', methods=['GET'])
def api_debug_similar_videos(video_id):

    from api.utils.twelvelabs_api import get_video_info, get_video_embedding
    from api.utils.weaviate_api import get_weaviate_client
    
    debug_info = {
        "video_id": video_id,
        "steps": []
    }
    
    try:
        client = get_weaviate_client()
        if not client:
            debug_info["error"] = "Weaviate client not initialized"
            return jsonify(debug_info), 500
        
        debug_info["steps"].append("Weaviate client is initialized")
        
        # Get video info
        video_info = get_video_info(video_id)
        debug_info["steps"].append(f"Twelve Labs API response status: {200 if video_info else 404}")
        
        if not video_info:
            debug_info["error"] = "Failed to get video info"
            return jsonify(debug_info), 400
            
        debug_info["video_info"] = {
            "filename": video_info.get("system_metadata", {}).get("filename", "unknown"),
            "has_user_metadata": "user_metadata" in video_info
        }
        
        # Get embedding data
        embedding_data = get_video_embedding(video_id)
        debug_info["embedding_status"] = embedding_data.get("status")
        
        if embedding_data.get("status") != "ready":
            debug_info["error"] = f"Embedding not ready: {embedding_data.get('error', 'Unknown error')}"
            return jsonify(debug_info), 400
        
        segments = embedding_data.get("video_embedding", {}).get("segments", [])
        debug_info["total_segments"] = len(segments)
        
        # Check for visual embedding
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
        
        # Check if video is in Weaviate
        try:
            collection = client.collections.get("NatureVideo")

            from weaviate.classes.query import Filter
            existing_check = collection.query.fetch_objects(
                filters=Filter.by_property("video_id").equal(video_id),
                limit=1
            )
            
            debug_info["video_in_weaviate"] = len(existing_check.objects) > 0
            
            # Do a similar vector search
            similar_results = collection.query.near_vector(
                near_vector=visual_embedding,
                limit=7,
                return_metadata=["certainty"], 
                return_properties=["video_id", "filename", "embedding_type", "scope"]
            )

            
            # debug_info["similar_results_count"] = len(similar_results.objects)
            
            # Extract just the similar videos (not including the original)
            similar_videos = []
            for obj in similar_results.objects:
                props = obj.properties
                if props.get("video_id") != video_id:
                    similar_videos.append({
                        "video_id": props.get("video_id"),
                        "filename": props.get("filename"),
                        "embedding_type": props.get("embedding_type"),
                        "scope": props.get("scope"),
                        "similarity": obj.metadata.certainty if hasattr(obj, 'metadata') and hasattr(obj.metadata, 'certainty') else None
                    })

            
            debug_info["similar_videos_found"] = len(similar_videos)
            debug_info["similar_videos_preview"] = similar_videos[:3]
            
        except Exception as e:
            debug_info["weaviate_error"] = str(e)
            import traceback
            debug_info["traceback"] = traceback.format_exc()
            
        return jsonify(debug_info)
        
    except Exception as e:
        debug_info["error"] = f"Unexpected error: {str(e)}"
        import traceback
        debug_info["traceback"] = traceback.format_exc()
        return jsonify(debug_info), 500


@weaviate_bp.route('/collection-stats', methods=['GET'])
def api_collection_stats():
    from api.utils.weaviate_api import get_collection_stats
    
    stats = get_collection_stats()
    
    if "error" in stats:
        return jsonify(stats), 500
    
    return jsonify(stats)