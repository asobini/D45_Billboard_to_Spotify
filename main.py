import requests
from bs4 import BeautifulSoup
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from urllib.parse import quote

# Configuration constants
BASE_URL = "https://www.billboard.com/charts/hot-100/"
CLIENT_ID = "4bc797ed45e34363af44d72bf6788ca2"
CLIENT_SECRET = "d1940d304b664eb296780dec000cad1d"
REDIRECT_URI = "http://example.com"

# Get target date from user
target_date = input("Which year do you want to travel to? Type the date in YYYY-MM-DD: ")
year = target_date.split("-")[0] # Extract year for Spotify search

# Scrape Billboard website
url_to_scrape = f"{BASE_URL}{target_date}/"
header = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"} # Spoof user agent to avoid bot detection by Billboard website
response = requests.get(url=url_to_scrape, headers=header) # Send GET request to the website

if response.status_code != 200: # Check if the request was successful
    print(f"Failed to fetch the webpage. Status code {response.status_code}")
    exit()

# Parse HTML with proper selectors
soup = BeautifulSoup(response.text, "html.parser")

# Get song titles and artists
song_data = [] # Store song data in a list of dictionaries
song_containers = soup.select("li.lrv-u-width-100p ul li h3.c-title") # Select all song titles
artist_containers = soup.select("li.lrv-u-width-100p ul li span.c-label") # Select all artists

# Pair titles with artists and filter metadata
for title, artist in zip(song_containers[:100], artist_containers[:100]): # Only process first 100 songs
    song_title = title.get_text(strip=True)
    artist_name = artist.get_text(strip=True)

    # Filter out non-song entries and metadata like songwriters and producers
    if len(song_title) > 2 and not any(word in artist_name for word in ["-", "Songwriter", "Producer"]):
        song_data.append({
            "title": song_title,
            "artist": artist_name.split("Featuring")[0].split("&")[0].split("With")[0].strip() # Clean up artist names
        })

# Spotify Authentication
sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="playlist-modify-private",
        show_dialog=True,
        username="315tmnf5k7oaeihj4dm4mdeacuxu"
    )
)

user_id = sp.current_user()["id"] # Get user ID from Spotify
print(f"Authenticated as user: {user_id}") # Print user ID

# Search Spotify with multiple fallbacks
song_uris = [] # Store Spotify URIs of found songs
for idx, song in enumerate(song_data[:100], 1):  # Only process first 100 songs
    try:
        # First try: Title + Artist + Year
        query = f"track:{quote(song['title'])} artist:{quote(song['artist'])} year:{year}" # Search query
        result = sp.search(q=query, type="track", limit=5) # Send search request to Spotify API

        if result["tracks"]["items"]:
            # Select most popular version
            track = max(result["tracks"]["items"], key=lambda x: x["popularity"]) # Select most popular track
            song_uris.append(track["uri"])
            print(f"✓ {idx}/100: {song['title']} - {song['artist']}")
            continue

        # Fallback 1: Title + Artist without year
        query = f"track:{quote(song['title'])} artist:{quote(song['artist'])}"
        result = sp.search(q=query, type="track", limit=5)
        if result["tracks"]["items"]:
            track = max(result["tracks"]["items"], key=lambda x: x["popularity"])
            song_uris.append(track["uri"])
            print(f"⚠ {idx}/100: {song['title']} (no year match)")
            continue

        # Fallback 2: Title only
        query = f"track:{quote(song['title'])}"
        result = sp.search(q=query, type="track", limit=5)
        if result["tracks"]["items"]:
            track = max(result["tracks"]["items"], key=lambda x: x["popularity"])
            song_uris.append(track["uri"])
            print(f"⚠ {idx}/100: {song['title']} (title only)")
        else:
            print(f"✗ {idx}/100: {song['title']} - Not Found")

    except Exception as e:
        print(f"⚠ Error processing {song['title']}: {str(e)}")

# Create playlist with found tracks
if song_uris:
    try:
        playlist = sp.user_playlist_create(
            user=user_id,
            name=f"{target_date} Billboard 100",
            public=False,
            description=f"Billboard Hot 100 for {target_date} | {len(song_uris)} tracks found"
        )
        sp.playlist_add_items(playlist["id"], song_uris)
        print(f"\n✅ Success! Created playlist with {len(song_uris)} songs")
        print(f"🔗 Playlist URL: {playlist['external_urls']['spotify']}")
    except Exception as e:
        print(f"\n❌ Playlist creation failed: {str(e)}")
else:
    print("\n⚠ No songs found to create playlist")