"""
Portal Agents - MCP-compatible autonomous agents
These agents can be invoked directly from Claude Code to perform multi-step tasks
"""

import json
import httpx
import os
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

load_dotenv()

# MCP Server URLs
MCP_SOCCER_URL = os.getenv("MCP_SOCCER_URL", "http://localhost:8081")
MCP_GOOGLE_URL = os.getenv("MCP_GOOGLE_URL", "http://localhost:8082")
MCP_MAPS_URL = os.getenv("MCP_MAPS_URL", "http://localhost:8083")
MCP_TOMTOM_URL = os.getenv("MCP_TOMTOM_URL", "http://localhost:8084")
MCP_DATABRICKS_URL = os.getenv("MCP_DATABRICKS_URL", "http://localhost:8085")


def execute_tool(server_url: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool on an MCP server"""
    try:
        print(f"🔧 Executing {tool_name} on {server_url}")
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{server_url}/execute",
                json={"tool_name": tool_name, "arguments": arguments}
            )
            result = response.json()["result"]
            if isinstance(result, str):
                result = json.loads(result)
            return result
    except Exception as e:
        return {"error": str(e)}


class DataAnalystAgent:
    """
    Autonomous agent that analyzes data from Databricks
    - Discovers available tables
    - Queries data based on user intent
    - Generates insights and reports
    - Emails results
    """

    def __init__(self):
        self.name = "Data Analyst Agent"
        self.results = []

    def run(self, query: str, table_name: Optional[str] = None, email_results: bool = True):
        """
        Run the data analyst agent

        Args:
            query: SQL query or natural language question
            table_name: Specific table to query (optional)
            email_results: Whether to email the results
        """
        print(f"\n{'='*60}")
        print(f"🤖 {self.name} Starting...")
        print(f"{'='*60}\n")

        # Step 1: List available tables if no table specified
        if not table_name:
            print("📋 Step 1: Discovering available tables...")
            tables_result = execute_tool(
                MCP_DATABRICKS_URL,
                "list_tables",
                {"catalog": "hive_metastore", "schema": "default"}
            )
            self.results.append({"step": "list_tables", "result": tables_result})
            print(f"✅ Found tables: {tables_result.get('tables', [])}")

            if tables_result.get('tables'):
                table_name = tables_result['tables'][0]
                print(f"📊 Using table: {table_name}\n")

        # Step 2: Get table schema
        if table_name:
            print(f"📋 Step 2: Getting schema for {table_name}...")
            schema_result = execute_tool(
                MCP_DATABRICKS_URL,
                "get_table_schema",
                {"table_name": table_name}
            )
            self.results.append({"step": "get_table_schema", "result": schema_result})
            print(f"✅ Schema: {schema_result.get('columns', [])}\n")

        # Step 3: Execute query
        print(f"📊 Step 3: Executing query...")
        sql_result = execute_tool(
            MCP_DATABRICKS_URL,
            "execute_sql",
            {"query": query}
        )
        self.results.append({"step": "execute_sql", "result": sql_result})
        print(f"✅ Query complete: {sql_result.get('total_rows', 0)} rows\n")

        # Step 4: Email results
        if email_results:
            print(f"📧 Step 4: Emailing results...")
            email_result = execute_tool(
                MCP_GOOGLE_URL,
                "email_me",
                {
                    "subject": f"Data Analysis: {table_name or 'Custom Query'}",
                    "data": json.dumps(sql_result, indent=2)
                }
            )
            self.results.append({"step": "email_results", "result": email_result})
            print(f"✅ Results emailed\n")

        print(f"{'='*60}")
        print(f"✅ {self.name} Complete!")
        print(f"{'='*60}\n")

        return self.results


class SportsIntelligenceAgent:
    """
    Autonomous agent for sports analysis
    - Gets team recent matches
    - Analyzes performance trends
    - Compares with league standings
    - Generates report
    """

    def __init__(self):
        self.name = "Sports Intelligence Agent"
        self.results = []

    def run(self, team_name: str, league: str = "PL", email_results: bool = True):
        """
        Run the sports intelligence agent

        Args:
            team_name: Name of the team to analyze
            league: League code (PL, PD, BL1, SA, FL1)
            email_results: Whether to email the report
        """
        print(f"\n{'='*60}")
        print(f"⚽ {self.name} Starting...")
        print(f"{'='*60}\n")

        # Step 1: Get team recent matches
        print(f"📊 Step 1: Getting recent matches for {team_name}...")
        matches_result = execute_tool(
            MCP_SOCCER_URL,
            "get_team_recent_matches",
            {"team_name": team_name}
        )
        self.results.append({"step": "team_matches", "result": matches_result})
        print(f"✅ Retrieved match data\n")

        # Step 2: Get league standings
        print(f"📊 Step 2: Getting {league} standings...")
        standings_result = execute_tool(
            MCP_SOCCER_URL,
            "get_league_standings",
            {"league": league}
        )
        self.results.append({"step": "league_standings", "result": standings_result})
        print(f"✅ Retrieved standings\n")

        # Step 3: Get latest league results
        print(f"📊 Step 3: Getting latest {league} results...")
        results_result = execute_tool(
            MCP_SOCCER_URL,
            "get_latest_results",
            {"league": league, "days": 7}
        )
        self.results.append({"step": "latest_results", "result": results_result})
        print(f"✅ Retrieved recent results\n")

        # Step 4: Email comprehensive report
        if email_results:
            print(f"📧 Step 4: Emailing intelligence report...")
            report = {
                "team": team_name,
                "league": league,
                "matches": matches_result,
                "standings": standings_result,
                "recent_results": results_result
            }
            email_result = execute_tool(
                MCP_GOOGLE_URL,
                "email_me",
                {
                    "subject": f"Sports Intelligence Report: {team_name}",
                    "data": json.dumps(report, indent=2)
                }
            )
            self.results.append({"step": "email_report", "result": email_result})
            print(f"✅ Report emailed\n")

        print(f"{'='*60}")
        print(f"✅ {self.name} Complete!")
        print(f"{'='*60}\n")

        return self.results


class LocationIntelligenceAgent:
    """
    Autonomous agent for location analysis
    - Searches for places
    - Checks traffic conditions
    - Finds nearby amenities
    - Calculates routes with traffic
    """

    def __init__(self):
        self.name = "Location Intelligence Agent"
        self.results = []

    def run(self, location: str, search_query: str, check_traffic: bool = True, email_results: bool = True):
        """
        Run the location intelligence agent

        Args:
            location: Location to analyze
            search_query: What to search for (e.g., "restaurants", "hotels")
            check_traffic: Whether to check traffic conditions
            email_results: Whether to email the report
        """
        print(f"\n{'='*60}")
        print(f"📍 {self.name} Starting...")
        print(f"{'='*60}\n")

        # Step 1: Search for places
        print(f"🔍 Step 1: Searching for {search_query} near {location}...")
        places_result = execute_tool(
            MCP_TOMTOM_URL,
            "search_places",
            {"query": search_query, "location": location, "limit": 10}
        )
        self.results.append({"step": "search_places", "result": places_result})
        print(f"✅ Found {places_result.get('count', 0)} places\n")

        # Step 2: Check traffic if requested
        if check_traffic:
            print(f"🚗 Step 2: Checking traffic conditions at {location}...")
            traffic_result = execute_tool(
                MCP_TOMTOM_URL,
                "get_traffic_info",
                {"location": location}
            )
            self.results.append({"step": "traffic_info", "result": traffic_result})
            print(f"✅ Traffic: {traffic_result.get('traffic_level', 'Unknown')}\n")

        # Step 3: Find nearby amenities
        print(f"🏪 Step 3: Finding nearby amenities...")
        nearby_result = execute_tool(
            MCP_TOMTOM_URL,
            "nearby_search",
            {"location": location, "category": "restaurant", "radius": 2000}
        )
        self.results.append({"step": "nearby_search", "result": nearby_result})
        print(f"✅ Found {nearby_result.get('count', 0)} nearby places\n")

        # Step 4: Email report
        if email_results:
            print(f"📧 Step 4: Emailing location report...")
            report = {
                "location": location,
                "search_query": search_query,
                "places_found": places_result,
                "traffic_conditions": traffic_result if check_traffic else None,
                "nearby_amenities": nearby_result
            }
            email_result = execute_tool(
                MCP_GOOGLE_URL,
                "email_me",
                {
                    "subject": f"Location Intelligence: {location}",
                    "data": json.dumps(report, indent=2)
                }
            )
            self.results.append({"step": "email_report", "result": email_result})
            print(f"✅ Report emailed\n")

        print(f"{'='*60}")
        print(f"✅ {self.name} Complete!")
        print(f"{'='*60}\n")

        return self.results


class ETLOrchestratorAgent:
    """
    Autonomous agent for ETL pipeline orchestration
    - Checks cluster status
    - Starts cluster if needed
    - Runs notebook
    - Monitors execution
    - Sends completion notification
    """

    def __init__(self):
        self.name = "ETL Orchestrator Agent"
        self.results = []

    def run(self, notebook_path: str, cluster_id: Optional[str] = None, parameters: Optional[Dict] = None, email_results: bool = True):
        """
        Run the ETL orchestrator agent

        Args:
            notebook_path: Path to Databricks notebook
            cluster_id: Cluster ID (optional, uses default if not provided)
            parameters: Notebook parameters
            email_results: Whether to email completion notification
        """
        print(f"\n{'='*60}")
        print(f"⚙️ {self.name} Starting...")
        print(f"{'='*60}\n")

        # Step 1: Check cluster status
        print(f"🖥️  Step 1: Checking cluster status...")
        cluster_status = execute_tool(
            MCP_DATABRICKS_URL,
            "get_cluster_status",
            {"cluster_id": cluster_id or ""}
        )
        self.results.append({"step": "cluster_status", "result": cluster_status})
        print(f"✅ Cluster state: {cluster_status.get('state', 'Unknown')}\n")

        # Step 2: Start cluster if needed
        if cluster_status.get('state') in ['TERMINATED', 'STOPPED']:
            print(f"🚀 Step 2: Starting cluster...")
            start_result = execute_tool(
                MCP_DATABRICKS_URL,
                "start_cluster",
                {"cluster_id": cluster_id or ""}
            )
            self.results.append({"step": "start_cluster", "result": start_result})
            print(f"✅ Cluster starting...\n")
        else:
            print(f"✅ Step 2: Cluster already running\n")

        # Step 3: Run notebook
        print(f"📓 Step 3: Running notebook {notebook_path}...")
        run_result = execute_tool(
            MCP_DATABRICKS_URL,
            "run_notebook",
            {
                "notebook_path": notebook_path,
                "parameters": parameters or {},
                "cluster_id": cluster_id or ""
            }
        )
        self.results.append({"step": "run_notebook", "result": run_result})
        run_id = run_result.get('run_id')
        print(f"✅ Notebook submitted: Run ID {run_id}\n")

        # Step 4: Check run status
        if run_id:
            print(f"📊 Step 4: Checking run status...")
            status_result = execute_tool(
                MCP_DATABRICKS_URL,
                "get_job_run_status",
                {"run_id": run_id}
            )
            self.results.append({"step": "run_status", "result": status_result})
            print(f"✅ Status: {status_result.get('state', 'Unknown')}\n")

        # Step 5: Email completion notification
        if email_results:
            print(f"📧 Step 5: Sending completion notification...")
            report = {
                "notebook": notebook_path,
                "run_id": run_id,
                "cluster_status": cluster_status,
                "run_result": run_result,
                "final_status": status_result if run_id else None
            }
            email_result = execute_tool(
                MCP_GOOGLE_URL,
                "email_me",
                {
                    "subject": f"ETL Pipeline Complete: {notebook_path}",
                    "data": json.dumps(report, indent=2)
                }
            )
            self.results.append({"step": "email_notification", "result": email_result})
            print(f"✅ Notification sent\n")

        print(f"{'='*60}")
        print(f"✅ {self.name} Complete!")
        print(f"{'='*60}\n")

        return self.results


class MultiServiceResearchAgent:
    """
    Autonomous agent that combines multiple services for research
    - Queries Databricks data
    - Gets sports information
    - Searches locations
    - Compiles comprehensive report
    """

    def __init__(self):
        self.name = "Multi-Service Research Agent"
        self.results = []

    def run(self, topic: str, include_data: bool = True, include_sports: bool = True, include_location: bool = True, email_results: bool = True):
        """
        Run the multi-service research agent

        Args:
            topic: Research topic
            include_data: Include Databricks data
            include_sports: Include sports data
            include_location: Include location data
            email_results: Whether to email the report
        """
        print(f"\n{'='*60}")
        print(f"🔍 {self.name} Starting...")
        print(f"📝 Topic: {topic}")
        print(f"{'='*60}\n")

        # Step 1: Query Databricks data
        if include_data:
            print(f"📊 Step 1: Querying Databricks data...")
            tables_result = execute_tool(
                MCP_DATABRICKS_URL,
                "list_tables",
                {"catalog": "hive_metastore", "schema": "default"}
            )
            self.results.append({"step": "databricks_data", "result": tables_result})
            print(f"✅ Found {tables_result.get('count', 0)} tables\n")

        # Step 2: Get sports data
        if include_sports:
            print(f"⚽ Step 2: Getting sports data...")
            sports_result = execute_tool(
                MCP_SOCCER_URL,
                "get_latest_results",
                {"league": "PL", "days": 3}
            )
            self.results.append({"step": "sports_data", "result": sports_result})
            print(f"✅ Retrieved sports data\n")

        # Step 3: Search locations
        if include_location:
            print(f"📍 Step 3: Searching locations...")
            location_result = execute_tool(
                MCP_TOMTOM_URL,
                "search_places",
                {"query": topic, "limit": 5}
            )
            self.results.append({"step": "location_data", "result": location_result})
            print(f"✅ Found {location_result.get('count', 0)} locations\n")

        # Step 4: Compile and email report
        if email_results:
            print(f"📧 Step 4: Compiling and emailing research report...")
            report = {
                "topic": topic,
                "databricks_data": [r for r in self.results if r["step"] == "databricks_data"],
                "sports_data": [r for r in self.results if r["step"] == "sports_data"],
                "location_data": [r for r in self.results if r["step"] == "location_data"]
            }
            email_result = execute_tool(
                MCP_GOOGLE_URL,
                "email_me",
                {
                    "subject": f"Multi-Service Research: {topic}",
                    "data": json.dumps(report, indent=2)
                }
            )
            self.results.append({"step": "email_report", "result": email_result})
            print(f"✅ Report emailed\n")

        print(f"{'='*60}")
        print(f"✅ {self.name} Complete!")
        print(f"{'='*60}\n")

        return self.results


# Example usage functions for easy invocation
def run_data_analyst(query: str, table_name: Optional[str] = None):
    """Quick runner for data analyst agent"""
    agent = DataAnalystAgent()
    return agent.run(query, table_name)


def run_sports_analyst(team_name: str, league: str = "PL"):
    """Quick runner for sports intelligence agent"""
    agent = SportsIntelligenceAgent()
    return agent.run(team_name, league)


def run_location_scout(location: str, search_query: str):
    """Quick runner for location intelligence agent"""
    agent = LocationIntelligenceAgent()
    return agent.run(location, search_query)


def run_etl_orchestrator(notebook_path: str, cluster_id: Optional[str] = None):
    """Quick runner for ETL orchestrator agent"""
    agent = ETLOrchestratorAgent()
    return agent.run(notebook_path, cluster_id)


def run_research_assistant(topic: str):
    """Quick runner for multi-service research agent"""
    agent = MultiServiceResearchAgent()
    return agent.run(topic)


if __name__ == "__main__":
    print("🤖 Portal Agents Available:")
    print("1. DataAnalystAgent - Analyze data from Databricks")
    print("2. SportsIntelligenceAgent - Analyze team performance")
    print("3. LocationIntelligenceAgent - Location and traffic analysis")
    print("4. ETLOrchestratorAgent - Manage ETL pipelines")
    print("5. MultiServiceResearchAgent - Cross-service research")
    print("\nUse these agents from Claude Code by importing and running them!")
