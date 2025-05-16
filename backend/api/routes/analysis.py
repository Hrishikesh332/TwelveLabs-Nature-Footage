from flask import Blueprint, jsonify, request, send_file
import logging
import time
import os
from datetime import datetime

from api.utils.generate_analysis import analyze_video, process_analysis_result
from api.utils.twelvelabs_api import list_videos, get_video_info
from api.utils.csv_utils import save_analysis_result, save_detailed_analysis_result, generate_structured_csv_report

logger = logging.getLogger(__name__)

analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/analyze/<video_id>', methods=['POST'])
def api_analyze_video(video_id):

    data = request.get_json() or {}
    prompt = data.get('prompt')
    use_lambda = data.get('use_lambda', True)
    
    video_info = get_video_info(video_id)
    filename = video_info.get("system_metadata", {}).get("filename", "Unknown") if video_info else "Unknown"
    
    try:
        logger.info(f"Analyzing video {video_id} ({filename})")
        result = analyze_video(video_id, prompt, use_lambda)
        
        # Process the result and update metadata
        success, processed_result = process_analysis_result(video_id, result)
        
        if success:
            status = "success"
            save_analysis_result(video_id, filename, status)
            save_detailed_analysis_result(video_id, filename, status, result.get('structured_data'))
        else:
            status = "failure"
            save_analysis_result(video_id, filename, status, processed_result)
            save_detailed_analysis_result(video_id, filename, status, None, processed_result)
        
        return jsonify({
            "success": success,
            "analysis": result,
            "video_id": video_id,
            "filename": filename,
            "metadata_update": "Success" if success else processed_result
        })
    
    except Exception as e:
        logger.error(f"Error analyzing video {video_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Save error to CSV
        save_analysis_result(video_id, filename, "error", str(e))
        
        return jsonify({
            "success": False,
            "error": f"Error analyzing video: {str(e)}",
            "video_id": video_id,
            "filename": filename
        }), 500

@analysis_bp.route('/batch-analyze', methods=['POST'])
def api_batch_analyze():

    data = request.get_json() or {}
    video_ids = data.get('video_ids', [])
    prompt = data.get('prompt')
    use_lambda = data.get('use_lambda', True)
    limit = data.get('limit')
    
    if not video_ids:
        # If no video IDs provided, fetch videos from the index
        videos_response = list_videos(page=1, page_limit=50)
        if not videos_response or 'data' not in videos_response:
            return jsonify({"error": "Failed to retrieve videos"}), 500
        
        video_ids = [video['_id'] for video in videos_response['data']]
    
    # Apply limit if specify while running
    if limit and isinstance(limit, int) and limit > 0:
        video_ids = video_ids[:limit]
    
    results = []
    successful_results = []
    
    # Process each video
    for video_id in video_ids:
        try:
            video_info = get_video_info(video_id)
            
            # Analyze the video
            result = analyze_video(video_id, prompt, use_lambda)
            
            # Process the result and update metadata
            success, processed_result = process_analysis_result(video_id, result)
            
            # Save results to CSV
            filename = video_info.get("system_metadata", {}).get("filename", "Unknown") if video_info else "Unknown"
            
            if success:
                status = "success"
                save_analysis_result(video_id, filename, status)
                save_detailed_analysis_result(video_id, filename, status, result.get('structured_data'))
            else:
                status = "failure"
                save_analysis_result(video_id, filename, status, processed_result)
                save_detailed_analysis_result(video_id, filename, status, None, processed_result)
            
            current_result = {
                "video_id": video_id,
                "video_info": video_info,
                "success": success,
                "analysis": result,
                "timestamp": int(time.time()),
                "metadata_update": "Success" if success else processed_result
            }
            
            results.append(current_result)
            
            if success:
                successful_results.append(current_result)
            
        except Exception as e:
            logger.error(f"Error analyzing video {video_id}: {str(e)}")
            
            # Get video info if not already fetched
            if 'video_info' not in locals() or video_info is None:
                try:
                    video_info = get_video_info(video_id)
                except:
                    video_info = {"_id": video_id}
            
            # Save error to CSV
            filename = video_info.get("system_metadata", {}).get("filename", "Unknown") if video_info else "Unknown"
            save_analysis_result(video_id, filename, "error", str(e))
            
            results.append({
                "video_id": video_id,
                "video_info": video_info,
                "success": False,
                "timestamp": int(time.time()),
                "error": f"Error analyzing video: {str(e)}"
            })
    
    # Generate CSV reports for the tracking
    if successful_results:
        try:
            successful_csv = generate_structured_csv_report(successful_results)
            
            timestamp = int(time.time())
            with open(f"successful_analyses_{timestamp}.csv", "w") as f:
                f.write(successful_csv.getvalue())
        except Exception as e:
            logger.error(f"Error generating CSV for successful analyses: {str(e)}")
    
    try:
        all_csv = generate_structured_csv_report(results)

        timestamp = int(time.time())
        with open(f"all_analyses_{timestamp}.csv", "w") as f:
            f.write(all_csv.getvalue())
    except Exception as e:
        logger.error(f"Error generating complete CSV report: {str(e)}")
    
    return jsonify({
        "success": True,
        "total": len(video_ids),
        "processed": len(results),
        "successful": len(successful_results),
        "results": results
    })

@analysis_bp.route('/download/report', methods=['GET'])
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