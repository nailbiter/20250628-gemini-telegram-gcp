## how to call Cloud Run with shell

```sh
curl -X POST "<URL for internal Cloud Run>" -H "Authorization: bearer $(gcloud auth print-identity-token)" -H "Content-Type: application/json" -d '{  "name": "Developer",  "message":{"text":"hi, how are you?"} }'
```
