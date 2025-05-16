import os
from flask import Flask
from flask_cors import CORS
import logging
import atexit
import requests
from datetime import datetime

from config.settings import (
    DEBUG, PORT, APP_URL,         #LOG_LEVEL, LOG_FILE,
    SCHEDULER_ENABLED, PING_INTERVAL_MINUTES
)


# logging.basicConfig(
#     level=getattr(logging), # LOG_LEVEL
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         # logging.FileHandler(LOG_FILE),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)

def create_app():

    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    

    from api.routes.index import index_bp
    from api.routes.video import video_bp
    from api.routes.search import search_bp
    from api.routes.analysis import analysis_bp
    from api.routes.embedding import embedding_bp
    from api.routes.weaviate import weaviate_bp
    
    app.register_blueprint(index_bp, url_prefix='/api')
    app.register_blueprint(video_bp, url_prefix='/api')
    app.register_blueprint(search_bp, url_prefix='/api')
    app.register_blueprint(analysis_bp, url_prefix='/api')
    app.register_blueprint(embedding_bp, url_prefix='/api')
    app.register_blueprint(weaviate_bp, url_prefix='/api')
    
    @app.route('/')
    def home():
        return "Nature Footage Platform API is running! Current time - " + str(datetime.now())
    
    # Initialize Weaviate client
    from api.utils.weaviate_api import init_weaviate_client, create_videos_schema
    if init_weaviate_client():
        create_videos_schema()
    
    # Set up scheduler
    if SCHEDULER_ENABLED:
        setup_scheduler()
    
    return app

def wake_up_app():
    try:
        if APP_URL:
            response = requests.get(APP_URL)
            if response.status_code == 200:
                logger.info(f"Successfully pinged {APP_URL} at {datetime.now()}")
            else:
                logger.error(f"Failed to ping {APP_URL} (status code: {response.status_code}) at {datetime.now()}")
        else:
            logger.warning("APP_URL environment variable not set.")
    except Exception as e:
        logger.error(f"Error occurred while pinging app: {e}")

def setup_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(wake_up_app, 'interval', minutes=PING_INTERVAL_MINUTES)
    
    # schedular for the embedding job creation
    # scheduler.add_job(update_embeddings, 'interval', hours=EMBEDDING_UPDATE_HOURS)
    
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    logger.info("Background scheduler started.")

if __name__ == '__main__':
    app = create_app()
    app.run(debug=DEBUG, port=PORT)