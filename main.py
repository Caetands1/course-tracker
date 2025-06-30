from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse,RedirectResponse

from pathlib import Path

import json

from playwright.async_api import async_playwright

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home():
    return templates.TemplateResponse("index.html", {"request": {}})

@app.get("/auth")
async def auth():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://learn.uea.ac.uk/ultra/course")

        try:
            # courses appear -> user is logged in + 2fa cookies logged
            await page.wait_for_selector("article.element-card.course-element-card", timeout=300_000)
        except:
            await browser.close()
            return HTMLResponse("<h1>Login timed out. Please try again.</h1>", status_code=408)

        await context.storage_state(path="auth.json")
        await browser.close()
        return HTMLResponse("<h1>You're all logged in! You can now close this tab.</h1>")

@app.get("/scrape")
async def scrape_blackboard():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="auth.json")

        page = await context.new_page()
        await page.goto("https://learn.uea.ac.uk/ultra/course")
        await page.wait_for_load_state("networkidle")

        for _ in range(15):
            await page.evaluate("""
                const container = document.getElementById('main-content-inner');
                if (container) {
                    container.scrollBy(0, 500);
                }
            """)
            await page.wait_for_timeout(700)

        courses = []
        course_articles = await page.query_selector_all("article.element-card.course-element-card")
        for article in course_articles:
            article_id = await article.get_attribute("id")
            title_elem = await article.query_selector("h4.js-course-title-element")
            title = await title_elem.inner_text() if title_elem else ""
            if article_id and title:
                # Clean up the article ID to remove any prefix
                article_id = article_id.replace("course-list-course-", "")
                courses.append({"id": article_id, "title": title})

        await browser.close()

        # Save to file
        Path("courses.json").write_text(json.dumps(courses, indent=4))

        #  Redirect user to /courses to view results
        return RedirectResponse(url="/courses", status_code=303)


@app.get("/courses", response_class=HTMLResponse)
async def show_courses(request: Request):
    path = Path("courses.json")
    if not path.exists():
        return HTMLResponse("<h1>No course data found. Scrape first.</h1>", status_code=404)

    courses = json.loads(path.read_text())
    return templates.TemplateResponse("courses.html", {"request": request, "courses": courses})

@app.get("scrapeCourse{course_id}", response_class=HTMLResponse)
async def scrape_course(request: Request, course_id: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="auth.json")

        page = await context.new_page()
        await page.goto(f"https://learn.uea.ac.uk/ultra/courses/{course_id}/outline")

        # Wait for the course content to load
        await page.wait_for_load_state("networkidle")

        

        await browser.close()

        return RedirectResponse(url="/courses", status_code=303)