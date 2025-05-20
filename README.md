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
* 🧠 **Pegasus Model Usage** for auto labeling and descriptive video details.
* ⚡ **Automatic Metadata Generation** with timestamps and clip scene level insights.
* 📦 **Video Embeddings Storage** in Weaviate for real time similarity search (video to video for recommendation).
* **Video-to-Video Recommendations** with fast nearest-neighbor lookup.
* **Caching Mechanism** for speeding up retrieval of frequently viewed content (Storing in metadata)
* **Confidence Scoring System** for video level and clip level evaluations.

---

## 🛠 Tech Stack

* **Frontend** – Next.js
* **Backend** – Python (Flask)
* **AI Services** – [TwelveLabs API](https://docs.twelvelabs.io/) (Marengo & Pegasus)
* **Vector DB** – [Weaviate](https://weaviate.io/)

---


## Overview Workflow 

<p align="center">
  <img src="https://github.com/Hrishikesh332/TwelveLabs-Nature-Footage/blob/main/backend/src/NatureFootage_Workflow.png" alt="Nature Footage Overview" width="100%">
</p>


## Folder Structure

```

├── README.md
├── __pycache__
    ├── analysis_worflow.cpython-312.pyc
    └── lambda_function.cpython-312.pyc
├── backend
    ├── .DS_Store
    ├── .env.example
    ├── .gitignore
    ├── README.md
    ├── api
    │   ├── .DS_Store
    │   ├── __init__.py
    │   ├── routes
    │   │   ├── __init__.py
    │   │   ├── analysis.py
    │   │   ├── embedding.py
    │   │   ├── index.py
    │   │   ├── search.py
    │   │   ├── video.py
    │   │   └── weaviate.py
    │   └── utils
    │   │   ├── __init__.py
    │   │   ├── csv_utils.py
    │   │   ├── generate_analysis.py
    │   │   ├── s3_utils.py
    │   │   ├── twelvelabs_api.py
    │   │   └── weaviate_api.py
    ├── app.py
    ├── config
    │   ├── __init__.py
    │   └── settings.py
    ├── requirements.txt
    ├── scripts
    │   └── batch_embedding.py
    ├── src
    │   └── banner.png
    └── tracking
    │   └── nature_footage.log
└── www.nature-footage.com
    ├── .gitignore
    ├── README.md
    ├── app
        ├── api
        │   ├── similar-videos
        │   │   └── [id]
        │   │   │   └── route.ts
        │   └── video
        │   │   └── [filename]
        │   │       └── route.ts
        ├── detail
        │   └── [id]
        │   │   └── page.tsx
        ├── globals.css
        ├── layout.tsx
        ├── loading.tsx
        ├── page.tsx
        └── search
        │   ├── loading.tsx
        │   └── page.tsx
    ├── components.json
    ├── components
        ├── api-key-checker.tsx
        ├── category-buttons.tsx
        ├── powered-by-text.tsx
        ├── related-searches.tsx
        ├── search-bar.tsx
        ├── theme-provider.tsx
        ├── video-results.tsx
        ├── video-grid.tsx
        ├── video-metadata.tsx
        └── ui/...
    ├── config
        └── api-config.ts
    ├── hooks
        ├── use-mobile.tsx
        └── use-toast.ts
    ├── lib
        └── utils.ts
    ├── next-env.d.ts
    ├── next.config.mjs
    ├── package-lock.json
    ├── package.json
    ├── pnpm-lock.yaml
    ├── postcss.config.mjs
    ├── public/...
    ├── styles
        └── globals.css
    ├── tailwind.config.ts
    ├── tsconfig.json
    └── types
        ├── hls.d.ts
        └── search.ts

```



## ⚙️ Local Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/Hrishikesh332/Twelve-Labs-Nature-Footage.git
   cd TwelveLabs-Nature-Footage
   ```

2. **For Frontend**

   ```bash
   cd www.nature-footage.com
   ```

3. **Setup dependencies**

   ```bash
   npm install --legacy-peer-deps
   ```

4. **Create .env file**
.env.example
   ```bash
   NEXT_PUBLIC_APP_URL="http://localhost:5000/" or deployed link (Running the backend server is mandatory for usage)
   ```

5. **Do run the app with**

   ```bash
   npm run dev
   ```


6. **Live At**

  `http://localhost:3000`



7. **For Backend**

Do checkout the README.md inside the `backend/` for the setup by - (With new terminal from root directory)
   ```bash
   cd backend
   ```


---

## Queries

For any doubts or help you can reach out to me via hrishikesh3321@gmail.com or ask in the [Discord Channel](https://discord.com/invite/Sh6BRfakJa)
