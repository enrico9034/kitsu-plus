from fastapi import FastAPI
from fastapi.responses import JSONResponse
import json
import os
import re
import httpx
from urllib.parse import quote

app = FastAPI()
# kitsu_addon_url = 'https://kitsufortheweebs.midnightignite.me'
kitsu_addon_url = 'https://anime-kitsu.strem.fun'
REQUEST_TIMEOUT = 30


def json_response(data):
    response = JSONResponse(data)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Surrogate-Control"] = "no-store"
    return response

@app.get("/")
async def home():
    return json_response({})


@app.get("/catalog/{type}/{id}.json")
@app.get("/catalog/{type}/{id}/{path}.json")
async def get_catalog_search(type: str, id: str, path: str = ''):
    catalog_type = id.split('-')[-1]

    # Search query extration
    match = re.search(r"search=([^&]+)", path)
    if match:
        search_query = quote(match.group(1))  # URL encode
    else:
        search_query = ""
    
    # Skip extration
    match = re.search(r"skip=(\d+)", path)
    if match:
        skip = int(match.group(1))
    else:
        skip = 0

    if search_query:
        url = f"https://kitsu.io/api/edge/anime?filter[subtype]={catalog_type}&filter[text]={search_query}&page[limit]=20&page[offset]={skip}"
    elif 'popular' in id:
        url = f"https://kitsu.io/api/edge/anime?filter[subtype]={catalog_type}&sort=popularityRank&page[limit]=20&page[offset]={skip}"
    elif 'rated' in id:
        url = f"https://kitsu.io/api/edge/anime?filter[subtype]={catalog_type}&sort=-averageRating&page[limit]=20&page[offset]={skip}"

    # Fetch kitsu API request
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(url)
        if response.status_code != 200:
            return json_response({"metas": []})
        kitsu_data = response.json()

    return json_response(build_meta_preview(kitsu_data))
        

@app.get("/meta/{type}/{id}.json")
async def get_meta(type: str, id: str):
    print(f"{kitsu_addon_url}/meta/{type}/{id}.json")
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        reponse = await client.get(f"{kitsu_addon_url}/meta/{type}/{id}.json")
        return json_response(reponse.json())


@app.get("/manifest.json")
async def get_manifest():
    with open("manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
    return json_response(manifest)


def build_meta_preview(kitsu_data: dict) -> dict:
    metas = []
    for item in kitsu_data.get('data', []):
        attributes = item['attributes']
        anime_type = attributes.get('subtype', '')
        metas.append({
            "id": f"kitsu:{item['id']}",
            "type": "movie" if anime_type == 'movie' else "series",
            "animeType": anime_type,
            "name": attributes['titles'].get('en') or attributes['titles'].get('en_us') or attributes['titles'].get('en_jp') or attributes['titles'].get('ja_jp'),
            "poster": attributes.get('posterImage', {}).get('small', ''),
            "description": attributes.get('synopsis'),
        })

    return {"metas": metas}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get("PORT", 7000)))