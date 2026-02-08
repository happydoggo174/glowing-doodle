from tool import app
import dish
import uvicorn
from fastapi.staticfiles import StaticFiles
app.mount("/user/image",StaticFiles(directory="user/image/"))
app.mount("/page",StaticFiles(directory="page/"))
@app.get("/")
async def ping():
    return 0
uvicorn.run(app)
