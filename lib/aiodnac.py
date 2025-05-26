import httpx
from typing import Any
from datetime import datetime, timedelta, timezone

TIMEOUT = 5.0

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

    async def get_sites(self,params:dict[str,Any]=None):
        return await self._get("/dna/intent/api/v1/site",params=params)
    
    async def get_devices(self,params:dict[str,Any]=None):
        return await self._get("/dna/intent/api/v1/network-device",params=params)
    
