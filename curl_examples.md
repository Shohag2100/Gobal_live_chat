# Real-Time Empire — curl examples

Replace HOST with your server host (e.g. `http://127.0.0.1:8000` or `http://10.10.7.51:8001`). Use the same host for the WebSocket connection.

## Register
```bash
curl -i -X POST "{{HOST}}/chat/api/register/" \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","username":"alice","full_name":"Alice Example","password":"secret","confirm_password":"secret"}' \
  -c cookiejar.txt
```

## Login (stores session cookie in `cookiejar.txt`)
```bash
curl -i -X POST "{{HOST}}/chat/api/login/" \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"secret"}' \
  -c cookiejar.txt -b cookiejar.txt
```

## Get current user (authenticated)
```bash
curl -i -X GET "{{HOST}}/chat/api/me/" -b cookiejar.txt
```

## Get CSRF token
```bash
curl -i -X GET "{{HOST}}/chat/api/csrf/" -b cookiejar.txt
```

## Logout
```bash
curl -i -X POST "{{HOST}}/chat/api/logout/" -b cookiejar.txt
```

## Upload image (authenticated)
```bash
curl -i -X POST "{{HOST}}/chat/api/upload_image/" \
  -H "Accept: application/json" \
  -F "image=@/path/to/photo.jpg" \
  -b cookiejar.txt -c cookiejar.txt
```

## Remove user (admin)
```bash
curl -i -X POST "{{HOST}}/chat/api/remove_user/" \
  -H "Content-Type: application/json" \
  -d '{"username":"targetuser"}' \
  -b cookiejar.txt
```

## Fetch private messages between authenticated user and `other`
```bash
curl -i -X GET "{{HOST}}/chat/api/private_messages/?username=other" -b cookiejar.txt
```

## WebSocket (wscat) — connect with session cookie
- After login, copy the `sessionid` cookie from `cookiejar.txt` and use it with wscat. Example (replace value):

```bash
# connect using wscat and send a global message
wscat -c "ws://127.0.0.1:8000/ws/chat/" -H "Cookie: sessionid=YOUR_SESSIONID"
> {"message": "Hello everyone"}

# join a private group (server will deliver private messages in that group)
> {"action":"join_private","to":"other"}

# send private message
> {"action":"private_message","to":"other","message":"Hi privately"}
```

If you don't have `wscat`, install with `npm i -g wscat` or use `websocat` (Linux).

---

If you want, I can also:
- Add Postman environment for `{{host}}` and include example tests in the collection.
- Export a ready-to-import Postman collection file that includes pre-request scripts to parse cookies (Postman can manage cookies automatically once you login in the GUI).

Tell me which option you prefer and I will add it.