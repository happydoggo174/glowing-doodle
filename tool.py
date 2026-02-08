import os.path
from random import randbytes
from os import dup
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from fastapi import Depends,FastAPI,UploadFile,Depends,Request,File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from typing import Optional
from contextlib import asynccontextmanager
import redis.asyncio as redis
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
database_url = os.environ.get('POSTGRES_URL')


# Ensure the scheme is 'postgresql://' if it's 'postgres://' (some libraries require this)
if database_url is not None and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

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
JWT_KEY=secrets.token_bytes(12)
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
class priv(IntEnum):
    user=1
    admin=2



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
    if(database_url):
        db_pool=await asyncpg.create_pool(dsn=database_url)
    else:
        db_pool=await asyncpg.pool.create_pool(user="postgres",database='postgres',host='localhost',password='12345678')
    yield
    await db_pool.close()
    await auth_redis.disconnect()
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
            return ""
        ex=file.filename
        if(not isinstance(ex,str) or len(ex)>180): 
            return""
        ex=ex.replace("\0","")
        ex=os.path.splitext(ex)[1]
        if(ex not in filter): 
            return ""
        if(anoymous):
            name:str=os.path.join(dir,randbytes(12).hex()+ex)
        else:
            if(type(file.filename)!=str or not is_vaild_filename(file.filename)): 
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
            return ""
        return name
    except Exception as e: 
        return""
