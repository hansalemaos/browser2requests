import ctypes
import subprocess
import sys
from ctypes import wintypes
from functools import cache
import pandas as pd
from flatten_any_dict_iterable_or_whatsoever import fla_tu
import pprint
import pychrome


startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startupinfo.wShowWindow = subprocess.SW_HIDE
creationflags = subprocess.CREATE_NO_WINDOW
invisibledict = {
    "startupinfo": startupinfo,
    "creationflags": creationflags,
    "start_new_session": True,
}

windll = ctypes.LibraryLoader(ctypes.WinDLL)
kernel32 = windll.kernel32
GetExitCodeProcess = windll.kernel32.GetExitCodeProcess
_GetShortPathNameW = kernel32.GetShortPathNameW
_GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
_GetShortPathNameW.restype = wintypes.DWORD


@cache
def get_short_path_name(long_name):
    try:
        output_buf_size = 4096
        output_buf = ctypes.create_unicode_buffer(output_buf_size)
        _ = _GetShortPathNameW(long_name, output_buf, output_buf_size)
        return output_buf.value
    except Exception as e:
        sys.stderr.write(f"{e}\n")
        return long_name


class Browser2Requests:
    r"""
    Browser2Requests - A class for capturing network requests in a browser and converting them to a pandas DataFrame.

    Usage:
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
        browser_instance.start_capture(url="http://example.com", print_results=True)

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
    """

    def __init__(self, executable, port=9222):
        r"""
        Initialize the Browser2Requests instance.

        Parameters:
            executable (str): Path to the Chromium executable.
            port (int): Port number for remote debugging (default is 9222).
        """
        self.executable = get_short_path_name(executable)
        self.port = port
        self.browser_process = subprocess.Popen(
            [executable, f"--remote-debugging-port={port}"]
        )
        self.browser = None
        self.url = f"http://127.0.0.1:{self.port}"
        self.tab = None
        self.resultdict = {}

    def stop_capture(self):
        r"""
        Stop the ongoing capture of network requests.

        Returns:
            Browser2Requests: The current instance for method chaining.
        """
        try:
            self.tab.stop()
        except Exception as fe:
            print(fe)
        return self

    def generate_dataframe(self):
        r"""
        Generate a pandas DataFrame from the captured network requests.

        Returns:
            pd.DataFrame: The DataFrame containing information about captured network requests.
        """
        df = pd.DataFrame(self.resultdict.values())
        allrequests = df.request.apply(pd.Series)
        allrequests.columns = [f"aa_request_{x}" for x in allrequests]
        allrequests.insert(
            0, "aa_python_requests", [() for _ in range(len(allrequests))]
        )
        initiator = df.initiator.apply(pd.Series)
        initiator.columns = [f"bb_initiator_{x}" for x in initiator]
        df = pd.concat([allrequests, initiator, df], axis=1)

        alldicts = []

        for q in df.request:
            q2 = q.copy()
            method = q2.get("method", None)
            headers = q2.get("headers", None)
            url = q2.get("url", None)
            hasPostData = q2.get("hasPostData", False)
            if method:
                del q2["method"]
            if headers:
                del q2["headers"]
            if url:
                del q2["url"]
            if hasPostData:
                data = q2.copy()
                params = {}
            else:
                data = {}
                params = q2.copy()
            finaldict = {"url": url, "headers": headers, "data": data, "params": params}
            alldicts.append((method, finaldict))

        df["aa_python_requests"] = alldicts
        forallframes = []
        for ini, item in df.iterrows():
            try:
                di = item["aa_python_requests"]
                fordataframe = []
                for v, k in fla_tu(di[1]):
                    try:
                        fordataframe.append(pd.DataFrame([v, *k]).T)
                    except Exception as fe:
                        sys.stderr.write(f"{fe}\n")
                        sys.stderr.flush()
                forallframes.append(
                    pd.concat(fordataframe, ignore_index=True).assign(
                        aa_element_id=ini, aa_method=di[0]
                    )
                )
                forallframes[-1]["aa_requests_dict"] = forallframes[-1][
                    "aa_element_id"
                ].apply(lambda hx: di[1])
            except Exception as fe:
                sys.stderr.write(f"{fe}\n")
                sys.stderr.flush()
        dfn = pd.concat(forallframes, ignore_index=True)
        dfn.rename(
            columns={0: "aa_value", 1: "aa_mainkey", 2: "aa_subkey"}, inplace=True
        )
        return dfn

    def start_capture(self, url, print_results=True):
        r"""
        Start capturing network requests for a specified URL.

        Parameters:
            url (str): The URL to capture network requests for.
            print_results (bool): Flag to print captured results to the console (default is True).

        Returns:
            Browser2Requests: The current instance for method chaining.
        """

        def request_will_be_sent(**kwargs):
            try:
                nonlocal counter
                self.resultdict[counter] = kwargs.copy()
                counter = counter + 1
                if print_results:
                    pprint.pprint(kwargs)
            except Exception as fe:
                sys.stderr.write(f"{fe}\n")
                sys.stderr.flush()

        self.browser = pychrome.Browser(url=self.url)
        self.tab = self.browser.new_tab()
        counter = 0
        self.tab.set_listener("Network.requestWillBeSent", request_will_be_sent)
        self.tab.start()
        self.tab.call_method("Network.enable")
        self.tab.call_method(
            "Page.navigate",
            url=url,
        )
        return self
