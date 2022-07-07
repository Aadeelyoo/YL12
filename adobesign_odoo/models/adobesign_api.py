import requests, json, urllib, datetime, os
import base64
from odoo.exceptions import UserError, ValidationError
from odoo import tools, _

root_path = os.path.dirname(os.path.abspath(__file__))

def valid_token_time(expires_in):
    expires_ins = datetime.datetime.fromtimestamp(int(expires_in) / 1e3)
    expires_in = expires_ins + datetime.timedelta(seconds=3600)
    nowDateTime = datetime.datetime.now()
    if nowDateTime > expires_in :
        return False
    return True

def get_refresh_token(api_access_point, redirect_url, client_id, client_secret, refresh_token):
    try:
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        url = 'https://' + api_access_point + '/oauth/v2/refresh'
        payload = "refresh_token=" + refresh_token + "&client_id=" + client_id + "&grant_type=refresh_token&client_secret=" + client_secret

        response = requests.post(url, headers=headers, data=payload, verify=False)
        response = json.loads(response.content.decode('utf-8'))
        access_token = response['access_token']
        return access_token
    except Exception as err:
        raise ValidationError(err)


class adobesign:
    def read_file(file_path):
        with open(file_path, 'rb') as f:
            content = base64.b64encode(f.read())
        return content


    def upload_document(api_access_point, file_path, access_token):
        base_url = "https://" + api_access_point + '/api/rest/v6' + '/transientDocuments'
        headers = {
            'Authorization': 'Bearer' + ' ' + access_token,
        }

        data = {
            'Mime-Type': 'application/pdf',
        }

        files = {'File': open(file_path, 'rb')}
        response = requests.post(base_url, headers=headers, data=data, files=files)
        return response.json().get('transientDocumentId')


    def send_agreement(api_access_point, access_token, transientDocumentId, recipient_email, file_name):
        base_url = "https://" + api_access_point + '/api/rest/v6' + '/agreements'
        headers = {
            'Authorization': 'Bearer' + ' ' + access_token,
            'Content-Type': 'application/json',
        }
        agreement_data = {

            "fileInfos": [{
                "transientDocumentId": transientDocumentId
            }],
            "name": file_name,
            "participantSetsInfo": [{
                "memberInfos": [{
                    "email": recipient_email
                }],
                "order": 1,
                "role": "SIGNER"
            }],
            "signatureType": "ESIGN",
            "state": "IN_PROCESS"
        }

        json_dumps = json.dumps(agreement_data)
        data = json.loads(json_dumps)
        response = requests.post(base_url, data=json_dumps, headers=headers)
        response_json = response.json()
        agreement_id = response_json['id']
        if agreement_id:
            return True, agreement_id
        return False, response_json.get('message')

    def send_agreement_multiple(api_access_point, access_token, transientDocumentId, recipient_email, file_name):
        base_url = "https://" + api_access_point + '/api/rest/v6' + '/agreements'
        headers = {
            'Authorization': 'Bearer' + ' ' + access_token,
            'Content-Type': 'application/json',
        }
        agreement_data = {

            "fileInfos": [{
                "transientDocumentId": transientDocumentId
            }],
            "name": file_name,
            "participantSetsInfo": [],
            "signatureType": "ESIGN",
            "state": "IN_PROCESS"
        }


        for recipient in recipient_email:
            agreement_data["participantSetsInfo"].append({
                "memberInfos" : [{
                    "name": recipient.name,
                    "email" : recipient.email
                }],
                "order" : 1,
                "role" : "SIGNER"
            })

        json_dumps = json.dumps(agreement_data)
        data = json.loads(json_dumps)
        response = requests.post(base_url, data=json_dumps, headers=headers)
        response_json = response.json()
        agreement_id = response_json['id']
        if agreement_id:
            return True, agreement_id
        return False, response_json.get('message')

    def get_file_path2(file, file_name):
        directory_path = os.path.join(root_path, "files")
        if not os.path.isdir(directory_path):
            os.mkdir(directory_path)
        path = os.path.join("files", file_name)
        complete_path = os.path.join(root_path, path)
        with open(complete_path, 'wb') as f:
            f.write(base64.b64decode(file))
        return complete_path



    #
    # def get_file_path(file):
    #     file_name = file.name
    #     file_data = file.sudo().read(['datas'])
    #     directory_path = os.path.join(root_path, "files")
    #     if not os.path.isdir(directory_path):
    #         os.mkdir(directory_path)
    #     path = os.path.join("files", file_name)
    #     complete_path = os.path.join(root_path, path)
    #     with open(complete_path, 'wb') as f:
    #         f.write(base64.b64decode(file.datas))
    #     return complete_path


    def get_agreement_events(api_access_point, access_token, agreement_id):
        base_url = "https://" + api_access_point + '/api/rest/v6' + '/agreements' + '/' + agreement_id + '/events'
        try:
            headers = {
                'Authorization': 'Bearer' + ' ' + access_token,
            }
            response = requests.get(base_url, headers=headers)

            if str(response.json().get('code')) == 'INVALID_ACCESS_TOKEN':
                raise UserError((response.json().get('message')))

            events = response.json().get('events')
            return events
        except Exception as err:
            return False

    def cancel_agreement(api_access_point, access_token, agreement_id):
        base_url = "https://" + api_access_point + '/api/rest/v6' + '/agreements' + '/' + agreement_id + '/state'
        headers = {
            'Content-Type' : 'application/json',
            'Authorization': 'Bearer' + ' ' + access_token,
        }

        payload = json.dumps({
            "state" : "CANCELLED",
            "agreementCancellationInfo" : {
                "comment" : "Cancelled by system.",
                "notifyOthers" : True
            }
        })
        # response = requests.put(base_url, data=json_dumps, headers=headers)
        response = requests.request("PUT", base_url, headers=headers, data=payload)
        print(response.status_code)
        print(response.content)
        if str(response.status_code) == '200' :
            return True
        return False


    def get_agreement_detail(api_access_point, access_token, agreement_id):
        base_url = "https://" + api_access_point + '/api/rest/v6' + '/agreements' + '/' + agreement_id
        try:
            headers = {
                'Authorization': 'Bearer' + ' ' + access_token,
            }
            response = requests.get(base_url, headers=headers)

            if str(response.json().get('code')) == 'INVALID_ACCESS_TOKEN':
                raise UserError((response.json().get('message')))

            status = response.json().get('status')
            name = response.json().get('name')
            return [status, name]
        except Exception as err:
            return False


    def download_agreement(api_access_point, access_token, agreement_id):
        base_url = "https://" + api_access_point + '/api/rest/v6' + '/agreements' + '/' + agreement_id + '/combinedDocument'
        headers = {
            'Authorization': 'Bearer' + ' ' + access_token,
        }
        response = requests.get(base_url, headers=headers)
        if str(response.status_code) == '200':
            return response.content
        return False


    def verify_token(access_token, redirect_url, expire_in, api_access_point, client_id, client_secret, refresh_token):
        is_valid = valid_token_time(expire_in)
        if not is_valid:
            new_access_token = get_refresh_token(api_access_point, redirect_url, client_id, client_secret, refresh_token)
            if new_access_token:
                return new_access_token
            else:
                return False
        return access_token

tools.adobesign = adobesign
