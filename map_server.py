

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import os

app = FastAPI(title="Soccer Results MCP Server")

# Football-Data.org API (free tier available)
SOCCER_API_URL = "https://api.football-data.org/v4"
SOCCER_API_KEY = "6860618448ab49f686839e09f2c09e30"  # Get free key at football-data.org

class ToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

class Tool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

@app.get("/tools")
async def list_tools() -> List[Tool]:
    """List all available soccer tools"""
    return [
        Tool(
            name="get_latest_results",
            description="Get latest soccer match results from major leagues. League codes: PL (Premier League), PD (La Liga), BL1 (Bundesliga), SA (Serie A), FL1 (Ligue 1)",
            inputSchema={
                "type": "object",
                "properties": {
                    "league": {
                        "type": "string",
                        "description": "League code: PL, PD, BL1, SA, FL1",
                        "default": "PL"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (1-10)",
                        "default": 3
                    }
                }
            }
        ),
        Tool(
            name="get_team_recent_matches",
            description="Get recent matches for a specific team by team name",
            inputSchema={
                "type": "object",
                "properties": {
                    "team_name": {
                        "type": "string",
                        "description": "Team name (e.g., 'Manchester United', 'Liverpool', 'Arsenal')"
                    }
                },
                "required": ["team_name"]
            }
        ),
        Tool(
            name="get_league_standings",
            description="Get current standings for a league",
            inputSchema={
                "type": "object",
                "properties": {
                    "league": {
                        "type": "string",
                        "description": "League code: PL, PD, BL1, SA, FL1",
                        "default": "PL"
                    }
                },
                "required": ["league"]
            }
        ),
        Tool(
            name="get_todays_matches",
            description="Get today's scheduled matches across all leagues",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

async def fetch_soccer_data(endpoint: str):
    """Fetch data from soccer API"""
    headers = {}
    if SOCCER_API_KEY:
        headers["X-Auth-Token"] = SOCCER_API_KEY
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SOCCER_API_URL}/{endpoint}",
                headers=headers,
                timeout=15.0
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                return {"error": "API rate limit exceeded. Please try again later."}
            elif response.status_code == 403:
                return {"error": "API key required or invalid. Get a free key at https://www.football-data.org/"}
            else:
                return {"error": f"API returned status {response.status_code}"}
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except Exception as e:
            return {"error": f"Network error: {str(e)}"}

# Team name to ID mapping (common teams)
TEAM_MAPPING = {
    "manchester united": 66,
    "man united": 66,
    "liverpool": 64,
    "arsenal": 57,
    "chelsea": 61,
    "manchester city": 65,
    "man city": 65,
    "tottenham": 73,
    "spurs": 73,
    "newcastle": 67,
    "west ham": 563,
    "everton": 62,
    "leicester": 338,
    "wolves": 76,
    "aston villa": 58,
    "brighton": 397,
    "barcelona": 81,
    "real madrid": 86,
    "atletico madrid": 78,
    "bayern munich": 5,
    "borussia dortmund": 4,
    "juventus": 109,
    "ac milan": 98,
    "inter milan": 108,
    "psg": 524,
    "paris saint-germain": 524,
}

@app.post("/execute")
async def execute_tool(request: ToolRequest):
    """Execute a soccer tool"""
    try:
        if request.tool_name == "get_latest_results":
            league = request.arguments.get("league", "PL")
            days = request.arguments.get("days", 3)
            
            date_to = datetime.now().strftime("%Y-%m-%d")
            date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            data = await fetch_soccer_data(
                f"competitions/{league}/matches?status=FINISHED&dateFrom={date_from}&dateTo={date_to}"
            )
            
            if "error" in data:
                return {"result": json.dumps({
                    "error": data["error"],
                    "note": "If you don't have an API key, get a free one at https://www.football-data.org/client/register"
                }, indent=2)}
            
            matches = data.get("matches", [])
            
            if not matches:
                return {"result": json.dumps({
                    "message": f"No finished matches found in the last {days} days for {league}",
                    "suggestion": "Try increasing the number of days or check a different league"
                }, indent=2)}
            
            results = []
            for match in matches:
                home_score = match.get('score', {}).get('fullTime', {}).get('home', '?')
                away_score = match.get('score', {}).get('fullTime', {}).get('away', '?')
                
                results.append({
                    "date": match.get("utcDate", "")[:10],
                    "home_team": match.get("homeTeam", {}).get("name", "Unknown"),
                    "away_team": match.get("awayTeam", {}).get("name", "Unknown"),
                    "score": f"{home_score}-{away_score}",
                    "competition": match.get("competition", {}).get("name", "Unknown")
                })
            
            return {"result": json.dumps({
                "league": league,
                "matches_found": len(results),
                "results": results
            }, indent=2)}
        
        elif request.tool_name == "get_team_recent_matches":
            team_name = request.arguments.get("team_name", "").lower()
            
            # Try to find team ID
            team_id = TEAM_MAPPING.get(team_name)
            
            if not team_id:
                # Return available teams
                available_teams = list(TEAM_MAPPING.keys())
                return {"result": json.dumps({
                    "error": f"Team '{team_name}' not found in database",
                    "available_teams": available_teams[:20],
                    "note": "Try one of the teams listed above"
                }, indent=2)}
            
            # Get team matches - fetch all matches for current season (season has ~60 matches)
            data = await fetch_soccer_data(f"teams/{team_id}/matches?limit=100")

            if "error" in data:
                return {"result": json.dumps({"error": data["error"]}, indent=2)}

            matches = data.get("matches", [])

            # Filter to only finished matches from current season (2025-2026) and sort by date descending
            current_season_start = "2025-08-01"
            finished_matches = [
                m for m in matches
                if m.get("status") == "FINISHED" and m.get("utcDate", "")[:10] >= current_season_start
            ]
            finished_matches.sort(key=lambda x: x.get("utcDate", ""), reverse=True)

            results = []
            for match in finished_matches:  # All finished matches from current season
                home_team = match.get("homeTeam", {}).get("name", "Unknown")
                away_team = match.get("awayTeam", {}).get("name", "Unknown")
                home_score = match.get('score', {}).get('fullTime', {}).get('home', '?')
                away_score = match.get('score', {}).get('fullTime', {}).get('away', '?')

                results.append({
                    "date": match.get("utcDate", "")[:10],
                    "home_team": home_team,
                    "away_team": away_team,
                    "score": f"{home_score}-{away_score}",
                    "competition": match.get("competition", {}).get("name", "Unknown"),
                    "status": match.get("status", "Unknown")
                })
            
            return {"result": json.dumps({
                "team": team_name.title(),
                "recent_matches": results
            }, indent=2)}
        
        elif request.tool_name == "get_league_standings":
            league = request.arguments.get("league", "PL")
            
            data = await fetch_soccer_data(f"competitions/{league}/standings")
            
            if "error" in data:
                return {"result": json.dumps({"error": data["error"]}, indent=2)}
            
            standings = data.get("standings", [])
            if not standings:
                return {"result": json.dumps({"error": "No standings data available"}, indent=2)}
            
            table = standings[0].get("table", [])
            results = []
            
            for position in table[:10]:  # Top 10
                results.append({
                    "position": position.get("position"),
                    "team": position.get("team", {}).get("name"),
                    "played": position.get("playedGames"),
                    "won": position.get("won"),
                    "drawn": position.get("draw"),
                    "lost": position.get("lost"),
                    "points": position.get("points"),
                    "goal_difference": position.get("goalDifference")
                })
            
            return {"result": json.dumps({
                "league": league,
                "standings": results
            }, indent=2)}
        
        elif request.tool_name == "get_todays_matches":
            today = datetime.now().strftime("%Y-%m-%d")
            
            data = await fetch_soccer_data(f"matches?dateFrom={today}&dateTo={today}")
            
            if "error" in data:
                return {"result": json.dumps({"error": data["error"]}, indent=2)}
            
            matches = data.get("matches", [])
            
            if not matches:
                return {"result": json.dumps({
                    "message": "No matches scheduled for today",
                    "date": today
                }, indent=2)}
            
            results = []
            for match in matches[:20]:  # Limit to 20 matches
                results.append({
                    "time": match.get("utcDate", "")[:16].replace('T', ' '),
                    "home_team": match.get("homeTeam", {}).get("name"),
                    "away_team": match.get("awayTeam", {}).get("name"),
                    "competition": match.get("competition", {}).get("name"),
                    "status": match.get("status")
                })
            
            return {"result": json.dumps({
                "date": today,
                "matches_today": len(results),
                "matches": results
            }, indent=2)}
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {request.tool_name}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "server": "soccer-mcp"}

@app.get("/")
async def root():
    return {
        "message": "Soccer Results MCP Server",
        "api_info": "Using football-data.org API",
        "note": "Get a free API key at https://www.football-data.org/client/register for more requests",
        "endpoints": {
            "tools": "/tools",
            "execute": "/execute",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Soccer MCP Server...")
    if not SOCCER_API_KEY:
        print("⚠️  No API key found. Get a free key at: https://www.football-data.org/client/register")
        print("   Add it to your .env file as: FOOTBALL_API_KEY=your-key")
    print("📍 Server: http://localhost:8081")
    uvicorn.run(app, host="0.0.0.0", port=8081)