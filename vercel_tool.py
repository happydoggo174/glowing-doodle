import asyncpg
from contextlib import asynccontextmanager
import os
from typing import Optional
from fastapi.security import HTTPAuthorizationCredentials,HTTPBearer
import upstash_redis.asyncio.client as redis
from fastapi import Depends,FastAPI
from fastapi.responses import ORJSONResponse
scheme=HTTPBearer(auto_error=False)
db_url=os.environ.get("POSTGRES_URL")
auth_url=os.environ.get("AUTH_REDIS")
auth_token=os.environ.get("AUTH_REDIS_TOKEN")
app=FastAPI(default_response_class=ORJSONResponse)
@asynccontextmanager
async def get_redis(url:Optional[str],token:Optional[str]):
    if(url is None or token is None):
        raise ValueError("redis url and token is needed")
    async with redis.Redis(url,token) as r:
        try:
            yield r
        except:pass
@asynccontextmanager
async def get_connection(transaction:bool=False):
    err=None
    async with await asyncpg.connect(dsn=db_url) as con:
        con:asyncpg.Connection
        try:
            if(transaction):
                async with con.transaction():
                    yield con
            else:
                yield con
        except Exception as e:
            err=e
    if(err is not None):raise err
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
        await r.expire(cred.credentials,15*600)
        uid,priv=data.split(b":")
        return session(int(uid),int(priv))