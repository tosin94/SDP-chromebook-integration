from google.oauth2 import service_account
from googleapiclient.discovery import build
from src.SDP.assets import SDPAssets
from dotenv import load_dotenv
import os
import src.SDP.SDP_API as SDP_API
import requests,time,json
# from urllib.parse import quote_plus, quote

load_dotenv()

class GoogleAdmin:
    '''
        Doc for googleapiclient
        https://github.com/googleapis/google-api-python-client/blob/main/docs/README.md
        TODO - change workflow where this module only returns data
        TODO - try/catch to process and log errors on all netwrok requests
        TODO - pull all the data first into a DB and then process into SDP
    '''
    def __init__(self, service_account_file, customerId, delegate):
        self.SCOPES = [
            'https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly',
            'https://www.googleapis.com/auth/admin.directory.user.readonly'
            ]
        self.delegate = delegate
        self.credentials = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=self.SCOPES, subject=self.delegate )
        self.service = build('admin', 'directory_v1', credentials=self.credentials)
        self.customer = customerId

    def list_all_chrome_os_devices(self):
        SDP = SDPAssets()
        page_token = None
        session = requests.Session()
        urlQuery = 'status:provisioned'
        request_no = 0

        while True:
            
            # Retrieve a page of Chrome OS devices
            response = self.service.chromeosdevices().list(
                customerId=self.customer,
                maxResults=100,  # Adjust the number of results per page as needed
                pageToken=page_token,
                query = urlQuery
               
            ).execute()

            # Process the devices on the current page
            devices = response.get('chromeosdevices', [])
            if request_no >= 100:
                print('Pausing execution for 60 seconds') #so execution does not stop due to too many requests
                time.sleep(60)
                print('Resuming execution...')
            
            SDP.upload("workstations",devices,session)
            
            # for device in devices:
            #     print(f"Device ID: {device['deviceId']}, Serial Number: {device['serialNumber']}, Model: {device['model']}")

            # Check for pagination
            page_token = response.get('nextPageToken')
            request_no += 100
            if not page_token:
                break
    

    def list_all_users(self):
        page_token = None
        sdp_u = SDP_API
        request_no = 0

        session = requests.Session()

        while True:
            # Retrieve a page of users
            response = self.service.users().list(
                customer=self.customer,
                maxResults=100,  # Adjust the number of results per page as needed
                pageToken=page_token,
                viewType="admin_view",
            ).execute()

            # Process the users on the current page
            users = response.get('users', [])
            if request_no >= 100:
                print('Pausing execution for 60 seconds') #so execution does not stop due to too many requests
                time.sleep(60)
                print('Resuming execution...')

            # sdp_u.uploadUsers(users, session)
            for user in users:
                # print(f"User ID: {user['id']}, Email: {user['primaryEmail']}")
                sdp_u.uploadUser(user,session)
                
                # print(json.dumps(user))

            # Check for pagination
            page_token = response.get('nextPageToken')
            request_no += 100
            if not page_token:
                break
        session.close()
        
    def getUser(self, user)-> str:
        sdp_u = SDP_API
        session = requests.Session()

        response = self.service.users().get(
            userKey= user,
            projection = 'full',
            viewType="admin_view"
        ).execute()

        sdp_u.uploadUser(response,session)
        # Process the users on the current page
        # print(json.dumps(response))
        # return json.dumps(response)
    
        
    def getAsset(self, asset)-> str:
        session = requests.Session()
        urlQuery = f'status:provisioned asset_id:{asset}'

        response = self.service.chromeosdevices().list(
                customerId=self.customer,
                maxResults=1,  # Adjust the number of results per page as needed
                query = urlQuery
               
            ).execute()
        return {"response": response , "session": session}
        # print(json.dumps(response))






def testCloudIdentity(service_account_file, customerId, delegate):
        SCOPES = ["https://www.googleapis.com/auth/cloud-identity.devices.readonly"]
        delegate = delegate
        credentials = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES, subject=delegate )
        service = build('cloudidentity', 'v1', credentials=credentials)
        customer = customerId

        response = service.devices().list(
        ).execute()

        print(response)

if __name__ == '__main__':
    # Set the necessary parameters
    service_account_file_path = os.getenv('creds')
    customer = os.getenv('customerId')
    delegate = os.getenv('delegated_admin')

    # Create an instance of the GoogleAdmin class
    # method = GoogleAdmin(service_account_file_path, customer, delegate)

    # List all Chrome OS devices
    # method.list_all_chrome_os_devices()
    # method.list_all_users()
    # testCloudIdentity(service_account_file_path,customer,delegate)