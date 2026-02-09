import psycopg
from contextlib import asynccontextmanager
import os
from typing import Optional
from fastapi.security import HTTPAuthorizationCredentials,HTTPBearer
import upstash_redis.asyncio.client as redis
from fastapi import Depends,FastAPI,UploadFile
from fastapi.responses import ORJSONResponse
from storage import store
from random import randbytes
from psycopg.rows import dict_row
scheme=HTTPBearer(auto_error=False)
db_url=os.environ.get("POSTGRES_URL")
auth_url=os.environ.get("AUTH_REDIS")
auth_token=os.environ.get("AUTH_REDIS_TOKEN")
dish_cache_url=os.environ.get("HOME_REDIS")
dish_cache_token=os.environ.get("HOME_REDIS_TOKEN")
app=FastAPI(default_response_class=ORJSONResponse)
con:psycopg.AsyncConnection|None=None
@asynccontextmanager
async def get_redis(url:Optional[str],token:Optional[str]):
    if(token is None or url is None):
        if(url is not None):
            import redis.asyncio as localredis
            yield localredis.Redis.from_url(url)
        else:
            raise ValueError("redis url and token is needed")
        return
    async with redis.Redis(url,token) as r:
        try:
            yield r
        except:pass
@asynccontextmanager
async def get_connection(transaction:bool=False):
    err=None
    global con
    if(con is None):
        if(db_url is not None):
            con=await psycopg.AsyncConnection.connect(db_url,row_factory=dict_row)
        else:
            con=await psycopg.AsyncConnection.connect(user="postgres",database='postgres',host='localhost',row_factory=dict_row)
    try:
        async with con.cursor() as cur:
            if(transaction):
                await cur.execute("BEGIN")
                yield cur
            else:
                yield cur
    except Exception as e:
        err=e
    finally:
        if(err is not None):
            if(transaction):
                await con.execute("ROLLBACK")
            raise err
        elif(transaction):
            await con.execute("COMMIT")
class session:
    __slots__="uid","priv"
    def __init__(self,uid:int,priv:int):
        self.uid=uid
        self.priv=priv
async def get_session(cred:Optional[HTTPAuthorizationCredentials]=Depends(scheme)):
    if(cred is None):return None
    async with get_redis(auth_url,auth_token) as r:
        data:Optional[bytes]=await r.get(cred.credentials)
        if(data is None):return None
        uid,priv=data.split(b":")
        return session(int(uid),int(priv))
def is_vaild_filename(filename:str)->bool:
    if(not isinstance(filename,str) or len(filename)>180): return False
    invaild={'\\', '/', '?', '*', ':', '|', '<', '>', '"','%'}
    for i in  filename:
        if i in invaild:
            return False
    return not os.path.isabs(filename) and filename.find("..")==-1
async def save_file(file:UploadFile,filter:tuple,dir:str="",anoymous:bool=True,max_size:int=6000000,public:bool=False):
    try:
        if(not isinstance(file.size,int) or file.size>max_size):
            return None
        ex=file.filename
        if(not isinstance(ex,str) or len(ex)>180): 
            return None
        ex=ex.replace("\0","")
        ex=os.path.splitext(ex)[1]
        if(ex not in filter): 
            return None
        if(anoymous):
            file_path:str=os.path.join(dir,randbytes(12).hex()+ex)
        else:
            if(type(file.filename)!=str or not is_vaild_filename(file.filename)): 
                return""
            file_path:str=os.path.join(dir,file.filename)
        tag=await store(file_path,await file.read(),public)
        return tag
    except Exception as e: 
        return None
async def sql_fetch(cur:psycopg.AsyncCursor,query:str,params:tuple=()):
    return await (await cur.execute(query,params)).fetchall()
async def sql_fetchrow(cur:psycopg.AsyncCursor,query:str,params:tuple=()):
    return await (await cur.execute(query,params)).fetchone()
async def sql_fetchval(cur:psycopg.AsyncCursor,query:str,params:tuple=()):
    r=await (await cur.execute(query,params)).fetchone()
    if(r is None):return None
    return r[0]