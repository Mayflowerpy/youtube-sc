import logging
import pickle
import json
import os
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
        credentials_file: str | Path = None,
        token_file: str | Path = "youtube_token.pickle",
    ):
        self.credentials_file = Path(credentials_file) if credentials_file else None
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
    ) -> Optional[str]:

        if not self.youtube:
            raise RuntimeError(
                "YouTubeService not authenticated. Call authenticate() first."
            )

        if "#shorts" not in description.lower():
            description = f"{description}\n\n#shorts"

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags[:500],
                "categoryId": "22",
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
            log.debug(f" Video uploaded successfully: {video_url}")
            return video_id

        raise RuntimeError(f"Upload failed, no video ID returned: {response}")

    def _authenticate(self):
        creds = self._load_credentials()

        if not creds or not creds.valid:
            creds = self._create_credentials(creds)

        return build("youtube", "v3", credentials=creds)

    def _load_credentials(self):
        if self.token_file.exists():
            with open(self.token_file, "rb") as token:
                return pickle.load(token)
        return None

    def _create_credentials(self, creds) -> object:
        if creds and creds.expired and creds.refresh_token:
            log.info("Refreshing expired YouTube credentials...")
            creds.refresh(Request())
        else:
            if not self.credentials_file.exists():
                raise RecursionError(
                    "Credentials file missing. Please download OAuth2 credentials from Google Cloud Console"
                )

            log.info("Starting YouTube OAuth2 authentication...")
            flow = Flow.from_client_secrets_file(
                str(self.credentials_file), self.scopes
            )
            flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"

            auth_url, _ = flow.authorization_url(prompt="consent")
            log.info(
                f"\n= Please visit this URL to authorize YouTube upload: {auth_url}"
            )
            code = input("=� Enter the authorization code: ")

            flow.fetch_token(code=code)
            creds = flow.credentials

        # Save credentials for next run
        with open(self.token_file, "wb") as token:
            pickle.dump(creds, token)

        return creds
