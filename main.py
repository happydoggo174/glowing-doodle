from vercel_tool import app
import dish
@app.get("/")
async def ping():
    return "running"
