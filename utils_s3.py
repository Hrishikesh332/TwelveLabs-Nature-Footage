import os
import boto3
from flask import Flask, Response, jsonify, request, stream_with_context
from dotenv import load_dotenv
import logging
import re

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("s3_stream.log"),
        logging.StreamHandler()
    ]
)

AWS_ACCESS_KEY_ID = os.getenv("TL_AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("TL_AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("TL_AWS_REGION")
S3_BUCKET_NAME = os.getenv("TL_S3_BUCKET_NAME")

if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME]):
    logging.error("Missing AWS credentials or S3 bucket name in .env file")
    raise EnvironmentError("Missing AWS credentials or S3 bucket name")

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)
s3_client = session.client("s3")

app = Flask(__name__)

def parse_range(range_header, file_size):
    match = re.match(r"bytes=(\\d+)-(\\d*)", range_header)
    if match:
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else file_size - 1
        return start, min(end, file_size - 1)
    return 0, file_size - 1

@app.route("/api/video/<path:filename>", methods=["GET"])
def stream_video(filename):
    logging.info(f"Request received for video: {filename}")
    try:
        head = s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=filename)
        file_size = head['ContentLength']

        range_header = request.headers.get('Range', None)
        if range_header:
            start, end = parse_range(range_header, file_size)
            byte_range = f"bytes={start}-{end}"
            logging.info(f"Streaming byte range: {byte_range}")
            s3_response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=filename, Range=byte_range)
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
            s3_response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=filename)
            data = s3_response['Body']

            def generate():
                for chunk in data.iter_chunks(chunk_size=8192):
                    yield chunk

            rv = Response(stream_with_context(generate()), mimetype='video/mp4')
            rv.headers.add('Content-Length', str(file_size))
            rv.headers.add('Accept-Ranges', 'bytes')
            return rv

    except s3_client.exceptions.NoSuchKey:
        logging.warning(f"File not found in S3: {filename}")
        return jsonify({"error": "File not found in S3."}), 404
    except Exception as e:
        logging.error(f"Error streaming video {filename}: {str(e)}")
        return jsonify({"error": "Could not stream video."}), 500

@app.route("/api/test", methods=["GET"])
def test_connection():
    try:
        s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, MaxKeys=1)
        logging.info("S3 connection test successful.")
        return jsonify({"status": "S3 connection successful."}), 200
    except Exception as e:
        logging.error(f"S3 connection failed: {str(e)}")
        return jsonify({"error": "S3 connection failed."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
