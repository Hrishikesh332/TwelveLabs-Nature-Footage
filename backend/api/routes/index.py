from flask import Blueprint, jsonify

index_bp = Blueprint('index', __name__)

@index_bp.route('/index', methods=['GET'])
def api_get_index_info():
    from api.utils.twelvelabs_api import get_index_info
    
    index_info = get_index_info()
    if index_info:
        return jsonify(index_info)
    return jsonify({"error": "Failed to retrieve index information"}), 500

@index_bp.route('/test', methods=['GET'])
def test_connection():
    from api.utils.s3_utils import test_s3_connection
    from api.utils.weaviate_api import get_weaviate_client
    from api.utils.twelvelabs_api import get_index_info
    
    # Test S3 connection
    s3_status = test_s3_connection()
    
    # Test Weaviate connection
    weaviate_client = get_weaviate_client()
    weaviate_status = weaviate_client is not None and weaviate_client.is_ready()
    
    # Test TwelveLabs
    twelvelabs_status = get_index_info() is not None
    
    return jsonify({
        "connections": {
            "twelvelabs_api": {
                "status": "connected" if twelvelabs_status else "disconnected",
                "message": "Successfully connected to TwelveLabs API" if twelvelabs_status else "Failed to connect to TwelveLabs API"
            },
            "s3": {
                "status": "connected" if s3_status else "disconnected",
                "message": "Successfully connected to S3" if s3_status else "Failed to connect to S3"
            },
            "weaviate": {
                "status": "connected" if weaviate_status else "disconnected",
                "message": "Successfully connected to Weaviate" if weaviate_status else "Failed to connect to Weaviate"
            }
        },
        "all_services_available": all([twelvelabs_status, s3_status, weaviate_status])
    })