"""MCP (Model Context Protocol) API routes with SSE transport."""

import json
import asyncio
import uuid
from typing import AsyncGenerator
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from services.mcp_service import MCPService


router = APIRouter(prefix="/mcp")


class MCPRequest(BaseModel):
    """MCP JSON-RPC request."""
    jsonrpc: str = "2.0"
    method: str
    id: int | str | None = None
    params: dict | None = None


# ============================================
# MCP SSE Transport (Spec-compliant)
# ============================================

class MCPSSEServer:
    """
    MCP SSE Server implementing the official MCP SSE transport spec.

    Flow:
    1. Client connects to GET /sse endpoint
    2. Server sends 'endpoint' event with POST URL for messages
    3. Client sends JSON-RPC messages to the POST endpoint
    4. Server responds via SSE 'message' events
    """

    def __init__(self):
        self.sessions: dict[str, dict] = {}

    def create_session(self, session_id: str, base_url: str) -> dict:
        """Create a new MCP session."""
        self.sessions[session_id] = {
            "mcp_service": MCPService(),
            "response_queue": asyncio.Queue(),
            "base_url": base_url,
        }
        return self.sessions[session_id]

    def get_session(self, session_id: str) -> dict | None:
        """Get an existing session."""
        return self.sessions.get(session_id)

    def close_session(self, session_id: str):
        """Close and cleanup a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]

    async def handle_message(self, session_id: str, message: dict) -> dict | None:
        """Handle incoming MCP message and queue response."""
        session = self.get_session(session_id)
        if not session:
            return {"jsonrpc": "2.0", "id": message.get("id"), "error": {"code": -32000, "message": "Session not found"}}

        mcp_service = session["mcp_service"]
        response = await mcp_service.handle_message(message)

        # Queue response for SSE delivery
        if response:
            await session["response_queue"].put(response)

        return response


# Global MCP SSE server instance
_mcp_server = MCPSSEServer()


async def mcp_sse_event_generator(session_id: str, base_url: str) -> AsyncGenerator[str, None]:
    """
    Generate SSE events following MCP SSE transport spec.

    Events:
    - 'endpoint': Sent once on connection with the POST URL
    - 'message': JSON-RPC responses from the server
    """
    session = _mcp_server.create_session(session_id, base_url)
    message_endpoint = f"{base_url}/api/mcp/messages/{session_id}"

    try:
        # Send the endpoint event (required by MCP SSE spec)
        yield f"event: endpoint\ndata: {message_endpoint}\n\n"

        # Process response queue
        response_queue = session["response_queue"]

        while True:
            try:
                # Wait for responses with timeout for keepalive
                response = await asyncio.wait_for(response_queue.get(), timeout=30.0)
                yield f"event: message\ndata: {json.dumps(response)}\n\n"
            except asyncio.TimeoutError:
                # Send a comment as keepalive (SSE spec allows comments starting with :)
                yield ": keepalive\n\n"

    except asyncio.CancelledError:
        pass
    finally:
        _mcp_server.close_session(session_id)


@router.get("/sse")
async def mcp_sse_endpoint(request: Request) -> StreamingResponse:
    """
    MCP SSE endpoint (spec-compliant).

    Connect to this endpoint to establish an MCP session.
    The server will send an 'endpoint' event with the URL to POST messages to.

    Example flow:
    1. GET /api/mcp/sse -> Receive 'endpoint' event with message URL
    2. POST to message URL with JSON-RPC requests
    3. Receive responses via 'message' SSE events
    """
    session_id = str(uuid.uuid4())

    # Determine base URL from request
    base_url = str(request.base_url).rstrip("/")
    # Handle proxy/forwarded headers
    if "x-forwarded-proto" in request.headers:
        proto = request.headers["x-forwarded-proto"]
        base_url = f"{proto}://{request.headers.get('host', request.base_url.netloc)}"

    return StreamingResponse(
        mcp_sse_event_generator(session_id, base_url),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.post("/messages/{session_id}")
async def mcp_post_message(session_id: str, request: Request) -> JSONResponse:
    """
    POST endpoint for MCP messages (spec-compliant).

    Send JSON-RPC messages to this endpoint. Responses are delivered
    via the SSE stream for the session.
    """
    session = _mcp_server.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Connect to /api/mcp/sse first.")

    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Handle the message
    response = await _mcp_server.handle_message(session_id, body)

    # Return 202 Accepted - response will be delivered via SSE
    # But also return the response directly for clients that prefer synchronous
    return JSONResponse(
        content=response or {"status": "accepted"},
        status_code=202 if response else 200
    )


# ============================================
# Alternative: Stateless JSON-RPC endpoint
# ============================================

@router.post("/rpc")
async def mcp_rpc(request: MCPRequest) -> dict:
    """
    Stateless MCP JSON-RPC endpoint.

    This provides a simpler REST-like interface for MCP tools
    without requiring SSE connection management.

    Use this for simple integrations where SSE is not needed.
    """
    mcp_service = MCPService()

    message = {
        "jsonrpc": request.jsonrpc,
        "method": request.method,
        "id": request.id,
        "params": request.params or {}
    }

    response = await mcp_service.handle_message(message)
    return response or {"status": "acknowledged"}


# ============================================
# Convenience endpoint for direct search
# ============================================

@router.post("/search")
async def mcp_search(
    query: str,
    limit: int = 5,
    category: str | None = None,
    subcategory: str | None = None,
    topic: str | None = None
) -> dict:
    """
    Direct semantic search endpoint (convenience wrapper).

    This is a simplified endpoint that directly calls the search_knowledge tool
    without requiring full MCP protocol handling.

    Args:
        query: Natural language search query
        limit: Maximum results (default: 5, max: 20)
        category: Optional category filter
        subcategory: Optional subcategory filter
        topic: Optional topic filter

    Returns:
        Search results with similarity scores
    """
    mcp_service = MCPService()

    message = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 1,
        "params": {
            "name": "search_knowledge",
            "arguments": {
                "query": query,
                "limit": min(limit, 20),
                "category": category,
                "subcategory": subcategory,
                "topic": topic
            }
        }
    }

    response = await mcp_service.handle_message(message)

    # Extract the result content
    if "result" in response and "content" in response["result"]:
        content = response["result"]["content"]
        if content and content[0].get("type") == "text":
            return json.loads(content[0]["text"])

    return response


# ============================================
# Health check for MCP
# ============================================

@router.get("/health")
async def mcp_health() -> dict:
    """MCP server health check."""
    return {
        "status": "healthy",
        "protocol": "mcp",
        "version": "2024-11-05",
        "transport": "sse",
        "endpoints": {
            "sse": "/api/mcp/sse",
            "rpc": "/api/mcp/rpc",
            "search": "/api/mcp/search"
        }
    }
