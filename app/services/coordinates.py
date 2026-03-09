import httpx

async def geocode_async(name: str):
    query = f"{name}, Kazakhstan"
    url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers={"User-Agent": "nomadtravel_kz_api"})
        data = resp.json()
        if not data:
            return None
        return data[0]