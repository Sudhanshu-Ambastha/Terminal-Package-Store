import httpx

async def check_for_updates(current_version: str, api_url: str) -> dict:
    """
    Checks the GitHub API for the latest release version of the application.

    Args:
        current_version: The version string of the currently running application (e.g., "1.0.0").
        api_url: The GitHub API URL for the latest release (e.g., ".../releases/latest").

    Returns:
        A dictionary with the check result, including status and message.
    """
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