from fastapi.routing import APIRouter
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import HTTPException
from vercel_tool import app,get_connection,get_redis,dish_cache_token,dish_cache_url
from dish_ssr import build_comments,build_dish,build_dish_page
import orjson
dish_route=APIRouter(prefix="/dish")
@dish_route.get("/comment")
async def get_dish_comment(dish_id:int,html:bool=True):
    async with get_connection() as con:
        ret=(await (await con.execute('''select id,name,image,content from comment where dish_id=%s''',
                                      (dish_id,))).fetchall())
        if(not html):
            return ret
        return Response(content=build_comments(ret))
@dish_route.get("")
async def get_dish(html:bool=True,page:int=0):
    try:
        ret=None
        has_redis=True#prepare for redis failure
        try:
            async with get_redis(dish_cache_url or "",dish_cache_token) as r:
                ret=await r.get(f"home:{page}")
        except:
            has_redis=False
        if(ret is None):
            async with get_connection() as con:
                ret=(await (await con.execute('''select id,name,image,tag,level,description,time 
                                              from dish limit 20 page ?''',(page*20,))).fetchall())
                if(has_redis):
                    async with get_redis(dish_cache_url or "",dish_cache_token) as r:
                        try:
                            await r.set(f"home:{page}",orjson.dumps(ret).decode())
                        except:
                            pass
        if(not html):
            return ret
        return Response(content=build_dish(ret))
    except Exception as e:
        print(e)
@dish_route.get("/detail/{dish_id}")
async def get_dish_detail(dish_id:int,html:bool=True):
    async with get_connection() as con:
        ret=await (await con.execute('''select name,image,tag,level,description,time,author,ingredient,instruction,chef_note,upload_time 
                            from dish where id=%s''',(dish_id,))).fetchone()
        if(ret is None):raise HTTPException(404,"no such recipe")
        if(not html):
            return ret
        com=(await con.execute('''select name,image,content from comment where dish_id=%s''',(dish_id,))).fetchall()
    com=[{"name":"phuc","image":"user/image/phuc.avif","content":"splendid recipe indeeed"},{"name":"phuc","image":"user/image/phuc.avif","content":"splendid recipe indeeed"},{"name":"phuc","image":"user/image/phuc.avif","content":"splendid recipe indeeed"}]     
    return Response(content=build_dish_page(ret,com),media_type="text/html")
app.include_router(dish_route)