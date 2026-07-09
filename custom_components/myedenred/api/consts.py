API_BASE_URL = "https://www.myedenred.pt/edenred-customer/v2"
API_LOGIN_URL = f"{API_BASE_URL}/authenticate/default"
API_LOGIN_CHALLENGE_URL = f"{API_LOGIN_URL}/challenge"
API_LIST_URL = f"{API_BASE_URL}/protected/card/list"
API_ACCOUNTMOVEMENT_URL = f"{API_BASE_URL}/protected/card/{{}}/accountmovement"

API_COMMON_PARAMS = {"appVersion": "1.0", "appType": "PORTAL", "channel": "WEB"}
