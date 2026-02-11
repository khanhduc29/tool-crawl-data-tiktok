import asyncio

async def auto_scroll(page, times=10, delay=1.2):
    for _ in range(times):
        await page.mouse.wheel(0, 3000)
        await asyncio.sleep(delay)

def safe_get(obj, *keys):
    for k in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(k)
    return obj
