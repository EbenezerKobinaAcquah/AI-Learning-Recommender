from flask import Flask, jsonify, request, render_template
import os
import googleapiclient.discovery
import requests
import re
import base64
from flask_cors import CORS
from bs4 import BeautifulSoup  # Add this import for BeautifulSoup


app = Flask(__name__)
CORS(app, resources={r"/Resources": {"origins": "http://localhost:3000"}})

# Set your YouTube Data API key
YOUTUBE_API_KEY = "AIzaSyD_xlg9gGZkIIRdNUyosA6JRv5MHDj6g_0"

def parse_duration(duration):
    # Use regular expressions to extract hours, minutes, and seconds from the duration string
    hours = re.findall(r'(\d+)H', duration)
    minutes = re.findall(r'(\d+)M', duration)
    seconds = re.findall(r'(\d+)S', duration)

    # Convert the extracted values to integers (if available) or default to 0
    hours = int(hours[0]) if hours else 0
    minutes = int(minutes[0]) if minutes else 0
    seconds = int(seconds[0]) if seconds else 0

    return f"{hours}h {minutes}m {seconds}s"

def scrape_youtube_videos(topic):
    api_service_name = "youtube"
    api_version = "v3"
    api_key = os.environ.get('YOUTUBE_API_KEY') or YOUTUBE_API_KEY

    youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=api_key)

    search_request = youtube.search().list(
        part="snippet",
        q=topic + " tutorial",
        type="video",
        maxResults=5
    )
    search_response = search_request.execute()

    video_ids = [item['id']['videoId'] for item in search_response['items']]
    videos_request = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids)
    )
    videos_response = videos_request.execute()

    videos = videos_response['items']

    sorted_videos = sorted(
        videos,
        key=lambda x: (int(x['statistics']['likeCount']), int(x['statistics']['viewCount'])),
        reverse=True
    )

    video_data = []
    for video in sorted_videos:
        title = video['snippet']['title']
        rating = video['statistics']['likeCount']
        views = video['statistics']['viewCount']
        duration = parse_duration(video['contentDetails']['duration'])
        author = video['snippet']['channelTitle']
        video_id = video['id']
        video_link = f"https://www.youtube.com/watch?v={video_id}"

        video_data.append({
            "Title": title,
            "Rating": rating,
            "Views": views,
            "Duration": duration,
            "Author": author,
            "Link": video_link
        })

    return video_data

# Your Udemy API client ID and client secret
udemy_client_id = "lAm73qgv7AGOYHITYayvW9ysLulRZABZXlNhYyJY"
udemy_client_secret = "pv7GB5fBCE7BHANSOOZd2OJznZfaXMhulGXnkP5c74YhOoBmoCKtTHGo4ohy82eIaUHmeeyjQasc88wpQs6nygsJRrIkqp7RCPb8sIU0ZU6kN6ESjXkjnCR4DAbOIBaV"

def get_udemy_courses(topic):
    credentials = f"{udemy_client_id}:{udemy_client_secret}"
    base64_credentials = base64.b64encode(credentials.encode()).decode()

    url = f"https://www.udemy.com/api-2.0/courses/"

    headers = {"Authorization": f"Basic {base64_credentials}"}
    params = {
        "search": topic,
        "price": "price-free",
        "page_size": 5,  # Limit the number of results per page
        "page": 1  # Get the first page of results
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()

        course_data = []
        for course in data['results']:
            title = course['title']
            description = course['headline']
            course_picture = course.get('image_480x270')  # Use the larger image size (480x270)
            author = course['visible_instructors'][0]['title']
            price = course['price']
            course_link = f"https://www.udemy.com{course['url']}"

            course_data.append({
                "Title": title,
                "Description": description,
                "Author": author,
                "Link": course_link,
                "Course_Picture": course_picture,  # Ensure this key is used for the image
                "Price": price
            })

        return course_data[:5]  # Return only the top 5 courses
    else:
        return []

def scrape_coursera_courses(topic):
    search_url = "https://www.coursera.org/search"
    params = {
        "query": topic,
        "price": "free"
    }

    response = requests.get(search_url, params=params)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        courses = []

        for course in soup.find_all('div', class_='result-item'):
            title = course.find('h2', class_='color-primary-text').get_text(strip=True)
            description = course.find('div', class_='result-text').get_text(strip=True)
            course_link = "https://www.coursera.org" + course.find('a', class_='rc-DesktopSearchResults').get('href')
            image = course.find('img', class_='image').get('src')

            courses.append({
                "Title": title,
                "Description": description,
                "Link": course_link,
                "Course_Picture": image
            })

        return courses[:5]  # Return only the top 5 free courses
    else:
        return []

# Route to render form
@app.route('/')
def index():
    return render_template('index.html')

# Route to process the form submission and render the results
@app.route('/Resources', methods=['POST'])
def resources():
    topic = request.form.get('topic')
    if not topic:
        return jsonify({"error": "Please provide a topic"}), 400

    youtube_results = scrape_youtube_videos(topic)
    udemy_results = get_udemy_courses(topic)
    coursera_results = scrape_coursera_courses(topic)

    # return jsonify({
    #     "youtube": youtube_results,
    #     "udemy": udemy_results,
    #     "coursera": coursera_results
    # })

    # Render the results on a new page
    return render_template('results.html', youtube=youtube_results, udemy=udemy_results, coursera=coursera_results)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
