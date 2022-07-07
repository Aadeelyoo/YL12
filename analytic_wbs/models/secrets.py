import base64
import datetime
import json
import time

from jose import jws
import os
import requests

class Adobe:
    def Adobe_Vars():
        v = {
            "CLIENT_ID": "2bb1a0011798402096cbce80ff19de64",
            "CLIENT_SECRET": "p8e-kwBtHGpCV8zkBdGRkFooCFZj8GXmr89R",
            "TECHNICAL_ACCOUNT_ID": "462E1F2E62387CF70A495F9C@techacct.adobe.com",
            "ORGANIZATION_ID": "40C21D2B62387C930A495C40@AdobeOrg",

            "ADOBE_MERGE_URL": "https://cpf-ue1.adobe.io/ops/:create?respondWith=%7B%22reltype%22%3A%20%22http%3A%2F%2Fns.adobe.com%2Frel%2Fprimary%22%7D"
        }
        v.update({
            "ACCESS_TOKEN" : generate_JWT(v)
        })
        return v


def generate_JWT(v):

    url = 'https://ims-na1.adobelogin.com/ims/exchange/jwt'
    ims_server = "ims-na1.adobelogin.com"
    currecnt_sec_time = int(round(time.time()))
    expiry_time = currecnt_sec_time + (60 * 60 * 24)
    jwtPayloadJson = {"iss" : v["ORGANIZATION_ID"], "sub": v["TECHNICAL_ACCOUNT_ID"],
                      "aud" : "https://{}/c/{}".format(ims_server, v["CLIENT_ID"]),
                      "https://{}/s/ent_documentcloud_sdk".format(ims_server): True,
                      "exp": expiry_time}

    accessTokenRequestPayload = {'client_id': v['CLIENT_ID']
                                ,'client_secret': v['CLIENT_SECRET']}

    # Request Access Key
    #This Needs to point at where your private key is on the file system
    path = os.path.realpath(
        os.path.join(os.path.dirname(__file__), '..', 'keys'))
    keyfile = open(path+'/private.key','r')
    private_key = keyfile.read()

    # Encode the jwt Token
    jwttoken = jws.sign(jwtPayloadJson, private_key, algorithm='RS256')
    print("Encoded JWT Token")


    accessTokenRequestPayload['jwt_token'] = jwttoken
    result = requests.post(url, data=accessTokenRequestPayload)
    resultjson = json.loads(result.text)
    print("Full output from the access token request")
    # print(json.dumps(resultjson, indent=4, sort_keys=True))

    return resultjson["access_token"]
