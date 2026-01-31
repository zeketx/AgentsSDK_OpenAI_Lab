"""Test Gmail connection and trigger OAuth flow if needed."""

import asyncio
from app.services.gmail_client import GmailClient


async def test_gmail():
    """Test Gmail connection - will trigger OAuth browser flow on first run."""
    print("🔐 Testing Gmail connection...")
    print("   (Browser will open for Google authentication if this is first time)")
    print()

    try:
        client = GmailClient()
        client.connect()
        labels = client.list_labels()

        print("✅ Gmail connected successfully!")
        print(f"📧 Found {len(labels)} labels")
        print()
        print("First 10 labels:")
        for label in labels[:10]:
            label_type = "📁" if label["type"] == "system" else "🏷️"
            print(f"  {label_type} {label['name']}")

        return True

    except FileNotFoundError as e:
        print(f"❌ Credentials file not found")
        print(f"   Error: {e}")
        print()
        print("📋 To fix:")
        print("   1. Go to Google Cloud Console > APIs & Services > Credentials")
        print("   2. Download your OAuth 2.0 Client ID (Desktop app)")
        print("   3. Save as 'gmail_credentials.json' in project root")
        return False

    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_gmail())
    exit(0 if success else 1)
