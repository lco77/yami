import json
import httpx
from typing import Any
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone

TIMEOUT = 5.0
SESSION_LIFETIME = 3600

@dataclass
class MerakiOrganization:
    id: str
    name: str
    url: str
    raw_data: dict[str, Any]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "MerakiOrganization":
        return cls(
            id = data.get("id"),
            name = data.get("name"),
            url = data.get("url"),
            raw_data = data
        )

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(asdict(self))  

@dataclass
class MerakiTemplate:
    id: str
    name: str
    product_type: list
    raw_data: dict[str, Any]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "MerakiTemplate":
        return cls(
            id = data.get("id"),
            name = data.get("name"),
            product_type = data.get("productTypes"),
            raw_data = data
        )

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(asdict(self))  

@dataclass
class MerakiNetwork:
    id: str
    name: str
    org: str
    product_type: list
    from_template:bool
    tags: list
    url: str
    raw_data: dict[str, Any]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "MerakiNetwork":
        return cls(
            id = data.get("id"),
            name = data.get("name"),
            org = data.get("organizationId"),
            product_type = data.get("productTypes"),
            from_template = data.get("isBoundToConfigTemplate"),
            tags = data.get("tags"),
            url = data.get("url"),
            raw_data = data
        )

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(asdict(self))  

@dataclass
class MerakiDevice:
    id: str
    name: str
    network: str
    serial: str
    version: str
    model: str
    type: str
    ip_address: str
    latitude: float
    longitude: float
    url: str
    tags: list
    raw_data: dict[str, Any]



    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "MerakiDevice":
        return cls(
            id = data.get("serial"),
            name = data.get("name"),
            network = data.get("networkId"),
            serial = data.get("serial"),
            version = data.get("firmware").replace("wireless-",""),
            model = data.get("model"),
            type = data.get("productType"),
            ip_address = data.get("lanIp"),
            latitude = data.get("lat"),
            longitude = data.get("lng"),
            url = data.get("url"),
            tags = data.get("tags"),
            raw_data = data
        )

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(asdict(self))  

class Meraki:
    def __init__(self, api_key:str, org_id:str, host:str="api.meraki.com", verify:bool=False, timeout:float=TIMEOUT):
        self.url = f"https://{host}/api/v1"
        self.org_id = org_id
        self.verify = verify
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }


    
    async def _get(self, url: str, params: dict[str, str] = {}):
        results = []
        # For paged results
        next_url = url
        merged_params = params | {"perPage": "500"}

        try:
            async with httpx.AsyncClient(headers=self.headers, verify=self.verify, timeout=self.timeout) as client:
                while next_url:
                    r = await client.get(next_url, params=merged_params, )
                    #print(f'Meraki {r.status_code} GET {r.url} text={r.text}')
                    if r.status_code != 200:
                        return None

                    # Merge results
                    page_data = r.json()
                    if isinstance(page_data, list):
                        results.extend(page_data)
                    else:
                        # For non-paginated single-object endpoints
                        return page_data

                    # Handle pagination via 'Link' header
                    link = r.headers.get("Link")
                    if link and 'rel="next"' in link:
                        # Extract URL from header
                        parts = link.split(";")[0].strip()
                        # remove < >
                        next_url = parts[1:-1]
                        # Clear params, since next_url already includes query
                        merged_params = {}
                    else:
                        next_url = None

            return results
        except Exception:
            return None

    # multi gets
    async def get_organizations(self, params = {}):
        data = await self._get(f"{self.url}/organizations", params)
        if data:
            return [ MerakiOrganization.from_api(e) for e in data ]
        return None

    async def get_templates(self, params = {}):
        data = await self._get(f"{self.url}/organizations/{self.org_id}/configTemplates", params)
        if data:
            return [ MerakiNetwork.from_api(e) for e in data ]
        return None
    
    async def get_networks(self, params = {}):
        data = await self._get(f"{self.url}/organizations/{self.org_id}/networks", params)
        if data:
            return [ MerakiNetwork.from_api(e) for e in data ]
        return None
    
    async def get_devices(self, params = {}):
        data = await self._get(f"{self.url}/organizations/{self.org_id}/devices", params)
        if data:
            return [ MerakiDevice.from_api(e) for e in data ]
        return None

    # single gets
    async def get_network(self, id):
        data = await self._get(f"{self.url}/networks/{id}")
        if data:
            return MerakiNetwork.from_api(data)
        return None

    async def get_device(self, id):
        data = await self._get(f"{self.url}/devices/{id}")
        if data:
            return MerakiDevice.from_api(data)
        return None