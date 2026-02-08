import asyncio
import asyncpg
import time
async def run():
    con:asyncpg.Connection=await asyncpg.connect(user='postgres',password='12345678')
    try:
        async with con.transaction():
            await con.execute('''CREATE TABLE comment(
                                id SERIAL,
                                dish_id INT,
                                uid INT,
                                name TEXT,
                                image TEXT,
                                content TEXT,
                                primary key(dish_id,uid)
                            )''')
            await con.execute('''CREATE TABLE dish(
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
            await con.execute(f'''insert into dish(name,image,tag,level,description,author,ingredient,instruction,time,upload_time) 
                            values('Buttermilk Pancakes with Berry Compote','dish/image/pancake.webp','DESSERT','medium','Start your morning with these fluffy, golden pancakes topped with a warm berry
                        compote. Made with simple ingredients you already have in your pantry, this breakfast favorite
                        brings comfort and joy to any table.','maria','[]'::JSONB,'[]'::JSONB,900,{int(time.time())})''')
    except Exception as e:
        print(e)
    finally:
        await con.close()
asyncio.run(run())