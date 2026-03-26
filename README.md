<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a0a0a,50:1a0a0a,100:dc2626&height=220&section=header&text=YT-SENTIMENT&fontSize=64&fontColor=ffffff&fontAlignY=38&fontAlign=50&desc=Advanced%20YouTube%20Comment%20%26%20Engagement%20Analysis&descSize=16&descAlignY=58&descAlign=50&descColor=fca5a580&animation=fadeIn" width="100%"/>

</div>

<br/>

<div align="center">

*A Flask-based engine for extracting, analyzing, and visualizing YouTube audience sentiment using local LLMs.*

</div>

<br/>

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=rect&color=0:dc2626,100:1a0a0a&height=1&section=header" width="40%"/>
</div>

<br/>

<div align="center">

### — Overview —

</div>

<br/>

YT-Sentiment is an analytical web application built to move beyond basic vanity metrics (likes/views) and understand true audience engagement. It integrates the YouTube Data API with hybrid sentiment processing (`TextBlob` + custom logic) and local, privacy-respecting AI (Ollama) to extract deep insights from video comment sections. 

The system automatically generates interactive charts, persists historical data for trend analysis, and outputs comprehensive markdown reports for every video processed.

<br/>

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=rect&color=0:dc2626,100:1a0a0a&height=1&section=header" width="40%"/>
</div>

<br/>

<div align="center">

### — Architecture —

</div>

<br/>

| Component | Layer | Function |
|:---|:---|:---|
| `app.py` | Controller | Flask application routing, web interface, and orchestration |
| `test.py` | Engine | Core logic — API interaction, NLP processing, and database operations |
| `qwen2.5-coder:1.5b`| AI Model | Local Ollama instance for deep contextual analysis and insights |
| `youtube_analysis.db` | Storage | SQLite database for historical trend tracking and persistence |
| Matplotlib | Visualization| Generates interactive sentiment distribution and timeline charts |

<br/>

**Execution Pipeline**

```text
User (Web Interface)
    └─ Submits YouTube URL
            └─ Fetches metadata & comment threads via Google API
                    └─ Processes sentiment (TextBlob + custom sarcasm logic)
                            └─ Passes aggregate data to local Ollama LLM
                                    └─ Generates insights, visualizations, and Markdown report
                                            └─ Saves to SQLite & returns to Web UI
```

<br/>

**Why local LLMs and custom logic?**

Standard NLP libraries often fail at internet dialect. By combining a baseline library (`TextBlob`) with custom agreement/sarcasm detection, we clean the data pipeline before feeding it to a local LLM (`qwen2.5-coder:1.5b`).

> This architecture ensures that complex, multi-layered video topics receive highly technical, context-aware breakdowns without sending sensitive user engagement data to third-party cloud AI providers.

<br/>

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=rect&color=0:dc2626,100:1a0a0a&height=1&section=header" width="40%"/>
</div>

<br/>

<div align="center">

### — Capabilities —

</div>

<br/>

| Feature | Detail |
|:---|:---|
| Data Extraction | Fetches video title, channel, metrics, and comment threads |
| Hybrid Sentiment | Combines standard NLP with custom sarcasm & agreement logic |
| AI Deep Insights | Technical breakdowns, audience suggestions, and industry relevance |
| Visualizations | Generates sentiment distribution and timeline trend charts |
| Historical Tracking | Browse past analyses via the web interface UI |
| Auto-Reporting | Generates detailed Markdown summaries for offline use |

<br/>

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=rect&color=0:dc2626,100:1a0a0a&height=1&section=header" width="40%"/>
</div>

<br/>

<div align="center">

### — Setup —

</div>

<br/>

**Requirements**

- Python 3.8+
- [Ollama](https://ollama.ai/) running locally
- Google Cloud Project with YouTube Data API v3 enabled

<br/>

**Configuration**

```bash
# 1. Clone the repository and setup environment
git clone [https://github.com/your-username/yt_sentiment_analyser.git](https://github.com/your-username/yt_sentiment_analyser.git)
cd yt_sentiment_analyser
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Pull the required local LLM model
ollama pull qwen2.5-coder:1.5b

# 4. Configure API Key
# Create a .env file in the root directory and add:
echo 'YOUTUBE_API_KEY="YOUR_YOUTUBE_API_KEY"' > .env
```

<br/>

**Running**

```bash
# Ensure Ollama daemon is running in the background, then start Flask:
python app.py

# Access the web interface at: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
```

<br/>

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=rect&color=0:dc2626,100:1a0a0a&height=1&section=header" width="40%"/>
</div>

<br/>

<div align="center">

### — Stack —

</div>

<br/>

**Backend** &nbsp;&nbsp; Python · Flask · SQLite

**AI & NLP** &nbsp;&nbsp; Ollama · TextBlob

**Data & Viz** &nbsp;&nbsp; Pandas · NumPy · Matplotlib

<br/>

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=rect&color=0:dc2626,100:1a0a0a&height=1&section=header" width="40%"/>
</div>

<br/>

<div align="center">

### — Note —

</div>

<br/>

<div align="center">

```text
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   This application relies on the YouTube Data API. Be mindful of     ║
║   your Google Cloud quota limits when scraping large comment pools.  ║
║                                                                      ║
║   The local AI analysis requires sufficient system RAM/VRAM to       ║
║   run the qwen2.5-coder:1.5b model effectively without bottlenecks.  ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

</div>

<br/>

<div align="center">

*Built under the MIT License*
&nbsp;·&nbsp;
[Report an Issue](https://github.com/your-username/yt_sentiment_analyser/issues)

<br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:dc2626,50:1a0a0a,100:0a0a0a&height=120&section=footer&animation=fadeIn" width="100%"/>

</div>
