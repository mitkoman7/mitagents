"""
Google Maps MCP Server - Simple API Key Based
Uses Google Maps API for location services
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import json
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Google Maps MCP Server - Simple API")

# Google Maps API configuration
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
GOOGLE_MAPS_BASE_URL = "https://maps.googleapis.com/maps/api"

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
        "message": "Google Maps MCP Server - API Key Based",
        "note": "Simple Google Maps integration using API key",
        "setup": "Set GOOGLE_MAPS_API_KEY in .env",
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
            description="Search for places (restaurants, hotels, shops, etc.). Args: query (str: search term like 'pizza near Times Square'), radius (int: optional, meters, default 5000)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'pizza restaurants', 'coffee shops near Central Park')"
                    },
                    "radius": {
                        "type": "integer",
                        "description": "Search radius in meters (default: 5000)",
                        "default": 5000
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_directions",
            description="Get directions between two locations. Args: origin (str: starting point), destination (str: end point), mode (str: optional, driving/walking/bicycling/transit, default driving)",
            inputSchema={
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Starting location (address or place name)"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination location (address or place name)"
                    },
                    "mode": {
                        "type": "string",
                        "description": "Travel mode: driving, walking, bicycling, transit",
                        "default": "driving"
                    }
                },
                "required": ["origin", "destination"]
            }
        ),
        Tool(
            name="calculate_distance",
            description="Calculate distance and travel time between locations. Args: origin (str), destination (str), mode (str: optional, default driving)",
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
                    "mode": {
                        "type": "string",
                        "description": "Travel mode: driving, walking, bicycling, transit",
                        "default": "driving"
                    }
                },
                "required": ["origin", "destination"]
            }
        ),
        Tool(
            name="get_place_details",
            description="Get detailed information about a place. Args: place_id (str: Google Place ID) OR place_name (str: place name to look up)",
            inputSchema={
                "type": "object",
                "properties": {
                    "place_id": {
                        "type": "string",
                        "description": "Google Place ID"
                    },
                    "place_name": {
                        "type": "string",
                        "description": "Place name to search for"
                    }
                }
            }
        ),
        Tool(
            name="nearby_search",
            description="Find places near a location. Args: location (str: address or place), type (str: place type like 'restaurant', 'cafe'), radius (int: optional, meters, default 5000)",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Center location for search"
                    },
                    "type": {
                        "type": "string",
                        "description": "Type of place (restaurant, cafe, hotel, gas_station, etc.)"
                    },
                    "radius": {
                        "type": "integer",
                        "description": "Search radius in meters",
                        "default": 5000
                    }
                },
                "required": ["location", "type"]
            }
        )
    ]

async def search_places(query: str, radius: int = 5000):
    """Search for places using text search"""
    if not GOOGLE_MAPS_API_KEY:
        return {"error": "Google Maps API key not configured"}
    
    try:
        print(f"🗺️  Searching for: {query}")
        
        url = f"{GOOGLE_MAPS_BASE_URL}/place/textsearch/json"
        params = {
            "query": query,
            "radius": radius,
            "key": GOOGLE_MAPS_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        if data.get("status") != "OK":
            return {"error": f"API error: {data.get('status')}", "message": data.get("error_message", "")}
        
        results = []
        for place in data.get("results", [])[:10]:  # Limit to 10 results
            results.append({
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "rating": place.get("rating"),
                "user_ratings_total": place.get("user_ratings_total"),
                "place_id": place.get("place_id"),
                "types": place.get("types", []),
                "open_now": place.get("opening_hours", {}).get("open_now") if "opening_hours" in place else None
            })
        
        print(f"✅ Found {len(results)} places")
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def get_directions(origin: str, destination: str, mode: str = "driving"):
    """Get directions between two locations"""
    if not GOOGLE_MAPS_API_KEY:
        return {"error": "Google Maps API key not configured"}
    
    try:
        print(f"🗺️  Getting directions: {origin} → {destination} ({mode})")
        
        url = f"{GOOGLE_MAPS_BASE_URL}/directions/json"
        params = {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "key": GOOGLE_MAPS_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        if data.get("status") != "OK":
            return {"error": f"API error: {data.get('status')}", "message": data.get("error_message", "")}
        
        route = data["routes"][0]
        leg = route["legs"][0]
        
        steps = []
        for step in leg["steps"]:
            steps.append({
                "instruction": step["html_instructions"].replace("<b>", "").replace("</b>", "").replace("<div style=\"font-size:0.9em\">", " ").replace("</div>", ""),
                "distance": step["distance"]["text"],
                "duration": step["duration"]["text"]
            })
        
        result = {
            "origin": leg["start_address"],
            "destination": leg["end_address"],
            "distance": leg["distance"]["text"],
            "duration": leg["duration"]["text"],
            "mode": mode,
            "steps": steps,
            "total_steps": len(steps)
        }
        
        print(f"✅ Route found: {result['distance']}, {result['duration']}")
        return result
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def calculate_distance(origin: str, destination: str, mode: str = "driving"):
    """Calculate distance and travel time"""
    if not GOOGLE_MAPS_API_KEY:
        return {"error": "Google Maps API key not configured"}
    
    try:
        print(f"🗺️  Calculating distance: {origin} → {destination}")
        
        url = f"{GOOGLE_MAPS_BASE_URL}/distancematrix/json"
        params = {
            "origins": origin,
            "destinations": destination,
            "mode": mode,
            "key": GOOGLE_MAPS_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        if data.get("status") != "OK":
            return {"error": f"API error: {data.get('status')}"}
        
        element = data["rows"][0]["elements"][0]
        
        if element.get("status") != "OK":
            return {"error": f"Route not found: {element.get('status')}"}
        
        result = {
            "origin": data["origin_addresses"][0],
            "destination": data["destination_addresses"][0],
            "distance": element["distance"]["text"],
            "distance_meters": element["distance"]["value"],
            "duration": element["duration"]["text"],
            "duration_seconds": element["duration"]["value"],
            "mode": mode
        }
        
        print(f"✅ Distance: {result['distance']}, Duration: {result['duration']}")
        return result
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def get_place_details(place_id: str = None, place_name: str = None):
    """Get detailed information about a place"""
    if not GOOGLE_MAPS_API_KEY:
        return {"error": "Google Maps API key not configured"}
    
    try:
        # If place_name provided, search for it first
        if not place_id and place_name:
            print(f"🗺️  Looking up place: {place_name}")
            search_result = await search_places(place_name, radius=5000)
            if "error" in search_result or not search_result.get("results"):
                return {"error": f"Could not find place: {place_name}"}
            place_id = search_result["results"][0]["place_id"]
        
        if not place_id:
            return {"error": "Either place_id or place_name is required"}
        
        print(f"🗺️  Getting details for place_id: {place_id}")
        
        url = f"{GOOGLE_MAPS_BASE_URL}/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "name,formatted_address,formatted_phone_number,rating,user_ratings_total,opening_hours,website,price_level,reviews,photos",
            "key": GOOGLE_MAPS_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        if data.get("status") != "OK":
            return {"error": f"API error: {data.get('status')}"}
        
        place = data["result"]
        
        result = {
            "name": place.get("name"),
            "address": place.get("formatted_address"),
            "phone": place.get("formatted_phone_number"),
            "rating": place.get("rating"),
            "user_ratings_total": place.get("user_ratings_total"),
            "website": place.get("website"),
            "price_level": place.get("price_level"),
            "opening_hours": place.get("opening_hours", {}).get("weekday_text", []) if "opening_hours" in place else None,
            "open_now": place.get("opening_hours", {}).get("open_now") if "opening_hours" in place else None
        }
        
        # Add top reviews
        if "reviews" in place:
            result["reviews"] = [
                {
                    "author": review.get("author_name"),
                    "rating": review.get("rating"),
                    "text": review.get("text"),
                    "time": review.get("relative_time_description")
                }
                for review in place.get("reviews", [])[:3]  # Top 3 reviews
            ]
        
        print(f"✅ Got details for: {result['name']}")
        return result
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"❌ {error_msg}")
        return {"error": error_msg}

async def nearby_search(location: str, type: str, radius: int = 5000):
    """Find places near a location"""
    if not GOOGLE_MAPS_API_KEY:
        return {"error": "Google Maps API key not configured"}
    
    try:
        print(f"🗺️  Searching for {type} near {location}")
        
        # First, geocode the location to get coordinates
        geocode_url = f"{GOOGLE_MAPS_BASE_URL}/geocode/json"
        geocode_params = {
            "address": location,
            "key": GOOGLE_MAPS_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            geocode_response = await client.get(geocode_url, params=geocode_params)
            geocode_data = geocode_response.json()
        
        if geocode_data.get("status") != "OK":
            return {"error": f"Could not find location: {location}"}
        
        coords = geocode_data["results"][0]["geometry"]["location"]
        
        # Now search for places nearby
        url = f"{GOOGLE_MAPS_BASE_URL}/place/nearbysearch/json"
        params = {
            "location": f"{coords['lat']},{coords['lng']}",
            "radius": radius,
            "type": type,
            "key": GOOGLE_MAPS_API_KEY
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        if data.get("status") != "OK":
            return {"error": f"API error: {data.get('status')}"}
        
        results = []
        for place in data.get("results", [])[:10]:
            results.append({
                "name": place.get("name"),
                "address": place.get("vicinity"),
                "rating": place.get("rating"),
                "user_ratings_total": place.get("user_ratings_total"),
                "place_id": place.get("place_id"),
                "open_now": place.get("opening_hours", {}).get("open_now") if "opening_hours" in place else None
            })
        
        print(f"✅ Found {len(results)} {type} places near {location}")
        return {
            "location": location,
            "type": type,
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
            radius = request.arguments.get("radius", 5000)
            
            if not query:
                return {"result": json.dumps({"error": "Missing required field: query"})}
            
            result = await search_places(query, radius)
            
        elif request.tool_name == "get_directions":
            origin = request.arguments.get("origin")
            destination = request.arguments.get("destination")
            mode = request.arguments.get("mode", "driving")
            
            if not origin or not destination:
                return {"result": json.dumps({"error": "Missing required fields: origin, destination"})}
            
            result = await get_directions(origin, destination, mode)
            
        elif request.tool_name == "calculate_distance":
            origin = request.arguments.get("origin")
            destination = request.arguments.get("destination")
            mode = request.arguments.get("mode", "driving")
            
            if not origin or not destination:
                return {"result": json.dumps({"error": "Missing required fields: origin, destination"})}
            
            result = await calculate_distance(origin, destination, mode)
            
        elif request.tool_name == "get_place_details":
            place_id = request.arguments.get("place_id")
            place_name = request.arguments.get("place_name")
            
            if not place_id and not place_name:
                return {"result": json.dumps({"error": "Either place_id or place_name is required"})}
            
            result = await get_place_details(place_id, place_name)
            
        elif request.tool_name == "nearby_search":
            location = request.arguments.get("location")
            type = request.arguments.get("type")
            radius = request.arguments.get("radius", 5000)
            
            if not location or not type:
                return {"result": json.dumps({"error": "Missing required fields: location, type"})}
            
            result = await nearby_search(location, type, radius)
            
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
    api_configured = bool(GOOGLE_MAPS_API_KEY)
    
    # Test API if configured
    api_working = False
    if api_configured:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{GOOGLE_MAPS_BASE_URL}/geocode/json",
                    params={"address": "New York", "key": GOOGLE_MAPS_API_KEY},
                    timeout=5.0
                )
                api_working = response.status_code == 200 and response.json().get("status") == "OK"
        except:
            pass
    
    return {
        "status": "healthy",
        "api_configured": api_configured,
        "api_working": api_working,
        "available_tools": ["search_places", "get_directions", "calculate_distance", "get_place_details", "nearby_search"]
    }

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🗺️  Starting Google Maps MCP Server")
    print("=" * 60)
    print(f"API Key: {'✅ Configured' if GOOGLE_MAPS_API_KEY else '❌ Missing'}")
    print(f"Port: 8083")
    print("=" * 60)
    
    if not GOOGLE_MAPS_API_KEY:
        print("\n⚠️  WARNING: GOOGLE_MAPS_API_KEY not set in .env")
        print("Get one at: https://console.cloud.google.com/google/maps-apis/")
        print("\nSteps:")
        print("1. Go to Google Cloud Console")
        print("2. Enable Maps JavaScript API, Places API, Directions API, Distance Matrix API")
        print("3. Create API credentials")
        print("4. Add to .env: GOOGLE_MAPS_API_KEY=your-key-here")
    
    uvicorn.run(app, host="0.0.0.0", port=8083)
