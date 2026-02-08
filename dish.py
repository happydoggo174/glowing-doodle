from fastapi.routing import APIRouter
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import HTTPException
from vercel_tool import app,get_connection
from dish_ssr import build_comments,build_dish,build_dish_page

dish_route=APIRouter(prefix="/dish")
@dish_route.get("/comment")
async def get_dish_comment(dish_id:int,html:bool=True):
    async with get_connection() as con:
        ret=await con.fetch('''select id,name,image,content from comment where dish_id=$1''',dish_id)
        if(not html):
            return ret
        return Response(content=build_comments(ret))
@dish_route.get("")
async def get_dish(html:bool=True):
    async with get_connection() as con:
        ret=await con.fetch('''select id,name,image,tag,level,description,time from dish''')
        if(not html):
            return ret
        return Response(content=build_dish(ret))
@dish_route.get("/detail/{dish_id}")
async def get_dish_detail(dish_id:int,html:bool=True):
    async with get_connection() as con:
        ret=await con.fetchrow('''select name,image,tag,level,description,time,author,ingredient,instruction,chef_note,upload_time 
                            from dish where id=$1''',dish_id)
        if(ret is None):raise HTTPException(404,"no such recipe")
        if(not html):
            return ret
        com=await con.fetch('''select name,image,content from comment where dish_id=$1''',dish_id)
    com=[{"name":"phuc","image":"user/image/phuc.avif","content":"splendid recipe indeeed"},{"name":"phuc","image":"user/image/phuc.avif","content":"splendid recipe indeeed"},{"name":"phuc","image":"user/image/phuc.avif","content":"splendid recipe indeeed"}]     
    return Response(content=build_dish_page(ret,com),media_type="text/html")
app.include_router(dish_route)