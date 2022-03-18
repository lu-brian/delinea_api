from pprint import pprint
from re import X
import requests as r

# tt0 = {
#     'tenantURL':'', # required
#     'tenantID': '', # required
#     'username': '', # required
#     'password': '', # optional: attempts password authentication
#     'appID': '',    # optional: initiates oauth
#     'appScope': ''  # optional: required if appID is set
# }

class Delinea_api():

    def __init__(self, tenant: dict, token_override: str | bool = False):

        self.tenant = tenant

        # Start Authentication
        # # bearer token override
        if token_override:
            self.bearer = token_override
        
        # # oauth authentication
        elif (tenant["appID"] and tenant["appScope"]):

            if not tenant['password']:
                tenant['password'] = getpass('enter password: ')
                
            head = {
                "X-CENTRIFY-NATIVE-CLIENT": "true",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            key = {
                "grant_type": "client_credentials",
                "scope": tenant['appScope'],
                "client_secret": tenant['password'],
                "client_id": tenant['username']
                }

            self.bearer = (r.post(f"https://{tenant['tenantURL']}/Oauth2/Token/{tenant['appID']}",headers=head,data=key).json())['access_token']

        # # advanced authentication
        else:
            head = {
                "X-CENTRIFY-NATIVE-CLIENT": "true",
                "Content-Type": "application/json"
            }

            key = {
                "TenantId": tenant['tenantID'],
                "User": tenant['username'],
                "Version": "1.0"
                }

            response = r.post(f"https://{tenant['tenantURL']}/Security/StartAuthentication",headers=head,json=key).json()
            sessionid = response["Result"]["SessionId"]
            
            def processMechanisms(response):
                mechanisms = response["Result"]["Challenges"][0]['Mechanisms']
                userpass = list(filter(lambda mech: mech['Name'] == 'UP', mechanisms))

                # # automatic password authentication
                if userpass and tenant["password"]:

                    key = {
                        "TenantId": tenant['tenantID'],
                        "SessionId": sessionid,
                        "MechanismId": userpass[0]['MechanismId'],
                        "Action": "Answer",
                        "Answer": tenant['password']
                    }

                    response = r.post(f"https://{tenant['tenantURL']}/Security/AdvanceAuthentication",headers=head,json=key)
                else:
                    count = 0
                    
                    # # selection for mechanisms
                    for mechanism in mechanisms:
                        print(f'{count} | {mechanism["PromptMechChosen"]}')
                        count += 1
                    
                    selection = input('# | > enter authentication (#): ')

                    try:
                        while int(selection) >= count:
                            print('# | ! authentication does not exist')
                            selection = input('# | > enter authentication (#): ')
                    except:
                        print(f'# | ! not a number selection')
                        exit()
                    
                    # # basic header template
                    data = {
                        "TenantId": tenant['tenantID'],
                        "SessionId": sessionid,
                        "MechanismId": mechanisms[int(selection)]['MechanismId'],
                        "Action": 'Answer',
                        "PersistentLogin": None
                    }

                    # # out of band
                    if mechanisms[int(selection)]['AnswerType'] == 'StartTextOob':
                        key = {
                            **data,
                            "Action": "StartTextOob",
                        }
                    # # secret question
                    elif mechanisms[int(selection)]['Name'] == 'SQ':
                        secrets = mechanisms[int(selection)]['MultipartMechanism']['MechanismParts']
                        answer = { secret['Uuid']: getpass(f'# {selection} > {secret["QuestionText"]}\n# {selection} > ') for secret in secrets }

                        key = {
                            **data,
                            "Answer": answer
                        }
                    # # password
                    else:
                        key = {
                            **data,
                            "Answer": getpass(f'# {selection} > enter password/pin: \n# {selection} > ')
                        }

                    response = r.post(f"https://{tenant['tenantURL']}/Security/AdvanceAuthentication",headers=head,json=key)

                # # continue if bearer found, otherwise repeat with new mechanism
                if '.ASPXAUTH' in response.cookies.keys():
                    self.bearer = response.cookies['.ASPXAUTH']
                    return None
                else:
                    return processMechanisms(response.json())
            
            processMechanisms(response)

    # Request
    def request(self, endpoint: str, key: dict | None = None):

        header = {
            "X-CENTRIFY-NATIVE-CLIENT": "true",
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Authorization": "Bearer " + self.bearer
        }
        
        if endpoint.lower() == "/redrock/query" or endpoint.lower() == "redrock/query":

            headers = {
                **header,
                "Accept-Encoding": "gzip, deflate, br"
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

            return r.post(f"https://{self.tenant['tenantURL']}/Redrock/query", headers=headers, json=query).json()

        elif endpoint.lower() == "/core/makefile" or endpoint.lower() == "core/makefile":

            headers = {
            **header,
            "Content-Type": "application/x-www-form-urlencoded",
            "Upgrade-Insecure-Requests": "1",
            "Accept-Encoding": "gzip, deflate, br"
            }

            rep = r.post(f"https://{self.tenant['tenantURL']}/{endpoint}", headers=headers, data=key)
            
            # # test if response is good
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

            return r.post(f"https://{self.tenant['tenantURL']}/{endpoint}", headers=header, json=key).json()
