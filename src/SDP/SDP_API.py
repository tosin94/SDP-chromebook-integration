from src.SDP.base import SDP
from urllib.parse import urlencode

# TODO temp delete later 
import requests
# //////////////////

'''
    0 -> POST, 1 --> GET, 2 --> NO_QUER_PARAMS
'''
method = ["POST","GET","NO_QUERY_PARAMS"]


'''
    list products that are in the name field of the request, e.g list all Dell XPS 13's only
'''
def getProductSearchCriteria(value) -> str:
   
    data = {
        "list_info": {
            "row_count": 100,
            "search_criteria": {
                "field" : "name",
                "condition" : "is",
                "value" : value
            }
        }
    }
    inputData = '''{}'''.format(data)
    data = urlencode({"input_data": inputData})

    return data

'''
    check if product exists, if not, create a new one
'''
def checkProduct(product, session) -> str:
    model = product.split('.', 1)
    if len(model) > 1:
        criteria = model[1]
        criteria = criteria.lstrip(' ')
    else:
        criteria = model[0]

    inputData = getProductSearchCriteria(criteria)
    response = SDP().sendRequest(inputData, method[1],'products',session)
    
    if response['list_info']['row_count'] > 0  :
        return criteria
    else:
        model = createProduct(product, session)
        return model
        

def createProduct(product, session):
    try:
        manufacturer, model = product.split('.',1)
        model = model.lstrip(' ')
        if len(product.split('.')) < 2:
            manufacturer = ''
    except:
        # in the likely case that there is no '.'
        manufacturer, model = product.split(' ',1)
        model = model.lstrip(' ')
        if len(product.split(' ',1)) < 2:
            manufacturer = ''

    data = {
        "product" : {
            "is_laptop": "true",
            "product_type": {
                "name" : "Workstation"
            },
            "name" : model,
            "manufacturer" : manufacturer
        }
    }
    inputData = '''{}'''.format(data)
    data = urlencode({"input_data": inputData}).encode()

    # TODO add logging here to know initial request is coming from this section
    SDP().sendRequest(data, method[0],'products',session)
    return model

# /////////////////////////
# //////    USERS   ///////
# /////////////////////////

'''
    check user exists in SDP
'''
def checkUserById(user, session):
    response = SDP().sendRequest(user, method[2],'users', session)
    print(response)


'''
    check if a user exists using the email
'''
def checkuserByEmail(user,session):

    # NOTE -- the search parameters are different than normal, typical key is search_criteria
    # URL --> ui.servicedeskplus.com/APIDocs3/index.html
    data ={
        "list_info" : {
            "search_fields" : {
                "email_id" : user
            }
        }
    }
    inputData = '''{}'''.format(data)
    data = urlencode({"input_data": inputData})

    response = SDP().sendRequest(data,method[1],'users',session)

    if response['list_info']['row_count'] == 1:
        return True
    else:
        print('check user by email. {} does not exist in SDP'.format(user))
        return False
    

def uploadUser(user,session):
    
    endpoint = 'users'

    data = { "user":
            {
                "first_name" : user['name']['givenName'],
                "email_id": user['primaryEmail'],
                "is_technician" : "false",
                "last_name" : user['name']['familyName'],
                "name" : user['name']['fullName']
            }
    }# department info in users isn't always available

    checkString = '_email-Archive'
    if checkString in user.get('primaryEmail'):
        return
    
    if user.get('organizations', '') != '':
        data['user']['department'] = {"name":''}
        data['user']['department']['name'] = user["organizations"][0]['department']
        data['user']['jobtitle'] = user["organizations"][0]['title']

    inputData = '''{}'''.format(data)
    data = urlencode({"input_data": inputData}).encode()

    SDP().sendRequest(data,method[0],endpoint, session)

def uploadUsers(users,session):
    for user in users:
        uploadUser(user,session)

def getHeaders():
    return SDP().getHeaders()