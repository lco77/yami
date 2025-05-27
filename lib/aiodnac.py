import json
import re
import httpx
from typing import Any
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone

TIMEOUT = 5.0
SESSION_LIFETIME = 3600

@dataclass
class DnacDevice:
    id: str
    hostname: str
    ip_address: str
    role: str = None
    version: str = None
    stack_size: int = 0
    uptime: int = 0
    platform: list[str] = field(default_factory=list)
    serial: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, device: dict[str, Any]) -> "DnacDevice":
        platform = [e.strip() for e in device.get("platformId", "").split(",")] if device.get("platformId") else []
        serial = [e.strip() for e in device.get("serialNumber", "").split(",")] if device.get("serialNumber") else []
        stack = len(serial) if serial else 0
        hostname = device.get("name", "").split(".")[0].upper() if device.get("name") else ""

        return cls(
            id=device.get("id", ""),
            hostname=hostname,
            ip_address=device.get("managementIpAddress", ""),
            role=device.get("deviceRole"),
            version=device.get("softwareVersion"),
            stack_size=stack,
            uptime=device.get("upTime", 0),
            platform=platform,
            serial=serial,
            raw_data=device
        )

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
        if self.token_time is not None and (datetime.now(timezone.utc) - self.token_time) < timedelta(seconds=SESSION_LIFETIME):
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
        data = await self._get("/dna/data/api/v1/networkDevices",params=params)

        if data and "response" in data:
            return [DnacDevice.from_dict(device) for device in data.get("response")]
        else:
            return None
    
    async def get_device(self,id:str):
        data = await self._get(f"/dna/data/api/v1/networkDevices/{id}")

        if data and "response" in data:
            return DnacDevice.from_dnac_api(data.get("response"))
        else:
            return None
