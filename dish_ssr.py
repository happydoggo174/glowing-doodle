import os
from fastapi import HTTPException
from html_util import assemble_time
from ssr_config import BASE_ADDR,GITHUB_ADDRESS
DISH_PAGE_HEAD=f'''<!DOCTYPE html><html lang="en"><head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hungry Ship</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet"
        integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB" crossorigin="anonymous">
    <link href="{GITHUB_ADDRESS}core.css" rel="stylesheet">
    <link rel="stylesheet" href="{GITHUB_ADDRESS}food_page_style.css">
    <link rel="stylesheet" href="{GITHUB_ADDRESS}comments.css">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"
        integrity="sha384-FKyoEForCGlyvwx9Hj09JcYn3nv7wiPVlz7YYwJrWVcXK/BmnVDxM+D2scQbITxI"
        crossorigin="anonymous"></script>
</head>'''
NAVBAR_HTML='''<header class="main_header">
        <div class="container text-center">
            <h1 class="main_tilte fade-in-up">Hungry Ship</h1>
            <p class="main_motto slide-in-right">sail around the culinary world</p>
        </div>
    </header>
    <nav class="main-nav">
        <div class="container">
            <ul class="nav justify-content-center">
                <li class="nav-item"><a class="nav-link" href="#home">Home</a></li>
                <li class="nav-item"><a class="nav-link" href="#recipes">Recipes</a></li>
                <li class="nav-item"><a class="nav-link" href="#about">About</a></li>
                <li class="nav-item"><a class="nav-link" href="#contact">Contact</a></li>
            </ul>
        </div>
    </nav>'''
DISH_PAGE_UTIL='''<div class="util_rows">
        <button class="util_btn">PRINT RECIPE</button>
        <button class="util_btn">SAVE RECIPE</button>
        <button class="util_btn">SHARE</button>
    </div>'''
def build_dish(dishes:list[dict[str,str|int]]):
    output=""
    for dish in dishes:
        level=dish["level"]
        color="green"
        if(level=="medium"):
            color="yellow"
        elif(level=="hard"):
            color="red"
        output+=f'''<div class="recipe-card {color}_hover" id={"dish:"+str(dish["id"])}>
                <a href="{BASE_ADDR+"dish/detail/"+str(dish["id"])}" class="card-link">
                    <img src="{BASE_ADDR+"dish/image/"+os.path.basename(str(dish["image"]))}">
                    <div class="info">
                        <span class="tag">{dish["tag"]}</span>
                        <span class="tilte">{dish["name"]}</span>
                        <span class="description">{dish["description"]}</span>
                        <div class="recipe-extra">
                            <span>{assemble_time(int(dish["time"]))}</span>
                            <span>{dish["level"]}</span>
                        </div>
                    </div>
                </a>
            </div>'''
    return output
def build_ingredients_string(content:dict[str,str|int|list[str]])->str:
    ingredients:list[str]=content["ingredient"]
    ingredients_string=""
    for i in ingredients:
        ingredients_string+=f"<li>{i}</li>"
    return f'''<div class="list_container"><h2>Ingredients</h2><ul class="ingredients-list">{ingredients_string}</ul></div>'''
def build_instructions_string(content:dict[str,str]):
    instructions=content["instruction"]
    instructions_string=""
    for i in instructions:
        instructions_string+=f"<li>{i}</li>"
    return f'''<div class="list_container"><h1>Instructions</h1>
    <ol class="instructions_list">{instructions_string}</ol></div>'''
def build_info_section(data:dict):
    return f'''<div class="info_section">
        <div class="info_item">👤 Chef {data["author"]}</div>
        <div class="info_item">📅 February 3, 2026</div>
        <div class="info_item">⏱ {assemble_time(data["time"],max_component=3)}</div>
        <span>{data["level"]}</span>
    </div>'''
def build_chef_note(data:dict[str,str]):
    return f'''<div class="list_container">
            <span style="display: block;font-family: serif;font-size: 14px;">Chef's Notes</span>
            <span>{data["chef_note"]}</span>
        </div>'''

def build_comments(data:list[dict[str,str]])->str:
    comment_string=""
    for i in data:
        comment_string+=f'''<div class="comment">
            <div class="commenter">
                <img src="{BASE_ADDR+"user/image/"+os.path.basename(i["image"])}">
                <b class="name">{i["name"]}</b>
            </div>
            <span class="content">{i["content"]}</span>
        </div>'''
    return f'''<b class="comment-banner">comments({len(data)})</b><div class="comments-row">{comment_string}</div>'''
def build_dish_page(dish:list[dict[str,str|int|list[str]]],comments:list[dict[str,str]]):
    data=dish
    if(data is None):
        raise HTTPException(404,"no such dish")
    ingredients_string=build_ingredients_string(data)
    instructions_string=build_instructions_string(data)
    info_section=build_info_section(data)
    chef_note=build_chef_note(data)
    comment_section=build_comments(comments)
    return f'''{DISH_PAGE_HEAD}<body>
    {NAVBAR_HTML}
    <b class="topic">{data["tag"]}</b>
    <h1 class="tilte">{data["name"]}</h1>{info_section}
    <img src="{BASE_ADDR+"dish/image/"+os.path.basename(data["image"])}" class="main_image">
    {DISH_PAGE_UTIL}
    <div class="center_row">
        <div class="description">{data["description"]}</div>
    {ingredients_string}{instructions_string}{chef_note}</div>{comment_section}'''