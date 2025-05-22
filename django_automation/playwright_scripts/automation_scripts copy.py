from playwright.sync_api import sync_playwright
import time
from django.core.cache import cache
import json
import requests

def send_graphql_request(graphql_data, zoeknummer):
    url = "https://api.prod.aws.ziggo.io/v2/api/my-enterprise/graphql"

    headers = {
        k.title(): v
        for k, v in graphql_data["graphql_headers"].items()
        if k in [
            "authorization", "content-type", "origin", "referer",
            "x-account-id", "x-ctx-id", "x-ctx-contact-id",
            "x-bc-id", "x-correlation-id", "x-userflow-id"
        ]
    }

    account_id = graphql_data.get("account_id")
    if not account_id:
        return {"error": "account_id ontbreekt"}

    payload = {
        "operationName": "getDetailedOverviewData",
        "variables": {
            "accountId": account_id,
            "billingCustomerId": None,
            "queryParameters": {
                "page": 0,
                "size": 10,
                "filters": [
                    {"id": "name_or_number_filter", "value": zoeknummer}
                ]
            }
        },
        "query": """
            query getDetailedOverviewData($accountId: String!, $billingCustomerId: String, $queryParameters: DetailedOverviewQueryParameters!) {
            detailedOverviewData(accountId: $accountId, billingCustomerId: $billingCustomerId, queryParameters: $queryParameters) {
                data {
                searchOutsideScope
                contactsOutsideScope {
                    formattedName
                    billingCustomerId
                    billingCustomerName
                    __typename
                }
                contacts {
                    restriction0900
                    assignedProductId
                    billingCustomerId
                    billingCustomerName
                    formattedBillingCustomer
                    contactId
                    email
                    formattedName
                    eroticRestriction
                    foreignCallRestriction
                    incomingRestriction
                    isDataOnly
                    msisdn
                    outgoingRestriction
                    roamingRestriction
                    rowId
                    simNumbers
                    status
                    statusReason
                    subscriberId
                    subscriptionType
                    vomNumbers
                    vpnNumber
                    __typename
                }
                __typename
                }
                pageMetadata {
                totalElements
                size
                totalPages
                number
                elements
                __typename
                }
                __typename
            }
            }
            """

    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}



def send_message(message, icon_class='', success=False, data=None):
    payload = {"message": message, "icon_class": icon_class, "success": success}
    if data:
        payload["data"] = data
    return f'data: {json.dumps(payload)}\n\n'

def validate_existing_session(sessie_data, zoeknummer):
    try:
        test_result = send_graphql_request(sessie_data, zoeknummer)
        if test_result.get("data") or test_result.get("contacts"):
            return True, test_result
    except Exception:
        pass
    return False, None



def wait_for_2fa_code(token, browser, send):
    for _ in range(180):
        code = cache.get(f"2fa_code:{token}")
        if code:
            return code
        if cache.get(f"2fa_cancel:{token}"):
            yield send("2FA geannuleerd door gebruiker.", "fas fa-ban")
            browser.close()
            return None
        time.sleep(0.5)
    yield send("Timeout: geen 2FA code ontvangen.", "fas fa-hourglass-end")
    browser.close()
    return None



def wait_for_bearer_token(page, timeout=10):
    for _ in range(timeout * 2):
        token = page.evaluate("window.localStorage.getItem('auth-token')")
        if token:
            return token
        time.sleep(0.5)
    return None

def handle_intercept(route, request, bearer_token_container, graphql_headers_container, graphql_payload_container):
    headers = request.headers
    lowercase_headers = {k.lower(): v for k, v in headers.items()}
    graphql_headers_container.update(lowercase_headers)

    auth_header = lowercase_headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        bearer_token_container["token"] = auth_header.split(" ")[1]

    post_data = request.post_data
    try:
        graphql_payload_container["json"] = json.loads(post_data)
    except:
        graphql_payload_container["raw"] = post_data

    route.continue_()

def setup_session_data(page, bearer_token, graphql_headers, graphql_payload):
    local_storage = page.evaluate("Object.entries(window.localStorage)")
    return {
        "bearer_token": bearer_token,
        "graphql_headers": graphql_headers,
        "graphql_payload": graphql_payload,
        "account_id": graphql_headers.get("x-account-id"),
        "cookies": page.context.cookies(),
        "account_url": page.url,
        "local_storage": [{"name": k, "value": v} for k, v in local_storage]
    }



def vodafone_login(username, password, token, zoeknummer_raw):
    yield send_message("Sessie ophalen...", "fas fa-cookie")

    zoeknummers = [zn.strip() for zn in zoeknummer_raw.split(",") if zn.strip()]
    
    if not zoeknummers:
        yield send_message("Geen geldige nummers opgegeven.", "fas fa-exclamation-triangle")
        return
    
    yield send_message("Browser wordt gestart...", "fas fa-spinner fa-spin")

    bearer_token_container = {}
    graphql_headers_container = {}
    graphql_payload_container = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        try:
            page = browser.new_page()
            page.route("**/graphql", lambda route, req: handle_intercept(
                route, req, bearer_token_container, graphql_headers_container, graphql_payload_container
            ))

            yield send_message("Pagina laden...", "fas fa-globe")
            page.goto("https://www.vodafone.nl/account/inloggen")
            page.wait_for_load_state("domcontentloaded")

            page.fill("#j_username", username)
            yield send_message("Gebruikersnaam ingevuld", "fas fa-user")
            page.fill("#j_password", password)
            yield send_message("Wachtwoord ingevuld", "fas fa-key")
            page.click("#loginFormSubmitButton")
            yield send_message("Formulier verstuurd...", "fas fa-paper-plane")
            page.wait_for_load_state("networkidle")

            if page.query_selector("#code"):
                yield send_message("2FA vereist. Wacht op invoer sms-code...", "fas fa-lock")
                trust_checkbox = page.query_selector("#trustedDevice")
                if trust_checkbox and trust_checkbox.is_visible():
                    trust_checkbox.check()
                    yield send_message("Vertrouw dit apparaat aangevinkt.", "fas fa-shield-alt")

                code = yield from wait_for_2fa_code(token, browser, send_message)
                if not code:
                    return
                page.fill("#code", code)
                page.click("button[data-cy='confirm-sms-token-form-submit-button']")
                yield send_message("2FA code ingevuld...", "fas fa-spinner fa-spin")
                page.wait_for_load_state("networkidle")
                page.wait_for_load_state("domcontentloaded")

            if "error.html" in page.url or "Inloggen is niet gelukt" in page.title():
                yield send_message("Inloggen is niet gelukt.", "fas fa-times-circle")
                return

            try:
                page.click("#onetrust-reject-all-handler", timeout=15000, force=True)
                yield send_message("Cookievoorkeuren afgehandeld.", "fas fa-cookie-bite")
            except:
                yield send_message("Cookievoorkeuren niet gevonden of al verwerkt.", "fas fa-cookie-bite")

            bearer_token = wait_for_bearer_token(page)
            if not bearer_token:
                bearer_token = bearer_token_container.get("token")

            sessie_data = setup_session_data(page, bearer_token, graphql_headers_container, graphql_payload_container)

            if bearer_token and zoeknummers:
                resultaten = {}
                for zn in zoeknummers:
                    try:
                        result = send_graphql_request(sessie_data, zn)
                        resultaten[zn] = result
                        yield send_message(f"Gegevens voor {zn} opgehaald.", "fas fa-search", True, result)
                    except Exception as e:
                        resultaten[zn] = {"error": str(e)}
                        yield send_message(f"Fout bij ophalen van {zn}: {str(e)}", "fas fa-bug")
                cache.set(f"graphql_result:{token}", resultaten, timeout=300)
            else:
                yield send_message("Fout: Bearer token niet gevonden", "fas fa-bug", False, sessie_data)

        except Exception as e:
            yield send_message(f"Fout: {str(e)}", "fas fa-bug")
        finally:
            yield send_message("Loginproces voltooid.", "fas fa-info-circle", True)
            browser.close()



def voer_vodafone_nummercheck_uit(username, password, token, zoeknummer_raw):
    with sync_playwright() as p:
            context, page = vodafone_login(p, username, password)

            # Hier kun je dingen doen na inloggen
            page.goto("https://www.vodafone.nl/zakelijk/my/v2/")
            print("[INFO] Mijn Vodafone geopend.")
            

            context.close()    

### WERKENDE VERSIE
