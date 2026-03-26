from flask import Flask, render_template, request, jsonify
import pandas as pd
import json
from datetime import datetime, timedelta
import sqlite3
import matplotlib
matplotlib.use('Agg')  # Set the backend to non-interactive 'Agg'
import matplotlib.pyplot as plt
import io
import base64
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

from test import (
    get_video_details, get_video_comments, advanced_sentiment_analysis,
    analyze_with_ollama, save_video_data, save_comments, save_analysis,
    init_database, DB_NAME
)

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_sentiment_chart(sentiment_scores):
    plt.figure(figsize=(10, 6))
    plt.hist(sentiment_scores, bins=20, color='#00ff9d', alpha=0.8, edgecolor='#00ff9d')
    plt.title('Distribution of Comment Sentiment Scores', color='#00ff9d', pad=20)
    plt.xlabel('Sentiment Score', color='#ffffff')
    plt.ylabel('Number of Comments', color='#ffffff')
    plt.grid(True, alpha=0.1)
    
    # Set dark background
    plt.gca().set_facecolor('#1a1a1a')
    plt.gcf().set_facecolor('#1a1a1a')
    
    # Style the ticks
    plt.xticks(color='#ffffff')
    plt.yticks(color='#ffffff')
    
    # Save plot to base64 string
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='#1a1a1a')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode()
    plt.close()
    
    return f'data:image/png;base64,{img_str}'

def create_engagement_timeline(comments_data):
    df = pd.DataFrame(comments_data)
    df['publishedAt'] = pd.to_datetime(df['publishedAt'])
    df = df.sort_values('publishedAt')
    
    # Create cumulative metrics
    df['cumulative_likes'] = df['likes'].cumsum()
    df['cumulative_replies'] = df['replyCount'].cumsum()
    
    plt.figure(figsize=(10, 6))
    plt.plot(df['publishedAt'], df['cumulative_likes'], label='Cumulative Likes', color='#00ff9d')
    plt.plot(df['publishedAt'], df['cumulative_replies'], label='Cumulative Replies', color='#6c63ff')
    
    plt.title('Engagement Timeline', color='#00ff9d', pad=20)
    plt.xlabel('Time', color='#ffffff')
    plt.ylabel('Count', color='#ffffff')
    plt.grid(True, alpha=0.1)
    plt.legend(facecolor='#1a1a1a', edgecolor='#ffffff', labelcolor='#ffffff')
    
    # Set dark background
    plt.gca().set_facecolor('#1a1a1a')
    plt.gcf().set_facecolor('#1a1a1a')
    
    # Style the ticks
    plt.xticks(rotation=45, color='#ffffff')
    plt.yticks(color='#ffffff')
    
    # Save plot to base64 string
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='#1a1a1a')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode()
    plt.close()
    
    return f'data:image/png;base64,{img_str}'

def create_sentiment_trend(comments_data, sentiment_scores):
    df = pd.DataFrame({
        'timestamp': pd.to_datetime([c['publishedAt'] for c in comments_data]),
        'sentiment': sentiment_scores
    })
    df = df.sort_values('timestamp')
    
    # Calculate rolling average
    df['rolling_sentiment'] = df['sentiment'].rolling(window=5).mean()
    
    plt.figure(figsize=(10, 6))
    plt.plot(df['timestamp'], df['rolling_sentiment'], color='#00ff9d')
    plt.axhline(y=0, color='#ffffff', linestyle='--', alpha=0.3)
    
    plt.title('Sentiment Trend Over Time', color='#00ff9d', pad=20)
    plt.xlabel('Time', color='#ffffff')
    plt.ylabel('Sentiment Score', color='#ffffff')
    plt.grid(True, alpha=0.1)
    
    # Set y-axis limits
    plt.ylim(-1, 1)
    
    # Set dark background
    plt.gca().set_facecolor('#1a1a1a')
    plt.gcf().set_facecolor('#1a1a1a')
    
    # Style the ticks
    plt.xticks(rotation=45, color='#ffffff')
    plt.yticks(color='#ffffff')
    
    # Save plot to base64 string
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='#1a1a1a')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode()
    plt.close()
    
    return f'data:image/png;base64,{img_str}'

def create_empty_chart(title):
    plt.figure(figsize=(10, 6))
    plt.text(0.5, 0.5, 'No data available', 
             horizontalalignment='center',
             verticalalignment='center',
             transform=plt.gca().transAxes,
             color='#888888',
             fontsize=14)
    
    plt.title(title, color='#00ff9d', pad=20)
    
    # Set dark background
    plt.gca().set_facecolor('#1a1a1a')
    plt.gcf().set_facecolor('#1a1a1a')
    
    # Remove axes
    plt.axis('off')
    
    # Save plot to base64 string
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor='#1a1a1a')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode()
    plt.close()
    
    return f'data:image/png;base64,{img_str}'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        video_url = request.form.get('video_url')
        if not video_url:
            return jsonify({'error': 'No video URL provided'}), 400

        # Extract video ID
        if "youtube.com/watch?v=" in video_url:
            video_id = video_url.split("v=")[-1].split("&")[0]
        elif "youtu.be/" in video_url:
            video_id = video_url.split("/")[-1].split("?")[0]
        else:
            return jsonify({'error': 'Invalid YouTube URL format'}), 400

        print(f"🎯 Processing video ID: {video_id}")

        # Get video details
        try:
            video_data = get_video_details(video_id)
            if not video_data:
                return jsonify({'error': 'Could not fetch video details'}), 400
            video_data['video_id'] = video_id
        except Exception as e:
            print(f"❌ Error fetching video details: {str(e)}")
            return jsonify({'error': f'Error fetching video details: {str(e)}'}), 500

        # Get comments
        try:
            comments_data = get_video_comments(video_id)
            if not comments_data:
                # Handle case where comments are disabled
                return jsonify({
                    'video_data': video_data,
                    'comments_disabled': True,
                    'message': 'Comments are disabled for this video',
                    'charts': {
                        'sentiment_distribution': create_empty_chart('Sentiment Distribution'),
                        'engagement_timeline': create_empty_chart('Engagement Timeline'),
                        'sentiment_trend': create_empty_chart('Sentiment Trend')
                    },
                    'ai_analysis': {
                        'content_analysis': {'points': ['Comments are disabled for this video']},
                        'technical_breakdown': {'points': ['Comments are disabled for this video']},
                        'audience_engagement': {'points': ['Comments are disabled for this video']},
                        'improvement_suggestions': {'points': ['Comments are disabled for this video']},
                        'industry_relevance': {'points': ['Comments are disabled for this video']}
                    }
                })
        except Exception as e:
            print(f"❌ Error fetching comments: {str(e)}")
            return jsonify({'error': f'Error fetching comments: {str(e)}'}), 500

        # Perform sentiment analysis
        try:
            sentiment_analysis = advanced_sentiment_analysis(comments_data)
        except Exception as e:
            print(f"❌ Error in sentiment analysis: {str(e)}")
            return jsonify({'error': f'Error in sentiment analysis: {str(e)}'}), 500

        # Get AI analysis
        try:
            ai_analysis = analyze_with_ollama(video_data, comments_data, sentiment_analysis)
        except Exception as e:
            print(f"❌ Error in AI analysis: {str(e)}")
            return jsonify({'error': f'Error in AI analysis: {str(e)}'}), 500

        # Create charts
        try:
            charts = {
                'sentiment_distribution': create_sentiment_chart(sentiment_analysis['sentiment_scores']),
                'engagement_timeline': create_engagement_timeline(comments_data),
                'sentiment_trend': create_sentiment_trend(comments_data, sentiment_analysis['sentiment_scores'])
            }
        except Exception as e:
            print(f"❌ Error creating charts: {str(e)}")
            return jsonify({'error': f'Error creating charts: {str(e)}'}), 500

        # Save data to database
        try:
            save_video_data(video_id, video_data)
            save_comments(video_id, comments_data, sentiment_analysis['sentiment_scores'])
            save_analysis(video_id, ai_analysis)
        except Exception as e:
            print(f"⚠️ Warning: Error saving to database: {str(e)}")
            # Continue execution as this is not critical

        return jsonify({
            'video_data': video_data,
            'comments_data': comments_data,
            'sentiment_analysis': sentiment_analysis,
            'ai_analysis': ai_analysis,
            'charts': charts
        })

    except Exception as e:
        print(f"❌ Unexpected error in analyze route: {str(e)}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/history')
def history():
    conn = get_db_connection()
    videos = conn.execute('SELECT * FROM videos ORDER BY last_analyzed DESC').fetchall()
    conn.close()
    return render_template('history.html', videos=videos)

@app.route('/video/<video_id>')
def video_details(video_id):
    conn = get_db_connection()
    video = conn.execute('SELECT * FROM videos WHERE video_id = ?', (video_id,)).fetchone()
    comments = conn.execute('SELECT * FROM comments WHERE video_id = ?', (video_id,)).fetchall()
    analysis = conn.execute('SELECT * FROM analysis WHERE video_id = ?', (video_id,)).fetchall()
    conn.close()
    
    return render_template('video_details.html', video=video, comments=comments, analysis=analysis)

if __name__ == '__main__':
    init_database()
    app.run(debug=True) 