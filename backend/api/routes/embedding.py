from flask import Blueprint, jsonify, request, send_file
import logging
import time

from api.utils.twelvelabs_api import list_videos, get_video_embedding
from api.utils.weaviate_api import store_video_embedding
from api.utils.csv_utils import track_embedding_status, get_embedding_status
from config.settings import EMBEDDING_STATUS_FILE

logger = logging.getLogger(__name__)

embedding_bp = Blueprint('embedding', __name__)

@embedding_bp.route('/batch-embed', methods=['POST'])
def api_batch_embed_videos():

    try:
        data = request.get_json() or {}
        page_size = min(50, data.get('page_size', 50))  
        max_pages = data.get('max_pages', 0)  # 0 means process all pages
        delay_between_pages = data.get('delay_seconds', 2) 
        
        # Initial response to determine pagination
        initial_response = list_videos(page=1, page_limit=page_size)
        if not initial_response or 'page_info' not in initial_response:
            return jsonify({"error": "Failed to retrieve videos"}), 500
        
        total_pages = initial_response['page_info']['total_page']
        total_videos = initial_response['page_info']['total_results']
        
        if max_pages > 0:
            total_pages = min(total_pages, max_pages)
            
        logger.info(f"Starting batch embedding for {total_videos} videos across {total_pages} pages")
        
        # Check for videos already embedded
        already_embedded = set()
        from api.utils.weaviate_api import get_weaviate_client
        
        client = get_weaviate_client()
        if client:
            try:
                collection = client.collections.get("NatureVideo")
                
                response = collection.query.fetch_objects(
                    limit=2000,
                    return_properties=["video_id"]
                )
                
                for obj in response.objects:
                    already_embedded.add(obj.properties.get("video_id"))
                
                logger.info(f"Found {len(already_embedded)} videos already embedded in Weaviate")
            except Exception as e:
                logger.error(f"Error checking existing embeddings: {str(e)}")
        
        all_results = []
        summary_report = {
            "total": 0,
            "skipped": 0,
            "stored": 0,
            "processing": 0,
            "failed": 0,
        }
        
        for current_page in range(1, total_pages + 1):
            logger.info(f"Processing page {current_page} of {total_pages}")
            
            if current_page == 1:
                videos_response = initial_response
            else:
                if current_page > 1 and delay_between_pages > 0:
                    time.sleep(delay_between_pages)
                
                videos_response = list_videos(page=current_page, page_limit=page_size)
            
            if not videos_response or 'data' not in videos_response:
                logger.error(f"Failed to retrieve videos for page {current_page}")
                continue
            
            video_ids = [video['_id'] for video in videos_response['data']]
            page_results = []
            
            # Process each video in the page
            for video_id in video_ids:
                summary_report["total"] += 1
                
                if video_id in already_embedded:
                    logger.info(f"Skipping video {video_id} - already embedded")
                    track_embedding_status(video_id, "skipped", None, "Already embedded")
                    page_results.append({
                        "video_id": video_id,
                        "status": "skipped",
                        "reason": "Already embedded"
                    })
                    summary_report["skipped"] += 1
                    continue
                    
                try:
                    # Get embeddings for the video
                    embedding_data = get_video_embedding(video_id)
                    
                    if embedding_data.get("status") == "ready":
                        # Store embeddings in Weaviate
                        success = store_video_embedding(video_id, embedding_data)
                        
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
                        # Track status for videos not ready
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
                    logger.error(f"Error processing video {video_id}: {error_msg}")
                    track_embedding_status(video_id, "error", None, error_msg)
                    page_results.append({
                        "video_id": video_id,
                        "status": "error",
                        "error": error_msg
                    })
                    summary_report["failed"] += 1
            
            all_results.extend(page_results)
            
            logger.info(f"Completed page {current_page}/{total_pages}: " +
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
        logger.error(f"Batch embedding failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Batch embedding failed: {str(e)}"}), 500


# Status of embedding operations
@embedding_bp.route('/embedding-status', methods=['GET'])
def api_embedding_status():

    return jsonify(get_embedding_status())

@embedding_bp.route('/download/embedding-status', methods=['GET'])
def download_embedding_status():

    if not os.path.isfile(EMBEDDING_STATUS_FILE):
        return jsonify({"error": "Embedding status CSV not found"}), 404
    
    return send_file(
        EMBEDDING_STATUS_FILE,
        mimetype='text/csv',
        as_attachment=True,
        download_name='embedding_status.csv'
    )


# Embedding for a specific video
@embedding_bp.route('/embedding/<video_id>', methods=['GET'])
def api_get_embedding(video_id):

    embedding_data = get_video_embedding(video_id)
    
    if embedding_data.get("status") == "ready":
        return jsonify({
            "success": True,
            "video_id": video_id,
            "embedding_data": embedding_data
        })
    else:
        error_msg = embedding_data.get("error", "Unknown error")
        return jsonify({
            "success": False,
            "video_id": video_id,
            "status": embedding_data.get("status", "error"),
            "error": error_msg
        }), 400

# Store embedding for a specific video in Weaviate
@embedding_bp.route('/store-embedding/<video_id>', methods=['POST'])
def api_store_embedding(video_id):

    try:
        embedding_data = get_video_embedding(video_id)
        
        if embedding_data.get("status") != "ready":
            error_msg = embedding_data.get("error", "Unknown error")
            track_embedding_status(video_id, "failed", None, error_msg)
            return jsonify({
                "success": False,
                "video_id": video_id,
                "status": embedding_data.get("status", "error"),
                "error": error_msg
            }), 400
        
        # Store in Weaviate
        success = store_video_embedding(video_id, embedding_data)
        
        if success:
            track_embedding_status(video_id, "stored", video_id)
            return jsonify({
                "success": True,
                "video_id": video_id,
                "message": "Embedding stored successfully"
            })
        else:
            track_embedding_status(video_id, "failed", None, "Failed to store in Weaviate")
            return jsonify({
                "success": False,
                "video_id": video_id,
                "error": "Failed to store embedding in Weaviate"
            }), 500
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error storing embedding for video {video_id}: {error_msg}")
        track_embedding_status(video_id, "error", None, error_msg)
        return jsonify({
            "success": False,
            "video_id": video_id,
            "error": error_msg
        }), 500