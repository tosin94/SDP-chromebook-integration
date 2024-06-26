from src.auth.SDP_init import auth
import json, os,sys
from dotenv import load_dotenv
from urllib.error import HTTPError
from urllib.parse import urlencode, parse_qs
import src.SDP.SDP_API as SDP_API
import requests,time,re
import pandas as PD
from datetime import datetime

load_dotenv()

'''
    map asset module keys to chrome export keys
    key --> asset module 
    value --> chrome keys
    view device_schema for more info on chrome keys
'''

'''use recent_users as user data, annotated- prefix are custom fields'''

'''for the state information, can be set to In Store by default since we are only pulling active Cbs'''

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

    def upload(self,destination,chromeDeviceData,session,**extraArgs):

        endpoint = self.module.get(destination)[0]
        url = self.BASE_URL + endpoint

        ACCESS_HEADERS = self.HEADER
        
        data = self.buildData(destination,chromeDeviceData, session)
        for payload in data:
            try:
                payloadDict = json.loads(payload)
                if extraArgs["changeState"]:
                    # change the state to in use
                    payloadDict["workstation"]["state"] = { "name": extraArgs["state"] }
                    payloadDict["workstation"]["user"] = {"email_id": extraArgs["user"]}
                    payload = json.dumps(payloadDict)
            except Exception as err:
                print(err)
                print("continuing")

            assetTag = json.loads(payload)['workstation']['asset_tag']
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
                            print('Data already exists --> \n\n Data %s \n %s \n' %(response.text,assetTag))
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
            "memory": self.memory,
            "mac_address": self.normal
        }
        
        postData = dict()
        postData[root_key] = {}

        # TODO - add more fields to be imported, mirror with winodws data in SDP
        for device in chromedeviceData:
            # print(device['annotatedAssetId'])
            for key,value in self.keys.items():
                func = switch.get(key,'prod')
                # postData[root_key][key] = func(device[value], session)
                postData[root_key][key] = func(device.get(value, ''), session)

            recentUsers = device.get('recentUsers', '')
            if recentUsers != '':
                mostRecentUser = recentUsers[0].get('email','')
                if mostRecentUser != '':
                    mostRecentUser = mostRecentUser.split('@',1)[0]
                else:
                    mostRecentUser = 'NO_USER'
            else:
                mostRecentUser = 'NO_USER'
            # cpuInfo = device.get("cpuInfo",[''])[0]
            # if cpuInfo != '':
            #     cpu_model = cpuInfo.get("model",'')
            #     clock_speed = cpuInfo.get("maxClockSpeedKhz", '')
            #     cores = len(cpuInfo.get("logicalCpus",['']))

                # postData[root_key]['processors'] = [{"name" : cpu_model,"speed": clock_speed, "number_of_cores": cores}]
                
                
            postData[root_key]['operating_system'] = self.opSYS(device.get('platformVersion', ''),device.get('osVersion',''))
            postData[root_key]['last_logged_user'] = self.normal(mostRecentUser,session)
            
            with open('src/chrome/input_data.json', 'w') as inputData:
                inputData.write(json.dumps(postData))

            yield json.dumps(postData)

    def importSingleChromeAsset(self, asset, state, assigned_user):
        from src.google_admin.auth import GoogleAdmin
        service_account_file_path = os.getenv('creds')
        customer = os.getenv('customerId')
        delegate = os.getenv('delegated_admin')
        google = GoogleAdmin(service_account_file_path,customer,delegate)
        # deviceData = []

        response = google.getAsset(asset)
        assetDetails = response["response"]["chromeosdevices"]
        # deviceData.append(assetDetails)
        session = response["session"]
        
        self.upload("workstations",assetDetails,session,state=state, changeState = True, user=assigned_user)

        

    def updateAssets(self):
        from src.google_admin.auth import GoogleAdmin
        service_account_file_path = os.getenv('creds')
        customer = os.getenv('customerId')
        delegate = os.getenv('delegated_admin')

        filename = './IT_ASSET_DB.csv'
        path = './assetRes.json'
        endpoint = "workstations"
        url = self.BASE_URL + endpoint 
        session = requests.session()
            
        def getWorkstationData():

            # get and save asset data
            data = {
                "list_info": {
                    "row_count": 100,
                    "page" : 1,
                    "search_criteria" : {
                        "field": "operating_system.os",
                        "condition": "not contains",
                        "values": ["windows", "Windows","mac","macos"]
                    },
                    "fields_required": ["id","name"]
                
                }
            }
            inputData = '''{}'''.format(data)
            inputData = urlencode({"input_data": inputData})

            try:
                request = requests.Request(
                    url= url,
                    headers=self.HEADER,
                    method='GET',
                    params=inputData
                )
                httpReq = session.prepare_request(request)
                has_rows = True
                request_count = 0

                with open(path, 'w') as asset_f:
                    asset_f.write('{ "assets": [')

                    while has_rows:
                        if request_count >= 100:
                            print("wait for 60seconds before continuing")
                            time.sleep(60)
                            request_count = 0
                        
                        httpResponse = session.send(httpReq).text
                        httpResponse = json.loads(httpResponse)

                        if isinstance(httpResponse.get('response_status',''), list):
                            status = httpResponse["response_status"][0]["status"]
                        else:
                            status = httpResponse["response_status"]["status"]

                        if status == "failed":
                            # if httpResponse['response_status'][0]['status_code'] != 2000:
                            raise requests.HTTPError(request=httpReq, response=httpResponse)
                        
                        has_rows = httpResponse["list_info"]['has_more_rows']
                        for rows in httpResponse["workstations"]:
                            id = rows["id"]
                            name = rows["name"]
                            writeData = '{{"{}" : "{}"}}'.format(id,name) + ','
                            asset_f.write(writeData )

                        if not has_rows:
                            asset_f.seek(0,2)
                            end = asset_f.tell()
                            asset_f.seek(end - 1)
                            asset_f.truncate()
                            asset_f.write(']}')

                        data["list_info"]["page"] += 1
                        
                        inputData = '''{}'''.format(data)
                        inputData = urlencode({"input_data": inputData})
                        request.params = inputData
                        httpReq = session.prepare_request(request)
                        request_count+=1
                        

            except requests.HTTPError as httpE:
                # TODO - log http error to for or elsewhere
                print(httpE)
                exit()

        def buildAndSendUpdateData():
            getWorkstationData()
            print('Collected workstation data...\n Now Sleeping for 60 seconds before carryng on')
            time.sleep(60) #just in case we are sending too many requests
            def toTimestamp(date_):
                if date_ != '':
                    date_ = int(datetime.strptime(date_, '%Y-%m-%dT%H:%M:%S.%f%z').timestamp()*1000)
                else:
                    return ''
                return date_
            
            try:
                google = GoogleAdmin(service_account_file_path,customer,delegate)

                with open(path, 'r') as assetsFile:
                    assets = json.load(assetsFile)
                    arr = assets['assets']
                    count = 0
                    for row in arr:
                        key = list(row.keys())[0]
                        asset = row.get(key)
                        try:
                            # get chromedata from google
                            response,session = google.getAsset(asset).values()
                            device = response.get("chromeosdevices",[''])[0]
                            if(device == ''):
                                # TODO log response 
                                print(f"\nskipped {asset}\n")
                                continue

                            os,version = device.get('platformVersion', ''),device.get('osVersion','')
                            recent_activity = toTimestamp(device.get("lastSync",''))
                            last_logged_user = device.get("recentUsers",[{"email": ''}])[0].get('email','')
                            enrollmentTime = toTimestamp(device.get("firstEnrollmentTime", ''))
                            lastReboot = toTimestamp(device.get("osUpdateStatus", {}).get("rebootTime", ''))
                            updateStatus = device.get("osUpdateStatus", {}).get("state", '')
                            updatesUntil = device.get("autoUpdateExpiration", '0') # comes as a timestamp
                            assetType = (lambda device: "Flex" if "FLEX" in device.get("orgUnitPath", '').upper() else "Chromebook")(device)

                            data = { "workstation":
                                    {
                                        "operating_system":{
                                            "os": os,
                                            "version":version
                                        },
                                        "workstation_udf_fields":{
                                            "udf_date1": {"value": recent_activity}, # recent activity
                                            "udf_char1": assetType, # asset type
                                            "udf_date2" : {"value": updatesUntil},
                                            "udf_date3" : {"value" : enrollmentTime}, # enrollment time
                                            "udf_date4" : {"value" :lastReboot}, # last reboot
                                            "udf_char2" : updateStatus, 
                                        },
                                        "last_logged_user": last_logged_user,

                                    }
                                }
                            data = '''{}'''.format(data)
                            input_data = urlencode({"input_data": data}).encode()

                            try:
                                url = self.BASE_URL + endpoint + f'/{key}'

                                request = requests.Request(
                                    url=url,
                                    headers=self.HEADER,
                                    method='PUT',
                                    data=input_data
                                )
                                httpReq = session.prepare_request(request)
                                httpResponse = session.send(httpReq)
                                response = json.loads(httpResponse.text)

                                status = response["response_status"]["status"]

                                if status == "failed":
                                    print(f"{asset} ==> {response}")
                                    # TODO - log response, remove pass
                                    pass
                                   

                                elif status == "success":
                                    # print(response)
                                    pass

                                count += 1
                                if count >= 100:
                                    print("waiting 60 seconds")
                                    time.sleep(60)
                                    count = 0

                            # TODO - log all these errors and stop script execution only where necessary
                            
                            except requests.HTTPError as err:
                                raise err
                            
                            except Exception as err:
                                # log the response
                                session.close()
                                raise err
                            


                        except Exception as err:
                            raise err

            except Exception as err:
                raise err
    
        buildAndSendUpdateData()

        def buildEditdData():

            try:

                data = PD.read_csv(filename)
                data.set_index('Asset tag', inplace=True)

                with open(path, 'r') as assetsFile:
                    assets = json.load(assetsFile)
                    arr = assets['assets']
                    count = 0
                    for row in arr:
                        key = list(row.keys())[0]
                        asset = row.get(key)
                        try:
                            
                            assetData = data.loc[asset]
                            expiry = assetData.get('End of Life Date', '')
                            user = assetData.get('Current User Name')
                            warranty = assetData.get('Warranty End', '')
                            model = assetData.get('Model', '')

                            rtn = sendDataCSV(key,expiry,user,warranty,asset,model,count) 
                            if rtn != None:                          
                                count = rtn
                            # print(assetData.get('DEVICE type'))
                            # print(assetData['Model'])
                            # print(f'{assetData[3]} ==> {assetData[0]}')
                        except KeyError as err:
                            pass

            except Exception as err:
                raise err

        # construct data to send to manage engine
        
        def sendDataCSV(id,expiry,user,warranty,tfno,model,count) -> int:
            
            url = self.BASE_URL + endpoint + f'/{id}'

            # do some conversion
            def convert_d(date_):
                if not isinstance(date_, str):
                    return ''
                if date_ == '':
                    return ''
                val = re.search(r"\d{2}/\d{2}/\d{4}",date_)
                if val:
                    res = val.group()
                    res = datetime.strptime(res, '%d/%m/%Y')
                    milliseonds = res.timestamp()*1000 #convert to millisecond
                    return int(milliseonds)
                else:
                    return ''
            
            def convert_u(user):
                if not isinstance(user, str):
                    return '' #change to default user
                domain = '@' + os.getenv('domain')
                # transform user START
                user = user.replace('`','')
                user = user.replace("'",'')
                user = user.replace('(Stock)','')
                user = user.replace('(stock)', '')
                user = user.replace('(Pool)','')
                user = user.replace('(pool)', '')
                user = user.replace('(Pool Chromebook)', '')
                user = user.replace('(pool chromebook)', '')
                user = user.strip()
                if len(user.split(' ',-1)) > 2:
                    # too many spaces -- add info into error file
                    return ''
                check = [ '(', ')', 'chromebook'.upper(),'laptop'.upper(),'kenya pool'.upper(),'new staff'.upper(),'Toberecruited'.upper(),'print room'.upper() ]
                for string in check:
                    if string in user.upper():
                        return ''
                # TRANSFORM END
                
                if "@" in user:
                    pass
            
                elif "." in user:
                    user += domain


                elif " " in user:
                    user = user.replace(" ", ".")
                    user += domain

                else:
                    # in case other conditions are missed
                    user = ''
                
                return user.lower()       
            
            expiry = convert_d(expiry)
            warranty = convert_d(warranty)
            initial_user = user
            user = convert_u(user)

            if user == '':
                if isinstance(initial_user, str):
                    entry = f'could not parse for user --> {initial_user}\nTF NO {tfno}\n\n'
                    with open('./logs/asset.log', 'a') as log:
                        log.write(entry)
                # no user to send to manageengine
                return
           
            data = { "workstation":
                    {
                        "state": {
                            "name": "In Use"
                        },
                        "warranty_expiry": {
                            "value": warranty
                        },
                        "user" : {
                            "email_id": user
                        },
                        "expiry_date" : {
                            "value": expiry
                        }
                    }
            }
            data = '''{}'''.format(data)
            input_data = urlencode({"input_data": data}).encode()

            try:

                request = requests.Request(
                    url=url,
                    headers=self.HEADER,
                    method='PUT',
                    data=input_data
                )
                httpReq = session.prepare_request(request)
                httpResponse = session.send(httpReq)
                response = json.loads(httpResponse.text)

                status = response["response_status"]["status"]

                if status == "failed":
                    with open("./logs/error.log", 'a') as err_log:
                        err_log.write(f'{str(response)}\n{parse_qs(input_data.decode())}\n{str(url)}\nTF Number => {tfno} User =>{user}\n\n')
                        # if expiry != '':
                        #     expiry = datetime.fromtimestamp((expiry/1000)).strftime("%Y-%m-%d")
                        # if warranty != '':
                        #     warranty = datetime.fromtimestamp((warranty/1000)).strftime("%Y-%m-%d")
                        # err_log.write(f'{tfno},{model},{"In Use"},{user},{expiry},{warranty}\n')

                elif status == "success":
                    with open("./logs/success.log", 'a') as succ:
                        succ.write(f'{user} <==> {id}\n{parse_qs(input_data.decode())}\n{str(url)}\n\n')

                count += 1
                if count >= 100:
                    print("waiting 60 seconds")
                    time.sleep(60)
                    count = 0

                return count

            except requests.HTTPError as err:
                raise err
            
            except Exception as err:
                session.close()
                raise err

if __name__ == "__main__":
    assets = SDPAssets()
    assets.updateAssets()