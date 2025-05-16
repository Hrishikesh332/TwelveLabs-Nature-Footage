import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
INDEX_ID = os.getenv("INDEX_ID")

AWS_ACCESS_KEY_ID = os.getenv("TL_AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("TL_AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("TL_AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("TL_S3_BUCKET_NAME")

WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

LAMBDA_FUNCTION_NAME = os.getenv("LAMBDA_FUNCTION_NAME", "pegasus-video-analysis")

DEBUG = os.getenv("DEBUG", "False").lower() == "true"
PORT = int(os.getenv("PORT", "5000"))
APP_URL = os.getenv("APP_URL", "http://localhost:5000")

EMBEDDING_STATUS_FILE = os.getenv("EMBEDDING_STATUS_FILE", "embedding_status.csv")
ANALYSIS_RESULTS_FILE = os.getenv("ANALYSIS_RESULTS_FILE", "video_analysis_results.csv")
DETAILED_ANALYSIS_RESULTS_FILE = os.getenv("DETAILED_ANALYSIS_RESULTS_FILE", "video_analysis_detailed_results.csv")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "tracking/nature_footage.log")

# Scheduler settings
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "True").lower() == "true"
PING_INTERVAL_MINUTES = int(os.getenv("PING_INTERVAL_MINUTES", "9"))
EMBEDDING_UPDATE_HOURS = int(os.getenv("EMBEDDING_UPDATE_HOURS", "24"))