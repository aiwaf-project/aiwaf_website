"""Run against a fresh tutorial server on port 5000."""

from urllib.error import HTTPError
from urllib.request import urlopen

for number in range(1, 5):
    try:
        with urlopen("http://127.0.0.1:5000/api/message") as response:
            print(number, response.status, response.read().decode().strip())
    except HTTPError as response:
        print(number, response.code, response.read().decode().strip())

with urlopen("http://127.0.0.1:5000/health") as response:
    print("health", response.status, response.read().decode().strip())
