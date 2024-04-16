import json
from src.auth.SDP_init import auth
from urllib.error import HTTPError
from urllib.parse import parse_qs

import requests

class SDP:

    def __init__(self) -> None:
        self.HEADER = auth().getSDPHeader()
        self.URL = 'https://servicedeskplus.uk/api/v3/'
        

    '''
    Encode your payload/data (if needed) before sending to this function
    Meethod will be POST or GET
    '''
    def sendRequest(self, data, method, endpoint,session, id = ''):

        endpoint = self.URL + endpoint

        # Default Request is get
        request = {
            "POST": requests.Request(url= endpoint,data=data, headers=self.HEADER,method='POST'),
            # "GET" : requests.Request(url=endpoint +'?{}'.format(data), headers=self.HEADER, method='GET'),
            "GET" : requests.Request(url=endpoint, headers=self.HEADER, method='GET',params=data),
            "NO_QUERY_PARAMS": requests.Request(url = endpoint + '/{}'.format(data), headers=self.HEADER, method='GET' ),
            "PUT": requests.Request(url= endpoint + '/{}'.format(id),data=data, headers=self.HEADER,method='PUT'),
        }
        httpRequest = request.get(method)
        httpRequest = session.prepare_request(httpRequest)

        try:
            # expecting to receive JSON so .text is prefered over .content 
            # TODO change where data is saved or whether to save data
            with open('src/SDP/product.json', 'w') as file:
                res = session.send(httpRequest).text
                file.write(res)
                tmp = json.loads(res)
                try:
                    if isinstance(tmp.get('response_status',''), list) :
                        status = tmp['response_status'][0]['status']
                        status_code = tmp['response_status'][0]['status_code']
                    else:
                        status = tmp["response_status"]['status']
                        #since manage engine simply don't have consistency...
                        if 'messages' in tmp['response_status']:
                            status_code = tmp["response_status"]["messages"][0]["status_code"]
                        else:
                            status_code = tmp["response_status"]["status_code"]

                    if status == 'failed':
                        if status_code != 4008:
                            raise requests.HTTPError(response=tmp['response_status'],request=httpRequest)
                        elif status_code == 4008:
                            return None
                        
                except requests.HTTPError as httpE:
                    #TODO log the error
                    # users api does not send a unique code for duplicate emails
                    if "requesters" in endpoint:
                        print(f"{httpE.response}\n{parse_qs(httpRequest.body.decode())}\n")
                        return
                    # any other error, raise it
                    session.close()
                    print(httpE)
                    exit(1)

            return json.loads(res)
        
        except HTTPError as e:
            session.close()
            # error = json.loads(e.read().decode())
            raise Exception(e)
        

    def getHeaders(self):
        return self.HEADER

if __name__ == '__main__':
    assets = SDP()
    product = {
        "product" : {
            "is_laptop": False,
            "product_type": {
            "name" : "Workstation"
        },
            "name" : "test-product"
        }
        
    }
    inputData = '''{}'''.format(product)
    # print(assets.sendRequest(urlencode(inputData))