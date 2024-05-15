from dotenv import load_dotenv
import argparse, os
from src.google_admin.auth import GoogleAdmin
from src.SDP.assets import SDPAssets


load_dotenv()

service_account_file_path = os.getenv('creds')
customer = os.getenv('customerId')
delegate = os.getenv('delegated_admin')

SDP_assets = SDPAssets()

 
'''
    TODO
    - Add asset_type as a default value for adding assets, also add to bulk importing (here and assets.py)
'''

ARGS = [
    '--importAssets', 
    '--assetTag',
    '--importUsers', 
    '--user', 
    '--updateUser', 
    '--updateUsers',
    '--state',
    '--assigned_user',
    '--updateAssets'
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

updateGroup = AssetParser.add_argument_group()

# assetGroup.add_argument(
#     ARGS[1],
#     help= 'e.g --assetTag TF005400',
#     default=None,
#     type=str
# )

'''
Argument group
'''
singleAssetGroup = AssetParser.add_argument_group(
    title='Import Single Asset',
    description= "Imports a single asset. e.g python start.py assets --assetTag <tfno> --state 'state' --assigned_user 'user@domain.com'"
    
    )
singleAssetGroup.add_argument(
        ARGS[1],
        type=str,
        help='e.g --assetTag TF005400',
    )
singleAssetGroup.add_argument(
    ARGS[6],
    help= 'e.g --state "In Store" || In Use . if state = in use, please provide user it is to be assigned to',
    default="In Store",
    type=str,
    choices=['In Store', 'In Use']
    
)
singleAssetGroup.add_argument(
    ARGS[7],
    help= "--assigned_user <user> e.g python start.py assets --importAssets --assetTag TFxxxxx --state in use --assigned_user user@domain.com",
    type=str
)

# updating all assets 
# updateAllGroup = AssetParser.add_argument_group(
#     title="Update all assets",
#     description="Updates all Chrome and flex assets currently held in SDP, will not add new devices"
# )

updateGroup.add_argument(
    ARGS[8],
    help="--updateAssets default value is True. Full example pyton start.py assets --updateAssets",
    default="true",
    choices=['true','false']
)


# assetGroup.add_argument(
#     ARGS[6],
#     help= "e.g --state In Store || In Use . if state = in use, please provide user it is to be assigned to",
#     default="in store",
#     type=str
# )
# assetGroup.add_argument(
#     ARGS[7],
#     help= "--assigned_user <user> e.g python start.py assets --importAssets --assetTag TFxxxxx --state in use --assigned_user user@domain.com",
#     default="None",
#     type=str
# )

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
sdp = GoogleAdmin(service_account_file_path,customer,delegate)

importAssets = args.get(KEYS[0], None)
assetTag = args.get(KEYS[1], None)
updateAssets = args.get(KEYS[8], None)

if importAssets and assetTag == None and updateAssets != "true":
    # import all assetss
    sdp.list_all_chrome_os_devices()
    exit()

elif assetTag != None:
    # import an asset
    state = args.get(KEYS[6], None)
    assigned_user = args.get(KEYS[7], None)

    if state.upper() == "in use".upper() and assigned_user == None:
        print("Please enter a value for assigned user. use python start.py assets --help for help")
        exit(1)
    else:
        SDP_assets.importSingleChromeAsset(assetTag,state,assigned_user)

elif updateAssets == 'true':
    SDP_assets.updateAssets()
        
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

