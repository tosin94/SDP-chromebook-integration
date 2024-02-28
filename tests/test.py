#from src.init import auth

# test = auth()
# #test.get_accessToken()
# #test.getRefreshToken()
# test.refresh_token() 

def hello(hi = 'no'):
    print('hello ' + hi)

switch = {
    "test": hello
}

switch.get('test')
val = switch.get('test')
val(hi='yes')

root = 'hello'
post = dict()
post[root] = {}
print(post)