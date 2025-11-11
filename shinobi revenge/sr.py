import requests
from pyamf import remoting, AMF3

AMF_URL = "https://amf.playshinobirevenge.com/"
APP_VERSION = "Public 0.18"
HASH_TOKEN = "7da52582be60n558k1bece2c31ce48e48e7b2bf0b85320a15e964430b8fccad8c1e198d04ecea6327eed68b68f797f97f245451af1416d7c97692034defdabfed054d495e4c0c69cceebd8a6d2196a48c99183649b1e33c6c4d6215c8d1544bd15652270c53428be2525d2e3efb5020afddcc71b428d73261ccd6ecbe05d3ae10f7eb07ebbf4728706b1af7bd93d6f6e9ae798bc3170cb09c10233550a8a31395c01d9be7269b7645f3409f5ab2f985cd84ceadda3166059df52367604426210eea88c20bfeeef5526e53efd5a8c2a8c"

S = requests.Session()
S.headers.update({
    "Referer": "app:/Shinobirevenge.swf",
    "Accept": "text/xml, application/xml, application/xhtml+xml, text/html;q=0.9, text/plain;q=0.8, text/css, image/png, image/jpeg, image/gif;q=0.8, application/x-shockwave-flash, video/mp4;q=0.9, flv-application/octet-stream;q=0.8, video/x-flv;q=0.7, audio/mp4, application/futuresplash, */*;q=0.5, application/x-mpegURL",
    "x-flash-version": "50,2,2,3",
    "Content-Type": "application/x-amf",
    "Accept-Encoding": "gzip,deflate",
    "User-Agent": "Mozilla/5.0 (Windows; U; en) AppleWebKit/533.19.4 (KHTML, like Gecko) AdobeAIR/50.2",
    "Host": "amf.playshinobirevenge.com",
    "Connection": "Keep-Alive",
})

def amf_request(target, params):
    env = remoting.Envelope(amfVersion=AMF3)
    env["/1"] = remoting.Request(target, [params])
    data = remoting.encode(env).getvalue()
    res = S.post(AMF_URL, data=data, timeout=30)
    res.raise_for_status()
    body = remoting.decode(res.content).bodies[0][1].body
    return body[0] if isinstance(body, list) and len(body) == 1 else body

def main():
    print("=== Shinobi Revenge Panel By Xtra ===")
    u = input("Username: ").strip()
    p = input("Password: ").strip()
    if not p:
        return print("Password cannot be empty!")

    amf_request("SystemLogin.checkVersion", [APP_VERSION])
    login = amf_request("SystemLogin.loginUser", [u, p])
    uid, sk = login["uid"], login["sessionkey"]
    print("Login OK!")

    amf_request("AC.verifyFiles", [sk, HASH_TOKEN])
    amf_request("FilesManager.checkClearCache", [uid])

    chars = amf_request("SystemLogin.getAllCharacters", [uid, sk]).get("account_data", [])
    if not chars:
        return print("No characters found.")

    for i, c in enumerate(chars, 1):
        print(f"[{i}] {c['character_name']} (Lv {c['character_level']}) id={c['char_id']}")
    cid = chars[int(input("Select: ")) - 1]["char_id"]

    data = amf_request("SystemLogin.getCharacterData", [cid, sk])
    print(f"Selected: {data['character_data']['character_name']} (Lv {data['character_data']['character_level']})")

if __name__ == "__main__":
    main()
