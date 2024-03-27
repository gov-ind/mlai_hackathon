import requests

def fetch_example_com():
    # Sending a GET request to example.com
    try:
        response = requests.get('http://example.com')
    except requests.exceptions.RequestException as e:
        # If the request fails, we return False
        return False

    # Checking if the request was successful
    if response.status_code == 200:
        return True
    else:
        return False

if __name__ == '__main__':
    result = fetch_example_com()
    if result:
        print("Request was successful")
    else:
        print("Request was blocked")