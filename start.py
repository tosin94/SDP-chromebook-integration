import argparse
import src.google_admin.auth as SDP
from dotenv import load_dotenv
import os

load_dotenv

service_account_file_path = os.getenv('creds')
customer = os.getenv('customerId')
delegate = os.getenv('delegated_admin')
sdp = SDP.GoogleAdmin(service_account_file_path,customer,delegate)


ARGS = [
    '--importAssets', 
    '--assetTag',
    '--importUsers', 
    '--user', 
    '--updateUser', 
    '--updateUsers'
    ]
KEYS = [(key.replace('--', '')) for key in ARGS]

parser = argparse.ArgumentParser(
        description= 'SDP API actions - import chrome devices, import users and update user information',
    )
sub_parser = parser.add_subparsers()

AssetParser = sub_parser.add_parser(
    name="assets",
    help=" Assets Helper"
    
)
assetGroup = AssetParser.add_mutually_exclusive_group()

assetGroup.add_argument(
    ARGS[0],
    help='import all assets, true or false. if you don\'t want to import all assets, you can skip this \
        arguement and specify the assettag to be imported',
    default="true",
    choices=['true', 'false']
)

assetGroup.add_argument(
    ARGS[1],
    help= 'e.g --assetTag TF005400',
    default=None,
    type=str
)

'''
    USER PARSER
'''

usersParser = sub_parser.add_parser(
    name="users",
    help="Users Helper"
)
userGroup = usersParser.add_mutually_exclusive_group()

userGroup.add_argument(
    ARGS[2],
    default="true",
    choices=['true', 'false'],
    help= 'e.g --importUsers true - also defaults to true',
)
userGroup.add_argument(
    ARGS[3],
    help= 'e.g --user test@email.com',
    default=None,
    type=str
)

args = vars(parser.parse_args())

'''
    process args

'''
importAssets = args.get(KEYS[0], None)
assetTag = args.get(KEYS[1], None)

if importAssets and assetTag == None:
    # import all assetss
    sdp.list_all_chrome_os_devices()
    exit()

elif importAssets and assetTag != None:
    # import an asset
    sdp.getAsset(assetTag)
    exit()

importUsers = args.get(KEYS[2], None)
user = args.get(KEYS[3], None)

if importUsers and user == None:
    # import all users
    sdp.list_all_users()
    exit()

elif importUsers and user != None:
    # import a user
    sdp.getUser(user)
    exit()

