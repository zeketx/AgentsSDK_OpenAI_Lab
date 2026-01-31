"""Gmail API client for email management operations."""

from typing import Any
import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailClient:
    """Client for Gmail API operations focused on organization and labeling."""

    def __init__(
        self,
        credentials_path: str | None = None,
        token_path: str | None = None,
    ):
        self.credentials_path = credentials_path or os.getenv(
            "GMAIL_CREDENTIALS_PATH", "gmail_credentials.json"
        )
        self.token_path = token_path or os.getenv(
            "GMAIL_TOKEN_PATH", "gmail_token.pickle"
        )
        self.service = None
        self._labels_cache: dict[str, str] = {}

    def _authenticate(self) -> Credentials:
        """Authenticate with Gmail API using OAuth2."""
        creds = None

        if os.path.exists(self.token_path):
            with open(self.token_path, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found: {self.credentials_path}\n"
                        "Download from Google Cloud Console > APIs & Services > Credentials"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(self.token_path, "wb") as token:
                pickle.dump(creds, token)

        return creds

    def connect(self) -> None:
        """Establish connection to Gmail API."""
        creds = self._authenticate()
        self.service = build("gmail", "v1", credentials=creds)
        self._refresh_labels_cache()

    def _refresh_labels_cache(self) -> None:
        """Refresh the labels cache."""
        if not self.service:
            raise RuntimeError("Not connected. Call connect() first.")

        results = self.service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])
        self._labels_cache = {label["name"]: label["id"] for label in labels}

    def list_labels(self) -> list[dict[str, Any]]:
        """List all Gmail labels."""
        if not self.service:
            raise RuntimeError("Not connected. Call connect() first.")

        results = self.service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])

        return [
            {
                "id": label["id"],
                "name": label["name"],
                "type": label["type"],
            }
            for label in labels
        ]

    def create_label(
        self,
        name: str,
        background_color: str = "#666666",
        text_color: str = "#ffffff",
    ) -> str:
        """Create a new Gmail label."""
        if not self.service:
            raise RuntimeError("Not connected. Call connect() first.")

        if name in self._labels_cache:
            return self._labels_cache[name]

        label_object = {
            "name": name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
            "color": {
                "backgroundColor": background_color,
                "textColor": text_color,
            },
        }

        try:
            label = (
                self.service.users()
                .labels()
                .create(userId="me", body=label_object)
                .execute()
            )
            self._labels_cache[name] = label["id"]
            return label["id"]
        except HttpError as e:
            if "Label name exists" in str(e):
                self._refresh_labels_cache()
                return self._labels_cache.get(name)
            raise

    def search_emails(
        self,
        query: str,
        max_results: int = 100,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """Search emails using Gmail query syntax."""
        if not self.service:
            raise RuntimeError("Not connected. Call connect() first.")

        max_results = min(max_results, 500)

        params = {
            "userId": "me",
            "q": query,
            "maxResults": max_results,
        }
        if page_token:
            params["pageToken"] = page_token

        results = self.service.users().messages().list(**params).execute()

        return {
            "messages": results.get("messages", []),
            "next_page_token": results.get("nextPageToken"),
            "result_size_estimate": results.get("resultSizeEstimate", 0),
        }

    def apply_label_to_emails(
        self,
        email_ids: list[str],
        label_name: str,
        chunk_size: int = 50,
    ) -> dict[str, Any]:
        """Apply a label to multiple emails in chunks."""
        if not self.service:
            raise RuntimeError("Not connected. Call connect() first.")

        if label_name not in self._labels_cache:
            label_id = self.create_label(label_name)
        else:
            label_id = self._labels_cache[label_name]

        total = len(email_ids)
        processed = 0
        errors = []

        for i in range(0, total, chunk_size):
            chunk = email_ids[i : i + chunk_size]

            for email_id in chunk:
                try:
                    self.service.users().messages().modify(
                        userId="me",
                        id=email_id,
                        body={"addLabelIds": [label_id]},
                    ).execute()
                    processed += 1
                except HttpError as e:
                    errors.append({"email_id": email_id, "error": str(e)})

        return {
            "total": total,
            "processed": processed,
            "errors": errors,
            "label_name": label_name,
        }
