import requests

def wxpusher_send(message):
    url = "http://wxpusher.zjiecode.com/api/send/message"
    headers = {'Content-Type': 'application/json'}
    data = {
        "appToken": "your_app_token",  # 替换为APP_TOKEN
        "content": message,
        "contentType": 1,
        "uids": ["your_uid"]           # 替换为微信UID
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()
