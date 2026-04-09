import curl_cffi

s = curl_cffi.Session()

url = 'https://dev.to/lifeportal20002010/mastering-uv-in-vs-code-the-ultra-fast-python-setup-guide-2n56'

r = s.get(url, impersonate='chrome')

print(r.text)