from html import escape
from functools import wraps
from math import floor
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
def assemble_time(duration:int,max_component:int=-1)->str:
    seconds=int(duration%60)
    minutes=int((duration/60)%60)
    hour=int((duration/3600)%24)
    days=int((duration/(3600*24))%30)
    weeks=floor(duration/(3600*24*7))
    out:list[str]=[]
    if(weeks>0):
        out.append(f"{weeks} weeks")
    if(days>0):
        out.append(f"{days} days")
    if(hour>0):
        out.append(f"{hour} hour")
    if(minutes>0):
        out.append(f"{minutes} minutes")
    if(seconds>0):
        out.append(f"{seconds} seconds")
    if(max_component>0 and len(out)>max_component):
        out=out[0:max_component]
    return " ".join(out)