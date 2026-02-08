import os.path
from random import randbytes
from os import dup
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from fastapi import Depends,FastAPI,UploadFile,Depends,Request,File
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional
from contextlib import asynccontextmanager
import redis.asyncio as redis
import orjson
import asyncpg
import asyncio
from fastapi.responses import ORJSONResponse
from enum import IntEnum
from PIL import Image
from hashlib import sha256,blake2b
from functools import wraps
from html import escape
import secrets
import jwt
def clean_html(val):
    if(isinstance(val,str)):
        return escape(val)
    if(isinstance(val,list) or isinstance(val,tuple)):
        safe=[]
        for itr in val:
            safe.append(clean_html(itr))
        return safe
    if(isinstance(val,dict)):
        safe={}
        for key,value in val.items():
            safe[key]=clean_html(value)
        return safe
    if(hasattr(val,"__dict__")):
        return clean_html(val.__dict__)
    return val
def safe_html(excluded=()):
    def call(func):
        @wraps(func)
        def runner(*args,**kwargs):
            safe_args=[]
            for arg in args:
                safe_args.append(clean_html(arg))
            safe_kwargs={}
            for key,value in kwargs.items():
                if(key in excluded):
                    safe_kwargs[key]=value
                else:
                    safe_kwargs[key]=clean_html(value)
            return func(*safe_args,**safe_kwargs)
        return runner
    return call
Image.MAX_IMAGE_PIXELS=36*1024*1024
scheme=HTTPBearer(auto_error=False)
auth_redis=redis.ConnectionPool(host='localhost',port=6379)
view_redis=redis.ConnectionPool(host='localhost',port=6380)
JWT_KEY=secrets.token_bytes(12)
RATE_REDIS="redis://localhost:6767"
rate_redis=redis.from_url(RATE_REDIS)
rate_script=rate_redis.register_script('''
        local key=KEYS[1]
        local val=redis.call("INCR",key)
        if val>1 then
            return val
        end
        local duration=tonumber(KEYS[2])
        redis.call("EXPIRE",key,duration)
        return val
        ''')
unrate_script=rate_redis.register_script('''
    local key=KEYS[1]
    local val=redis.call("DECR",key)
    if val>-1 then
        return
    end
    redis.call("DELETE",key)
''')
rate_script_ex=rate_redis.register_script('''
        local key=KEYS[1]
        local count=tonumber(ARGV[1])
        local val=redis.call("INCRBY",key,count)
        if val>count then
            return val
        end
        local duration=tonumber(KEYS[2])
        redis.call("EXPIRE",key,duration)
        return val
        ''')
db_pool=None
def sign_profile(profile:list[str]):
    return jwt.encode({"images":profile,"for":"profile"},JWT_KEY,"HS256")
class session:
    __slots__="uid","priv"
    def __init__(self,uid:int,priv:int):
        self.uid=uid
        self.priv=priv
def get_ip(request: Request):
    # Try to get the IP from headers, fall back to request.client.host
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        # The first IP in the list is the real client IP
        client_ip = x_forwarded_for.split(",")[0]
    else:
        client_ip = request.client.host
    return client_ip
async def check_login(username:str,r:Request):
    ip=get_ip(r)
    key=blake2b(orjson.dumps({"name":username,"ip":ip}),digest_size=16).digest()
    if(int(await rate_script(keys=[key,"60"]))>10):raise HTTPException(429)
    if(int(await rate_script(keys=[ip,"180"]))>600):raise HTTPException(429)
    return ip
class priv(IntEnum):
    user=1
    admin=2
class ec(IntEnum):
    post_video=1
    delete_video=2
    get_info=3
    get_profile=4
    ping=5
    edit_info=6
    get_video=7
    get_video_cover=8
    get_video_detail=9
    watch_video=10
    get_published=11
    post_dish=12
    post_video_comment=13



async def get_session(cred:Optional[HTTPAuthorizationCredentials]=Depends(scheme)):
    if(cred is None):return None
    async with redis.Redis(connection_pool=auth_redis) as r:
        data:Optional[bytes]=await r.get(cred.credentials)
        if(data is None):return None
        await r.expire(cred.credentials,15*600)
        uid,priv=data.split(b":")
        return session(int(uid),int(priv))
@asynccontextmanager
async def lifespan(app:Optional[FastAPI]):
    global db_pool
    db_pool=await asyncpg.pool.create_pool(user="postgres",database='postgres',host='localhost',password='12345678')
    yield
    await db_pool.close()
    await auth_redis.disconnect()
    await view_redis.disconnect()
@asynccontextmanager
async def get_connection(transaction:bool=False):
    assert(db_pool is not None)
    err=None
    async with db_pool.acquire() as con:
        con:asyncpg.Connection
        try:
            if(transaction):
                async with con.transaction():
                    yield con
            else:
                yield con
        except Exception as e:
            err=e
            await con.execute("ROLLBACK")
    if(err is not None):raise err
app=FastAPI(lifespan=lifespan,default_response_class=ORJSONResponse)
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:8000","http://localhost:23107"],
                   allow_credentials=True,allow_headers=["*"],allow_methods=["*"])
app.add_middleware(GZipMiddleware,minimum_size=1024,compresslevel=6)
def is_vaild_filename(filename:str)->bool:
    if(not isinstance(filename,str) or len(filename)>180): return False
    invaild={'\\', '/', '?', '*', ':', '|', '<', '>', '"','%'}
    for i in  filename:
        if i in invaild:
            return False
    return not os.path.isabs(filename) and filename.find("..")==-1
async def save_file(file:UploadFile,filter:tuple,dir:str="",anoymous:bool=True,max_size:int=6000000):
    try:
        if(not isinstance(file.size,int) or file.size>max_size):
            print("size limit exceeded")
            return ""
        ex=file.filename
        if(not isinstance(ex,str) or len(ex)>180): 
            print("no name")
            return""
        ex=ex.replace("\0","")
        ex=os.path.splitext(ex)[1]
        if(ex not in filter): 
            print("invaild extension")
            return ""
        if(anoymous):
            name:str=os.path.join(dir,randbytes(12).hex()+ex)
        else:
            if(type(file.filename)!=str or not is_vaild_filename(file.filename)): 
                print("invaild filename",file.filename)
                return""
            name:str=os.path.join(dir,file.filename)
        if(os.path.exists(name)): return ""
        buf_size=16384
        if(file.size>=1000000):buf_size=65536
        loop=asyncio.get_running_loop()
        try:
            with open(name,"b+x",buffering=buf_size) as fp:
                await loop.run_in_executor(None,fp.write,await file.read())
        except Exception as e:
            print(f"error saving file {e}")
            return ""
        return name
    except Exception as e: 
        print(e)
        return""
async def drop_rate(uid:int,endpoint:int,limit:int,duration:int=60,count:int=1):
    key = f"{endpoint}:{uid}"
    res=await rate_script_ex(keys=[key,str(duration)],args=[str(count),])
    if(int(res)>limit):raise HTTPException(429)
class RateLimit():
    def __init__(self,endpoint:int,limit:int,ip_limit:int=-1,duration:int=60):
        self.endpoint=endpoint
        self.limit=limit
        self.duration=duration
        self.ip_limit=ip_limit
    async def __call__(self,r:Request,user:Optional[session]=Depends(get_session)):
        if(user is None):
            if(self.ip_limit<1):
                raise HTTPException(401,"missing session")
            key = f"{self.endpoint}:{get_ip(r)}"
            res=await rate_script(keys=[key,str(self.duration)])
            if(int(res)>self.ip_limit):raise HTTPException(429)
            return None
        key = f"{self.endpoint}:{user.uid}"
        res=await rate_script(keys=[key,str(self.duration)])
        if(int(res)>self.limit):raise HTTPException(429)
        return user
