"""
TomTom Maps MCP Server - FREE Alternative to Google Maps
2,500 requests/day FREE (75,000/month)
Better free tier than Google Maps!
"""

from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import json
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="TomTom Maps MCP Server")

# TomTom API configuration
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")
TOMTOM_BASE_URL = "https://api.tomtom.com"

class ToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

class Tool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

@app.get("/")
async def root():
    return {
        "message": "TomTom Maps MCP Server - FREE Tier!",
        "note": "2,500 requests/day FREE (better than Google Maps)",
        "setup": "Set TOMTOM_API_KEY in .env",
        "get_key": "https://developer.tomtom.com/",
        "endpoints": {
            "tools": "/tools",
            "execute": "/execute",
            "health": "/health"
        }
    }

@app.get("/tools")
async def list_tools() -> List[Tool]:
    """List all available tools"""
    return [
        Tool(
            name="search_places",
            description="Search for places (restaurants, hotels, gas stations, etc.). Args: query (str), limit (int: optional, max 100, default 10)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'pizza', 'hotel', 'gas station')"
                    },
                    "location": {
                        "type": "string",
                        "description": "Location to search near (e.g., 'New York', 'Times Square')",
                        "default": ""
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (max 100)",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_directions",
            description="Get turn-by-turn directions with real-time traffic. Args: origin (str), destination (str), traffic (bool: optional, include traffic data, default true)",
            inputSchema={
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Starting location"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination location"
                    },
                    "traffic": {
                        "type": "boolean",
                        "description": "Include real-time traffic",
                        "default": True
                    }
                },
                "required": ["origin", "destination"]
            }
        ),
        Tool(
            name="calculate_distance",
            description="Calculate distance and ETA with traffic. Args: origin (str), destination (str)",
            inputSchema={
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Starting location"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination location"
                    }
                },
                "required": ["origin", "destination"]
            }
        ),
        Tool(
            name="get_traffic_info",
            description="Get real-time traffic information for an area. Args: location (str: address or coordinates)",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Location to check traffic (address or place name)"
                    }
                },
                "required": ["location"]
            }
        ),
        Tool(
            name="nearby_search",
            description="Find places nearby. Args: location (str), category (str: restaurant/hotel/gas_station/parking/cafe/bar), radius (int: meters, default 5000)",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Center location"
                    },
                    "category": {
                        "type": "string",
                        "description": "Category: restaurant, hotel, gas_station, parking, cafe, bar, atm, hospital"
                    },
                    "radius": {
                        "type": "integer",
                        "description": "Search radius in meters",
                        "default": 5000
                    }
                },
                "required": ["location", "category"]
            }
        )
    ]

async def geocode(location: str):
    """Convert address to coordinates"""
    if not TOMTOM_API_KEY:
        return None
    
    try:
        url = f"{TOMTOM_BASE_URL}/search/2/geocode/{location}.json"
        params = {"key": TOMTOM_API_KEY, "limit": 1}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        if data.get("results"):
            pos = data["results"][0]["position"]
            return f"{pos['lat']},{pos['lon']}"
        return None
    except:
        return None

async def search_places(query: str, location: str = "", limit: int = 10):
    """Search for places"""
    if not TOMTOM_API_KEY:
        return {"error": "TomTom API key not configured"}
    
    try:
        print(f"🗺️  Searching for: {query}")
        
        url = f"{TOMTOM_BASE_URL}/search/2/search/{query}.json"
        params = {
            "key": TOMTOM_API_KEY,
            "limit": min(limit, 100)
        }
        
        # Add location bias if provided
        if location:
            coords = await geocode(location)
            if coords:
                params["lat"], params["lon"] = coords.split(",")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        results = []
        for place in data.get("results", []):
            results.append({
                "name": place.get("poi", {}).get("name", "Unknown"),
                "address": place.get("address", {}).get("freeformAddress", ""),
                "category": place.get("poi", {}).get("categories", []),
                "phone": place.get("poi", {}).get("phone", ""),
                "distance": place.get("dist", 0),
                "position": place.get("position", {})
            })
        
        print(f"✅ Found {len(results)} places")
        return {
            "query": query,
            "location": location,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def get_directions(origin: str, destination: str, traffic: bool = True):
    """Get directions with traffic"""
    if not TOMTOM_API_KEY:
        return {"error": "TomTom API key not configured"}
    
    try:
        print(f"🗺️  Getting directions: {origin} → {destination}")
        
        # Geocode origin and destination
        origin_coords = await geocode(origin)
        dest_coords = await geocode(destination)
        
        if not origin_coords or not dest_coords:
            return {"error": "Could not geocode locations"}
        
        url = f"{TOMTOM_BASE_URL}/routing/1/calculateRoute/{origin_coords}:{dest_coords}/json"
        params = {
            "key": TOMTOM_API_KEY,
            "traffic": str(traffic).lower(),
            "instructionsType": "text"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        route = data["routes"][0]
        summary = route["summary"]
        
        steps = []
        for leg in route.get("legs", []):
            for point in leg.get("points", []):
                if "instruction" in point:
                    steps.append({
                        "instruction": point["instruction"],
                        "distance": f"{point.get('routeOffsetInMeters', 0)}m"
                    })
        
        result = {
            "origin": origin,
            "destination": destination,
            "distance": f"{summary['lengthInMeters'] / 1000:.1f} km",
            "duration": f"{summary['travelTimeInSeconds'] // 60} minutes",
            "duration_in_traffic": f"{summary.get('trafficDelayInSeconds', 0) // 60} min delay" if traffic else None,
            "fuel_consumption": f"{summary.get('fuelConsumptionInLiters', 0):.2f} L",
            "steps": steps[:20],  # First 20 steps
            "total_steps": len(steps)
        }
        
        print(f"✅ Route: {result['distance']}, {result['duration']}")
        return result
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def calculate_distance(origin: str, destination: str):
    """Calculate distance and ETA"""
    if not TOMTOM_API_KEY:
        return {"error": "TomTom API key not configured"}
    
    try:
        print(f"🗺️  Calculating: {origin} → {destination}")
        
        origin_coords = await geocode(origin)
        dest_coords = await geocode(destination)
        
        if not origin_coords or not dest_coords:
            return {"error": "Could not geocode locations"}
        
        url = f"{TOMTOM_BASE_URL}/routing/1/calculateRoute/{origin_coords}:{dest_coords}/json"
        params = {
            "key": TOMTOM_API_KEY,
            "traffic": "true"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        summary = data["routes"][0]["summary"]
        
        result = {
            "origin": origin,
            "destination": destination,
            "distance": f"{summary['lengthInMeters'] / 1000:.1f} km ({summary['lengthInMeters'] / 1609:.1f} miles)",
            "duration_no_traffic": f"{summary['travelTimeInSeconds'] // 60} minutes",
            "duration_with_traffic": f"{(summary['travelTimeInSeconds'] + summary.get('trafficDelayInSeconds', 0)) // 60} minutes",
            "traffic_delay": f"{summary.get('trafficDelayInSeconds', 0) // 60} minutes",
            "fuel_consumption": f"{summary.get('fuelConsumptionInLiters', 0):.2f} liters"
        }
        
        print(f"✅ {result['distance']}, {result['duration_with_traffic']}")
        return result
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def get_traffic_info(location: str):
    """Get traffic information"""
    if not TOMTOM_API_KEY:
        return {"error": "TomTom API key not configured"}
    
    try:
        print(f"🗺️  Getting traffic for: {location}")
        
        coords = await geocode(location)
        if not coords:
            return {"error": f"Could not find location: {location}"}
        
        lat, lon = coords.split(",")
        
        # Get traffic flow
        url = f"{TOMTOM_BASE_URL}/traffic/services/4/flowSegmentData/absolute/10/json"
        params = {
            "key": TOMTOM_API_KEY,
            "point": f"{lat},{lon}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        flow = data.get("flowSegmentData", {})
        
        result = {
            "location": location,
            "current_speed": f"{flow.get('currentSpeed', 0)} km/h",
            "free_flow_speed": f"{flow.get('freeFlowSpeed', 0)} km/h",
            "current_travel_time": f"{flow.get('currentTravelTime', 0)} seconds",
            "free_flow_travel_time": f"{flow.get('freeFlowTravelTime', 0)} seconds",
            "confidence": flow.get("confidence", 0),
            "road_closure": flow.get("roadClosure", False)
        }
        
        # Calculate congestion level
        if flow.get("freeFlowSpeed", 1) > 0:
            congestion = (1 - flow.get("currentSpeed", 0) / flow.get("freeFlowSpeed", 1)) * 100
            if congestion < 10:
                result["traffic_level"] = "🟢 Light traffic"
            elif congestion < 30:
                result["traffic_level"] = "🟡 Moderate traffic"
            elif congestion < 50:
                result["traffic_level"] = "🟠 Heavy traffic"
            else:
                result["traffic_level"] = "🔴 Severe congestion"
        
        print(f"✅ Traffic: {result.get('traffic_level', 'Unknown')}")
        return result
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def nearby_search(location: str, category: str, radius: int = 5000):
    """Find nearby places by category"""
    if not TOMTOM_API_KEY:
        return {"error": "TomTom API key not configured"}
    
    try:
        print(f"🗺️  Searching {category} near {location}")
        
        coords = await geocode(location)
        if not coords:
            return {"error": f"Could not find location: {location}"}
        
        lat, lon = coords.split(",")
        
        url = f"{TOMTOM_BASE_URL}/search/2/nearbySearch/.json"
        params = {
            "key": TOMTOM_API_KEY,
            "lat": lat,
            "lon": lon,
            "radius": radius,
            "categorySet": category,
            "limit": 20
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        results = []
        for place in data.get("results", []):
            results.append({
                "name": place.get("poi", {}).get("name", "Unknown"),
                "address": place.get("address", {}).get("freeformAddress", ""),
                "distance": f"{place.get('dist', 0):.0f}m",
                "phone": place.get("poi", {}).get("phone", ""),
                "categories": place.get("poi", {}).get("categories", [])
            })
        
        print(f"✅ Found {len(results)} {category} places")
        return {
            "location": location,
            "category": category,
            "radius": f"{radius}m",
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

@app.post("/execute")
async def execute_tool(request: ToolRequest):
    """Execute a tool"""
    try:
        print(f"🗺️  Executing: {request.tool_name}")
        print(f"📦 Arguments: {request.arguments}")
        
        if request.tool_name == "search_places":
            query = request.arguments.get("query")
            location = request.arguments.get("location", "")
            limit = request.arguments.get("limit", 10)
            
            if not query:
                return {"result": json.dumps({"error": "Missing required field: query"})}
            
            result = await search_places(query, location, limit)
            
        elif request.tool_name == "get_directions":
            origin = request.arguments.get("origin")
            destination = request.arguments.get("destination")
            traffic = request.arguments.get("traffic", True)
            
            if not origin or not destination:
                return {"result": json.dumps({"error": "Missing required fields: origin, destination"})}
            
            result = await get_directions(origin, destination, traffic)
            
        elif request.tool_name == "calculate_distance":
            origin = request.arguments.get("origin")
            destination = request.arguments.get("destination")
            
            if not origin or not destination:
                return {"result": json.dumps({"error": "Missing required fields: origin, destination"})}
            
            result = await calculate_distance(origin, destination)
            
        elif request.tool_name == "get_traffic_info":
            location = request.arguments.get("location")
            
            if not location:
                return {"result": json.dumps({"error": "Missing required field: location"})}
            
            result = await get_traffic_info(location)
            
        elif request.tool_name == "nearby_search":
            location = request.arguments.get("location")
            category = request.arguments.get("category")
            radius = request.arguments.get("radius", 5000)
            
            if not location or not category:
                return {"result": json.dumps({"error": "Missing required fields: location, category"})}
            
            result = await nearby_search(location, category, radius)
            
        else:
            error_msg = f"Unknown tool: {request.tool_name}"
            print(f"❌ {error_msg}")
            return {"result": json.dumps({"error": error_msg})}
        
        print(f"✅ Execution complete")
        return {"result": json.dumps(result, indent=2)}
        
    except Exception as e:
        error_msg = f"Error executing {request.tool_name}: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return {"result": json.dumps({"error": error_msg})}

@app.get("/health")
async def health():
    """Health check"""
    api_configured = bool(TOMTOM_API_KEY)
    
    # Test API if configured
    api_working = False
    if api_configured:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{TOMTOM_BASE_URL}/search/2/geocode/New+York.json",
                    params={"key": TOMTOM_API_KEY, "limit": 1},
                    timeout=5.0
                )
                api_working = response.status_code == 200
        except:
            pass
    
    return {
        "status": "healthy",
        "api_configured": api_configured,
        "api_working": api_working,
        "free_tier": "2,500 requests/day (75,000/month)",
        "available_tools": ["search_places", "get_directions", "calculate_distance", "get_traffic_info", "nearby_search"]
    }

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🗺️  Starting TomTom Maps MCP Server")
    print("=" * 60)
    print(f"API Key: {'✅ Configured' if TOMTOM_API_KEY else '❌ Missing'}")
    print(f"Port: 8084")
    print(f"💰 FREE TIER: 2,500 requests/day (75,000/month)")
    print("=" * 60)
    
    if not TOMTOM_API_KEY:
        print("\n⚠️  WARNING: TOMTOM_API_KEY not set in .env")
        print("Get FREE API key at: https://developer.tomtom.com/")
        print("\nSteps:")
        print("1. Go to https://developer.tomtom.com/")
        print("2. Sign up (FREE)")
        print("3. Create app and get API key")
        print("4. Add to .env: TOMTOM_API_KEY=your-key-here")
        print("\n✨ Much better free tier than Google Maps!")
    
    uvicorn.run(app, host="0.0.0.0", port=8084)
