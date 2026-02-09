import asyncio
import time
import os
from psycopg.connection_async import AsyncConnection
async def run():
    con=None
    try:
        db_url=os.environ.get("POSTGRES_URL")
        if(db_url is not None):
            con=(await AsyncConnection.connect(conninfo=db_url))
        else:
            con=(await AsyncConnection.connect(user='postgres',password='postgres'))
        cur=con.cursor()
        await cur.execute("BEGIN")
        await cur.execute('''CREATE TABLE comment(
                            id SERIAL,
                            dish_id INT,
                            uid INT,
                            name TEXT,
                            image TEXT,
                            content TEXT,
                            primary key(dish_id,uid)
                        )''')
        await cur.execute('''CREATE TABLE dish(
                            id SERIAL primary key,
                            name TEXT UNIQUE,
                            image TEXT,
                            tag TEXT,
                            level TEXT,
                            description TEXT,
                            author TEXT,
                            ingredient JSONB,
                            instruction JSONB,
                            chef_note TEXT,
                            time int,
                            upload_time bigint
                        )''')
        await cur.execute(f'''insert into dish(name,image,tag,level,description,author,ingredient,instruction,time,upload_time) 
                        values('Buttermilk Pancakes with Berry Compote','dish/image/pancake.webp','DESSERT','medium','Start your morning with these fluffy, golden pancakes topped with a warm berry
                    compote. Made with simple ingredients you already have in your pantry, this breakfast favorite
                    brings comfort and joy to any table.','maria','[]'::JSONB,'[]'::JSONB,900,{int(time.time())})''')
    except Exception as e:
        print(e)
    finally:
        if(con is not None):
            await con.close()
asyncio.run(run())