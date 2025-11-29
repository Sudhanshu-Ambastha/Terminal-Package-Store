import httpx

async def check_for_updates(current_version: str, api_url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(api_url)
            response.raise_for_status() 

        latest_release = response.json()
        
        latest_version_tag = latest_release.get("tag_name", "v0.0.0").lstrip('v')
        
        current_version_tuple = tuple(map(int, current_version.split('.')))
        latest_version_tuple = tuple(map(int, latest_version_tag.split('.')))

        if latest_version_tuple > current_version_tuple:
            return {
                "status": "update_available", 
                "latest_version": latest_version_tag
            }
        
        return {
            "status": "latest",
            "latest_version": latest_version_tag
        }

    except httpx.HTTPStatusError as e:
        return {
            "status": "error",
            "message": f"Could not reach GitHub API. Status: {e.response.status_code}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Network Error: {e}"
        }