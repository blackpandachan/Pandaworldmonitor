import asyncio

from sentinel.main import mcp


async def test_mcp_tool_inventory_contains_core_tools() -> None:
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}
    expected = {
        "mcp_fetch_news",
        "mcp_fetch_conflict_events",
        "mcp_fetch_natural_events",
        "mcp_fetch_infrastructure_status",
        "mcp_fetch_gdelt_events",
        "mcp_search_news_archive",
        "mcp_classify_articles",
        "mcp_generate_situation_brief",
        "mcp_generate_delta_brief",
        "mcp_compute_risk_scores",
        "mcp_detect_convergence",
        "mcp_manage_watchlist",
        "mcp_check_watchlist_alerts",
        "mcp_get_map_layer_data",
        "mcp_get_dashboard_state",
    }
    assert expected.issubset(names)
