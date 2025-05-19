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
                "size": 1000,
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

def vodafone_login(username, password, token, zoeknummer):
    def send(message, icon_class='', success=False, data=None):
        payload = {"message": message, "icon_class": icon_class, "success": success}
        if data:
            payload["data"] = data
        return f'data: {json.dumps(payload)}\n\n'

    def wait_for_bearer_token(page, timeout=10):
        for _ in range(timeout * 2):
            token = page.evaluate("window.localStorage.getItem('auth-token')")
            if token:
                print("[DEBUG] Bearer token gevonden in localStorage")
                return token
            time.sleep(0.5)
        print("[FOUT] Geen bearer token in localStorage gevonden")
        return None

    bearer_token_container = {}
    graphql_headers_container = {}
    graphql_payload_container = {}

    def intercept_graphql(route, request):
        headers = request.headers
        lowercase_headers = {k.lower(): v for k, v in headers.items()}
        graphql_headers_container.update(lowercase_headers)

        auth_header = lowercase_headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            print("[DEBUG] Bearer token uit header:", auth_header)
            bearer_token_container["token"] = auth_header.split(" ")[1]

        post_data = request.post_data
        try:
            graphql_payload_container["json"] = json.loads(post_data)
        except:
            graphql_payload_container["raw"] = post_data

        route.continue_()

    yield send("Browser wordt gestart...", "fas fa-spinner fa-spin")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        try:
            page = browser.new_page()
            page.route("**/graphql", intercept_graphql)

            yield send("Pagina laden...", "fas fa-globe")
            page.goto("https://www.vodafone.nl/account/inloggen")

            page.wait_for_selector("#j_username")
            page.fill("#j_username", username)
            yield send("Gebruikersnaam ingevuld", "fas fa-user")

            page.wait_for_selector("#j_password")
            page.fill("#j_password", password)
            yield send("Wachtwoord ingevuld", "fas fa-key")

            page.wait_for_selector("#loginFormSubmitButton")
            page.click("#loginFormSubmitButton")
            yield send("Formulier verstuurd, wacht op reactie...", "fas fa-paper-plane")
            page.wait_for_load_state("networkidle")

            if page.query_selector("#code"):
                yield send("2FA vereist. Wacht op invoer sms-code...", "fas fa-lock")
                for _ in range(180):
                    code = cache.get(f"2fa_code:{token}")
                    if code:
                        break
                    if cache.get(f"2fa_cancel:{token}"):
                        yield send("2FA geannuleerd door gebruiker.", "fas fa-ban")
                        browser.close()
                        return
                    time.sleep(0.5)
                else:
                    yield send("Timeout: geen 2FA code ontvangen.", "fas fa-hourglass-end")
                    browser.close()
                    return
                page.fill("#code", code)
                page.click("button[data-cy='confirm-sms-token-form-submit-button']")
                yield send("2FA code ingevuld, controleren...", "fas fa-spinner fa-spin")
                page.wait_for_load_state("networkidle")

            if "error.html" in page.url or "Inloggen is niet gelukt" in page.title():
                yield send("Inloggen is niet gelukt.", "fas fa-times-circle")
                browser.close()
                return

            try:
                page.wait_for_selector("#onetrust-reject-all-handler", timeout=5000)
                page.click("#onetrust-reject-all-handler", timeout=1000, force=True)
                yield send("Cookievoorkeuren afgehandeld.", "fas fa-cookie-bite")
            except:
                yield send("Cookievoorkeuren niet gevonden of al verwerkt.", "fas fa-cookie-bite")

            bearer_token = wait_for_bearer_token(page)
            if not bearer_token:
                bearer_token = bearer_token_container.get("token")

            data_response = {
                "bearer_token": bearer_token,
                "graphql_headers": graphql_headers_container,
                "graphql_payload": graphql_payload_container,
                "account_id": graphql_headers_container.get("x-account-id")
            }

            if bearer_token and zoeknummer:
                sessie_data = {
                    "bearer_token": bearer_token,
                    "graphql_headers": graphql_headers_container,
                    "graphql_payload": graphql_payload_container,
                    "account_id": graphql_headers_container.get("x-account-id"),
                    "cookies": page.context.cookies(),
                    "account_url": page.url
                }
                cache.set(f"vodafone_session:{token}", sessie_data, timeout=300)

                try:
                    lookup_result = send_graphql_request(sessie_data, zoeknummer)
                    cache.set(f"graphql_result:{token}", lookup_result, timeout=300)
                    yield send(f"result = {lookup_result}", "fas fa-search", True, lookup_result)
                    print(lookup_result)
                    yield send("Nummergegevens opgehaald.", "fas fa-search", True, lookup_result)
                except Exception as e:
                    yield send(f"Lookup fout: {str(e)}", "fas fa-bug")

            else:
                yield send("Fout: Bearer token niet gevonden", "fas fa-bug", False, data_response)

            print(data_response)

        except Exception as e:
            yield send(f"Fout: {str(e)}", "fas fa-bug")
        finally:
            yield send("Loginproces voltooid.", "fas fa-info-circle", True)
            browser.close()