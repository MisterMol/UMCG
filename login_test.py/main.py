import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page, Playwright, BrowserContext

# Configuratie
load_dotenv()
SESSION_DIR = "session"
STATE_PATH = Path(SESSION_DIR) / "state.json"
LOGIN_URL = "https://www.vodafone.nl/account/inloggen"
DASHBOARD_CHECK_SELECTOR = '[data-testid="search-employeeSearchBar-input"]'

USERNAME = os.getenv("VF_USERNAME")
PASSWORD = os.getenv("VF_PASSWORD")

# Logging configuratie
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def handle_cookie_popup(page: Page) -> None:
    try:
        page.click("#onetrust-reject-all-handler", timeout=3000)
        logging.info("Cookies geweigerd.")
    except Exception:
        logging.info("Geen cookie-popup of al afgehandeld.")


def is_logged_in(page: Page) -> bool:
    """Controleert of de gebruiker ingelogd is."""
    try:
        page.goto("https://www.vodafone.nl/zakelijk/my/v2/", timeout=15000)
        handle_cookie_popup(page)
        page.wait_for_selector(DASHBOARD_CHECK_SELECTOR, timeout=8000)
        return True
    except Exception as e:
        logging.warning(f"Niet ingelogd of fout bij controle: {e}")
        return False


def perform_login(page: Page, username: str, password: str) -> bool:
    """Voert de login uit inclusief optionele 2FA."""
    page.goto(LOGIN_URL)
    page.wait_for_load_state("domcontentloaded")

    try:
        page.fill("#j_username", username)
        logging.info("Gebruikersnaam ingevuld.")
        page.fill("#j_password", password)
        logging.info("Wachtwoord ingevuld.")
        page.click("#loginFormSubmitButton")
        logging.info("Loginformulier verzonden.")
    except Exception as e:
        logging.error(f"Fout tijdens invullen loginformulier: {e}")
        return False

    page.wait_for_load_state("networkidle")

    # 2FA detectie
    try:
        page.wait_for_selector("#code", timeout=5000)
        logging.info("2FA vereist. Wacht op invoer...")

        checkbox = page.query_selector("#trustedDevice")
        if checkbox:
            checkbox.check()
            logging.info("Vertrouwd apparaat aangevinkt.")

        code = input("📲 Voer je 2FA-code in (via sms ontvangen): ").strip()
        page.fill("#code", code)
        page.click("button[data-cy='confirm-sms-token-form-submit-button']")
        logging.info("2FA code ingevuld en verstuurd.")

        page.wait_for_load_state("networkidle")
        page.wait_for_load_state("domcontentloaded")

    except Exception as e:
        logging.info(f"Geen 2FA gevraagd of fout bij 2FA: {e}")

    if "error.html" in page.url or "Inloggen is niet gelukt" in page.title():
        logging.error("Inloggen is niet gelukt of foutpagina gedetecteerd.")
        return False

    handle_cookie_popup(page)
    return True


def login(playwright: Playwright, username: str, password: str) -> tuple[BrowserContext, Page] | None:
    """Beheert sessie-login, laadt bestaande cookies of voert login uit."""
    os.makedirs(SESSION_DIR, exist_ok=True)
    browser = playwright.chromium.launch(headless=False)

    if STATE_PATH.exists():
        context = browser.new_context(storage_state=str(STATE_PATH))
        page = context.new_page()
        if is_logged_in(page):
            logging.info("Sessiecookies zijn geldig, login niet nodig.")
            return context, page
        else:
            logging.info("Sessiecookies ongeldig, opnieuw inloggen vereist.")
            context.close()

    # Nieuwe login
    context = browser.new_context()
    page = context.new_page()
    if not perform_login(page, username, password):
        context.close()
        raise Exception("Login is mislukt.")

    context.storage_state(path=str(STATE_PATH))
    logging.info("Ingelogd en sessie opgeslagen.")
    return context, page


def main() -> None:
    """Main script na succesvolle login."""
    with sync_playwright() as p:
        if not USERNAME or not PASSWORD:
            logging.error("Gebruikersnaam of wachtwoord ontbreekt in .env-bestand.")
            return

        try:
            context, page = login(p, USERNAME, PASSWORD)
            page.goto("https://www.vodafone.nl/zakelijk/my/v2/")
            logging.info("Mijn Vodafone geopend.")

            content = page.content()
            logging.info(f"Pagina geladen, HTML-grootte: {len(content)} tekens")

            context.close()
        except Exception as e:
            logging.error(f"Login of verwerking mislukt: {e}")


if __name__ == "__main__":
    main()
