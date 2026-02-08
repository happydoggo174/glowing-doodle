from vercel_tool import app
import dish
import uvicorn
from fastapi.staticfiles import StaticFiles
@app.get("/")
async def ping():
    return "running"
uvicorn.run(app)
