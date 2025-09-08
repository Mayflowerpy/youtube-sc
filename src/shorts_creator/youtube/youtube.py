import logging
import pickle
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

log = logging.getLogger(__name__)


class YouTubeService:
    """Service for uploading videos to YouTube using OAuth2 authentication."""
    
    def __init__(self, credentials_file: str | Path, token_file: str | Path = "youtube_token.pickle"):
        """
        Initialize YouTube service.
        
        Args:
            credentials_file: Path to OAuth2 credentials JSON file from Google Cloud Console
            token_file: Path to store authentication token for reuse
        """
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        self.youtube = None
        self.scopes = ["https://www.googleapis.com/auth/youtube.upload"]
        
    def authenticate(self) -> bool:
        """
        Authenticate with YouTube API using OAuth2.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            creds = None
            
            # Load existing token if available
            if self.token_file.exists():
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
                    
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    log.info("Refreshing expired YouTube credentials...")
                    creds.refresh(Request())
                else:
                    if not self.credentials_file.exists():
                        log.error(f"YouTube credentials file not found: {self.credentials_file}")
                        log.error("Please download OAuth2 credentials from Google Cloud Console")
                        return False
                        
                    log.info("Starting YouTube OAuth2 authentication...")
                    flow = Flow.from_client_secrets_file(
                        str(self.credentials_file), self.scopes)
                    flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                    
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    print(f'\n= Please visit this URL to authorize YouTube upload: {auth_url}')
                    code = input('=� Enter the authorization code: ')
                    
                    flow.fetch_token(code=code)
                    creds = flow.credentials
                    
                # Save credentials for next run
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)
                    
            self.youtube = build('youtube', 'v3', credentials=creds)
            log.info(" YouTube authentication successful")
            return True
            
        except Exception as e:
            log.error(f"L YouTube authentication failed: {e}")
            return False
            
    def upload_video(
        self, 
        video_path: str | Path, 
        title: str, 
        description: str = "", 
        tags: list[str] = None, 
        privacy: str = "private"
    ) -> Optional[str]:
        """
        Upload video to YouTube.
        
        Args:
            video_path: Path to video file to upload
            title: Video title (max 100 characters)
            description: Video description (max 5000 characters)
            tags: List of tags for the video
            privacy: Privacy setting ('private', 'public', 'unlisted')
            
        Returns:
            Video ID if successful, None if failed
        """
        if not self.youtube:
            log.error("Not authenticated. Call authenticate() first.")
            return None
            
        video_path = Path(video_path)
        if not video_path.exists():
            log.error(f"Video file not found: {video_path}")
            return None
            
        tags = tags if tags is not None else []
        
        # Ensure title and description fit YouTube limits
        title = title[:100]
        description = description[:5000]
        
        # Ensure #shorts hashtag for YouTube Shorts
        if '#shorts' not in description.lower():
            description = f"{description}\n\n#shorts"
            
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags[:500],  # YouTube tag limit
                'categoryId': '22',  # People & Blogs category
                'defaultLanguage': 'en',
                'defaultAudioLanguage': 'en'
            },
            'status': {
                'privacyStatus': privacy,
                'selfDeclaredMadeForKids': False
            }
        }
        
        try:
            log.info(f"=� Uploading video: {title}")
            
            media = MediaFileUpload(
                str(video_path),
                chunksize=-1,
                resumable=True,
                mimetype='video/mp4'
            )
            
            request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    log.debug(f"Upload progress: {progress}%")
                    
            if 'id' in response:
                video_id = response['id']
                video_url = f"https://youtu.be/{video_id}"
                log.info(f" Video uploaded successfully: {video_url}")
                return video_id
            else:
                log.error(f"L Upload failed with response: {response}")
                return None
                
        except HttpError as e:
            log.error(f"L YouTube API error: {e}")
            return None
        except Exception as e:
            log.error(f"L Upload failed: {e}")
            return None