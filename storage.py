import vercel.blob.aio as blob
import os
import asyncio
blob_token=os.environ.get("BLOB_TOKEN")
cilent=None
if(blob_token is not None):
    cilent=blob.AsyncBlobClient()
async def store_fs(path:str,content:bytes):
    loop=asyncio.get_running_loop()
    try:
        with open(path,"w+b") as fp:
            await loop.run_in_executor(None,fp.write,content)
        return path
    except:
        return None
async def store_vercel(path:str,content:bytes,public:bool):
    assert(cilent is not None)
    stream=(await cilent.create_multipart_uploader(path=path,access="public" if public else "private"))
    try:
        return (await stream.upload_part(1,content)).etag
    except Exception as e:
        print(e)
        return None
async def store(path:str,content:bytes,public:bool=False)->str|None:
    if(cilent is None):
        return await store_fs(path,content)
    return await store_vercel(path,content,public)
async def load_fs(name:str):
    try:
        loop=asyncio.get_running_loop()
        with open(name,"rb") as fp:
            return await loop.run_in_executor(None,fp.read)
    except:return None
async def load_vercel(name:str):
    assert(cilent is not None)
    try:
        return await cilent.get(name)
    except:
        return None
async def load(name:str)->bytes|None:
    if(cilent is None):
        return await load_fs(name)
    return await load_vercel(name)
async def delete_fs(name:str):
    try:
        loop=asyncio.get_running_loop()
        await loop.run_in_executor(None,os.remove,name)
        return True
    except:return False
async def delete_vercel(name:str):
    assert(cilent is not None)
    try:
        await cilent.delete(name)
    except:
        return False
    return True
async def delete(name:str)->bool:
    if(cilent is None):return await delete_fs(name)
    return await delete_vercel(name)
