import logging
import pickle
import json
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

log = logging.getLogger(__name__)


class YouTubeService:
    """Service for uploading videos to YouTube using OAuth2 authentication."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        project_id: Optional[str] = None,
        auth_uri: str = "https://accounts.google.com/o/oauth2/auth",
        token_uri: str = "https://oauth2.googleapis.com/token",
        auth_provider_x509_cert_url: str = "https://www.googleapis.com/oauth2/v1/certs",
        redirect_uris: list[str] = ["http://localhost"],
        token_file: str | Path = "youtube_token.pickle",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.project_id = project_id
        self.auth_uri = auth_uri
        self.token_uri = token_uri
        self.auth_provider_x509_cert_url = auth_provider_x509_cert_url
        self.redirect_uris = redirect_uris
        self.token_file = Path(token_file)
        self.scopes = ["https://www.googleapis.com/auth/youtube.upload"]
        self.youtube = self._authenticate()

    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        privacy: str = "private",
        category_id: str = "28",  # Science & Technology
    ) -> Optional[str]:
        """Upload video to YouTube."""
        if not self.youtube:
            raise RuntimeError(
                "YouTubeService not authenticated. Authentication failed during initialization."
            )

        if "#shorts" not in description.lower():
            description = f"{description}\n\n#shorts"

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags[:500],  # YouTube tag limit
                "categoryId": category_id,
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en",
            },
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
        }

        media = MediaFileUpload(
            str(video_path),
            chunksize=-1,
            resumable=True,
            mimetype="video/mp4",
        )

        request = self.youtube.videos().insert(
            part=",".join(body.keys()), body=body, media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                log.debug(f"Upload progress: {progress}%")

        if "id" in response:
            video_id = response["id"]
            video_url = f"https://youtu.be/{video_id}"
            log.info(f"✅ Video uploaded successfully: {video_url}")
            return video_id

        raise RuntimeError(f"Upload failed, no video ID returned: {response}")

    def _authenticate(self):
        """Authenticate with YouTube API using OAuth2."""
        creds = self._load_credentials()

        if not creds or not creds.valid:
            creds = self._create_credentials(creds)

        return build("youtube", "v3", credentials=creds)

    def _load_credentials(self):
        """Load existing OAuth2 token from file."""
        if self.token_file.exists():
            try:
                with open(self.token_file, "rb") as token:
                    return pickle.load(token)
            except Exception as e:
                log.warning(f"Failed to load existing token: {e}")
        return None

    def _create_credentials(self, creds):
        """Create or refresh OAuth2 credentials."""
        if creds and creds.expired and creds.refresh_token:
            log.info("Refreshing expired YouTube credentials...")
            creds.refresh(Request())
        else:
            log.info("Starting YouTube OAuth2 authentication...")

            # Create client secrets dict from constructor parameters
            client_secrets = {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "project_id": self.project_id,
                    "auth_uri": self.auth_uri,
                    "token_uri": self.token_uri,
                    "auth_provider_x509_cert_url": self.auth_provider_x509_cert_url,
                    "redirect_uris": self.redirect_uris,
                }
            }

            flow = Flow.from_client_config(client_secrets, self.scopes)
            flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"

            auth_url, _ = flow.authorization_url(prompt="consent")
            log.info(
                f"\n🔐 Please visit this URL to authorize YouTube upload: {auth_url}"
            )
            code = input("📋 Enter the authorization code: ")

            flow.fetch_token(code=code)
            creds = flow.credentials

        # Save credentials for next run
        try:
            with open(self.token_file, "wb") as token:
                pickle.dump(creds, token)
        except Exception as e:
            log.warning(f"Failed to save token: {e}")

        return creds
