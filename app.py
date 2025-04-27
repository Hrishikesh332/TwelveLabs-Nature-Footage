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

load_dotenv()
INDEX_ID = os.getenv("INDEX_ID")
API_KEY = os.getenv("API_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

app = Flask(__name__)

lambda_client = boto3.client(
    'lambda', 
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
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
    # Generate a CSV report from structured analysis results
    csv_data = io.StringIO()
    csv_writer = csv.writer(csv_data)
    
    csv_writer.writerow([
        'Video ID', 'Filename', 'Analysis Timestamp', 
        'Shot', 'Subject', 'Action', 'Environment', 
        'Status', 'Raw Analysis'
    ])
    
    # Write data rows
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


@app.route('/api/search', methods=['POST'])
def api_search_videos():
    data = request.get_json() or {}
    
    query_text = data.get('query_text', '')
    search_options = data.get('options', ['visual'])
    page = data.get('page', 1)
    page_token = data.get('page_token')
    page_limit = 15 
    
    if not query_text:
        return jsonify({"error": "Search query text is required"}), 400
    
    try:
        client = TwelveLabs(api_key=API_KEY)
        

        search_params = {
            "index_id": INDEX_ID,
            "query_text": query_text,
            "options": search_options,
            "threshold": "high", 
            "page_limit": page_limit, 
            "sort_option": "score", 
        }
        
        if page_token:
            search_params["page_token"] = page_token
        
        search_results = client.search.query(**search_params)
        
        results = []
        for clip in search_results.data:
            video_id = clip.video_id
            
            video_url = f"https://api.twelvelabs.io/v1.3/indexes/{INDEX_ID}/videos/{video_id}"
            headers = {"x-api-key": API_KEY}
            
            try:
                video_response = requests.get(video_url, headers=headers)
                video_response.raise_for_status()
                video_data = video_response.json()
                
                video_url = None
                if "hls" in video_data and "video_url" in video_data["hls"]:
                    video_url = video_data["hls"]["video_url"]
                
                thumbnail_url = clip.thumbnail_url
                if not thumbnail_url and "hls" in video_data and "thumbnail_urls" in video_data["hls"] and video_data["hls"]["thumbnail_urls"]:
                    thumbnail_url = video_data["hls"]["thumbnail_urls"][0]
                
                filename = video_data.get("system_metadata", {}).get("filename")
                
                results.append({
                    "video_id": video_id,
                    "score": clip.score,
                    "start": clip.start,
                    "end": clip.end,
                    "confidence": clip.confidence,
                    "video_url": video_url,
                    "thumbnail_url": thumbnail_url,
                    "filename": filename
                })
            except Exception as e:
                app.logger.error(f"Error fetching video details for {video_id}: {str(e)}")
                results.append({
                    "video_id": video_id,
                    "score": clip.score,
                    "start": clip.start,
                    "end": clip.end,
                    "confidence": clip.confidence,
                    "video_url": None,
                    "thumbnail_url": clip.thumbnail_url
                })
        
        total_results = search_results.page_info.total_results
        limit_per_page = search_results.page_info.limit_per_page
        next_page_token = search_results.page_info.next_page_token

        total_pages = (total_results + limit_per_page - 1) // limit_per_page if total_results > 0 else 1
        
        return jsonify({
            "success": True,
            "query": query_text,
            "options": search_options,
            "results": results,
            "pagination": {
                "page": page,
                "total_results": total_results,
                "total_pages": total_pages,
                "next_page_token": next_page_token,
                "has_more": next_page_token is not None
            }
        })
        
    except Exception as e:
        app.logger.error(f"Error searching videos: {str(e)}")
        return jsonify({"error": f"Failed to search videos: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)