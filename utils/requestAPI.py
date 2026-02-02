import asyncio
import aiohttp

ENDPOINTS = {
    "basic": "053cea08-09bc-40ec-8f7a-156f0677aff3",
    "history": "56063a99-8a3e-4ff4-912e-5966c0279bad",
    "disabled": "c8b9f9c8-4612-4068-934f-d4acd2e3c06e",
    "models": "142afde2-6228-49f9-8a29-9b6c3a0cbe40",
    "special_import": "03adc637-b6fe-402b-9937-7c3d3afc9140"
}

BASE_URL = "https://data.gov.il/api/3/action/datastore_search"

async def fetch(session, resource_id, query, limit=1):
    url = f"{BASE_URL}?resource_id={resource_id}&q={query}&limit={limit}"
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                records = data.get("result", {}).get("records", [])
                return records[0] if records else None
            return None
    except Exception as e:
        print(f"Error fetching {resource_id}: {e}")
        return None

async def getData(car_number):
    async with aiohttp.ClientSession() as session:
        # Launch all initial requests that only depend on car_number
        tasks = {
            "basic": fetch(session, ENDPOINTS["basic"], car_number),
            "history": fetch(session, ENDPOINTS["history"], car_number),
            "disabled": fetch(session, ENDPOINTS["disabled"], car_number),
            "special": fetch(session, ENDPOINTS["special_import"], car_number)
        }
        
        # Wait for all of them together
        results = await asyncio.gather(*tasks.values())
        res_dict = dict(zip(tasks.keys(), results))

        # Determine which basic info to use
        basic_res = res_dict["basic"] or res_dict["special"]
        
        if not basic_res:
            return None

        # Only the 'models' request stays sequential because it depends on basic_res
        degem_nm = basic_res.get("degem_nm")
        model_res = None
        if degem_nm:
            model_res = await fetch(session, ENDPOINTS["models"], degem_nm)

        return {
            "basic": basic_res,
            "model": model_res,
            "special_import": res_dict["special"] if not res_dict["basic"] else None,
            "kilometers": res_dict["history"].get('kilometer_test_aharon') if res_dict["history"] else None,
            "is_disabled": 1 if res_dict["disabled"] else 0
        }