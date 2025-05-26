import json
import re
import httpx
from typing import Any
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone

TIMEOUT = 5.0

# helper function to convert uptime in days
def uptime_to_days(uptime_str):
    # Pattern: optional "xxx days, ", then H:MM:SS(.XX)
    match = re.match(r'(?:(\d+)\s+days?,\s+)?(\d+):(\d+):(\d+)(?:\.\d+)?', uptime_str)
    if not match:
        raise ValueError(f"Invalid uptime format: {uptime_str}")

    days = int(match.group(1)) if match.group(1) else 0
    hours = int(match.group(2))
    minutes = int(match.group(3))
    seconds = int(match.group(4))

    # Total time as timedelta
    total_time = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    return total_time.days

@dataclass
class DnacDevice:
    id: str
    hostname: str
    ip_address: str
    version: str = None
    stack_size: int = 0
    uptime: int = 0
    platform: list[str] = field(default_factory=list)
    serial: list[str] = field(default_factory=list)

    def todict(self):
        return asdict(self)

    def tojson(self):
        return json.dumps(asdict(self))  
    
class Dnac:
    def __init__(self, host:str, username:str, password:str, verify:bool=False, timeout:float=TIMEOUT):
        self.host = host
        self.username = username
        self.password = password
        self.verify = verify
        self.timeout = timeout
        self.url = f"https://{host}"
        self.token_time = None

    def connect(self)->bool:
        # check if a valid token is set
        if self.token_time is not None and (datetime.now(timezone.utc) - self.token_time) < timedelta(seconds=3600):
            return True
        # otherwise proceed with authentication
        r = httpx.post(
            f"{self.url}/dna/system/api/v1/auth/token",
            auth = (self.username,self.password),
            headers = {'content-type': 'application/json'},
            verify = self.verify,
        )
        if r.status_code == 200:
            self.token_time = datetime.now(timezone.utc)
            self.headers = {
                "X-Auth-Token": r.json()["Token"],
                "Content-type": "application/json"
            }
            return True
        else:
            return False
    
    async def _get(self,object:str, params:dict[str,Any]=None)->list[Any]:
        # check or set authentication
        if not self.connect():
            return None
        # prepare request
        url = f"{self.url}{object}"
        async with httpx.AsyncClient(headers=self.headers,verify=self.verify,timeout=self.timeout) as client:
            r = await client.get(url, headers=self.headers, params=params)
        # check response
        if r.status_code == 200:
            return r.json()
        else:
            return None

    async def get_devices(self,params:dict[str,Any]=None):
        data = await self._get("/dna/intent/api/v1/network-device",params=params)
        devices = []
        #print(json.dumps(data,indent=4))
        if data and "response" in data:
            for device in data.get("response"):
                platform = [e.strip() for e in device.get("platformId").split(",")] if "platformId" in device and device.get("platformId") else []
                serial = [e.strip() for e in device.get("serialNumber").split(",")] if "serialNumber" in device and device.get("serialNumber") else []
                if platform:
                    stack = len(serial)
                else:
                    stack = 0
                devices.append(DnacDevice(
                    id = device.get("id"),
                    hostname = device.get("hostname").split(".")[0].upper(),
                    ip_address = device.get("managementIpAddress"),
                    version = device.get("softwareVersion"),
                    stack_size = stack,
                    uptime = uptime_to_days(device.get("upTime")),
                    platform = platform,
                    serial = serial
                ))
            return devices
        else:
            return None
    
