from pprint import pprint
from re import X
import requests as r

# Tenant Information [{tenant URL}, {tenantID}, {username}, {password}, {appID-optional}, {scope-optional}]
# example:
# t0 = ["abc1234.my.centrify.net","abc1234", "user@domain.com","password"]


class Delinea_api():

    def __init__(self, tenant: list, bearer: str | bool = False):

        self.tenant = tenant

        # Start Authentication
        if bearer:
            
            self.bearer = bearer

        elif len(tenant) >= 5:

            head = {
            "X-CENTRIFY-NATIVE-CLIENT": "true",
            "Content-Type": "application/x-www-form-urlencoded",
            }

            key = {
                "grant_type": "client_credentials",
                "scope": tenant[5],
                "client_secret": tenant[3],
                "client_id": tenant[2]
                }

            self.bearer = (r.post(f"https://{tenant[0]}/Oauth2/Token/{tenant[4]}",headers=head,data=key).json())['access_token']

        else:

            head = {
                "X-CENTRIFY-NATIVE-CLIENT": "true",
                "Content-Type": "application/json"
            }

            key = {
                "TenantId": tenant[1],
                "User": tenant[2],
                "Version": "1.0"
                }

            response = r.post(f"https://{tenant[0]}/Security/StartAuthentication",headers=head,json=key).json()
            sessionid: str = response["Result"]["SessionId"]
            
            mechanismid_00 = response["Result"]["Challenges"][0]['Mechanisms'][0]['MechanismId']

            key = {
                "TenantId": tenant[1],
                "SessionId": sessionid,
                "MechanismId": mechanismid_00,
                "Action": "Answer",
                "Answer": tenant[3]
                }

            adv_response = r.post(f"https://{tenant[0]}/Security/AdvanceAuthentication",headers=head,json=key)
            print(adv_response)

            self.bearer =  adv_response.cookies['.ASPXAUTH']

    # Post
    def post(self, endpoint, key=None):
        
        if endpoint.lower() == "/redrock/query":

            headers = {
                "X-CENTRIFY-NATIVE-CLIENT": "true",
                "Content-Type": "application/json",
                'Accept': "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                'Authorization': "Bearer " + self.bearer
                }
            
            query = {
                "Script":key,
                "args":
                    {
                    "PageNumber":1,
                    "PageSize":100,
                    "Limit":10000,
                    "Caching":-1,
                    }
                }

            return r.post(f"https://{self.tenant[0]}/Redrock/query", headers=headers, json=query).json()

        elif endpoint.lower() == "/core/makefile":

            headers = {
            "X-CENTRIFY-NATIVE-CLIENT": "true",
            "Content-Type": "application/x-www-form-urlencoded",
            'accept': "*/*",
            'Upgrade-Insecure-Requests': '1',
            'Accept-Encoding': 'gzip, deflate, br',
            'Authorization': "Bearer " + self.bearer
            }

            rep = r.post(f"https://{self.tenant[0]}{endpoint}", headers=headers, data=key)
            
            # test if response is good
            if rep.status_code == 200:
                loc = input('\nFile Location (e.g. c:\\filename.txt): \n> ')

                if loc == '':
                    open("file", 'wb').write(rep.content)
                    print()
                else:
                    open(loc, 'wb').write(rep.content)
                    print()
                return {'status':'200'}

            else:

                return rep.json()

        else:

            headers = {
            "X-CENTRIFY-NATIVE-CLIENT": "true",
            "Content-Type": "application/json",
            'accept': "*/*",
            'Authorization': "Bearer " + self.bearer
            }

            return r.post("https://"+self.tenant[0]+endpoint, headers=headers, json=key).json()