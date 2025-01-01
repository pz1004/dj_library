from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from pydantic import BaseModel
import pandas as pd
import json
from main import fetch_books, create_total_search_result

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


class SearchRequest(BaseModel):
    keywords: List[str]
    libraries: Optional[List[str]] = None


# Load the library list from the JSON file
with open('static/lib_list.json', 'r', encoding='utf-8') as f:
    lib_list = json.load(f)


@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "libraries": lib_list.keys()}
    )


@app.post("/search", response_class=HTMLResponse)
async def search_books(
    request: Request,
    keywords: str = Form(...),
    libraries: Optional[List[str]] = Form(None)
):
    print("LIBRARY")
    print(libraries)
    keywords_list = keywords.splitlines()
    results = create_total_search_result(keywords_list, libraries)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "results": results.to_html(index=False).replace('<td>', '<td class="left-align">', 1),
            "libraries": lib_list.keys(),
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
