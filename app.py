from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from pydantic import BaseModel
import pandas as pd
import lib_list
from main import fetch_books, create_total_search_result

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


class SearchRequest(BaseModel):
    keywords: List[str]
    libraries: Optional[List[str]] = None


@app.get("/", response_class=HTMLResponse)
async def read_form():
    return templates.TemplateResponse(
        "index.html", {"request": {}, "libraries": lib_list.lib_code.keys()}
    )


@app.post("/search", response_class=HTMLResponse)
async def search_books(
    keywords: str = Form(...), libraries: Optional[List[str]] = Form(None)
):
    print("LIBRARY")
    print(libraries)
    keywords_list = keywords.splitlines()
    results = create_total_search_result(keywords_list, libraries)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": {},
            "results": results.to_html(index=False).replace('<td>', '<td class="left-align">', 1),
            "libraries": lib_list.lib_code.keys(),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, auto)
