# 🌿 Nature Footage Search Platform

A modern search and recommendation system for **Nature Footage**, a stock library housing over 4000 hours of diverse nature content — from wildlife to oceans and mountains.  

This project upgrades towards search interface by integrating **TwelveLabs** semantic search APIs and metadata enrichment with the Generate Endpoint of the Pegasus model.

---

## Features

- Integration with TwelveLabs Search and Generate APIs
- Automatic metadata generation after indexing using TwelveLabs Generate API
- Storage of video embeddings in a database for fast retrieval for video to video recommendations.
- Video recommendations with the Weaviate vector database

---

## 🛠 Tech Stack

- **Frontend** - NextJs
- **Backend** - Python (FastAPI / Flask)
- **AI Services** -  [TwelveLabs API](https://docs.twelvelabs.io/) with Marengo and Pegasus Model
- **Vector Database**: [Weaviate](https://weaviate.io/)
- **Video Preview**: `m3u8` streaming format

---

## 🛠 Local Setup

Follow these steps to set up the project locally:

1. **Clone the repository**
   ```bash
   git clone https://github.com/Hrishikesh332/Twelve-Labs-Nature-Footage.git
   cd Twelve-Labs-Nature-Footage
   ```

2. **Set up a virtual environment**
   ```bash
    python3 -m venv venv
    source venv/bin/activate   # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies**
   ```bash
    pip install -r requirements.txt
   ```
 
4. **Configure Environment Variables**
   ```bash
    TWELVELABS_API_KEY=your_twelvelabs_api_key
   ```

5. **Run the application**
   ```bash
    python app.py
   ```

5. **Access the API locally**
    Base URL- `http://localhost:5000`


## 📚 API Endpoints

### Test Index Information
```bash
curl -X GET http://localhost:5000/api/index
```

### List Videos
```bash
curl -X GET "http://localhost:5000/api/videos?limit=50"
```

### Analyze a Single Video
```bash
curl -X POST http://localhost:5000/api/analyze/{video_id} \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Describe this video in detail."}'
```

### Batch Analyze All Videos
```bash
curl -X POST http://localhost:5000/api/batch-analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Describe this video in detail."}'
```

### Search Videos (with Filters)

```bash
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query_text": "underwater monkey shot", "options": ["visual"]}'

```


