"""
Soccer Analyzer MCP Server
Analyzes match results and provides predictions using statistical analysis
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import os

app = FastAPI(title="Soccer Analyzer MCP Server")

# Football-Data.org API
SOCCER_API_URL = "https://api.football-data.org/v4"
SOCCER_API_KEY = os.getenv("FOOTBALL_API_KEY", "6860618448ab49f686839e09f2c09e30")

# Team ID mapping
TEAM_MAPPING = {
    "manchester united": 66, "liverpool": 64, "arsenal": 57, "chelsea": 61,
    "manchester city": 65, "tottenham": 73, "newcastle": 67, "west ham": 563,
    "aston villa": 58, "brighton": 397, "crystal palace": 354, "brentford": 402,
    "fulham": 63, "wolves": 76, "bournemouth": 1044, "nottingham forest": 351,
    "everton": 62, "leicester": 338, "ipswich": 349, "southampton": 340,
    "real madrid": 86, "barcelona": 81, "atletico madrid": 78, "sevilla": 559,
    "bayern munich": 5, "borussia dortmund": 4, "juventus": 109, "inter milan": 108,
    "ac milan": 98, "psg": 524, "lyon": 523, "marseille": 516
}

class ToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

class Tool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

@app.get("/tools")
async def list_tools() -> List[Tool]:
    """List all available analyzer tools"""
    return [
        Tool(
            name="predict_match",
            description="Predict the outcome of an upcoming match between two teams based on recent form and head-to-head history",
            inputSchema={
                "type": "object",
                "properties": {
                    "home_team": {
                        "type": "string",
                        "description": "Home team name (e.g., 'Manchester United', 'Liverpool')"
                    },
                    "away_team": {
                        "type": "string",
                        "description": "Away team name (e.g., 'Arsenal', 'Chelsea')"
                    }
                },
                "required": ["home_team", "away_team"]
            }
        ),
        Tool(
            name="analyze_team_form",
            description="Analyze a team's recent form including wins, losses, goals scored, and performance trend",
            inputSchema={
                "type": "object",
                "properties": {
                    "team_name": {
                        "type": "string",
                        "description": "Team name to analyze"
                    }
                },
                "required": ["team_name"]
            }
        ),
        Tool(
            name="head_to_head",
            description="Get head-to-head statistics between two teams",
            inputSchema={
                "type": "object",
                "properties": {
                    "team1": {
                        "type": "string",
                        "description": "First team name"
                    },
                    "team2": {
                        "type": "string",
                        "description": "Second team name"
                    }
                },
                "required": ["team1", "team2"]
            }
        ),
        Tool(
            name="get_team_stats",
            description="Get detailed statistics for a team including goals, clean sheets, and scoring patterns",
            inputSchema={
                "type": "object",
                "properties": {
                    "team_name": {
                        "type": "string",
                        "description": "Team name"
                    }
                },
                "required": ["team_name"]
            }
        ),
        Tool(
            name="league_predictions",
            description="Get predictions for upcoming matches in a league",
            inputSchema={
                "type": "object",
                "properties": {
                    "league": {
                        "type": "string",
                        "description": "League code: PL (Premier League), PD (La Liga), BL1 (Bundesliga), SA (Serie A), FL1 (Ligue 1)",
                        "default": "PL"
                    }
                }
            }
        ),
        Tool(
            name="goal_probability",
            description="Calculate the probability of goals in a match (over/under analysis)",
            inputSchema={
                "type": "object",
                "properties": {
                    "home_team": {
                        "type": "string",
                        "description": "Home team name"
                    },
                    "away_team": {
                        "type": "string",
                        "description": "Away team name"
                    }
                },
                "required": ["home_team", "away_team"]
            }
        )
    ]

async def fetch_soccer_data(endpoint: str):
    """Fetch data from soccer API"""
    headers = {"X-Auth-Token": SOCCER_API_KEY} if SOCCER_API_KEY else {}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SOCCER_API_URL}/{endpoint}",
                headers=headers,
                timeout=15.0
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

async def get_team_matches(team_id: int, limit: int = 10):
    """Get recent matches for a team"""
    data = await fetch_soccer_data(f"teams/{team_id}/matches?limit={limit}")
    if "error" in data:
        return []

    matches = data.get("matches", [])
    finished = [m for m in matches if m.get("status") == "FINISHED"]
    finished.sort(key=lambda x: x.get("utcDate", ""), reverse=True)
    return finished

def calculate_form_score(matches: List[dict], team_id: int) -> dict:
    """Calculate form score from recent matches"""
    if not matches:
        return {"score": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0}

    wins, draws, losses = 0, 0, 0
    goals_for, goals_against = 0, 0
    points = 0

    for match in matches[:10]:  # Last 10 matches
        home_id = match.get("homeTeam", {}).get("id")
        home_score = match.get("score", {}).get("fullTime", {}).get("home", 0) or 0
        away_score = match.get("score", {}).get("fullTime", {}).get("away", 0) or 0

        if home_id == team_id:
            goals_for += home_score
            goals_against += away_score
            if home_score > away_score:
                wins += 1
                points += 3
            elif home_score == away_score:
                draws += 1
                points += 1
            else:
                losses += 1
        else:
            goals_for += away_score
            goals_against += home_score
            if away_score > home_score:
                wins += 1
                points += 3
            elif home_score == away_score:
                draws += 1
                points += 1
            else:
                losses += 1

    total_matches = wins + draws + losses
    form_score = (points / (total_matches * 3)) * 100 if total_matches > 0 else 0

    return {
        "score": round(form_score, 1),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "goal_difference": goals_for - goals_against,
        "avg_goals_scored": round(goals_for / total_matches, 2) if total_matches > 0 else 0,
        "avg_goals_conceded": round(goals_against / total_matches, 2) if total_matches > 0 else 0,
        "matches_analyzed": total_matches
    }

def predict_winner(home_form: dict, away_form: dict, home_team: str, away_team: str) -> dict:
    """Predict match winner based on form analysis"""

    # Base probabilities (home advantage ~55%)
    home_base = 45
    away_base = 30
    draw_base = 25

    # Adjust based on form scores
    form_diff = home_form["score"] - away_form["score"]

    # Form adjustment (max 20% swing)
    form_adjustment = min(max(form_diff / 5, -20), 20)

    # Goal scoring adjustment
    home_attack = home_form["avg_goals_scored"] * 5
    away_attack = away_form["avg_goals_scored"] * 5

    # Defense adjustment
    home_defense = (2 - home_form["avg_goals_conceded"]) * 5
    away_defense = (2 - away_form["avg_goals_conceded"]) * 5

    # Calculate final probabilities
    home_prob = home_base + form_adjustment + (home_attack - away_defense) / 2
    away_prob = away_base - form_adjustment + (away_attack - home_defense) / 2
    draw_prob = 100 - home_prob - away_prob

    # Normalize to ensure total is 100%
    total = home_prob + away_prob + draw_prob
    home_prob = round((home_prob / total) * 100, 1)
    away_prob = round((away_prob / total) * 100, 1)
    draw_prob = round(100 - home_prob - away_prob, 1)

    # Determine prediction
    if home_prob > away_prob and home_prob > draw_prob:
        prediction = f"{home_team} Win"
        confidence = "High" if home_prob > 50 else "Medium" if home_prob > 40 else "Low"
    elif away_prob > home_prob and away_prob > draw_prob:
        prediction = f"{away_team} Win"
        confidence = "High" if away_prob > 45 else "Medium" if away_prob > 35 else "Low"
    else:
        prediction = "Draw"
        confidence = "Medium" if draw_prob > 30 else "Low"

    # Predicted score based on averages
    predicted_home_goals = round((home_form["avg_goals_scored"] + away_form["avg_goals_conceded"]) / 2)
    predicted_away_goals = round((away_form["avg_goals_scored"] + home_form["avg_goals_conceded"]) / 2)

    return {
        "prediction": prediction,
        "confidence": confidence,
        "probabilities": {
            "home_win": home_prob,
            "draw": draw_prob,
            "away_win": away_prob
        },
        "predicted_score": f"{predicted_home_goals}-{predicted_away_goals}",
        "analysis": {
            "home_form_score": home_form["score"],
            "away_form_score": away_form["score"],
            "home_attack_rating": round(home_form["avg_goals_scored"] * 10, 1),
            "away_attack_rating": round(away_form["avg_goals_scored"] * 10, 1),
            "home_defense_rating": round((2 - home_form["avg_goals_conceded"]) * 10, 1),
            "away_defense_rating": round((2 - away_form["avg_goals_conceded"]) * 10, 1)
        }
    }

@app.post("/execute")
async def execute_tool(request: ToolRequest):
    """Execute a soccer analyzer tool"""
    try:
        if request.tool_name == "predict_match":
            home_team = request.arguments.get("home_team", "").lower()
            away_team = request.arguments.get("away_team", "").lower()

            home_id = TEAM_MAPPING.get(home_team)
            away_id = TEAM_MAPPING.get(away_team)

            if not home_id or not away_id:
                return {"result": json.dumps({
                    "error": "Team not found",
                    "available_teams": list(TEAM_MAPPING.keys())[:20]
                }, indent=2)}

            # Get recent matches for both teams
            home_matches = await get_team_matches(home_id, 50)
            away_matches = await get_team_matches(away_id, 50)

            # Calculate form
            home_form = calculate_form_score(home_matches, home_id)
            away_form = calculate_form_score(away_matches, away_id)

            # Generate prediction
            prediction = predict_winner(home_form, away_form, home_team.title(), away_team.title())

            return {"result": json.dumps({
                "match": f"{home_team.title()} vs {away_team.title()}",
                "prediction": prediction["prediction"],
                "confidence": prediction["confidence"],
                "predicted_score": prediction["predicted_score"],
                "win_probabilities": prediction["probabilities"],
                "analysis": prediction["analysis"],
                "home_recent_form": {
                    "last_10_matches": f"{home_form['wins']}W-{home_form['draws']}D-{home_form['losses']}L",
                    "goals_scored": home_form["goals_for"],
                    "goals_conceded": home_form["goals_against"]
                },
                "away_recent_form": {
                    "last_10_matches": f"{away_form['wins']}W-{away_form['draws']}D-{away_form['losses']}L",
                    "goals_scored": away_form["goals_for"],
                    "goals_conceded": away_form["goals_against"]
                }
            }, indent=2)}

        elif request.tool_name == "analyze_team_form":
            team_name = request.arguments.get("team_name", "").lower()
            team_id = TEAM_MAPPING.get(team_name)

            if not team_id:
                return {"result": json.dumps({
                    "error": f"Team '{team_name}' not found",
                    "available_teams": list(TEAM_MAPPING.keys())[:20]
                }, indent=2)}

            matches = await get_team_matches(team_id, 50)
            form = calculate_form_score(matches, team_id)

            # Determine trend
            recent_5 = calculate_form_score(matches[:5], team_id) if len(matches) >= 5 else form
            older_5 = calculate_form_score(matches[5:10], team_id) if len(matches) >= 10 else form

            if recent_5["score"] > older_5["score"] + 10:
                trend = "Improving"
            elif recent_5["score"] < older_5["score"] - 10:
                trend = "Declining"
            else:
                trend = "Stable"

            # Get recent results
            recent_results = []
            for match in matches[:5]:
                home = match.get("homeTeam", {}).get("name", "Unknown")
                away = match.get("awayTeam", {}).get("name", "Unknown")
                home_score = match.get("score", {}).get("fullTime", {}).get("home", 0)
                away_score = match.get("score", {}).get("fullTime", {}).get("away", 0)
                date = match.get("utcDate", "")[:10]
                recent_results.append(f"{date}: {home} {home_score}-{away_score} {away}")

            return {"result": json.dumps({
                "team": team_name.title(),
                "form_rating": f"{form['score']}/100",
                "trend": trend,
                "last_10_matches": f"{form['wins']}W-{form['draws']}D-{form['losses']}L",
                "goals_scored": form["goals_for"],
                "goals_conceded": form["goals_against"],
                "goal_difference": form["goal_difference"],
                "avg_goals_per_match": form["avg_goals_scored"],
                "avg_goals_conceded_per_match": form["avg_goals_conceded"],
                "attack_rating": f"{round(form['avg_goals_scored'] * 10, 1)}/20",
                "defense_rating": f"{round((2 - form['avg_goals_conceded']) * 10, 1)}/20",
                "recent_results": recent_results
            }, indent=2)}

        elif request.tool_name == "head_to_head":
            team1 = request.arguments.get("team1", "").lower()
            team2 = request.arguments.get("team2", "").lower()

            team1_id = TEAM_MAPPING.get(team1)
            team2_id = TEAM_MAPPING.get(team2)

            if not team1_id or not team2_id:
                return {"result": json.dumps({
                    "error": "Team not found",
                    "available_teams": list(TEAM_MAPPING.keys())[:20]
                }, indent=2)}

            # Get matches for team1 and filter for h2h
            matches = await get_team_matches(team1_id, 100)

            h2h_matches = []
            team1_wins, team2_wins, draws = 0, 0, 0
            team1_goals, team2_goals = 0, 0

            for match in matches:
                home_id = match.get("homeTeam", {}).get("id")
                away_id = match.get("awayTeam", {}).get("id")

                if (home_id == team1_id and away_id == team2_id) or (home_id == team2_id and away_id == team1_id):
                    home_score = match.get("score", {}).get("fullTime", {}).get("home", 0) or 0
                    away_score = match.get("score", {}).get("fullTime", {}).get("away", 0) or 0

                    if home_id == team1_id:
                        team1_goals += home_score
                        team2_goals += away_score
                        if home_score > away_score:
                            team1_wins += 1
                        elif away_score > home_score:
                            team2_wins += 1
                        else:
                            draws += 1
                    else:
                        team1_goals += away_score
                        team2_goals += home_score
                        if away_score > home_score:
                            team1_wins += 1
                        elif home_score > away_score:
                            team2_wins += 1
                        else:
                            draws += 1

                    h2h_matches.append({
                        "date": match.get("utcDate", "")[:10],
                        "home": match.get("homeTeam", {}).get("name"),
                        "away": match.get("awayTeam", {}).get("name"),
                        "score": f"{home_score}-{away_score}"
                    })

            total_matches = team1_wins + team2_wins + draws

            return {"result": json.dumps({
                "head_to_head": f"{team1.title()} vs {team2.title()}",
                "total_meetings": total_matches,
                "record": {
                    f"{team1.title()}_wins": team1_wins,
                    "draws": draws,
                    f"{team2.title()}_wins": team2_wins
                },
                "goals": {
                    f"{team1.title()}": team1_goals,
                    f"{team2.title()}": team2_goals
                },
                "dominance": team1.title() if team1_wins > team2_wins else team2.title() if team2_wins > team1_wins else "Even",
                "recent_meetings": h2h_matches[:5]
            }, indent=2)}

        elif request.tool_name == "get_team_stats":
            team_name = request.arguments.get("team_name", "").lower()
            team_id = TEAM_MAPPING.get(team_name)

            if not team_id:
                return {"result": json.dumps({
                    "error": f"Team '{team_name}' not found",
                    "available_teams": list(TEAM_MAPPING.keys())[:20]
                }, indent=2)}

            matches = await get_team_matches(team_id, 50)

            home_matches, away_matches = [], []
            clean_sheets = 0
            failed_to_score = 0
            both_teams_scored = 0

            for match in matches:
                home_id = match.get("homeTeam", {}).get("id")
                home_score = match.get("score", {}).get("fullTime", {}).get("home", 0) or 0
                away_score = match.get("score", {}).get("fullTime", {}).get("away", 0) or 0

                is_home = home_id == team_id
                team_score = home_score if is_home else away_score
                opponent_score = away_score if is_home else home_score

                if is_home:
                    home_matches.append({"scored": team_score, "conceded": opponent_score})
                else:
                    away_matches.append({"scored": team_score, "conceded": opponent_score})

                if opponent_score == 0:
                    clean_sheets += 1
                if team_score == 0:
                    failed_to_score += 1
                if team_score > 0 and opponent_score > 0:
                    both_teams_scored += 1

            total = len(matches)
            home_goals = sum(m["scored"] for m in home_matches)
            away_goals = sum(m["scored"] for m in away_matches)

            return {"result": json.dumps({
                "team": team_name.title(),
                "matches_analyzed": total,
                "home_record": {
                    "matches": len(home_matches),
                    "goals_scored": home_goals,
                    "avg_goals": round(home_goals / len(home_matches), 2) if home_matches else 0
                },
                "away_record": {
                    "matches": len(away_matches),
                    "goals_scored": away_goals,
                    "avg_goals": round(away_goals / len(away_matches), 2) if away_matches else 0
                },
                "clean_sheets": clean_sheets,
                "clean_sheet_percentage": f"{round((clean_sheets / total) * 100, 1)}%" if total > 0 else "0%",
                "failed_to_score": failed_to_score,
                "scoring_percentage": f"{round(((total - failed_to_score) / total) * 100, 1)}%" if total > 0 else "0%",
                "both_teams_scored": both_teams_scored,
                "btts_percentage": f"{round((both_teams_scored / total) * 100, 1)}%" if total > 0 else "0%"
            }, indent=2)}

        elif request.tool_name == "goal_probability":
            home_team = request.arguments.get("home_team", "").lower()
            away_team = request.arguments.get("away_team", "").lower()

            home_id = TEAM_MAPPING.get(home_team)
            away_id = TEAM_MAPPING.get(away_team)

            if not home_id or not away_id:
                return {"result": json.dumps({
                    "error": "Team not found",
                    "available_teams": list(TEAM_MAPPING.keys())[:20]
                }, indent=2)}

            home_matches = await get_team_matches(home_id, 50)
            away_matches = await get_team_matches(away_id, 50)

            home_form = calculate_form_score(home_matches, home_id)
            away_form = calculate_form_score(away_matches, away_id)

            # Calculate expected goals
            home_xg = (home_form["avg_goals_scored"] + away_form["avg_goals_conceded"]) / 2
            away_xg = (away_form["avg_goals_scored"] + home_form["avg_goals_conceded"]) / 2
            total_xg = home_xg + away_xg

            # Over/Under probabilities (simplified Poisson-like estimation)
            over_15 = min(85, 50 + (total_xg - 2) * 15)
            over_25 = min(75, 40 + (total_xg - 2.5) * 15)
            over_35 = min(60, 25 + (total_xg - 3) * 15)

            # BTTS probability
            btts_prob = min(80, (home_form["avg_goals_scored"] * 20) + (away_form["avg_goals_scored"] * 20))

            return {"result": json.dumps({
                "match": f"{home_team.title()} vs {away_team.title()}",
                "expected_goals": {
                    "home": round(home_xg, 2),
                    "away": round(away_xg, 2),
                    "total": round(total_xg, 2)
                },
                "over_under_probabilities": {
                    "over_1.5_goals": f"{round(over_15, 1)}%",
                    "over_2.5_goals": f"{round(over_25, 1)}%",
                    "over_3.5_goals": f"{round(over_35, 1)}%"
                },
                "btts_probability": f"{round(btts_prob, 1)}%",
                "most_likely_scoreline": f"{round(home_xg)}-{round(away_xg)}",
                "analysis_note": "Probabilities based on recent form and scoring patterns"
            }, indent=2)}

        elif request.tool_name == "league_predictions":
            league = request.arguments.get("league", "PL")

            # Get upcoming matches
            data = await fetch_soccer_data(f"competitions/{league}/matches?status=SCHEDULED")

            if "error" in data:
                return {"result": json.dumps({"error": data["error"]}, indent=2)}

            matches = data.get("matches", [])[:5]  # Next 5 matches

            predictions = []
            for match in matches:
                home_name = match.get("homeTeam", {}).get("name", "Unknown")
                away_name = match.get("awayTeam", {}).get("name", "Unknown")
                home_id = match.get("homeTeam", {}).get("id")
                away_id = match.get("awayTeam", {}).get("id")
                match_date = match.get("utcDate", "")[:10]

                # Get form for both teams
                home_matches = await get_team_matches(home_id, 20)
                away_matches = await get_team_matches(away_id, 20)

                home_form = calculate_form_score(home_matches, home_id)
                away_form = calculate_form_score(away_matches, away_id)

                # Simple prediction
                if home_form["score"] > away_form["score"] + 15:
                    pred = f"{home_name} Win"
                elif away_form["score"] > home_form["score"] + 10:
                    pred = f"{away_name} Win"
                else:
                    pred = "Draw likely"

                predictions.append({
                    "date": match_date,
                    "match": f"{home_name} vs {away_name}",
                    "prediction": pred,
                    "home_form": f"{home_form['score']}/100",
                    "away_form": f"{away_form['score']}/100"
                })

            return {"result": json.dumps({
                "league": league,
                "upcoming_predictions": predictions
            }, indent=2)}

        else:
            return {"result": json.dumps({"error": f"Unknown tool: {request.tool_name}"}, indent=2)}

    except Exception as e:
        return {"result": json.dumps({"error": str(e)}, indent=2)}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Soccer Analyzer MCP"}

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🔮 Soccer Analyzer MCP Server")
    print("=" * 60)
    print("📊 Tools available:")
    print("   - predict_match: Predict match outcomes")
    print("   - analyze_team_form: Analyze team's recent form")
    print("   - head_to_head: Head-to-head statistics")
    print("   - get_team_stats: Detailed team statistics")
    print("   - league_predictions: Upcoming match predictions")
    print("   - goal_probability: Over/under and BTTS analysis")
    print("=" * 60)
    print("🌐 Starting server on http://localhost:8087")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8087)
