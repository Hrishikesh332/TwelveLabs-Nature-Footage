<p align="center">
  <img src="https://github.com/Hrishikesh332/TwelveLabs-Nature-Footage/blob/main/backend/src/banner.png" alt="Nature Footage Banner" width="100%">
</p>

<h1 align="center">Nature Footage</h1>

AI driven platform for **Nature Footage Search & Recommendations**, tapping into a stock library of over 4,000 hours of wildlife, ocean, and natural scenery — ranging from **4K Royalty-Free clips** to **12K Premium Footage**.

🎥 Backed by 750+ professional filmmakers and covering over 6,000 species globally. The purpose of this platform is to enhances discovery using **semantic video search and intelligent Video-to-Text for video details generation** with **TwelveLabs Marengo & Pegasus models**.

---

## 📚 Table of Contents

* [Features](#-features)
* [Tech Stack](#-tech-stack)
* [Local Setup](#-local-setup)

---

## 🚀 Features

* 🔎 **Semantic Video Search** using TwelveLabs Search Endpoint.
* 🧠 **Pegasus Model Usage** for auto labeling and descriptive video details..
* ⚡ **Automatic Metadata Generation** with timestamps and clip scene level insights.
* 📦 **Video Embeddings Storage** in Weaviate for real time similarity search (video to video for recommendation).
* 🔁 **Video-to-Video Recommendations** with fast nearest-neighbor lookup.
* 💾 **Caching Mechanism** for speeding up retrieval of frequently viewed content (Storing in metadata)
* 📊 **Confidence Scoring System** for video level and clip level evaluations.

---

## 🛠 Tech Stack

* **Frontend** – Next.js
* **Backend** – Python (Flask)
* **AI Services** – [TwelveLabs API](https://docs.twelvelabs.io/) (Marengo & Pegasus)
* **Vector DB** – [Weaviate](https://weaviate.io/)

---

## ⚙️ Local Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/Hrishikesh332/Twelve-Labs-Nature-Footage.git
   cd Twelve-Labs-Nature-Footage
   ```

2. **Set up a virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Add Environment Variables**

   Do copy and have a look at the `.env.example`

5. **Run the Flask app**

   ```bash
   python app.py
   ```

6. **Live At**

  `http://localhost:5000`

---
