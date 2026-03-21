"""Form fill agent — Playwright-based ATS form filling."""

import asyncio
import random
from playwright.async_api import Page
from backend.utils.browser import get_browser, new_page
from backend.config import get_settings
from loguru import logger

ESCALATION_TRIGGERS = [
    "captcha",
    "recaptcha",
    "hcaptcha",
    "login required",
    "sign in",
    "sso required",
    "assessment required",
    "cover letter manual entry required",
    "salary expectation",
    "custom essay question",
]


async def human_type(page: Page, selector: str, text: str):
    """Type text with human-like delays."""
    await page.click(selector)
    for char in text:
        await page.keyboard.type(char, delay=random.randint(30, 80))
        if random.random() < 0.05:
            await asyncio.sleep(random.uniform(0.1, 0.3))


async def detect_ats(page: Page) -> str:
    """Detect ATS type from DOM."""
    url = page.url.lower()
    if "greenhouse" in url:
        return "greenhouse"
    if "lever" in url:
        return "lever"
    if "workday" in url or "myworkdayjobs" in url:
        return "workday"
    if "ashby" in url:
        return "ashby"

    # Check page content
    content = await page.content()
    content_lower = content.lower()
    if "greenhouse" in content_lower:
        return "greenhouse"
    if "lever" in content_lower:
        return "lever"

    return "generic"


async def check_escalation(page: Page) -> str | None:
    """Check if page has any escalation triggers."""
    content = (await page.content()).lower()
    for trigger in ESCALATION_TRIGGERS:
        if trigger in content:
            return trigger
    return None


async def fill_greenhouse(page: Page, resume: dict, profile: dict):
    """Fill Greenhouse application form."""
    logger.info("Filling Greenhouse form")
    # Name fields
    name_parts = (profile.get("full_name") or "").split(" ", 1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    for selector, value in [
        ("#first_name", first_name),
        ("#last_name", last_name),
        ("#email", profile.get("email", "")),
        ("#phone", profile.get("phone", "")),
    ]:
        try:
            if await page.query_selector(selector):
                await human_type(page, selector, value)
        except Exception as e:
            logger.debug(f"Field {selector} not found or failed: {e}")


async def fill_lever(page: Page, resume: dict, profile: dict):
    """Fill Lever application form."""
    logger.info("Filling Lever form")
    for selector, value in [
        ('input[name="name"]', profile.get("full_name", "")),
        ('input[name="email"]', profile.get("email", "")),
        ('input[name="phone"]', profile.get("phone", "")),
        ('input[name="urls[LinkedIn]"]', profile.get("linkedin_url", "")),
        ('input[name="urls[GitHub]"]', f"https://github.com/{profile.get('github_username', '')}"),
    ]:
        try:
            if await page.query_selector(selector):
                await human_type(page, selector, value)
        except Exception as e:
            logger.debug(f"Field {selector} not found or failed: {e}")


async def fill_generic(page: Page, resume: dict, profile: dict):
    """Generic form fill — best effort."""
    logger.info("Filling generic form")
    # Try common field patterns
    name = profile.get("full_name", "")
    email = profile.get("email", "")

    for label, value in [("name", name), ("email", email)]:
        try:
            field = await page.query_selector(f'input[name*="{label}" i]')
            if not field:
                field = await page.query_selector(f'input[placeholder*="{label}" i]')
            if field:
                await field.fill(value)
        except Exception as e:
            logger.debug(f"Generic fill for {label} failed: {e}")


async def upload_resume_pdf(page: Page, pdf_url: str, ats_type: str):
    """Upload resume PDF to the form."""
    # Download PDF from Supabase Storage first
    import httpx
    import tempfile

    async with httpx.AsyncClient() as client:
        response = await client.get(pdf_url)
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(response.content)
        tmp.close()

    # Find file input
    file_input = await page.query_selector('input[type="file"]')
    if file_input:
        await file_input.set_input_files(tmp.name)
        logger.info("Resume PDF uploaded")
    else:
        logger.warning("No file input found for resume upload")


async def fill_application_form(
    application_id: str,
    apply_url: str,
    resume: dict,
    profile: dict,
) -> dict:
    """Main form fill entry point."""
    browser = await get_browser()
    page = await new_page(browser)

    try:
        await page.goto(apply_url, wait_until="networkidle", timeout=30000)

        # Check for escalation triggers
        escalation = await check_escalation(page)
        if escalation:
            logger.warning(f"Escalation triggered: {escalation}")
            return {"submitted": False, "escalation": escalation, "log": {"reason": escalation}}

        # Detect ATS and fill
        ats_type = await detect_ats(page)
        logger.info(f"Detected ATS: {ats_type}")

        match ats_type:
            case "greenhouse":
                await fill_greenhouse(page, resume, profile)
            case "lever":
                await fill_lever(page, resume, profile)
            case _:
                await fill_generic(page, resume, profile)

        # Upload resume
        if resume.get("resume_pdf_url"):
            await upload_resume_pdf(page, resume["resume_pdf_url"], ats_type)

        # Pre-submit screenshot
        pre_screenshot = await page.screenshot(full_page=True)

        # Find and click submit
        submit_btn = (
            await page.query_selector('button[type="submit"]')
            or await page.query_selector('input[type="submit"]')
            or await page.query_selector('button:has-text("Submit")')
            or await page.query_selector('button:has-text("Apply")')
        )

        if submit_btn:
            await submit_btn.click()
            await page.wait_for_load_state("networkidle", timeout=10000)
            post_screenshot = await page.screenshot()
            logger.info("Form submitted successfully")
            return {"submitted": True, "log": {"ats_type": ats_type}}
        else:
            logger.warning("Submit button not found")
            return {"submitted": False, "log": {"reason": "submit_button_not_found"}}

    finally:
        await page.close()
