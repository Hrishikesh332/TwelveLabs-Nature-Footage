import os
import boto3
from flask import Response, stream_with_context
import logging
import re

from config.settings import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
    S3_BUCKET_NAME
)

logger = logging.getLogger(__name__)

# Initialize S3 client
if all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME]):
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
    s3_client = session.client("s3")
else:
    s3_client = None
    logger.error("Missing AWS credentials or S3 bucket name in environment variables")

def parse_range(range_header, file_size):

    match = re.match(r"bytes=(\d+)-(\d*)", range_header)
    if match:
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else file_size - 1
        return start, min(end, file_size - 1)
    return 0, file_size - 1

def stream_video_from_s3(filename):
    from flask import request  # Needed here for range header
    if not s3_client:
        logger.error("S3 client not initialized")
        return Response("S3 client not initialized", status=500)

    try:
        logger.info(f"Request received for video: {filename}")
        
        # Construct full S3 key
        s3_key = f"species/{filename}" if not filename.startswith("species/") else filename

        head = s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        file_size = head['ContentLength']

        range_header = request.headers.get('Range', None)
        if range_header:
            start, end = parse_range(range_header, file_size)
            byte_range = f"bytes={start}-{end}"
            logger.info(f"Streaming byte range: {byte_range}")
            s3_response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Range=byte_range)
            data = s3_response['Body']

            def generate():
                for chunk in data.iter_chunks(chunk_size=8192):
                    yield chunk

            rv = Response(stream_with_context(generate()), status=206, mimetype='video/mp4')
            rv.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
            rv.headers.add('Accept-Ranges', 'bytes')
            rv.headers.add('Content-Length', str(end - start + 1))
            return rv
        else:
            s3_response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
            data = s3_response['Body']

            def generate():
                for chunk in data.iter_chunks(chunk_size=8192):
                    yield chunk

            rv = Response(stream_with_context(generate()), mimetype='video/mp4')
            rv.headers.add('Content-Length', str(file_size))
            rv.headers.add('Accept-Ranges', 'bytes')
            return rv

    except s3_client.exceptions.NoSuchKey:
        logger.warning(f"File not found in S3: {filename}")
        return Response("File not found in S3.", status=404)
    except Exception as e:
        logger.error(f"Error streaming video {filename}: {str(e)}")
        return Response("Could not stream video.", status=500)

def test_s3_connection():

    try:
        if not s3_client:
            logger.error("S3 client not initialized")
            return False
            
        s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, MaxKeys=1)
        logger.info("S3 connection test successful.")
        return True
    except Exception as e:
        logger.error(f"S3 connection failed: {str(e)}")
        return False

def get_video_path(video_id):

    return f"videos/{video_id}/original.mp4"