from src.auth.SDP_init import auth
import json, os
from dotenv import load_dotenv
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen,Request
import src.SDP.SDP_API as SDP_API
import requests

load_dotenv()

'''
    map asset module keys to chrome export keys
    key --> asset module 
    value --> chrome keys
    view device_schema for more info on chrome keys
'''

'''use recent_users as user data, annotated- prefix are custom fields'''

'''for the state information, can be set to In use by default since we are only pulling active Cbs'''

'''
    be wary of keys that might not be there, may need default values
    "state_history_comments": "notes",
    "warranty_expiry": "supportEndDate",
'''

class SDPAssets:

    keys = {
        "name": "annotatedAssetId",
        "asset_tag": "annotatedAssetId",
        "location": "annotatedLocation",
        "state": "status",
        "serial_number": "serialNumber",
        "product" : "model",
        "memory": "systemRamTotal",

    }

    HEADER = {}

    ''' Where array is [endpoint,root_key] '''
    module = {
        "assets" : ["assets", "asset"],
        "workstations" : ["workstations", "workstation"]
    }
    
    BASE_URL = 'https://servicedeskplus.uk/api/v3/'

    def __init__(self) -> None:
            Auth = auth()
            self.HEADER = Auth.getSDPHeader()
            self.SDP_RES = os.getenv('SDP_RES')

    def nameId(self,value, session):
        return {
            "name" : value
        }
    def department(self,value, session):
        return {
            "name": "test-department"
        }
    def state(self,value, session):
        return {
            "name" : "In Store"
        }

    def normal(self,value, session):
        return value
    
    def memory(self,value, session):
        return{
            "physical_memory": value
        }
    
    def prod(self,value, session):
        value = "NO MODEL" if value == '' else SDP_API.checkProduct(value, session)
        return {
            # "name": "test-chromebook"
            "name": value
        }
    def opSYS(self,platform, osV):
        return{
            "os": platform,
            "version": osV
        }

    def upload(self,destination,chromeDeviceData,session):

        endpoint = self.module.get(destination)[0]
        url = self.BASE_URL + endpoint

        ACCESS_HEADERS = self.HEADER
        
        data = self.buildData(destination,chromeDeviceData, session)
        for payload in data:
            # print(payload)
            postData = urlencode({"input_data": payload}).encode()
            httpReq = requests.Request(url=url,data=postData,headers=ACCESS_HEADERS,method='POST')
            httpReq = session.prepare_request(httpReq)

            try:
                with open(self.SDP_RES, 'w') as sdp:
                    response = session.send(httpReq)
                    resText = json.loads(response.text)

                    if response.status_code not in [200,201,2000]:
                        sdp.write(json.dumps(json.loads(response.text)))

                        '''
                            this key is only available on a bad request but doesn't mean code execution should end
                            if operation tried to upload non-unique data... (check and skip)
                        '''
                        if resText["response_status"]["messages"][0]["status_code"] == 4008:
                            print('Data already exists --> \n\n Data %s \n %s \n' %(response.text,payload))
                            # TODO - log the input data, and email IT support
                            # TODO - code to alert IT on potential duplicate that has been skipped
                            # could do so by sending a ticket to IT support with the log file for duplicates
                            continue
                        raise requests.HTTPError(response)                  
                    
                    sdp.write(json.dumps(json.loads(response.text)))

            except requests.HTTPError as httpE:
                session.close()
                raise Exception('Response {} Error: {} Input Data: {}'.format(response.text,httpE,payload))
            
            except Exception as err:
                session.close()
                raise Exception(err)


    def buildData(self, destination, chromedeviceData, session):

        root_key = self.module.get(destination)[1]

        switch ={
            "name": self.normal,
            "state": self.state,
            "product": self.prod,
            "department": self.department,
            "asset_tag": self.normal,
            "location" : self.normal,
            "serial_number": self.normal,
            "model" : self.prod,
            "memory": self.memory
        }
        
        postData = dict()
        postData[root_key] = {}

        for device in chromedeviceData:
            print(device['annotatedAssetId'])
            for key,value in self.keys.items():
                func = switch.get(key,'prod')
                # postData[root_key][key] = func(device[value], session)
                postData[root_key][key] = func(device.get(value, ''), session)

            mostRecentUser = device.get('recentUsers', '')
            mostRecentUser = (mostRecentUser[0]['email']).split('@',1)[0] if mostRecentUser != '' else 'NO_USER'

            
            postData[root_key]['operating_system'] = self.opSYS(device.get('platformVersion', ''),device.get('osVersion',''))
            postData[root_key]['last_logged_user'] = self.normal(mostRecentUser,session)
            
            with open('src/chrome/input_data.json', 'w') as inputData:
                inputData.write(json.dumps(postData))

            yield json.dumps(postData)
