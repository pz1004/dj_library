from __future__ import annotations

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import json
from main import create_total_search_result

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


class SearchRequest(BaseModel):
    keywords: list[str]
    libraries: list[str] | None = None


# Load the library list from the JSON file
with open('static/lib_list.json', 'r', encoding='utf-8') as f:
    lib_list = json.load(f)


@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "libraries": list(lib_list.keys())}
    )


@app.post("/search", response_class=HTMLResponse)
async def search_books(
    request: Request,
    keywords: str = Form(...),
    libraries: list[str] | None = Form(None),
) -> HTMLResponse:
    keywords_list = [kw.strip() for kw in keywords.splitlines() if kw.strip()]
    results = create_total_search_result(keywords_list, libraries)
    # Replace only the first <td> to left-align the title column.
    results_html = results.to_html(index=False).replace("<td>", '<td class="left-align">', 1)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "results": results_html,
            "libraries": list(lib_list.keys()),
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
