# =============================================================================
# Chapter 12: The Protocol Layer
# MCP, ACP, and the Interoperability Standard
# Design of Agentic Systems with Case Studies
# =============================================================================
# This notebook contains two parallel implementations of a research agent:
#   System A — Ad-hoc integration (the failure case)
#   System B — MCP-based integration (the architectural solution)
#
# Run all cells in order. The failure case in System A is deliberate.
# Follow the exercises at the end to trigger and observe the failure yourself.
# =============================================================================

# ── Dependencies ──────────────────────────────────────────────────────────────
# Standard library only, except for the AI Scaffold in Part 0 which requires:
#   pip install nest_asyncio
# All tool stubs are implemented inline for reproducibility.

import json
import copy
from typing import Any

print("Chapter 12: The Protocol Layer")
print("=" * 60)


# =============================================================================
# PART 0 — AI SCAFFOLD: MCP TOOL DEFINITION GENERATOR
# =============================================================================
# This scaffold calls the Anthropic API to enumerate candidate MCP tool
# definitions from a plain-English system description.
#
# The AI handles one bounded task: proposing tool schemas from a description.
# It cannot decide whether those schemas correctly model user intent vs. API
# structure. That judgment is yours.
#
# The Block failure mode (30+ tools mirroring GraphQL endpoints one-to-one)
# is a granularity decision the AI will often replicate if you let it.
# Your job at the Human Decision Node is to catch that before it propagates.
# =============================================================================

import json

# ── System description (edit this to match your own agent system) ─────────────

SYSTEM_DESCRIPTION = """
A research agent that helps analysts answer questions about companies.
It needs to search the web for recent news, query an internal database
of financial reports, look up SEC filings by company ticker, and fetch
the current stock price for a given symbol.
"""

# ── API call ──────────────────────────────────────────────────────────────────

async def generate_tool_definitions(system_description: str) -> list[dict]:
    """
    Calls the Anthropic API to propose MCP tool definitions from a
    plain-English system description. Returns a list of tool schema dicts.
    """
    import urllib.request

    prompt = f"""You are an MCP server architect. Given the following system description,
propose a minimal set of MCP tool definitions. Each tool should be scoped around
user intent, not around underlying API endpoints. Return ONLY a JSON array of
tool definition objects, each with: name, description, and inputSchema.
No preamble, no markdown fences, just the raw JSON array.

System description:
{system_description}"""

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    raw_text = data["content"][0]["text"].strip()
    return json.loads(raw_text)


# ── Run the scaffold ──────────────────────────────────────────────────────────

print("\n[AI SCAFFOLD] Generating candidate MCP tool definitions...\n")

try:
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()
    proposed_tools = asyncio.get_event_loop().run_until_complete(
        generate_tool_definitions(SYSTEM_DESCRIPTION)
    )

    print("Proposed tool definitions:\n")
    for i, tool in enumerate(proposed_tools, 1):
        print(f"  Tool {i}: {tool['name']}")
        print(f"    Description: {tool['description']}")
        print(f"    Required inputs: {tool['inputSchema'].get('required', [])}")
        print()

except Exception as e:
    print(f"API call failed: {e}")
    print("Running with fallback stub tools for offline use.\n")
    proposed_tools = [
        {"name": "search_web", "description": "Search the web for recent information.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
        {"name": "lookup_database", "description": "Query internal financial reports.", "inputSchema": {"type": "object", "properties": {"entity": {"type": "string"}}, "required": ["entity"]}},
    ]
    for i, tool in enumerate(proposed_tools, 1):
        print(f"  Tool {i}: {tool['name']} — {tool['description']}")
    print()


# =============================================================================
# MANDATORY HUMAN DECISION NODE
# =============================================================================
# Review the proposed tool definitions above before proceeding.
#
# Ask yourself:
#   1. Are these tools scoped around USER INTENT or around API ENDPOINTS?
#      (One tool per GraphQL mutation is the Block failure mode — too granular.)
#   2. Does each tool represent a complete, meaningful action the agent
#      would want to take — or a raw API call the agent would have to chain?
#   3. Are any tools missing that the system description implies?
#   4. Are any tools redundant or over-specified?
#
# You must answer these questions before the demo proceeds.
# The AI proposed a structure. You decide whether it is correct.
# Document your decision below — this moment belongs in your video.
#
# DECISION: [Replace this line with your assessment and any corrections]
#   Example: "Tool 3 (get_stock_price) is correctly scoped — single intent,
#             single result. Tool 2 (lookup_database) is too broad and should
#             be split into lookup_financials and lookup_filings to reflect
#             distinct data sources with different latency profiles."
# =============================================================================

print("=" * 60)
print("MANDATORY HUMAN DECISION NODE")
print()
print("Review the proposed tools above.")
print("Answer before running the next cell:")
print()
print("  1. Are tools scoped around user intent or API endpoints?")
print("  2. Are any tools missing or redundant?")
print("  3. Would you accept, modify, or reject this tool set?")
print()
print("Document your decision in the comment block above.")
print("This is the moment that belongs on camera.")
print("=" * 60)

# Halt. Do not run the next cell until you have documented your decision.
# The architecture below uses the proposed_tools list — if you reject or
# modify the AI's proposal, update proposed_tools before continuing.



# =============================================================================
# PART 1 — SYSTEM A: AD-HOC INTEGRATION
# =============================================================================
# The research agent in System A calls tools by directly importing connector
# functions. Each connector knows the exact response format of its tool.
# The agent's core logic is entangled with integration details.
# =============================================================================

print("\n[SYSTEM A] Ad-hoc Integration\n")

# ── Tool stubs (simulating external services) ─────────────────────────────────

def mock_web_search_v1(query: str, max_results: int = 3) -> dict:
    """
    Simulates a web search API (Version 1).
    Response format: {"results": [...]}
    """
    return {
        "results": [
            {"title": f"Result 1 for '{query}'", "snippet": "Relevant content A."},
            {"title": f"Result 2 for '{query}'", "snippet": "Relevant content B."},
        ]
    }

def mock_db_lookup(entity: str) -> dict:
    """
    Simulates an internal database query.
    Response format: {"records": [...]}
    """
    return {
        "records": [
            {"id": 1, "entity": entity, "report": f"Internal report on {entity}."},
        ]
    }

# ── Ad-hoc connectors (baked into agent logic) ────────────────────────────────

def adhoc_search(query: str) -> list[str]:
    """Hardcoded connector: assumes response["results"]"""
    raw = mock_web_search_v1(query)
    return [r["snippet"] for r in raw["results"]]   # ← fragile assumption

def adhoc_db(entity: str) -> list[str]:
    """Hardcoded connector: assumes response["records"]"""
    raw = mock_db_lookup(entity)
    return [r["report"] for r in raw["records"]]    # ← fragile assumption

# ── System A agent ────────────────────────────────────────────────────────────

def research_agent_adhoc(query: str) -> str:
    """
    Research agent using ad-hoc integration.
    Tool access is the agent's responsibility.
    """
    web_results  = adhoc_search(query)
    db_results   = adhoc_db(query)
    all_results  = web_results + db_results
    return f"[System A] Research on '{query}':\n" + "\n".join(f"  - {r}" for r in all_results)

# ── Run System A (working state) ──────────────────────────────────────────────
print("Running System A (working state)...")
output = research_agent_adhoc("protocol standards in agentic systems")
print(output)


# =============================================================================
# MANDATORY HUMAN DECISION NODE
# =============================================================================
# The ad-hoc connector architecture above assumes that all tool responses
# are stateless and follow a fixed, known schema at development time.
#
# Before proceeding to the failure demonstration, answer this question:
#
# QUESTION: In your target use case, are any of your tools:
#   (a) Versioned APIs that may change their response schema over time?
#   (b) Third-party services outside your team's control?
#   (c) Shared across multiple agents built by different teams?
#
# If ANY of the above is true, the ad-hoc architecture WILL eventually fail.
# The question is not whether it breaks — it is when and how expensively.
#
# DECISION: [Document your answer here before running the failure cell below]
#   Example: "Yes — we use a third-party web search API (condition a and b).
#             Ad-hoc integration is not viable. Proceeding with System B."
# =============================================================================

print("\n" + "=" * 60)
print("MANDATORY HUMAN DECISION NODE")
print("Pause here. Read the comment block above.")
print("Document your architectural decision before continuing.")
print("=" * 60)


# =============================================================================
# PART 2 — TRIGGERING THE FAILURE (System A)
# =============================================================================
# Simulates a vendor API version bump: response key changes from
# "results" to "data.items" — a common real-world breaking change.
# =============================================================================

print("\n[FAILURE DEMONSTRATION] Triggering schema change in System A\n")

def mock_web_search_v2(query: str, max_results: int = 3) -> dict:
    """
    Simulates web search API Version 2 after a vendor update.
    Breaking change: response format is now {"data": {"items": [...]}}
    """
    return {
        "data": {
            "items": [
                {"title": f"Result 1 for '{query}'", "snippet": "Relevant content A."},
                {"title": f"Result 2 for '{query}'", "snippet": "Relevant content B."},
            ]
        }
    }

# Patch the stub to simulate the vendor update
import builtins
_original_search = mock_web_search_v1

def patched_adhoc_search(query: str) -> list[str]:
    """Same connector code — but the tool now returns v2 format."""
    raw = mock_web_search_v2(query)           # ← vendor changed the format
    return [r["snippet"] for r in raw["results"]]  # ← KeyError: 'results'

print("Calling System A with updated tool (v2 schema)...")
try:
    web_results = patched_adhoc_search("protocol standards")
    print(web_results)
except KeyError as e:
    print(f"  ✗ FAILURE: KeyError {e}")
    print(f"  The agent's connector expected 'results' but received 'data.items'.")
    print(f"  Fix requires locating and updating every agent that calls this tool.")
    print(f"  If 3 agents share this connector, all 3 are broken.")


# =============================================================================
# PART 3 — SYSTEM B: MCP-BASED INTEGRATION
# =============================================================================
# The MCP architecture separates concerns:
#   - MCP Servers own integration details (parsing, auth, normalization)
#   - Agents own reasoning logic only
#   - The contract between them is a stable tool schema
# =============================================================================

print("\n" + "=" * 60)
print("[SYSTEM B] MCP-Based Integration\n")

# ── MCP Tool Schema Definition ────────────────────────────────────────────────
# This is the contract. The agent knows only this — not the implementation.

WEB_SEARCH_SCHEMA = {
    "name": "search_web",
    "description": "Search the web for current information on a topic.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query":       {"type": "string",  "description": "The search query"},
            "max_results": {"type": "integer", "description": "Max results", "default": 5}
        },
        "required": ["query"]
    }
}

DB_LOOKUP_SCHEMA = {
    "name": "lookup_database",
    "description": "Query the internal research database for reports on an entity.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "entity": {"type": "string", "description": "Entity name to look up"}
        },
        "required": ["entity"]
    }
}

# ── MCP Server (owns integration details) ────────────────────────────────────

class MCPServer:
    """
    A minimal MCP server implementation.
    Exposes tools via a standard schema and handles all response normalization
    internally — shielding agents from upstream format changes.
    """

    def __init__(self, name: str):
        self.name = name
        self._tools: dict[str, dict] = {}
        self._handlers: dict[str, Any] = {}

    def register_tool(self, schema: dict, handler):
        self._tools[schema["name"]] = schema
        self._handlers[schema["name"]] = handler

    def list_tools(self) -> list[dict]:
        """Capability manifest — returned to any connecting host."""
        return list(self._tools.values())

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Execute a tool call and return a normalized MCP result."""
        if name not in self._handlers:
            return {"isError": True, "content": [{"type": "text", "text": f"Unknown tool: {name}"}]}
        try:
            result = self._handlers[name](**arguments)
            return {"isError": False, "content": [{"type": "text", "text": json.dumps(result)}]}
        except Exception as e:
            return {"isError": True, "content": [{"type": "text", "text": str(e)}]}


# ── Tool handlers (normalization lives here, not in the agent) ────────────────

def handle_web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Calls the web search API and normalizes the response.
    When the vendor updates their format, only this function changes.
    The agent is unaffected.
    """
    raw = mock_web_search_v2(query, max_results)   # ← using v2 intentionally
    # Normalization: flatten whatever structure the vendor uses
    items = raw.get("data", {}).get("items", raw.get("results", []))
    return [{"snippet": item["snippet"]} for item in items]

def handle_db_lookup(entity: str) -> list[dict]:
    raw = mock_db_lookup(entity)
    return [{"report": r["report"]} for r in raw["records"]]


# ── Wire up the MCP server ────────────────────────────────────────────────────

research_server = MCPServer("research-tools")
research_server.register_tool(WEB_SEARCH_SCHEMA, handle_web_search)
research_server.register_tool(DB_LOOKUP_SCHEMA, handle_db_lookup)

print("MCP Server capability manifest:")
for tool in research_server.list_tools():
    print(f"  • {tool['name']}: {tool['description']}")


# ── MCP Client (runs inside the host, routes tool calls) ─────────────────────

class MCPClient:
    def __init__(self, server: MCPServer):
        self.server = server
        self._manifest = server.list_tools()

    def get_available_tools(self) -> list[dict]:
        return self._manifest

    def invoke(self, tool_name: str, arguments: dict) -> Any:
        result = self.server.call_tool(tool_name, arguments)
        if result["isError"]:
            raise RuntimeError(result["content"][0]["text"])
        return json.loads(result["content"][0]["text"])


# ── System B agent (knows only tool schemas, not implementations) ─────────────

def research_agent_mcp(query: str, client: MCPClient) -> str:
    """
    Research agent using MCP-based integration.
    Calls tools by name and schema — never by implementation detail.
    """
    available_tools = client.get_available_tools()
    tool_names = [t["name"] for t in available_tools]

    results = []

    if "search_web" in tool_names:
        web_results = client.invoke("search_web", {"query": query, "max_results": 3})
        results.extend([r["snippet"] for r in web_results])

    if "lookup_database" in tool_names:
        db_results = client.invoke("lookup_database", {"entity": query})
        results.extend([r["report"] for r in db_results])

    return f"[System B] Research on '{query}':\n" + "\n".join(f"  - {r}" for r in results)


# ── Run System B against the v2 tool (same vendor, no agent changes needed) ───

client = MCPClient(research_server)
print("\nRunning System B (with v2 tool schema — no agent changes required)...")
output = research_agent_mcp("protocol standards in agentic systems", client)
print(output)
print("\n  ✓ System B absorbed the schema change at the server boundary.")
print("  The agent code was not modified.")


# =============================================================================
# PART 4 — EXERCISES
# =============================================================================
# These exercises make the architectural cost of coupling legible.
# Work through them in order. Record your observations.
# =============================================================================

print("\n" + "=" * 60)
print("EXERCISES")
print("=" * 60)

print("""
Exercise 1 — Schema Change Cost
--------------------------------
You already saw this: patched_adhoc_search() breaks when the vendor changes
their response format. System B's agent was unaffected.

TASK: In the ad-hoc system, imagine you have 3 agents all calling
mock_web_search_v1 directly. How many functions need to change when
the vendor updates to v2?

ANSWER: __ (write your number)
Expected: 3  (one per agent)

In System B: How many functions change?
ANSWER: __ 
Expected: 1  (only handle_web_search in the MCP server)


Exercise 2 — Adding a Tool
---------------------------
Add a mock news feed tool to both systems.

SYSTEM A TASK: Write a new connector function adhoc_news() and add it
to research_agent_adhoc(). Count the locations you had to modify.

SYSTEM B TASK: Register a new tool on research_server. Note that
research_agent_mcp() does NOT need to change — it discovers tools
dynamically from the manifest.

LOCATIONS CHANGED in System A: __
LOCATIONS CHANGED in System B: __  (hint: 1)
""")

# ── Starter code for Exercise 2, System B ────────────────────────────────────

NEWS_FEED_SCHEMA = {
    "name": "fetch_news",
    "description": "Fetch recent news headlines on a topic.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "News topic"}
        },
        "required": ["topic"]
    }
}

def handle_news_feed(topic: str) -> list[dict]:
    """Mock news feed handler."""
    return [
        {"headline": f"Breaking: New developments in {topic}"},
        {"headline": f"Analysis: The future of {topic}"},
    ]

# TODO: Uncomment the line below to add the tool and re-run the agent.
# research_server.register_tool(NEWS_FEED_SCHEMA, handle_news_feed)
# Then call: research_agent_mcp("protocol standards", client)
# Observe that the agent picks up the new tool without any agent code changes.

print("""
Exercise 3 — Adding a Second Agent
------------------------------------
TASK: Create a summarization_agent_mcp() that also needs web search.
In System B, how much integration code do you write?

EXPECTED ANSWER: Zero. The new agent connects to the same MCPClient
and calls "search_web" by name. The MCP server is already running.
The N+M structure means a new agent costs 0 additional integration work
per existing tool.

Compare this to System A, where a new agent would need its own
adhoc_search() function — or share the fragile original, coupling
both agents to the same connector bug surface.
""")

print("=" * 60)
print("End of Chapter 12 Demo")
print("Companion chapter: chapter/chapter-12.md")
print("=" * 60)
