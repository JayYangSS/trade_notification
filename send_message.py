import requests

APP_TOKEN = "AT_zAb5ylTsmXVGpTtUmdcNFAlkUZZW5Fa8"
UID = "UID_4BCMVhDdzLPqVg55NgAVnUkKPDO3"
def wxpusher_send(message):
    url = "http://wxpusher.zjiecode.com/api/send/message"
    headers = {'Content-Type': 'application/json'}
    data = {
        "appToken": APP_TOKEN,  # 替换为APP_TOKEN
        "content": message,
        "contentType": 1,
        "uids": [UID]           # 替换为微信UID
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()
