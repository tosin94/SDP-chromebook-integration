""" 
    authentication to service desk REST API - no need for a http server as self client is being used
    self client creates the initial grant token which can then be used to get the access and refresh tokens
    scopes in use:
        SDPOnDemand.assets.CREATE,SDPOnDemand.assets.READ,SDPOnDemand.setup.CREATE,SDPOnDemand.setup.READ,SDPOnDemand.users.READ,SDPOnDemand.users.CREATE,SDPOnDemand.assets.UPDATE
    
    grant token is created at https://api-console.zoho.uk/ under the manage-engine 
    admin account which has access to SDP and endpoint central

"""

import json, datetime, requests
from dotenv import load_dotenv
import os

load_dotenv()

class auth:
    #update - get sensitive auth details from the env file
    TOKEN_URL = ''
    #ensure the keys in the array are the same as that of the auth_info.json file
    auth_properties = ['Content-Type','code','grant_type','client_id','client_secret']
    AUTH_HEADERS = {}

    SDP_HEADER={
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept":"application/vnd.manageengine.v3+json",
        "Authorization" : ""
    }
    ACCESS_TOKEN = 'access_token'
    REFRESH = 'refresh_token'

    def __init__(self) -> None:
        self.oauth_path = os.getenv('oauth_path')
        with open(self.oauth_path, 'r') as auth_file:
            auth = json.load(auth_file)
            self.TOKEN_URL = auth['token_url']
            for prop in self.auth_properties:
                self.AUTH_HEADERS[prop] = auth[prop]
        self.tokenPath = os.getenv('token')
        
            
   
    
    def generate_accessToken(self):
        response = requests.post(self.TOKEN_URL, self.AUTH_HEADERS,verify=True)
        with open(self.tokenPath, 'w') as token:
            data = json.loads(response.text)
            data['token_time'] = str(datetime.datetime.now())
            data = json.dumps(data)
            token.write(data)
            
    def get_accessToken(self):
        self.checkToken()
        with open(self.tokenPath, 'r') as token:
            access_token = json.load(token)[self.ACCESS_TOKEN]
        
        return access_token


    def refresh_token(self):
        print('refreshing the token')
        refresh_token = self.getRefreshToken()
        headers = {
            "Content-Type": "application/x-www-form-url-encoded",
            "refresh_token": refresh_token,
            "grant_type": 'refresh_token',
            "client_id": self.AUTH_HEADERS['client_id'],
            "client_secret": self.AUTH_HEADERS['client_secret']
        }
        response = requests.post(self.TOKEN_URL,data=headers,verify=True)
        token = json.loads(response.text)[self.ACCESS_TOKEN] #new access token

        with open(self.tokenPath, 'r') as refresh:
            data = json.load(refresh)
        with open(self.tokenPath, 'w') as refresh:
            data[self.ACCESS_TOKEN] = token
            data['token_time'] = str(datetime.datetime.now())
            data = json.dumps(data)
            refresh.write(data)
    
    def getRefreshToken(self):
        with open(self.tokenPath,'r') as token:
            data = json.load(token)[self.REFRESH]
            return data
    
    def checkToken(self)-> bool:
        with open('src/auth/token.json', 'r') as token:
            oldTime = json.load(token)['token_time']
            oldTime = datetime.datetime.strptime(oldTime,'%Y-%m-%d %H:%M:%S.%f')
            timeNow = datetime.datetime.now()

        if oldTime.day == timeNow.day:
            if int(timeNow.timestamp() - oldTime.timestamp()) <= 3500:
                return True
            else:
                self.refresh_token()
                return False
        else:
            print('token has expired.. refreshing the token')
            self.refresh_token()
            return False
            
    def getSDPHeader(self):
        self.checkToken() #check and update the token if necessary
        with open(self.tokenPath,'r') as token:
            output = json.load(token) #dict

        auth_token = output[self.ACCESS_TOKEN]
        self.SDP_HEADER['Authorization'] = 'Zoho-oauthtoken ' + auth_token
        return self.SDP_HEADER
    
if __name__ == '__main__':
    start = auth()
    start.generate_accessToken()
    # print(start.getSDPHeader())