import os
import csv
import io
import json
import logging
from datetime import datetime

from config.settings import (
    EMBEDDING_STATUS_FILE,
    ANALYSIS_RESULTS_FILE,
    DETAILED_ANALYSIS_RESULTS_FILE
)

logger = logging.getLogger(__name__)

def track_embedding_status(video_id, status, task_id=None, error=None):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    file_exists = os.path.isfile(EMBEDDING_STATUS_FILE)
    
    with open(EMBEDDING_STATUS_FILE, 'a', newline='') as csvfile:
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
        logger.error(log_message)
    else:
        logger.info(log_message)

def get_embedding_status():

    try:
        if not os.path.isfile(EMBEDDING_STATUS_FILE):
            return {
                "success": True,
                "message": "No embedding status data available",
                "status": {}
            }
        
        with open(EMBEDDING_STATUS_FILE, 'r') as csvfile:
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
            
            return {
                "success": True,
                "summary": status_counts,
                "status": status_by_video
            }
            
    except Exception as e:
        logger.error(f"Error getting embedding status: {str(e)}")
        return {"error": f"Error getting embedding status: {str(e)}"}

def save_analysis_result(video_id, filename, status, error=None):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    file_exists = os.path.isfile(ANALYSIS_RESULTS_FILE)
    
    with open(ANALYSIS_RESULTS_FILE, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['timestamp', 'video_id', 'filename', 'status', 'error']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow({
            'timestamp': timestamp,
            'video_id': video_id,
            'filename': filename,
            'status': status,
            'error': error or ""
        })

def save_detailed_analysis_result(video_id, filename, status, analysis_data=None, error=None):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    file_exists = os.path.isfile(DETAILED_ANALYSIS_RESULTS_FILE)
    
    with open(DETAILED_ANALYSIS_RESULTS_FILE, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'timestamp', 'video_id', 'filename', 'status', 
            'shot', 'subject', 'action', 'environment', 
            'narrative_flow', 'additional_details', 'summary', 'error'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        row_data = {
            'timestamp': timestamp,
            'video_id': video_id,
            'filename': filename,
            'status': status,
            'error': error or ""
        }
        
        if analysis_data and isinstance(analysis_data, dict):
            row_data['shot'] = analysis_data.get('Shot', '')
            
            subject = analysis_data.get('Subject', {})
            if isinstance(subject, dict):
                subject_str = []
                for key, value in subject.items():
                    if value:
                        subject_str.append(f"{key}: {value}")
                row_data['subject'] = " | ".join(subject_str)
            else:
                row_data['subject'] = str(subject)
            
            row_data['action'] = analysis_data.get('Action', '')
            
            environment = analysis_data.get('Environment', {})
            if isinstance(environment, dict):
                env_str = []
                for key, value in environment.items():
                    if value:
                        env_str.append(f"{key}: {value}")
                row_data['environment'] = " | ".join(env_str)
            else:
                row_data['environment'] = str(environment)
            
            row_data['narrative_flow'] = analysis_data.get('Narrative Flow', '')
            row_data['additional_details'] = analysis_data.get('Additional Details', '')
            
            # Summary
            summary = []
            if analysis_data.get('Shot'):
                summary.append(f"Shot: {analysis_data['Shot']}")
            if analysis_data.get('Action'):
                summary.append(f"Action: {analysis_data['Action']}")
            
            # Add subject to summary
            if isinstance(analysis_data.get('Subject'), dict):

                for id_key in ['Identification', 'Specific identification', 'Species/Category', 'Type']:
                    if id_key in analysis_data['Subject'] and analysis_data['Subject'][id_key]:
                        summary.append(f"Subject: {analysis_data['Subject'][id_key]}")
                        break
            elif analysis_data.get('Subject'):
                summary.append(f"Subject: {analysis_data['Subject']}")
            
            row_data['summary'] = " | ".join(summary)
        
        writer.writerow(row_data)

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
        filename = video_info.get('user_metadata', {}).get('filename', 'N/A')
        
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

def normalize_metadata_key(key):

    import re
    
    key = key.replace(" ", "_")
    key = re.sub(r'[^a-zA-Z0-9_]', '', key)
    return key.lower()