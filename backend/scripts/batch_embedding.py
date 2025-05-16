import os
import time
import argparse
import logging
from datetime import datetime

from config.settings import API_KEY, INDEX_ID
from api.utils.twelvelabs_api import list_videos, get_video_embedding
from api.utils.weaviate_api import init_weaviate_client, store_video_embedding
from api.utils.csv_utils import track_embedding_status

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("batch_embedding.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Process videos in batch to extract embeddings and store them in Weaviate
def batch_embed_videos(page_size=50, max_pages=0, delay_seconds=2, skip_existing=True):

    # Initial response to determine pagination
    logger.info(f"Starting batch embedding with page_size={page_size}, max_pages={max_pages}")
    
    initial_response = list_videos(page=1, page_limit=page_size)
    if not initial_response or 'page_info' not in initial_response:
        logger.error("Failed to retrieve videos")
        return {"error": "Failed to retrieve videos"}
    
    total_pages = initial_response['page_info']['total_page']
    total_videos = initial_response['page_info']['total_results']
    
    if max_pages > 0:
        total_pages = min(total_pages, max_pages)
        
    logger.info(f"Found {total_videos} videos across {total_pages} pages")
    
    # Check for videos already embedded if requested
    already_embedded = set()
    if skip_existing:
        if init_weaviate_client():
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
            if current_page > 1 and delay_seconds > 0:
                time.sleep(delay_seconds)
            
            videos_response = list_videos(page=current_page, page_limit=page_size)
        
        if not videos_response or 'data' not in videos_response:
            logger.error(f"Failed to retrieve videos for page {current_page}")
            continue
        
        video_ids = [video['_id'] for video in videos_response['data']]
        page_results = []
        
        # Process each video
        for video_id in video_ids:
            summary_report["total"] += 1
            
            if skip_existing and video_id in already_embedded:
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
                # Get embeddings
                embedding_data = get_video_embedding(video_id)
                
                if embedding_data.get("status") == "ready":
                    # Store in Weaviate
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
                
            # Delay
            if delay_seconds > 0:
                time.sleep(delay_seconds)
        
        all_results.extend(page_results)
        
        # Log progress after each page
        logger.info(f"Completed page {current_page}/{total_pages}: " +
                   f"Processed {len(page_results)} videos, " +
                   f"Total progress: {summary_report['stored']} stored, " +
                   f"{summary_report['skipped']} skipped, " +
                   f"{summary_report['processing']} processing, " +
                   f"{summary_report['failed']} failed")
    
    logger.info("Batch embedding completed")
    logger.info(f"Summary: Total: {summary_report['total']}, " +
               f"Stored: {summary_report['stored']}, " +
               f"Skipped: {summary_report['skipped']}, " +
               f"Processing: {summary_report['processing']}, " +
               f"Failed: {summary_report['failed']}")
    
    return {
        "success": True,
        "summary": summary_report,
        "pages_processed": total_pages,
        "results_count": len(all_results)
    }

def main():

    parser = argparse.ArgumentParser(description='Process videos in batch to extract embeddings')
    parser.add_argument('--page-size', type=int, default=50, help='Number of videos per page')
    parser.add_argument('--max-pages', type=int, default=0, help='Maximum number of pages to process (0 = all)')
    parser.add_argument('--delay', type=float, default=2, help='Delay in seconds between processing videos')
    parser.add_argument('--force', action='store_true', help='Process all videos, even if already embedded')
    
    args = parser.parse_args()
    
    if not API_KEY or not INDEX_ID:
        logger.error("API_KEY and INDEX_ID must be set in environment variables")
        print("Error, API_KEY and INDEX_ID must be set in environment variables")
        return 1
    
    result = batch_embed_videos(
        page_size=args.page_size,
        max_pages=args.max_pages,
        delay_seconds=args.delay,
        skip_existing=not args.force
    )
    
    if "error" in result:
        print(f"Error: {result['error']}")
        return 1
    
    print("\nBatch Embedding Summary")
    print(f"Total videos processed: {result['summary']['total']}")
    print(f"Videos stored: {result['summary']['stored']}")
    print(f"Videos skipped: {result['summary']['skipped']}")
    print(f"Videos processing: {result['summary']['processing']}")
    print(f"Videos failed: {result['summary']['failed']}")
    print(f"\nSee batch_embedding.log for detailed logs")
    
    return 0

if __name__ == "__main__":
    exit(main())