"""MCP (Model Context Protocol) service for semantic search over knowledge embeddings."""

import json
from typing import Any
from dataclasses import dataclass, field
from enum import Enum

from db.repositories.knowledge_repo import KnowledgeRepository
from services.embedding_service import EmbeddingService


class MCPMessageType(str, Enum):
    """MCP message types."""
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    RESOURCES_LIST = "resources/list"
    ERROR = "error"


@dataclass
class MCPTool:
    """MCP tool definition."""
    name: str
    description: str
    input_schema: dict


@dataclass
class MCPResource:
    """MCP resource definition."""
    uri: str
    name: str
    description: str
    mime_type: str = "application/json"


@dataclass
class MCPContext:
    """Context for MCP session."""
    initialized: bool = False
    client_info: dict = field(default_factory=dict)


class MCPService:
    """Service for handling MCP protocol requests."""

    # MCP Protocol version
    PROTOCOL_VERSION = "2024-11-05"

    # Server info
    SERVER_NAME = "sherlock-knowledge"
    SERVER_VERSION = "1.0.0"

    def __init__(
        self,
        knowledge_repo: KnowledgeRepository | None = None,
        embedding_service: EmbeddingService | None = None,
    ):
        """
        Initialize MCP service.

        Args:
            knowledge_repo: Repository for knowledge records
            embedding_service: Service for generating embeddings
        """
        self.knowledge_repo = knowledge_repo or KnowledgeRepository()
        self.embedding_service = embedding_service or EmbeddingService()
        self.context = MCPContext()

    def get_tools(self) -> list[MCPTool]:
        """Get available MCP tools."""
        return [
            MCPTool(
                name="search_knowledge",
                description="Search the knowledge base using natural language queries. Returns semantically similar documents based on vector embeddings.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 5, max: 20)",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20
                        },
                        "category": {
                            "type": "string",
                            "description": "Optional category filter"
                        },
                        "subcategory": {
                            "type": "string",
                            "description": "Optional subcategory filter"
                        },
                        "topic": {
                            "type": "string",
                            "description": "Optional topic filter"
                        },
                        "similarity_threshold": {
                            "type": "number",
                            "description": "Minimum similarity score (0-1, default: 0.5)",
                            "default": 0.5,
                            "minimum": 0,
                            "maximum": 1
                        }
                    },
                    "required": ["query"]
                }
            ),
            MCPTool(
                name="get_knowledge_by_id",
                description="Retrieve a specific knowledge document by its ID.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The UUID of the knowledge document"
                        }
                    },
                    "required": ["id"]
                }
            ),
            MCPTool(
                name="list_categories",
                description="List all available categories, subcategories, and topics in the knowledge base.",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            )
        ]

    def get_resources(self) -> list[MCPResource]:
        """Get available MCP resources."""
        return [
            MCPResource(
                uri="sherlock://knowledge/all",
                name="All Knowledge",
                description="Access to all knowledge documents in the database"
            )
        ]

    async def handle_message(self, message: dict) -> dict:
        """
        Handle incoming MCP message.

        Args:
            message: MCP message dict with 'jsonrpc', 'method', 'id', and optional 'params'

        Returns:
            MCP response dict
        """
        method = message.get("method", "")
        msg_id = message.get("id")
        params = message.get("params", {})

        try:
            if method == "initialize":
                return self._handle_initialize(msg_id, params)
            elif method == "notifications/initialized":
                # Client notification, no response needed
                self.context.initialized = True
                return None
            elif method == "tools/list":
                return self._handle_tools_list(msg_id)
            elif method == "tools/call":
                return await self._handle_tools_call(msg_id, params)
            elif method == "resources/list":
                return self._handle_resources_list(msg_id)
            elif method == "resources/read":
                return await self._handle_resources_read(msg_id, params)
            else:
                return self._error_response(msg_id, -32601, f"Method not found: {method}")
        except Exception as e:
            return self._error_response(msg_id, -32603, str(e))

    def _handle_initialize(self, msg_id: Any, params: dict) -> dict:
        """Handle initialize request."""
        self.context.client_info = params.get("clientInfo", {})

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                },
                "serverInfo": {
                    "name": self.SERVER_NAME,
                    "version": self.SERVER_VERSION
                }
            }
        }

    def _handle_tools_list(self, msg_id: Any) -> dict:
        """Handle tools/list request."""
        tools = self.get_tools()
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.input_schema
                    }
                    for tool in tools
                ]
            }
        }

    async def _handle_tools_call(self, msg_id: Any, params: dict) -> dict:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "search_knowledge":
            result = await self._tool_search_knowledge(arguments)
        elif tool_name == "get_knowledge_by_id":
            result = await self._tool_get_knowledge_by_id(arguments)
        elif tool_name == "list_categories":
            result = await self._tool_list_categories(arguments)
        else:
            return self._error_response(msg_id, -32602, f"Unknown tool: {tool_name}")

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2, default=str)
                    }
                ]
            }
        }

    def _handle_resources_list(self, msg_id: Any) -> dict:
        """Handle resources/list request."""
        resources = self.get_resources()
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "resources": [
                    {
                        "uri": resource.uri,
                        "name": resource.name,
                        "description": resource.description,
                        "mimeType": resource.mime_type
                    }
                    for resource in resources
                ]
            }
        }

    async def _handle_resources_read(self, msg_id: Any, params: dict) -> dict:
        """Handle resources/read request."""
        uri = params.get("uri", "")

        if uri == "sherlock://knowledge/all":
            records, total = await self.knowledge_repo.get_all(limit=100)
            content = {
                "total": total,
                "records": [
                    {
                        "id": str(r.id),
                        "title": r.title,
                        "category": r.category,
                        "subcategory": r.subcategory,
                        "topic": r.topic
                    }
                    for r in records
                ]
            }
        else:
            return self._error_response(msg_id, -32602, f"Unknown resource: {uri}")

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(content, indent=2, default=str)
                    }
                ]
            }
        }

    async def _tool_search_knowledge(self, arguments: dict) -> dict:
        """Execute search_knowledge tool."""
        query = arguments.get("query", "")
        limit = min(arguments.get("limit", 5), 20)
        category = arguments.get("category")
        subcategory = arguments.get("subcategory")
        topic = arguments.get("topic")
        similarity_threshold = arguments.get("similarity_threshold", 0.5)

        if not query:
            return {"error": "Query is required", "results": []}

        # Generate embedding for the query
        query_embedding = await self.embedding_service.generate_embedding(query)

        # Perform semantic search
        try:
            results = await self.knowledge_repo.semantic_search(
                query_embedding=query_embedding,
                limit=limit,
                similarity_threshold=similarity_threshold,
                category=category,
                subcategory=subcategory,
                topic=topic,
            )
        except Exception:
            # Fallback to simple search if filtered search fails
            results = await self.knowledge_repo.semantic_search_simple(
                query_embedding=query_embedding,
                limit=limit,
            )

        return {
            "query": query,
            "total_results": len(results),
            "results": [
                {
                    "id": str(knowledge.id),
                    "title": knowledge.title,
                    "category": knowledge.category,
                    "subcategory": knowledge.subcategory,
                    "topic": knowledge.topic,
                    "raw_data": knowledge.raw_data[:500] + "..." if len(knowledge.raw_data) > 500 else knowledge.raw_data,
                    "paraphrased_data": knowledge.paraphrased_data[:500] + "..." if len(knowledge.paraphrased_data) > 500 else knowledge.paraphrased_data,
                    "image": knowledge.image,
                    "similarity_score": round(similarity, 4)
                }
                for knowledge, similarity in results
            ]
        }

    async def _tool_get_knowledge_by_id(self, arguments: dict) -> dict:
        """Execute get_knowledge_by_id tool."""
        doc_id = arguments.get("id", "")

        if not doc_id:
            return {"error": "ID is required"}

        record = await self.knowledge_repo.get_by_id(doc_id)

        if not record:
            return {"error": f"Document not found: {doc_id}"}

        return {
            "id": str(record.id),
            "title": record.title,
            "category": record.category,
            "subcategory": record.subcategory,
            "topic": record.topic,
            "raw_data": record.raw_data,
            "paraphrased_data": record.paraphrased_data,
            "image": record.image,
            "url": record.url,
            "status": record.status.value if hasattr(record.status, 'value') else record.status,
            "created_at": str(record.created_at),
            "updated_at": str(record.updated_at)
        }

    async def _tool_list_categories(self, arguments: dict) -> dict:
        """Execute list_categories tool."""
        # Get all completed records to extract unique categories
        records, _ = await self.knowledge_repo.get_all(limit=1000)

        categories = {}
        for record in records:
            if record.category not in categories:
                categories[record.category] = {}
            if record.subcategory not in categories[record.category]:
                categories[record.category][record.subcategory] = set()
            if record.topic:
                categories[record.category][record.subcategory].add(record.topic)

        # Convert to list format
        result = []
        for cat, subcats in categories.items():
            cat_entry = {
                "name": cat,
                "subcategories": []
            }
            for subcat, topics in subcats.items():
                cat_entry["subcategories"].append({
                    "name": subcat,
                    "topics": list(topics)
                })
            result.append(cat_entry)

        return {
            "total_categories": len(result),
            "categories": result
        }

    def _error_response(self, msg_id: Any, code: int, message: str) -> dict:
        """Create error response."""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": code,
                "message": message
            }
        }
