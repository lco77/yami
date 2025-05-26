import asyncio
import httpx
import json
from typing import Any
from dataclasses import dataclass, asdict

WAPI = "v2.10"
TIMEOUT = 15.0
PAGING = 1000


@dataclass
class Network:
    _ref: str
    network: str
    comment: str=None
    extattrs: dict=None

    def todict(self):
            return asdict(self)
    
    def tojson(self):
            return json.dumps(asdict(self))      


@dataclass
class FixedAddress:
    _ref: str
    ipv4addr: str
    mac: str
    name: str=None
    comment: str=None
    extattrs: dict=None

    def todict(self):
            return asdict(self)
    
    def tojson(self):
            return json.dumps(asdict(self))   

@dataclass
class FilterMac:
    _ref: str
    name: str
    comment: str=None

    def todict(self):
            return asdict(self)
    
    def tojson(self):
            return json.dumps(asdict(self))

@dataclass
class MacFilterAddress:
    _ref: str
    filter: str
    mac:str
    #never_expires: bool
    #is_registered_user: bool
    extattrs: dict=None
    comment: str=None
    
    #username: str=None
    #expiration_time: str=None

    def todict(self):
            return asdict(self)

    def tojson(self):
            return json.dumps(asdict(self))

class Infoblox:
    def __init__(self, host:str, username:str, password:str, wapi_version:str=WAPI, verify:bool=False, timeout:float=TIMEOUT, paging:int=PAGING):
        self.host = host
        self.username = username
        self.password = password
        self.wapi_version = wapi_version
        self.verify = verify
        self.timeout = timeout
        self.paging = paging
        self.url = f"https://{host}/wapi/{wapi_version}"
        self.client = httpx.AsyncClient(
            auth=httpx.BasicAuth(username=username, password=password),
            verify=verify,
            timeout=timeout
        )

    async def _get(self,object:str,**params)->list[Any]:
        url = f"{self.url}/{object}"
        # Enable paged results
        params = params | {"_paging":1,"_max_results":self.paging,"_return_as_object":1}
        data = []
        # Loop on pages
        while True:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            page = response.json()
            data = data + page.get("result",[])
            # Break if no more pages
            if not page.get("next_page_id",None) is None:
                params = {"_page_id": page.get("next_page_id")}
            else:
                break
        return data      

    async def get_filtermac(self,**params)->list[FilterMac]:
        data = await self._get("filtermac",**params)
        return [ FilterMac(**e) for e in data ]

    async def get_macfilteraddress(self,**params)->list[MacFilterAddress]:
        data = await self._get("macfilteraddress",**params)
        return [ MacFilterAddress(**e) for e in data ]

    async def get_extensibleattributedef(self,**params):
        return await self._get("extensibleattributedef",**params)

    async def get_fixedaddress(self,**params)->list[FixedAddress]:
        data = await self._get("fixedaddress",**params)
        return [ FixedAddress(**e) for e in data ]
    
    async def get_network(self,**params)->list[Network]:
        data = await self._get("network",**params)
        return [ Network(**e) for e in data ]