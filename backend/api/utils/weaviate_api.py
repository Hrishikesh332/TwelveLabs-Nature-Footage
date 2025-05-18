import weaviate
from weaviate.auth import AuthApiKey
from weaviate.classes.config import Configure, Property, DataType, VectorDistances
from weaviate.util import generate_uuid5
import logging
import traceback

from config.settings import WEAVIATE_URL, WEAVIATE_API_KEY

logger = logging.getLogger(__name__)


weaviate_client = None

def init_weaviate_client():

    global weaviate_client
    
    if not WEAVIATE_URL or not WEAVIATE_API_KEY:
        logger.error("WEAVIATE_URL or WEAVIATE_API_KEY environment variables not set")
        return False
    
    try:
        weaviate_client = weaviate.connect_to_weaviate_cloud(
            cluster_url=WEAVIATE_URL,
            auth_credentials=AuthApiKey(WEAVIATE_API_KEY),
        )
        
        if not weaviate_client.is_ready():
            logger.error("Weaviate client is not ready")
            return False
            
        logger.info("Weaviate client initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing Weaviate client: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def get_weaviate_client():

    global weaviate_client
    
    if weaviate_client is None:
        init_weaviate_client()
        
    return weaviate_client

def create_videos_schema():

    client = get_weaviate_client()
    if not client:
        logger.error("Weaviate client not initialized")
        return False

    try:
        collections = client.collections.list_all()
        if "NatureVideo" not in collections:
            client.collections.create(
                name="NatureVideo",
                description="Nature video embeddings from Twelve Labs",
                vectorizer="none", 
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=VectorDistances.COSINE,
                    ef_construction=128,
                    max_connections=16,
                    vector_cache_max_objects=1000000
                ),
                properties=[
                    Property(name="video_id", data_type=DataType.TEXT, description="Twelve Labs video ID"),
                    Property(name="filename", data_type=DataType.TEXT, description="Original filename"),
                    Property(name="duration", data_type=DataType.NUMBER, description="Video duration in seconds"),
                    Property(name="embedding_type", data_type=DataType.TEXT, description="Type of embedding (visual-text, audio)"),
                    Property(name="scope", data_type=DataType.TEXT, description="Scope of embedding (clip, video)"),
                    Property(name="start_time", data_type=DataType.NUMBER, description="Start time of the clip"),
                    Property(name="end_time", data_type=DataType.NUMBER, description="End time of the clip"),
                ]
            )
            logger.info("Created NatureVideo collection in Weaviate")
        else:
            logger.info("NatureVideo collection already exists in Weaviate")
        return True
    except Exception as e:
        logger.error(f"Failed to create collection: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def recreate_videos_schema(vector_dimensions=None):

    client = get_weaviate_client()
    if not client:
        logger.error("Weaviate client not initialized")
        return False
    
    try:
        collections = client.collections.list_all()
        if "NatureVideo" in collections:
            client.collections.delete("NatureVideo")
            logger.info("Deleted existing NatureVideo collection")
        
        # Create new collection
        client.collections.create(
            name="NatureVideo",
            description="Nature video embeddings from Twelve Labs",
            vectorizer_config=None,  
            vector_index_config=Configure.VectorIndex.hnsw(
                distance_metric=VectorDistances.COSINE,
                ef_construction=128,
                max_connections=16,
                vector_cache_max_objects=1000000
            ),
            properties=[
                Property(name="video_id", data_type=DataType.TEXT, description="Twelve Labs video ID"),
                Property(name="filename", data_type=DataType.TEXT, description="Original filename"),
                Property(name="duration", data_type=DataType.NUMBER, description="Video duration in seconds"),
                Property(name="embedding_type", data_type=DataType.TEXT, description="Type of embedding (visual-text, audio)"),
                Property(name="scope", data_type=DataType.TEXT, description="Scope of embedding (clip, video)"),
                Property(name="start_time", data_type=DataType.NUMBER, description="Start time of the clip"),
                Property(name="end_time", data_type=DataType.NUMBER, description="End time of the clip"),
            ]
        )
        
        dimensions_info = f" with {vector_dimensions} dimensions" if vector_dimensions else ""
        logger.info(f"Created NatureVideo collection successfully{dimensions_info}")
        return True
    except Exception as e:
        logger.error(f"Error creating collection: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def store_video_embedding(video_id, embedding_data, video_metadata=None):
    client = get_weaviate_client()
    if not client:
        logger.error("Weaviate client not initialized")
        return False

    try:
        logger.info(f"Storing embedding for video {video_id}")

        collections = client.collections.list_all()
        if "NatureVideo" not in collections:
            logger.warning("NatureVideo collection does not exist, creating it...")
            create_videos_schema()

        collection = client.collections.get("NatureVideo")

        if not video_metadata:
            from api.utils.twelvelabs_api import get_video_info
            video_metadata = get_video_info(video_id)

        filename = video_metadata.get("system_metadata", {}).get("filename", "unknown")
        duration = float(video_metadata.get("system_metadata", {}).get("duration", 0))

        segments = embedding_data.get("video_embedding", {}).get("segments", [])

        visual_segments = [s for s in segments if s.get("embedding_option") == "visual-text"]

        segment = next((s for s in visual_segments if s.get("embedding_scope") == "video"), None)
        if not segment and visual_segments:
            segment = visual_segments[0]

        if not segment:
            logger.warning(f"No suitable visual-text embedding found for video {video_id}")
            return False

        vector = segment.get("float", [])
        if not vector:
            logger.warning("Empty vector found")
            return False

        embedding_type = segment.get("embedding_option", "visual-text")
        scope = segment.get("embedding_scope", "unknown")
        start_time = float(segment.get("start_offset_sec", 0))
        end_time = float(segment.get("end_offset_sec", duration))

        properties = {
            "video_id": video_id,
            "filename": filename,
            "duration": duration,
            "embedding_type": embedding_type,
            "scope": scope,
            "start_time": start_time,
            "end_time": end_time
        }

        object_id = f"{video_id}_{embedding_type}_{scope}"
        object_uuid = generate_uuid5(object_id)

        collection.data.insert(properties=properties, vector=vector, uuid=object_uuid)
        logger.info(f"Stored visual embedding for video {video_id}")

        return True

    except Exception as e:
        logger.error(f"Error storing embedding: {str(e)}")
        logger.error(traceback.format_exc())
        return False




def find_similar_videos(video_id, embedding_vector=None, limit=10):
    client = get_weaviate_client()
    if not client:
        logger.error("Weaviate client not initialized")
        return []

    try:
        logger.info(f"Finding similar videos for video_id: {video_id}")
        if not embedding_vector:
            from api.utils.twelvelabs_api import get_video_embedding
            embedding_data = get_video_embedding(video_id)
            
            if embedding_data.get("status") != "ready":
                logger.error(f"Embedding not ready for video_id: {video_id}")
                return []
            
            segments = embedding_data.get("video_embedding", {}).get("segments", [])
            embedding_vector = None
            embedding_scope = None
            
            # Try using video scope first
            for segment in segments:
                if segment.get("embedding_option") == "visual-text" and segment.get("embedding_scope") == "video":
                    embedding_vector = segment.get("float", [])
                    embedding_scope = "video"
                    logger.info("Found video scope visual-text embedding")
                    break
            
            if not embedding_vector:
                for segment in segments:
                    if segment.get("embedding_option") == "visual-text":
                        embedding_vector = segment.get("float", [])
                        embedding_scope = "clip"
                        logger.info("Using clip scope visual-text embedding (fallback)")
                        break
            
            if not embedding_vector:
                logger.error("No visual-text embedding found")
                return []
            
            logger.info(f"Using embedding with {len(embedding_vector)} dimensions, scope: {embedding_scope}")
    
        collection = client.collections.get("NatureVideo")
        
        # Search for similar videos 
        logger.info(f"Searching Weaviate for similar videos (limit: {limit + 1})")
        results = collection.query.near_vector(
            near_vector=embedding_vector,
            limit=limit + 1,
            return_properties=["video_id", "filename", "embedding_type", "scope"],
            return_metadata=["certainty"]
        )
        
        similar_videos = []
        for obj in results.objects:
            result_video_id = obj.properties.get("video_id")
            if result_video_id == video_id:
                continue

            similarity = obj.metadata.certainty if hasattr(obj, 'metadata') and hasattr(obj.metadata, 'certainty') else None
            
            similar_videos.append({
                "video_id": result_video_id,
                "filename": obj.properties.get("filename"),
                "embedding_type": obj.properties.get("embedding_type"),
                "scope": obj.properties.get("scope"),
                "similarity_score": similarity,
                "similarity_percentage": round(similarity * 100, 2) if similarity is not None else None
            })
            
            if len(similar_videos) >= limit:
                break
        
        logger.info(f"Found {len(similar_videos)} similar videos")
        return similar_videos

    except Exception as e:
        logger.error(f"Error finding similar videos: {str(e)}")
        logger.error(traceback.format_exc())
        return []


def get_collection_stats():

    client = get_weaviate_client()
    if not client:
        logger.error("Weaviate client not initialized")
        return {"error": "Weaviate client not initialized"}
    
    try:
        logger.info("Getting collection statistics")
        
        collection = client.collections.get("NatureVideo")
        try:
            aggregate_response = collection.aggregate.over_all(total_count=True)
            total_count = aggregate_response.total_count
        except Exception as e:
            logger.error(f"Error getting aggregate count: {str(e)}")
            total_count = 0
        
        try:
            response = collection.query.fetch_objects(
                limit=2000,
                return_properties=["video_id", "embedding_type", "scope"]
            )
            
            objects = []
            for obj in response.objects:
                objects.append(obj.properties)
            
        except Exception as e:
            logger.error(f"Error querying objects: {str(e)}")
            objects = []
        
        unique_videos = set()
        embedding_types = {}
        scopes = {}
        
        for obj in objects:
            video_id = obj.get("video_id")
            embedding_type = obj.get("embedding_type")
            scope = obj.get("scope")
            
            if video_id:
                unique_videos.add(video_id)
            
            if embedding_type:
                embedding_types[embedding_type] = embedding_types.get(embedding_type, 0) + 1
            
            if scope:
                scopes[scope] = scopes.get(scope, 0) + 1
        
        stats = {
            "total_objects": total_count,
            "sampled_objects": len(objects),
            "unique_videos": len(unique_videos),
            "average_objects_per_video": round(total_count / len(unique_videos), 2) if unique_videos else 0,
            "embedding_types": embedding_types,
            "scopes": scopes
        }
        
        return stats
    
    except Exception as e:
        logger.error(f"Error getting collection stats: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": f"Error getting collection stats: {str(e)}"}