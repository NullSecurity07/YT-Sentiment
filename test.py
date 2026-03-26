import os
import json
import requests
import time
import sqlite3
from datetime import datetime
from collections import Counter
from textblob import TextBlob
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 1️⃣ CONFIGURATION
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    raise ValueError("Please set the YOUTUBE_API_KEY environment variable")

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5-coder:1.5b"
MAX_RETRIES = 3
RETRY_DELAY = 2
OLLAMA_TIMEOUT = 120  # Increased timeout to 2 minutes

# Database configuration
DB_NAME = "youtube_analysis.db"

POSITIVE_WORDS = ['love', 'great', 'awesome', 'amazing', 'excellent', 'good', 'fantastic', 'helpful', 'thanks', 'best', 'perfect', 'brilliant', 'outstanding', 'impressive', 'wonderful']
NEGATIVE_WORDS = ['hate', 'terrible', 'awful', 'bad', 'worst', 'horrible', 'useless', 'waste', 'poor', 'disappointing', 'mediocre', 'boring', 'confusing', 'overrated', 'underwhelming']

# 2️⃣ Initialize YouTube API
youtube_service = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY, static_discovery=False)

# 3️⃣ Helper functions
def get_video_details(video_id):
    try:
        print(f"🔍 Fetching details for video ID: {video_id}")
        request = youtube_service.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id
        )
        response = request.execute()
        if not response.get('items'):
            print("❌ No video found with the provided ID")
            return None
        video_data = response['items'][0]
        stats = video_data['statistics']
        # Convert duration from ISO 8601 to readable format
        duration = video_data['contentDetails']['duration']
        duration = duration.replace('PT', '').replace('H', 'h ').replace('M', 'm ').replace('S', 's')
        return {
            'title': video_data['snippet']['title'],
            'description': video_data['snippet']['description'],
            'published_at': video_data['snippet']['publishedAt'],
            'channel_title': video_data['snippet']['channelTitle'],
            'view_count': int(stats.get('viewCount', 0)),
            'like_count': int(stats.get('likeCount', 0)),
            'comment_count': int(stats.get('commentCount', 0)),
            'duration': duration
        }
    except HttpError as e:
        print(f"❌ YouTube API Error: {e}")
        return None

def get_video_comments(video_id, max_results=100):
    try:
        comments = []
        next_page_token = None
        while len(comments) < max_results:
            request = youtube_service.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(100, max_results - len(comments)),
                order="relevance",
                pageToken=next_page_token
            )
            response = request.execute()
            if not response.get('items'):
                break
            for item in response.get('items', []):
                snippet = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    'text': snippet.get('textDisplay', ''),
                    'author': snippet.get('authorDisplayName', ''),
                    'likes': int(snippet.get('likeCount', 0)),
                    'publishedAt': snippet.get('publishedAt', ''),
                    'replyCount': int(item['snippet'].get('totalReplyCount', 0))
                })
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        return comments
    except HttpError as e:
        print(f"❌ YouTube API Error: {e}")
        return []

def advanced_sentiment_analysis(comments):
    results = {
        'positive': 0,
        'negative': 0,
        'neutral': 0,
        'sentiment_scores': [],
        'top_positive': [],
        'top_negative': [],
        'engagement_metrics': {
            'total_likes': 0,
            'avg_likes': 0,
            'total_replies': 0,
            'avg_replies': 0
        }
    }
    
    if not comments:
        return results
    
    total_likes = 0
    total_replies = 0
    
    # Keywords that might indicate sarcasm or agreement
    sarcasm_indicators = ['lol', 'haha', '😂', '🤣', '😅', '😆', '😄', '😁', '😊', '😉', '😜', '😎', '😏', '😒', '😑', '😐', '😶', '😕', '😟', '😞', '😔', '😣', '😖', '😫', '😩', '😢', '😭', '😤', '😠', '😡', '😈', '👿', '💀', '🤡', '🤮', '🤢', '🤧', '🤒', '🤕', '🤠', '🤡', '🤥', '🤫', '🤭', '🤔', '🤐', '🤨', '😐', '😑', '😶', '😏', '😒', '🙄', '😬', '🤥', '😌', '😔', '😪', '😴', '😷', '🤒', '🤕', '🤢', '🤮', '🤧', '🥵', '🥶', '🥴', '😵', '🤯', '🤠', '🥳', '😎', '🤓', '👻', '👽', '🤖', '😺', '😸', '😹', '😻', '😼', '😽', '🙀', '😿', '😾']
    agreement_indicators = ['agree', 'true', 'correct', 'right', 'exactly', 'indeed', 'absolutely', 'definitely', 'certainly', 'sure', 'yes', 'yeah', 'yep', 'yup', 'totally', 'completely', 'fully', 'entirely', 'wholly', 'thoroughly', 'perfectly', 'precisely', 'accurately', 'properly', 'appropriately', 'suitably', 'adequately', 'satisfactorily', 'acceptably', 'tolerably', 'passably', 'reasonably', 'fairly', 'moderately', 'relatively', 'comparatively', 'somewhat', 'partially', 'partly', 'slightly', 'marginally', 'nominally', 'trivially', 'negligibly', 'insignificantly', 'minimally', 'barely', 'hardly', 'scarcely', 'rarely', 'seldom', 'infrequently', 'occasionally', 'sometimes', 'periodically', 'intermittently', 'sporadically', 'irregularly', 'inconsistently', 'variably', 'fluctuatingly', 'unsteadily', 'unreliably', 'unpredictably', 'uncertainly', 'doubtfully', 'questionably', 'debatably', 'arguably', 'possibly', 'potentially', 'conceivably', 'theoretically', 'hypothetically', 'speculatively', 'tentatively', 'provisionally', 'conditionally', 'temporarily', 'interim', 'transitional', 'provisional', 'tentative', 'experimental', 'pilot', 'trial', 'test', 'sample', 'specimen', 'example', 'instance', 'case', 'situation', 'circumstance', 'condition', 'state', 'status', 'position', 'situation', 'context', 'environment', 'atmosphere', 'climate', 'mood', 'tone', 'attitude', 'disposition', 'temperament', 'character', 'nature', 'personality', 'identity', 'individuality', 'uniqueness', 'distinctiveness', 'particularity', 'specificity', 'specialty', 'specialization', 'expertise', 'proficiency', 'competence', 'capability', 'ability', 'skill', 'talent', 'gift', 'aptitude', 'faculty', 'capacity', 'potential', 'possibility', 'opportunity', 'chance', 'prospect', 'outlook', 'future', 'destiny', 'fate', 'fortune', 'luck', 'chance', 'coincidence', 'accident', 'incident', 'event', 'occurrence', 'happening', 'phenomenon', 'circumstance', 'situation', 'condition', 'state', 'status', 'position', 'situation', 'context', 'environment', 'atmosphere', 'climate', 'mood', 'tone', 'attitude', 'disposition', 'temperament', 'character', 'nature', 'personality', 'identity', 'individuality', 'uniqueness', 'distinctiveness', 'particularity', 'specificity', 'specialty', 'specialization', 'expertise', 'proficiency', 'competence', 'capability', 'ability', 'skill', 'talent', 'gift', 'aptitude', 'faculty', 'capacity', 'potential', 'possibility', 'opportunity', 'chance', 'prospect', 'outlook', 'future', 'destiny', 'fate', 'fortune', 'luck', 'chance', 'coincidence', 'accident', 'incident', 'event', 'occurrence', 'happening', 'phenomenon']
    
    for comment in comments:
        text = comment['text'].lower()
        
        # Check for sarcasm indicators
        has_sarcasm = any(indicator in text for indicator in sarcasm_indicators)
        
        # Check for agreement indicators
        has_agreement = any(indicator in text for indicator in agreement_indicators)
        
        # Basic word-based sentiment
        pos_count = sum(word in text for word in POSITIVE_WORDS)
        neg_count = sum(word in text for word in NEGATIVE_WORDS)
        
        # TextBlob sentiment analysis
        blob = TextBlob(text)
        sentiment_score = blob.sentiment.polarity
        
        # Adjust sentiment score based on context
        if has_sarcasm:
            # If sarcasm is detected, invert the sentiment score
            sentiment_score = -sentiment_score
        elif has_agreement:
            # If agreement is detected, make the sentiment more positive
            sentiment_score = abs(sentiment_score)
        
        results['sentiment_scores'].append(sentiment_score)
        
        if sentiment_score > 0.1:
            results['positive'] += 1
            if len(results['top_positive']) < 5:
                results['top_positive'].append({
                    'text': comment['text'],
                    'score': sentiment_score,
                    'likes': comment['likes']
                })
        elif sentiment_score < -0.1:
            results['negative'] += 1
            if len(results['top_negative']) < 5:
                results['top_negative'].append({
                    'text': comment['text'],
                    'score': sentiment_score,
                    'likes': comment['likes']
                })
        else:
            results['neutral'] += 1
            
        total_likes += comment['likes']
        total_replies += comment['replyCount']
    
    # Calculate engagement metrics
    num_comments = len(comments)
    results['engagement_metrics'] = {
        'total_likes': total_likes,
        'avg_likes': round(total_likes / num_comments, 2) if num_comments else 0,
        'total_replies': total_replies,
        'avg_replies': round(total_replies / num_comments, 2) if num_comments else 0
    }
    
    # Sort top comments by sentiment score
    results['top_positive'].sort(key=lambda x: x['score'], reverse=True)
    results['top_negative'].sort(key=lambda x: x['score'])
    
    return results

def init_database():
    """Initialize the SQLite database with required tables."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create videos table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS videos (
        video_id TEXT PRIMARY KEY,
        title TEXT,
        channel_title TEXT,
        published_at TEXT,
        view_count INTEGER,
        like_count INTEGER,
        comment_count INTEGER,
        duration TEXT,
        last_analyzed TIMESTAMP
    )
    ''')
    
    # Create comments table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT,
        text TEXT,
        author TEXT,
        likes INTEGER,
        published_at TEXT,
        reply_count INTEGER,
        sentiment_score REAL,
        FOREIGN KEY (video_id) REFERENCES videos (video_id)
    )
    ''')
    
    # Create analysis table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT,
        section TEXT,
        points TEXT,
        created_at TIMESTAMP,
        FOREIGN KEY (video_id) REFERENCES videos (video_id)
    )
    ''')
    
    conn.commit()
    conn.close()

def save_video_data(video_id, video_data):
    """Save video data to the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT OR REPLACE INTO videos 
    (video_id, title, channel_title, published_at, view_count, like_count, comment_count, duration, last_analyzed)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        video_id,
        video_data['title'],
        video_data['channel_title'],
        video_data['published_at'],
        video_data['view_count'],
        video_data['like_count'],
        video_data['comment_count'],
        video_data['duration'],
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()

def save_comments(video_id, comments_data, sentiment_scores):
    """Save comments and their sentiment scores to the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    for comment, score in zip(comments_data, sentiment_scores):
        cursor.execute('''
        INSERT INTO comments 
        (video_id, text, author, likes, published_at, reply_count, sentiment_score)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            video_id,
            comment['text'],
            comment['author'],
            comment['likes'],
            comment['publishedAt'],
            comment['replyCount'],
            score
        ))
    
    conn.commit()
    conn.close()

def save_analysis(video_id, analysis_data):
    """Save AI analysis results to the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    for section, data in analysis_data.items():
        points_json = json.dumps(data['points'])
        cursor.execute('''
        INSERT INTO analysis 
        (video_id, section, points, created_at)
        VALUES (?, ?, ?, ?)
        ''', (
            video_id,
            section,
            points_json,
            datetime.now().isoformat()
        ))
    
    conn.commit()
    conn.close()

def get_historical_context(video_id):
    """Get historical data for context in analysis."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get previous analyses for the same channel
    cursor.execute('''
    SELECT v.channel_title, a.section, a.points
    FROM videos v
    JOIN analysis a ON v.video_id = a.video_id
    WHERE v.channel_title = (
        SELECT channel_title FROM videos WHERE video_id = ?
    )
    AND v.video_id != ?
    ORDER BY a.created_at DESC
    LIMIT 5
    ''', (video_id, video_id))
    
    historical_data = cursor.fetchall()
    
    conn.close()
    return historical_data

def analyze_with_ollama(video_data, comments_data, sentiment_analysis):
    """Enhanced analysis with historical context."""
    # Get historical context
    historical_context = get_historical_context(video_data['video_id'])
    
    # Prepare historical context string
    context_str = ""
    if historical_context:
        context_str = "\nHistorical Context from Previous Videos:\n"
        for channel, section, points in historical_context:
            context_str += f"\n{section} from {channel}:\n"
            points_list = json.loads(points)
            for point in points_list[:2]:  # Only include top 2 points from each historical analysis
                context_str += f"- {point}\n"
    
    # Prepare sentiment context
    sentiment_context = f"""
Sentiment Analysis Summary:
- Positive Comments: {sentiment_analysis['positive']}
- Negative Comments: {sentiment_analysis['negative']}
- Neutral Comments: {sentiment_analysis['neutral']}
- Average Sentiment Score: {sum(sentiment_analysis['sentiment_scores'])/len(sentiment_analysis['sentiment_scores']) if sentiment_analysis['sentiment_scores'] else 0:.2f}

Top Positive Comments:
{chr(10).join([f"- {comment['text']}" for comment in sentiment_analysis['top_positive'][:3]])}

Top Negative Comments:
{chr(10).join([f"- {comment['text']}" for comment in sentiment_analysis['top_negative'][:3]])}
"""
    
    prompt = f"""You are a cloud computing and technical content expert. Analyze this video and provide a detailed technical analysis:

Video Title: {video_data['title']}
Channel: {video_data['channel_title']}
Published: {video_data['published_at']}
Views: {video_data['view_count']:,}
Likes: {video_data['like_count']:,}
Comments: {video_data['comment_count']:,}

{sentiment_context}

{context_str}

Please analyze the following technical aspects and provide your response in this exact format:

1. Content Analysis:
- [Your analysis point 1]
- [Your analysis point 2]
- [Your analysis point 3]

2. Technical Breakdown:
- [Your analysis point 1]
- [Your analysis point 2]
- [Your analysis point 3]

3. Audience Engagement:
- [Your analysis point 1]
- [Your analysis point 2]
- [Your analysis point 3]

4. Improvement Suggestions:
- [Your analysis point 1]
- [Your analysis point 2]
- [Your analysis point 3]

5. Industry Relevance:
- [Your analysis point 1]
- [Your analysis point 2]
- [Your analysis point 3]

Please ensure each section has exactly 3 bullet points starting with a hyphen (-). Focus on providing specific, actionable insights based on the video content and comment analysis."""

    try:
        print("🤖 Sending request to Ollama...")
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "num_predict": 1024
                }
            },
            timeout=OLLAMA_TIMEOUT
        )
        response.raise_for_status()
        
        # Parse the JSON response
        response_json = response.json()
        response_text = response_json.get('response', '').strip()
        print("📝 Raw Ollama response received")
        
        # Create a basic analysis structure
        analysis = {
            'content_analysis': {'points': []},
            'technical_breakdown': {'points': []},
            'audience_engagement': {'points': []},
            'improvement_suggestions': {'points': []},
            'industry_relevance': {'points': []}
        }
        
        # Parse the response text
        current_section = None
        points_buffer = []
        
        for line in response_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Check for section headers
            if '1. Content Analysis' in line:
                current_section = 'content_analysis'
            elif '2. Technical Breakdown' in line:
                current_section = 'technical_breakdown'
            elif '3. Audience Engagement' in line:
                current_section = 'audience_engagement'
            elif '4. Improvement Suggestions' in line:
                current_section = 'improvement_suggestions'
            elif '5. Industry Relevance' in line:
                current_section = 'industry_relevance'
            elif current_section and line.startswith('-'):
                point = line[1:].strip()
                if point and not point.startswith('[') and not point.endswith(']'):
                    points_buffer.append(point)
                    if len(points_buffer) == 3:
                        analysis[current_section]['points'] = points_buffer
                        points_buffer = []
        
        # If any section is missing points, generate default points based on available data
        if not any(analysis[section]['points'] for section in analysis):
            # Generate default points based on video data and sentiment analysis
            analysis['content_analysis']['points'] = [
                f"Video titled '{video_data['title']}' has received {video_data['view_count']:,} views",
                f"Channel {video_data['channel_title']} has a strong following with {video_data['like_count']:,} likes",
                f"Video was published on {video_data['published_at']}"
            ]
            
            analysis['technical_breakdown']['points'] = [
                f"Video has generated {video_data['comment_count']:,} comments",
                f"Average engagement rate based on likes and comments",
                "Technical content analysis requires more specific video details"
            ]
            
            analysis['audience_engagement']['points'] = [
                f"Positive comments: {sentiment_analysis['positive']}",
                f"Negative comments: {sentiment_analysis['negative']}",
                f"Neutral comments: {sentiment_analysis['neutral']}"
            ]
            
            analysis['improvement_suggestions']['points'] = [
                "Consider increasing engagement through more interactive content",
                "Focus on maintaining positive sentiment in comments",
                "Analyze successful videos for content optimization"
            ]
            
            analysis['industry_relevance']['points'] = [
                "Content aligns with current industry trends",
                "Strong community engagement indicates relevance",
                "Video performance suggests good market fit"
            ]
        
        # Save the analysis to database
        save_analysis(video_data['video_id'], analysis)
        
        return analysis
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error communicating with Ollama: {e}")
        return {
            'content_analysis': {'points': ['Analysis failed due to API error']},
            'technical_breakdown': {'points': ['Analysis failed due to API error']},
            'audience_engagement': {'points': ['Analysis failed due to API error']},
            'improvement_suggestions': {'points': ['Analysis failed due to API error']},
            'industry_relevance': {'points': ['Analysis failed due to API error']}
        }

# 4️⃣ Main logic
def main():
    try:
        # Initialize database
        init_database()
        
        print("🔗 Enter the YouTube video URL:")
        video_url = input().strip()
        
        if "youtube.com/watch?v=" not in video_url and "youtu.be/" not in video_url:
            print("❌ Invalid YouTube URL format")
            return
            
        if "youtube.com" in video_url:
            video_id = video_url.split("v=")[-1].split("&")[0]
        else:  # youtu.be format
            video_id = video_url.split("/")[-1].split("?")[0]
            
        print(f"🎯 Extracted video ID: {video_id}")

        print("📺 Fetching video details...")
        video_data = get_video_details(video_id)
        if not video_data:
            print("❌ Could not fetch video details.")
            return
            
        # Add video_id to video_data for database operations
        video_data['video_id'] = video_id
        
        # Save video data to database
        save_video_data(video_id, video_data)

        print("💬 Fetching comments...")
        comments_data = get_video_comments(video_id)
        if not comments_data:
            print("❌ No comments found or comments are disabled.")
            return

        print("🔍 Doing advanced sentiment analysis...")
        sentiment_analysis = advanced_sentiment_analysis(comments_data)
        
        # Save comments and sentiment scores to database
        save_comments(video_id, comments_data, sentiment_analysis['sentiment_scores'])

        print("🧠 Sending to Ollama for deep analysis...")
        ai_analysis = analyze_with_ollama(video_data, comments_data, sentiment_analysis)

        md_filename = f"youtube_analysis_{video_id}.md"
        save_markdown_report(video_data, comments_data, sentiment_analysis, ai_analysis, md_filename)

        print(f"✅ Analysis complete! Report saved as: {md_filename}")
        
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        print("Please make sure:")
        print("1. Ollama is running locally on port 11434")
        print("2. The nous-hermes:7b model is installed")
        print("3. You have a stable internet connection")

def save_markdown_report(video_data, comments_data, sentiment_analysis, ai_analysis, filename):
    sections = []
    
    # Video Information
    sections.extend([
        "# Technical Content Analysis Report",
        "",
        "## Video Information",
        f"**Title:** {video_data['title']}",
        f"**Channel:** {video_data['channel_title']}",
        f"**Published:** {video_data['published_at']}",
        f"**Duration:** {video_data['duration']}",
        "",
        "## Performance Metrics",
        f"- Views: {video_data['view_count']:,}",
        f"- Likes: {video_data['like_count']:,}",
        f"- Comments: {video_data['comment_count']:,}",
        f"- View-to-Like Ratio: {(video_data['like_count']/video_data['view_count']*100):.2f}%",
        "",
        "## Comment Analysis",
        "### Sentiment Breakdown",
        f"- Positive Comments: {sentiment_analysis['positive']}",
        f"- Negative Comments: {sentiment_analysis['negative']}",
        f"- Neutral Comments: {sentiment_analysis['neutral']}",
        f"- Average Sentiment Score: {sum(sentiment_analysis['sentiment_scores'])/len(sentiment_analysis['sentiment_scores']) if sentiment_analysis['sentiment_scores'] else 0:.2f}",
        "",
        "### Engagement Metrics",
        f"- Total Comment Likes: {sentiment_analysis['engagement_metrics']['total_likes']:,}",
        f"- Average Likes per Comment: {sentiment_analysis['engagement_metrics']['avg_likes']}",
        f"- Total Replies: {sentiment_analysis['engagement_metrics']['total_replies']:,}",
        f"- Average Replies per Comment: {sentiment_analysis['engagement_metrics']['avg_replies']}",
        "",
        "### Top Positive Comments"
    ])
    
    # Add positive comments
    for comment in sentiment_analysis['top_positive']:
        sections.append(f"- {comment['text']} (Score: {comment['score']:.2f}, Likes: {comment['likes']})")
    
    sections.extend([
        "",
        "### Top Negative Comments"
    ])
    
    # Add negative comments
    for comment in sentiment_analysis['top_negative']:
        sections.append(f"- {comment['text']} (Score: {comment['score']:.2f}, Likes: {comment['likes']})")
    
    # Technical Analysis sections
    sections.extend([
        "",
        "## Technical Analysis",
        "### Content Analysis",
        ""
    ])
    
    # Add content analysis points
    for point in ai_analysis.get('content_analysis', {}).get('points', ['No analysis available']):
        sections.append(f"- {point}")
    
    sections.extend([
        "",
        "### Technical Breakdown",
        ""
    ])
    
    # Add technical breakdown points
    for point in ai_analysis.get('technical_breakdown', {}).get('points', ['No analysis available']):
        sections.append(f"- {point}")
    
    sections.extend([
        "",
        "### Audience Engagement",
        ""
    ])
    
    # Add audience engagement points
    for point in ai_analysis.get('audience_engagement', {}).get('points', ['No analysis available']):
        sections.append(f"- {point}")
    
    sections.extend([
        "",
        "### Improvement Suggestions",
        ""
    ])
    
    # Add improvement suggestions
    for point in ai_analysis.get('improvement_suggestions', {}).get('points', ['No analysis available']):
        sections.append(f"- {point}")
    
    sections.extend([
        "",
        "### Industry Relevance",
        ""
    ])
    
    # Add industry relevance points
    for point in ai_analysis.get('industry_relevance', {}).get('points', ['No analysis available']):
        sections.append(f"- {point}")
    
    # Add timestamp
    sections.extend([
        "---",
        f"*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    ])
    
    # Write the report
    with open(filename, "w") as f:
        f.write("\n".join(sections))

if __name__ == "__main__":
    main()

