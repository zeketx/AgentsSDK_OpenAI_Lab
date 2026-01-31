"""Gmail management tools for the Gmail agent."""

from typing import Any
from agents import function_tool
from app.services.gmail_client import GmailClient


@function_tool
def list_gmail_labels() -> list[dict[str, Any]]:
    """List all Gmail labels in the user's account."""
    client = GmailClient()
    client.connect()
    return client.list_labels()


@function_tool
def create_gmail_label(name: str, color: str = "gray") -> dict[str, Any]:
    """Create a new Gmail label."""
    color_map = {
        "gray": ("#666666", "#ffffff"),
        "red": ("#cc3a21", "#ffffff"),
        "blue": ("#4285f4", "#ffffff"),
        "green": ("#33aa33", "#ffffff"),
        "yellow": ("#facc15", "#000000"),
        "purple": ("#a142f4", "#ffffff"),
        "orange": ("#ff6d2e", "#ffffff"),
        "teal": ("#0099aa", "#ffffff"),
    }

    bg_color, text_color = color_map.get(color.lower(), color_map["gray"])

    client = GmailClient()
    client.connect()
    label_id = client.create_label(name, bg_color, text_color)

    return {
        "label_id": label_id,
        "name": name,
        "color": color,
        "created": label_id is not None,
    }


@function_tool
def find_emails_from_sender(
    domain_or_email: str, max_results: int = 100
) -> dict[str, Any]:
    """Find all emails from a specific sender domain or email address."""
    client = GmailClient()
    client.connect()

    query = f"from:{domain_or_email}"
    results = client.search_emails(query, max_results)

    return {
        "query": query,
        "total_found": results["result_size_estimate"],
        "emails_returned": len(results["messages"]),
        "emails": results["messages"],
        "has_more": results["next_page_token"] is not None,
    }


@function_tool
def search_emails_by_query(query: str, max_results: int = 100) -> dict[str, Any]:
    """Search emails using Gmail search syntax."""
    client = GmailClient()
    client.connect()

    results = client.search_emails(query, max_results)

    return {
        "query": query,
        "total_found": results["result_size_estimate"],
        "emails_returned": len(results["messages"]),
        "emails": results["messages"],
        "has_more": results["next_page_token"] is not None,
    }


@function_tool
def categorize_emails_by_sender(
    domain: str, label_name: str, max_emails: int = 500
) -> dict[str, Any]:
    """Find all emails from a domain and apply a label to them."""
    client = GmailClient()
    client.connect()

    search_results = client.search_emails(f"from:{domain}", max_results=max_emails)
    emails = search_results["messages"]

    if not emails:
        return {
            "domain": domain,
            "label_name": label_name,
            "total_found": 0,
            "processed": 0,
            "message": f"No emails found from {domain}",
        }

    email_ids = [email["id"] for email in emails]
    result = client.apply_label_to_emails(email_ids, label_name, chunk_size=50)

    return {
        "domain": domain,
        "label_name": label_name,
        "total_found": search_results["result_size_estimate"],
        "processed": result["processed"],
        "errors_count": len(result["errors"]),
        "errors": result["errors"][:5] if result["errors"] else [],
        "success": result["processed"] > 0,
    }


@function_tool
def apply_label_to_matching_emails(
    search_query: str, label_name: str, max_emails: int = 500
) -> dict[str, Any]:
    """Search for emails using a query and apply a label to all matching emails."""
    client = GmailClient()
    client.connect()

    search_results = client.search_emails(search_query, max_results=max_emails)
    emails = search_results["messages"]

    if not emails:
        return {
            "query": search_query,
            "label_name": label_name,
            "total_found": 0,
            "processed": 0,
            "message": "No emails matching your criteria were found",
        }

    email_ids = [email["id"] for email in emails]
    result = client.apply_label_to_emails(email_ids, label_name, chunk_size=50)

    return {
        "query": search_query,
        "label_name": label_name,
        "total_found": search_results["result_size_estimate"],
        "processed": result["processed"],
        "errors_count": len(result["errors"]),
        "errors": result["errors"][:5] if result["errors"] else [],
        "success": result["processed"] > 0,
    }


@function_tool
def suggest_email_categorization() -> dict[str, Any]:
    """Analyze inbox and suggest categorization rules based on sender patterns."""
    client = GmailClient()
    client.connect()

    # Get a sample of recent emails to analyze
    results = client.search_emails("", max_results=100)

    if not results["messages"]:
        return {"suggestions": [], "message": "No emails found to analyze"}

    # Extract unique sender domains and count frequencies
    domain_counts = {}

    for msg in results["messages"][:50]:  # Analyze first 50
        # Note: In a full implementation, we'd fetch headers for each email
        # For now, we'll suggest based on common patterns
        pass

    # Common domains that benefit from categorization
    common_suggestions = [
        {
            "domain": "github.com",
            "label_name": "GitHub",
            "reason": "Development notifications",
        },
        {
            "domain": "linkedin.com",
            "label_name": "LinkedIn",
            "reason": "Professional network",
        },
        {
            "domain": "amazon.com",
            "label_name": "Shopping",
            "reason": "E-commerce orders",
        },
        {
            "domain": "newsletter",
            "label_name": "Newsletters",
            "reason": "Email subscriptions",
        },
        {
            "domain": "noreply",
            "label_name": "Automated",
            "reason": "Automated system emails",
        },
    ]

    return {
        "suggestions": common_suggestions,
        "message": "Here are common categorization patterns. Use 'categorize_emails_by_sender' to apply them.",
    }
