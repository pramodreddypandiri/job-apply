"""Form fill agent — Playwright-based ATS form filling."""

import asyncio
import os
import random
import tempfile
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
            if value and await page.query_selector(selector):
                await human_type(page, selector, value)
        except Exception as e:
            logger.debug(f"Field {selector} not found or failed: {e}")


async def fill_lever(page: Page, resume: dict, profile: dict):
    """Fill Lever application form."""
    logger.info("Filling Lever form")
    github_url = f"https://github.com/{profile.get('github_username', '')}" if profile.get("github_username") else ""

    for selector, value in [
        ('input[name="name"]', profile.get("full_name", "")),
        ('input[name="email"]', profile.get("email", "")),
        ('input[name="phone"]', profile.get("phone", "")),
        ('input[name="urls[LinkedIn]"]', profile.get("linkedin_url", "")),
        ('input[name="urls[GitHub]"]', github_url),
    ]:
        try:
            if value and await page.query_selector(selector):
                await human_type(page, selector, value)
        except Exception as e:
            logger.debug(f"Field {selector} not found or failed: {e}")


async def fill_ashby(page: Page, resume: dict, profile: dict):
    """Fill Ashby application form."""
    logger.info("Filling Ashby form")
    name_parts = (profile.get("full_name") or "").split(" ", 1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    # Ashby uses _systemfield_ prefixed name attributes
    for selector, value in [
        ('input[name*="first" i]', first_name),
        ('input[name*="last" i]', last_name),
        ('input[name*="email" i]', profile.get("email", "")),
        ('input[name*="phone" i]', profile.get("phone", "")),
        ('input[name*="linkedin" i]', profile.get("linkedin_url", "")),
    ]:
        try:
            field = await page.query_selector(selector)
            if field and value:
                await field.fill(value)
        except Exception as e:
            logger.debug(f"Ashby field {selector} failed: {e}")

    # Also try placeholder-based matching
    for placeholder, value in [
        ("First", first_name),
        ("Last", last_name),
        ("Email", profile.get("email", "")),
        ("Phone", profile.get("phone", "")),
    ]:
        if not value:
            continue
        try:
            field = await page.query_selector(f'input[placeholder*="{placeholder}"]')
            if field:
                current = await field.input_value()
                if not current:
                    await field.fill(value)
        except Exception as e:
            logger.debug(f"Ashby placeholder {placeholder} failed: {e}")


async def fill_generic(page: Page, resume: dict, profile: dict):
    """Generic form fill — best effort."""
    logger.info("Filling generic form")
    fields = {
        "name": profile.get("full_name", ""),
        "email": profile.get("email", ""),
        "phone": profile.get("phone", ""),
        "location": profile.get("target_locations", ""),
        "linkedin": profile.get("linkedin_url", ""),
    }

    for label, value in fields.items():
        if not value:
            continue
        try:
            field = await page.query_selector(f'input[name*="{label}" i]')
            if not field:
                field = await page.query_selector(f'input[placeholder*="{label}" i]')
            if not field:
                field = await page.query_selector(f'input[id*="{label}" i]')
            if field:
                await field.fill(value)
        except Exception as e:
            logger.debug(f"Generic fill for {label} failed: {e}")


async def upload_resume_pdf(page: Page, pdf_url: str, ats_type: str):
    """Upload resume PDF to the form."""
    import httpx

    tmp_path = None
    try:
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            # Use service key auth in case bucket is private
            headers = {
                "apikey": settings.supabase_service_key,
                "Authorization": f"Bearer {settings.supabase_service_key}",
            }
            response = await client.get(pdf_url, headers=headers, follow_redirects=True)
            if response.status_code != 200:
                logger.warning(f"Resume PDF download failed: {response.status_code}")
                return

            tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            tmp_path = tmp.name
            tmp.write(response.content)
            tmp.close()

        file_input = await page.query_selector('input[type="file"]')
        if file_input:
            await file_input.set_input_files(tmp_path)
            logger.info("Resume PDF uploaded")
        else:
            logger.warning("No file input found for resume upload")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


async def _upload_screenshot(screenshot_bytes: bytes, application_id: str, name: str) -> str | None:
    """Upload screenshot to Supabase Storage and return public URL."""
    try:
        from backend.db.client import supabase
        settings = get_settings()
        base_url = settings.supabase_url.rstrip("/")
        path = f"screenshots/{application_id}/{name}.png"
        supabase.storage.from_("resumes").upload(
            path, screenshot_bytes, {"content-type": "image/png"}
        )
        return f"{base_url}/storage/v1/object/public/resumes/{path}"
    except Exception as e:
        logger.warning(f"Screenshot upload failed: {e}")
        return None


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
        await page.goto(apply_url, wait_until="domcontentloaded", timeout=45000)
        # Wait a bit for JS to render form fields
        await page.wait_for_timeout(3000)

        # Check for escalation triggers
        escalation = await check_escalation(page)
        captcha_triggers = {"captcha", "recaptcha", "hcaptcha"}
        is_captcha = escalation and any(t in escalation for t in captcha_triggers)

        if escalation and not is_captcha:
            # Hard escalation — can't proceed at all (login, SSO, etc.)
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
            case "ashby":
                await fill_ashby(page, resume, profile)
            case _:
                await fill_generic(page, resume, profile)

        # Upload resume
        if resume.get("resume_pdf_url"):
            await upload_resume_pdf(page, resume["resume_pdf_url"], ats_type)

        # Pre-submit screenshot
        pre_bytes = await page.screenshot(full_page=True)
        pre_url = await _upload_screenshot(pre_bytes, application_id, "pre_submit")

        # If CAPTCHA detected, form is filled but we can't auto-submit
        if is_captcha:
            logger.info(f"CAPTCHA detected — form filled, awaiting manual completion. URL: {apply_url}")
            return {
                "submitted": False,
                "escalation": "captcha",
                "screenshot_url": pre_url,
                "log": {
                    "ats_type": ats_type,
                    "reason": "captcha_manual_required",
                    "message": "Form has been filled. Please open the Chrome window, solve the CAPTCHA, and click Submit.",
                },
            }

        # Find and click submit
        submit_btn = (
            await page.query_selector('button[type="submit"]')
            or await page.query_selector('input[type="submit"]')
            or await page.query_selector('button:has-text("Submit")')
            or await page.query_selector('button:has-text("Apply")')
        )

        if submit_btn:
            await submit_btn.click()
            await page.wait_for_timeout(3000)
            post_bytes = await page.screenshot()
            post_url = await _upload_screenshot(post_bytes, application_id, "post_submit")
            logger.info("Form submitted successfully")
            return {
                "submitted": True,
                "screenshot_url": post_url or pre_url,
                "log": {"ats_type": ats_type},
            }
        else:
            logger.warning("Submit button not found")
            return {
                "submitted": False,
                "screenshot_url": pre_url,
                "log": {"reason": "submit_button_not_found"},
            }

    finally:
        await page.close()
