# A class for capturing network requests in a browser and converting them to a pandas DataFrame - Windows only

## pip install browser2requests

### Tested against Windows / Python 3.11 / Anaconda


```python
from time import sleep
from browser2requests import Browser2Requests

# Specify the path to the Chromium executable (ungoogled recommended).
# https://ungoogled-software.github.io/ungoogled-chromium-binaries/releases/windows/64bit/
executable = r"C:\Users\hansc\Downloads\ungoogled-chromium_120.0.6099.71-1.1_windows_x64\ungoogled-chromium_120.0.6099.71-1.1_windows\chrome.exe"

# Create an instance of Browser2Requests with the specified executable and port.
browser_instance = Browser2Requests(executable=executable, port=9222)

# Allow some time for the browser to start (5 seconds in this example).
sleep(5)

# Start capturing network requests for a specified URL.
browser_instance.start_capture(url="http://192.168.9.1/index.html#login", print_results=True)

# Optionally perform actions in the browser, e.g., navigation, form submissions.

# Stop the capture and generate a pandas DataFrame of captured requests.
browser_instance.stop_capture()
df = browser_instance.generate_dataframe()

# Use the captured requests to reproduce actions using the `requests` library.
import requests
s = requests.session()
for key, item in df.iterrows():
	res = None
	if item['aa_method'] == 'GET':
		res = s.get(**item['aa_requests_dict'])
	elif item['aa_method'] == 'POST':
		res = s.post(**item['aa_requests_dict'])
	print(res)
```