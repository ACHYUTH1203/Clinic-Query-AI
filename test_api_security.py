import requests
import time

URL = "http://127.0.0.1:8000/chat"

print("--- 1. TESTING INPUT VALIDATION ---")

response_short = requests.post(URL, json={"question": "hi"})
print(f"Sent 'hi' -> Status: {response_short.status_code}")
print(f"Response: {response_short.text}\n")


response_space = requests.post(URL, json={"question": "     "})
print(f"Sent spaces -> Status: {response_space.status_code}")
print(f"Response: {response_space.text}\n")



print("Sending 6 valid requests rapidly to trigger the 5/minute limit...")

for i in range(1, 7):
    response = requests.post(URL, json={"question": f"How many patients do we have? attempt {i}"})
    if response.status_code == 200:
        print(f"Request {i}:  Success (200)")
    elif response.status_code == 429:
        print(f"Request {i}:  BLOCKED! Rate Limit Hit (429)")
        print(f"Error Message: {response.text}")
    else:
        print(f"Request {i}: Unexpected Status {response.status_code}")