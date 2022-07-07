import base64
import io
import json
import os
import requests
import time

from jose import jws
from odoo import tools
from odoo.tools.translate import _
from tempfile import NamedTemporaryFile, TemporaryFile


def Adobe_Vars():
    v = {
        "CLIENT_ID": "2bb1a0011798402096cbce80ff19de64",
        "CLIENT_SECRET": "p8e-kwBtHGpCV8zkBdGRkFooCFZj8GXmr89R",
        "TECHNICAL_ACCOUNT_ID": "462E1F2E62387CF70A495F9C@techacct.adobe.com",
        "ORGANIZATION_ID": "40C21D2B62387C930A495C40@AdobeOrg",

        "ADOBE_MERGE_URL": "https://cpf-ue1.adobe.io/ops/:create?respondWith=%7B%22reltype%22%3A%20%22http%3A%2F%2Fns.adobe.com%2Frel%2Fprimary%22%7D"
    }
    v.update({
        "ACCESS_TOKEN" : generate_jwt(v)
    })
    return v


ADOBE_URL = "https://cpf-ue1.adobe.io/ops/:create?respondWith=%7B%22reltype%22%3A%20%22http%3A%2F%2Fns.adobe.com%2Frel%2Fprimary%22%7D"
ADOBE_HEADER = {
    "Prefer": "respond-async,wait=10",
    "Accept": "application/json, text/plain, */*",
    "Catch-Control": "no-cache",
    'Connection': 'close'
}

ADOBE_PAYLOAD = {
    "cpf:inputs" : {
        "documentsIn" : []
    },
    "cpf:engine" : {
        "repo:assetId" : "urn:aaid:cpf:Service-916ee91c156b42349a7847a7d564fb13"
    },
    "cpf:outputs" : {
        "documentOut" : {
            "cpf:location" : "OutputFile.pdf",
            "dc:format" : "application/pdf"
        }
    }
}


def generate_jwt(v):

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
    # print("Encoded JWT Token")


    accessTokenRequestPayload['jwt_token'] = jwttoken
    result = requests.post(url, data=accessTokenRequestPayload)
    resultjson = json.loads(result.text)
    # print("Full output from the access token request")
    # /(json.dumps(resultjson, indent=4, sort_keys=True))

    return resultjson["access_token"]


class Adobe:
    def process_from_stack(self):
        i = 0
        files = []
        merged_pdf = ""
        for document in self:
            try:
                # file = io.BytesIO(base64.b64decode(document))
                file = TemporaryFile()
                file.write(base64.b64decode(document))
                file.seek(0)
                filename = "InputFile%d" % i
                files.append(('InputFile{}'.format(i), ('{}.pdf'.format(filename), file, 'application/pdf')))

                doc = {
                    "documentIn" : {
                        "cpf:location": filename,
                        "dc:format": "application/pdf"
                    }
                }
                ADOBE_PAYLOAD["cpf:inputs"]["documentsIn"].append(doc)
                i = i + 1
            except Exception as e:
                raise Exception(_("Error in filling: %s") % e)

        adobe = Adobe_Vars()
        try:
            url = requests.utils.requote_uri(ADOBE_URL)
            ADOBE_PAYLOAD["cpf:outputs"]["documentOut"]["cpf:location"] = "{}.pdf".format(time.time())

            payload = {'contentAnalyzerRequests': json.dumps(ADOBE_PAYLOAD)}
            ADOBE_HEADER.update({
                "Authorization" : f"Bearer {adobe['ACCESS_TOKEN']}",
                "x-api-key" : f"{adobe['CLIENT_ID']}",
            })

            req = requests.post(url, data=payload, headers=ADOBE_HEADER, files=files)
            req.raise_for_status()

            poll = True
            while poll:
                with requests.get(req.headers['location'], headers=ADOBE_HEADER, stream=True) as r:
                # new_request = requests.get(req.headers['location'], headers=ADOBE_HEADER)

                    if r.status_code == 200:
                        merged_pdf = r.content
                        # open('test.docx', 'wb').write(new_request.content)

                        # Debug check json file
                        dir_path = os.path.dirname(os.path.realpath(__file__))
                        ts = str(time.time())
                        # with open(os.path.join(dir_path, "signed-" + ts + ".pdf"), 'w') as f:
                        #     f.write(new_request.content)
                        open(os.path.join(dir_path, "signed-" + ts + ".pdf"), 'wb').write(r.content)
                        req.close()
                        r.close()
                            # json.dump(new_request.content, f, indent=2)
                        print("New json file is created from data.json file")
                        poll = False
                        return merged_pdf
                    else:
                        time.sleep(5)
        except Exception as e:
            raise Exception(_("Error in request: %s") % e)


tools.adobe_merge = Adobe
