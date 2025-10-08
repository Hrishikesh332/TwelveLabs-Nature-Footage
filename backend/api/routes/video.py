from flask import Blueprint, jsonify, request, Response
import logging

logger = logging.getLogger(__name__)


video_bp = Blueprint('video', __name__)


# List videos from the TwelveLabs index
@video_bp.route('/videos', methods=['GET'])
def api_list_videos():
    from api.utils.twelvelabs_api import list_videos
    
    page = request.args.get('page', 1, type=int)
    page_limit = request.args.get('limit', 50, type=int)
    sort_by = request.args.get('sort_by', 'created_at')
    sort_option = request.args.get('sort_option', 'desc')
    filename = request.args.get('filename')
    
    videos = list_videos(page, page_limit, sort_by, sort_option, filename)
    if videos:
        return jsonify(videos)
    return jsonify({"error": "Failed to retrieve videos"}), 500


# Information about a specific video
@video_bp.route('/videos/<video_id>', methods=['GET'])
def api_get_video_info(video_id):

    from api.utils.twelvelabs_api import get_video_info
    from api.utils.s3_utils import get_video_path
    
    include_embeddings = request.args.get('include_embeddings', 'false').lower() == 'true'
    
    video_info = get_video_info(video_id, include_embeddings)
    if video_info:
        # If S3 streaming is enabled, add stream URL
        video_path = get_video_path(video_id)
        stream_url = f"/api/video/{video_path}"
        
        if "hls" not in video_info:
            video_info["hls"] = {}
        
        # Replace the video URL with our streaming URL
        video_info["hls"]["video_url"] = stream_url
        
        return jsonify(video_info)
    return jsonify({"error": "Failed to retrieve video information"}), 500


# Stream a video file from S3
@video_bp.route('/video/<path:filename>', methods=['GET'])
def api_stream_video(filename):
    from api.utils.s3_utils import stream_video_from_s3
    

    if '/' not in filename and filename.endswith('.mp4'):
        logger.info(f"Received simple filename: {filename}, trying to construct S3 path...")
        
        # Try common S3 path patterns based on the filename
        # Pattern: JU231212_0147.mp4 -> JU/JU231212/q4/JU231212_0147.mp4
        if filename.startswith('JU') and '_' in filename:
            # Extract the prefix (e.g., "JU231212" from "JU231212_0147.mp4")
            prefix = filename.split('_')[0]
            # Try the pattern: JU/JU231212/q4/JU231212_0147.mp4
            likely_path = f"JU/{prefix}/q4/{filename}"
            logger.info(f"Trying likely S3 path: {likely_path}")
            
            # Test if this path exists in S3
            try:
                from api.utils.s3_utils import s3_client
                from config.settings import S3_BUCKET_NAME
                s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=likely_path)
                logger.info(f"Found video at path: {likely_path}")
                return stream_video_from_s3(likely_path)
            except Exception as e:
                logger.warning(f"Path {likely_path} not found in S3: {str(e)}")
        
        # If pattern matching fails, try the original filename
        logger.warning(f"Could not find video with filename: {filename}")
    
    return stream_video_from_s3(filename)


# Get metadata for a specific video
@video_bp.route('/metadata/<video_id>', methods=['GET'])
def api_get_metadata(video_id):
    from api.utils.twelvelabs_api import get_video_metadata
    
    metadata = get_video_metadata(video_id)
    return jsonify(metadata)


# Update metadata for a specific video
@video_bp.route('/metadata/<video_id>', methods=['PUT'])
def api_update_metadata(video_id):
    from api.utils.twelvelabs_api import update_video_metadata
    
    data = request.get_json() or {}
    
    if not data:
        return jsonify({"error": "No metadata provided"}), 400
    
    success, result = update_video_metadata(video_id, data)
    
    if success:
        return jsonify({
            "success": True,
            "result": result
        })
    
    return jsonify({"error": "Failed to update metadata", "details": result}), 500


# Update a single field in the metadata for a specific video
@video_bp.route('/metadata/<video_id>/field', methods=['PUT'])
def api_update_metadata_field(video_id):
    from api.utils.twelvelabs_api import update_single_field_metadata
    
    data = request.get_json() or {}
    
    if not data or 'field_name' not in data or 'field_value' not in data:
        return jsonify({"error": "Missing required fields: field_name and field_value"}), 400
    
    field_name = data['field_name']
    field_value = data['field_value']
    
    success, result = update_single_field_metadata(video_id, field_name, field_value)
    
    if success:
        return jsonify({
            "success": True,
            "result": result
        })
    
    return jsonify({"error": "Failed to update metadata field", "details": result}), 500