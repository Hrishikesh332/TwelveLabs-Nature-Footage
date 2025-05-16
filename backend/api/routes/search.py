from flask import Blueprint, jsonify, request
import logging

from api.utils.twelvelabs_api import search_videos, search_by_page_token, get_video_info
from api.utils.s3_utils import get_video_path

logger = logging.getLogger(__name__)

search_bp = Blueprint('search', __name__)

@search_bp.route('/search', methods=['POST'])
def api_search_videos():

    data = request.get_json() or {}
    
    query_text = data.get('query_text', '')
    search_options = data.get('options', ['visual'])
    page_limit = data.get('page_limit', 15)  
    threshold = data.get('threshold', 'high')
    
    if not query_text:
        return jsonify({"error": "Search query text is required"}), 400
    
    try:
        logger.info(f"Search request received: query={query_text}, options={search_options}")
        
        search_results = search_videos(query_text, search_options, page_limit, threshold)
        
        if not search_results:
            return jsonify({"error": "Search failed"}), 500
        
        results = []
        
        # Process each video in the search results
        for video in search_results.data:
            video_id = getattr(video, 'id', None) or getattr(video, 'video_id', None)
            
            if not video_id:
                continue
            
            # Get additional video information
            video_info = get_video_info(video_id)
            
            if video_info:
                # Create S3 streaming URL 
                filename = video_info.get("system_metadata", {}).get("filename", "Unknown")
                video_stream_url = f"/api/video/{filename}"
                
                thumbnail_url = getattr(video, 'thumbnail_url', None)
                if not thumbnail_url and "hls" in video_info and "thumbnail_urls" in video_info["hls"] and video_info["hls"]["thumbnail_urls"]:
                    thumbnail_url = video_info["hls"]["thumbnail_urls"][0]
                
                filename = video_info.get("system_metadata", {}).get("filename", "Unknown")
                
                # Process clips
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
                
                # Create result object
                video_result = {
                    "video_id": video_id,
                    "score": video_score,
                    "filename": filename,
                    "video_url": video_stream_url,
                    "thumbnail_url": thumbnail_url,
                    "clips": clips
                }
                
                results.append(video_result)
            else:
                # Fallback if video info is not available
                results.append({
                    "video_id": video_id,
                    "score": getattr(video, 'score', None),
                    "thumbnail_url": getattr(video, 'thumbnail_url', None)
                })
        
        # Process pagination information
        page_info = search_results.page_info
        pagination = {
            "total_results": getattr(page_info, 'total_results', 0),
            "limit_per_page": getattr(page_info, 'limit_per_page', 0),
            "next_page_token": getattr(page_info, 'next_page_token', None),
            "prev_page_token": getattr(page_info, 'prev_page_token', None),
            "has_more": getattr(page_info, 'next_page_token', None) is not None
        }
        
        # Calculate total pages
        if pagination["total_results"] > 0 and pagination["limit_per_page"] > 0:
            pagination["total_pages"] = (pagination["total_results"] + pagination["limit_per_page"] - 1) // pagination["limit_per_page"]
        else:
            pagination["total_pages"] = 1
        
        # Return complete response
        return jsonify({
            "success": True,
            "query": query_text,
            "options": search_options,
            "results": results,
            "pagination": pagination
        })
        
    except Exception as e:
        logger.error(f"Error searching videos: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Failed to search videos: {str(e)}"}), 500

@search_bp.route('/search/next', methods=['POST'])
def api_search_next_page():

    data = request.get_json() or {}
    
    page_token = data.get('page_token')
    
    if not page_token:
        return jsonify({"error": "Page token is required"}), 400
    
    try:
        search_results = search_by_page_token(page_token)
        
        if not search_results:
            return jsonify({"error": "Failed to retrieve next page"}), 500
        
        results = []
        
        # Process each video in the search results
        for video in search_results.data:
            video_id = getattr(video, 'id', None) or getattr(video, 'video_id', None)
            
            if not video_id:
                continue
            
            # Get additional video information
            video_info = get_video_info(video_id)
            
            if video_info:
                # Create S3 streaming URL 
                filename = video_info.get("system_metadata", {}).get("filename", "Unknown")
                video_stream_url = f"/api/video/{filename}"
                
                thumbnail_url = getattr(video, 'thumbnail_url', None)
                if not thumbnail_url and "hls" in video_info and "thumbnail_urls" in video_info["hls"] and video_info["hls"]["thumbnail_urls"]:
                    thumbnail_url = video_info["hls"]["thumbnail_urls"][0]
                
                filename = video_info.get("system_metadata", {}).get("filename", "Unknown")
                
                # Process clips
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
                
                # Create result object
                video_result = {
                    "video_id": video_id,
                    "score": video_score,
                    "filename": filename,
                    "video_url": video_stream_url,
                    "thumbnail_url": thumbnail_url,
                    "clips": clips
                }
                
                results.append(video_result)
            else:
                # Fallback if video info is not available
                results.append({
                    "video_id": video_id,
                    "score": getattr(video, 'score', None),
                    "thumbnail_url": getattr(video, 'thumbnail_url', None)
                })
        
        # Process pagination information
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
        logger.error(f"Error fetching next page: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Failed to fetch next page: {str(e)}"}), 500