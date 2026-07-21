"""Python Client for Paper Format Corrector API.

Provides a convenient Python interface for interacting with the REST API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class PaperFormatClient:
    """Client for interacting with Paper Format Corrector API.

    Usage:
        client = PaperFormatClient("http://localhost:8000")
        result = client.correct_document("paper.docx", preset="ieee")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 300.0,
        api_key: str | None = None,
    ):
        """Initialize the client.

        Args:
            base_url: Base URL of the API server
            timeout: Request timeout in seconds
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key
        self._session = None

    def _get_session(self):
        """Get or create HTTP session."""
        if self._session is None:
            if HAS_HTTPX:
                self._session = httpx.Client(timeout=self.timeout)
            elif HAS_REQUESTS:
                self._session = requests.Session()
                self._session.timeout = self.timeout
            else:
                raise ImportError(
                    "Either 'httpx' or 'requests' package is required. "
                    "Install with: pip install httpx  OR  pip install requests"
                )
        return self._session

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        files: dict | None = None,
    ) -> dict:
        """Make an API request.

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint
            data: JSON data for POST requests
            files: Files for upload

        Returns:
            JSON response as dictionary
        """
        url = f"{self.base_url}{endpoint}"
        session = self._get_session()
        headers = self._get_headers()

        if files:
            # For file uploads, don't set Content-Type
            headers.pop("Content-Type", None)

        if HAS_HTTPX:
            if files:
                response = session.request(
                    method, url, files=files, data=data, headers=headers
                )
            else:
                response = session.request(
                    method, url, json=data, headers=headers
                )
            response.raise_for_status()
            return response.json()
        else:  # requests
            if files:
                response = session.request(
                    method, url, files=files, data=data, headers=headers
                )
            else:
                response = session.request(
                    method, url, json=data, headers=headers
                )
            response.raise_for_status()
            return response.json()

    def health_check(self) -> dict:
        """Check API health status."""
        return self._request("GET", "/health")

    # ── Document Correction ──────────────────────────────────

    def correct_document(
        self,
        file_path: str | Path,
        preset: str | None = None,
        requirement_doc: str | None = None,
        score: bool = True,
        diff: bool = True,
        output_format: str = "docx",
    ) -> dict:
        """Correct a document.

        Args:
            file_path: Path to the document to correct
            preset: Preset template name (e.g., 'ieee', 'apa')
            requirement_doc: Path to requirement document
            score: Whether to compute quality score
            diff: Whether to generate diff report
            output_format: Output format (docx, pdf)

        Returns:
            dict with keys: output_file, report, diff_file, score
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        files = {"file": (file_path.name, open(file_path, "rb"), "application/octet-stream")}
        data = {}
        if preset:
            data["preset"] = preset
        if requirement_doc:
            data["requirement_doc"] = requirement_doc
        data["score"] = str(score).lower()
        data["diff"] = str(diff).lower()
        data["output_format"] = output_format

        try:
            return self._request("POST", "/correct", data=data, files=files)
        finally:
            files["file"][1].close()

    # ── Batch Processing ─────────────────────────────────────

    def batch_correct(
        self,
        file_paths: list[str | Path],
        preset: str | None = None,
    ) -> dict:
        """Process multiple documents in batch.

        Args:
            file_paths: List of document paths
            preset: Preset template name

        Returns:
            dict with batch results
        """
        files = []
        for fp in file_paths:
            path = Path(fp)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            files.append(
                ("files", (path.name, open(path, "rb"), "application/octet-stream"))
            )

        data = {}
        if preset:
            data["preset"] = preset

        try:
            return self._request("POST", "/batch", data=data, files=files)
        finally:
            for _, (file_obj, _, _) in files:
                file_obj.close()

    # ── Task Queue ───────────────────────────────────────────

    def submit_task(
        self,
        file_path: str | Path,
        template_id: str | None = None,
        filename: str = "",
    ) -> dict:
        """Submit a document correction task to the queue.

        Args:
            file_path: Path to the document file on the server.
            template_id: Optional template slug to apply.
            filename: Original filename for display.

        Returns:
            dict with task_id and initial status.
        """
        data = {
            "file_path": str(file_path),
            "template_id": template_id,
            "filename": filename or Path(file_path).name,
        }
        return self._request("POST", "/tasks/submit", data=data)

    def get_task_status(self, task_id: str) -> dict:
        """Get the status of a submitted task.

        Args:
            task_id: The task ID returned by submit_task.

        Returns:
            dict with task status, progress, and result info.
        """
        return self._request("GET", f"/tasks/{task_id}")

    def list_tasks(self, status: str | None = None, limit: int = 50) -> dict:
        """List all tasks, optionally filtered by status.

        Args:
            status: Filter by status (pending/processing/completed/failed).
            limit: Maximum number of tasks to return.

        Returns:
            dict with total count and task list.
        """
        query_parts = [f"limit={limit}"]
        if status:
            query_parts.append(f"status={status}")
        query_string = "&".join(query_parts)
        return self._request("GET", f"/tasks?{query_string}")

    def remove_task(self, task_id: str) -> dict:
        """Remove a completed or failed task.

        Args:
            task_id: The task ID to remove.

        Returns:
            dict with confirmation message.
        """
        return self._request("DELETE", f"/tasks/{task_id}")

    def download_task_result(self, task_id: str, output_path: str | Path) -> str:
        """Download the result file of a completed task.

        Args:
            task_id: The completed task ID.
            output_path: Where to save the result file.

        Returns:
            Path to the downloaded file.
        """
        url = urljoin(self.base_url, f"/tasks/{task_id}/result")
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if HAS_HTTPX:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, follow_redirects=True)
                resp.raise_for_status()
                output_path.write_bytes(resp.content)
        elif HAS_REQUESTS:
            resp = requests.get(url, timeout=self.timeout, allow_redirects=True)
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
        else:
            raise ImportError("httpx or requests is required for downloading files")

        return str(output_path)

    # ── Document Scanning ────────────────────────────────────

    def scan_document(self, file_path: str | Path) -> dict:
        """Scan document structure and return element inventory.

        Args:
            file_path: Path to the document

        Returns:
            dict with document structure information
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        files = {"file": (file_path.name, open(file_path, "rb"), "application/octet-stream")}
        try:
            return self._request("POST", "/scan", files=files)
        finally:
            files["file"][1].close()

    # ── Style Learning ───────────────────────────────────────

    def learn_style(self, file_path: str | Path) -> dict:
        """Learn style profile from a sample document.

        Args:
            file_path: Path to the sample document

        Returns:
            dict with learned style profile
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        files = {"file": (file_path.name, open(file_path, "rb"), "application/octet-stream")}
        try:
            return self._request("POST", "/learn", files=files)
        finally:
            files["file"][1].close()

    # ── Templates ────────────────────────────────────────────

    def list_templates(
        self,
        category: str | None = None,
        keyword: str | None = None,
    ) -> list[dict]:
        """List available templates.

        Args:
            category: Filter by category
            keyword: Search by keyword

        Returns:
            List of template dictionaries
        """
        params = {}
        if category:
            params["category"] = category
        if keyword:
            params["keyword"] = keyword

        query = "&".join(f"{k}={v}" for k, v in params.items())
        endpoint = f"/templates?{query}" if query else "/templates"
        return self._request("GET", endpoint)

    def get_template(self, slug: str) -> dict:
        """Get template details.

        Args:
            slug: Template identifier

        Returns:
            Template details dictionary
        """
        return self._request("GET", f"/templates/{slug}")

    def create_template(
        self,
        name: str,
        category: str,
        config: dict,
    ) -> dict:
        """Create a new personal template.

        Args:
            name: Template name
            category: Template category
            config: Format rules configuration

        Returns:
            Created template info
        """
        return self._request(
            "POST",
            "/templates",
            data={"name": name, "category": category, "config": config},
        )

    def delete_template(self, slug: str) -> dict:
        """Delete a template.

        Args:
            slug: Template identifier

        Returns:
            Deletion confirmation
        """
        return self._request("DELETE", f"/templates/{slug}")

    def export_template(
        self,
        slug: str,
        format: str = "yaml",
    ) -> Path:
        """Export template to file.

        Args:
            slug: Template identifier
            format: Export format (yaml/json)

        Returns:
            Path to downloaded file
        """
        url = f"{self.base_url}/templates/{slug}/export?format={format}"
        session = self._get_session()

        if HAS_HTTPX:
            response = session.get(url)
            response.raise_for_status()
        else:
            response = session.get(url)
            response.raise_for_status()

        # Save to temp file
        output_path = Path(f"template_{slug}.{format}")
        output_path.write_bytes(response.content)
        return output_path

    def validate_template(self, config: dict) -> dict:
        """Validate template configuration.

        Args:
            config: Configuration to validate

        Returns:
            Validation result
        """
        return self._request("POST", "/templates/validate", data=config)

    def list_categories(self) -> dict:
        """List all template categories."""
        return self._request("GET", "/templates/categories/list")

    def list_organizations(self) -> dict:
        """List all organizations."""
        return self._request("GET", "/templates/organizations/list")

    def list_tags(self) -> dict:
        """List all tags."""
        return self._request("GET", "/templates/tags/list")

    # ── Reports ──────────────────────────────────────────────

    def get_report(self, report_id: int) -> dict:
        """Get processing report by ID.

        Args:
            report_id: Report ID

        Returns:
            Report details
        """
        return self._request("GET", f"/reports/{report_id}")

    def list_reports(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List processing reports.

        Args:
            limit: Maximum number of reports
            offset: Offset for pagination

        Returns:
            List of report summaries
        """
        return self._request(
            "GET",
            f"/reports?limit={limit}&offset={offset}",
        )

    # ── Model Discovery ──────────────────────────────────────

    def list_llm_models(self) -> list[dict]:
        """List available LLM models."""
        return self._request("GET", "/llm/models")

    def probe_llm_model(self, model_id: str) -> dict:
        """Probe if an LLM model is available."""
        return self._request("GET", f"/llm/models/{model_id}/probe")

    def list_ai_doc_models(self) -> list[dict]:
        """List available AI document generation models."""
        return self._request("GET", "/ai-doc/models")

    def probe_ai_doc_model(self, model_id: str) -> dict:
        """Probe if an AI doc model is available."""
        return self._request("GET", f"/ai-doc/models/{model_id}/probe")

    # ── Cover Generation ─────────────────────────────────────

    def generate_cover(self, metadata: dict) -> dict:
        """Generate a cover page.

        Args:
            metadata: Cover page metadata (title, author, etc.)

        Returns:
            Cover page file info
        """
        return self._request("POST", "/cover", data=metadata)

    # ── AI Document Generation ───────────────────────────────

    def generate_document(
        self,
        description: str,
        model: str | None = None,
        provider: str | None = None,
    ) -> dict:
        """Generate a document from natural language description.

        Args:
            description: Document description
            model: LLM model to use
            provider: LLM provider

        Returns:
            Generated document info
        """
        data = {"description": description}
        if model:
            data["model"] = model
        if provider:
            data["provider"] = provider
        return self._request("POST", "/ai-doc/generate", data=data)

    def chat_ai_doc(
        self,
        messages: list[dict],
        model: str | None = None,
        provider: str | None = None,
    ) -> dict:
        """Chat with AI document generator.

        Args:
            messages: List of message dicts (role, content)
            model: LLM model to use
            provider: LLM provider

        Returns:
            AI response
        """
        data = {"messages": messages}
        if model:
            data["model"] = model
        if provider:
            data["provider"] = provider
        return self._request("POST", "/ai-doc/chat", data=data)

    # ── Utility ──────────────────────────────────────────────

    def close(self):
        """Close the client session."""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def create_client(
    base_url: str = "http://localhost:8000",
    **kwargs,
) -> PaperFormatClient:
    """Create a client instance.

    Args:
        base_url: API server URL
        **kwargs: Additional client parameters

    Returns:
        PaperFormatClient instance
    """
    return PaperFormatClient(base_url=base_url, **kwargs)
