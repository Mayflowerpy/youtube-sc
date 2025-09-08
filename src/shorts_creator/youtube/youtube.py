import logging
import pickle
import json
import webbrowser
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

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        data_dir: Path,
        project_id: Optional[str] = None,
        auth_uri: str = "https://accounts.google.com/o/oauth2/auth",
        token_uri: str = "https://oauth2.googleapis.com/token",
        auth_provider_x509_cert_url: str = "https://www.googleapis.com/oauth2/v1/certs",
        redirect_uris: list[str] = ["http://localhost:8080"],
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.project_id = project_id
        self.auth_uri = auth_uri
        self.token_uri = token_uri
        self.auth_provider_x509_cert_url = auth_provider_x509_cert_url
        self.redirect_uris = redirect_uris
        self.token_file = data_dir / "youtube_token.pickle"
        self.scopes = [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.force-ssl",
        ]
        self.youtube = self._authenticate()

    def check_quota_status(self) -> bool:
        request = self.youtube.channels().list(part="snippet", mine=True, maxResults=1)
        response = request.execute()
        log.info(f"✅ YouTube API quota check passed: {json.dumps(response)}")
        return True

    def _log_quota_info(self):
        """Log detailed quota information."""
        log.error("📊 YouTube Data API v3 Quota Information:")
        log.error("   • Free tier: 10,000 units/day")
        log.error("   • Video upload cost: ~1,600 units")
        log.error("   • Daily limit: ~6 uploads")
        log.error("   • Quota resets at midnight Pacific Time")
        log.error("🔧 Solutions:")
        log.error("   • Wait for quota reset (midnight PT)")
        log.error("   • Check Google Cloud Console for usage details")
        log.error(
            "   • Request quota increase: https://console.cloud.google.com/iam-admin/quotas"
        )
        log.error("   • Verify you're using the correct project")

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
        try:
            creds = self._load_credentials()

            if not creds or not creds.valid:
                creds = self._create_credentials(creds)

            youtube = build("youtube", "v3", credentials=creds)
            log.info("✅ YouTube API client initialized successfully")
            return youtube
        except Exception as e:
            log.error(f"❌ Failed to authenticate with YouTube API: {e}")
            log.error("🔧 Common solutions:")
            log.error("   • Check your client_id and client_secret")
            log.error("   • Verify OAuth2 redirect URIs in Google Cloud Console")
            log.error("   • Ensure YouTube Data API v3 is enabled")
            log.error("   • Delete youtube_token.pickle and try again")
            raise e

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
            flow.redirect_uri = "http://localhost:8080"

            # Run local server for OAuth callback
            creds = self._run_local_server_flow(flow)

        # Save credentials for next run
        try:
            with open(self.token_file, "wb") as token:
                pickle.dump(creds, token)
        except Exception as e:
            raise e

        return creds

    def _run_local_server_flow(self, flow):
        """Run OAuth2 flow using local server to handle callback."""
        try:
            # Try to use the built-in local server flow
            creds, _ = flow.run_local_server(
                host="localhost", port=8080, open_browser=True, timeout_seconds=300
            )
            return creds
        except Exception as e:
            log.error(f"Local server OAuth flow failed: {e}")
            # Fallback to manual flow with copy-paste
            return self._run_manual_flow(flow)

    def _run_manual_flow(self, flow):
        """Fallback manual OAuth flow for when local server fails."""
        log.info("Falling back to manual OAuth flow...")

        # Generate authorization URL
        auth_url, _ = flow.authorization_url(prompt="consent")

        log.info(f"\n🔐 Please visit this URL to authorize YouTube upload:")
        log.info(f"{auth_url}")
        log.info("\nAfter authorizing, you'll be redirected to localhost:8080")
        log.info(
            "Copy the ENTIRE URL from your browser's address bar after the redirect"
        )

        # Get the full redirect URL from user
        redirect_response = input("\n📋 Paste the full redirect URL here: ").strip()

        # Extract authorization code from URL
        if "code=" in redirect_response:
            # Parse the authorization code from the URL
            import urllib.parse

            parsed_url = urllib.parse.urlparse(redirect_response)
            code = urllib.parse.parse_qs(parsed_url.query)["code"][0]

            flow.fetch_token(code=code)
            return flow.credentials
        else:
            raise RuntimeError("Invalid redirect URL provided")
