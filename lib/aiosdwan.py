#!/usr/bin/env python3
import asyncio
import json
from dataclasses import dataclass, asdict, fields
from ipaddress import IPv4Address, IPv4Network
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta, timezone

import httpx


SEMAPHORE = 10
TIMEOUT = 15.0
SESSION_LIFETIME = 1800

# Utility function to convert epoch uptime
def ms_to_uptime_days(ms):
    try:
        ts = int(ms) / 1000
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        uptime = now - dt
        return uptime.days
    except:
        return None
    
@dataclass
class DeviceData:
    uuid: str
    fabric: str
    persona: str
    system_ip: Optional[IPv4Address]
    hostname: Optional[str]
    site_id: Optional[int]
    model: Optional[str]
    version: Optional[str]
    template_id: Optional[str]
    template_name: Optional[str]
    is_managed: bool
    is_valid: bool
    is_sync: bool
    is_reachable: bool
    raw_data: Dict[str, Any]
    latitude: float = 0.0
    longitude: float = 0.0
    uptime: str = None

    def todict(self):
        result = {}
        for field in fields(self):
            value = getattr(self, field.name)
            # Serialize IPv4Address to string
            if isinstance(value, IPv4Address):
                result[field.name] = str(value)
            else:
                result[field.name] = value
        return result

    def tojson(self):
        return json.dumps(self.todict())

@dataclass
class InterfaceData:
    if_name: str
    if_desc: str
    if_type: str
    if_mac: str
    vpn_id: str
    ip: IPv4Address
    network: IPv4Network
    raw_data: Dict[str, Any]


@dataclass
class VrrpData:
    if_name: str
    group: int
    priority: int
    preempt: bool
    master: bool
    ip: IPv4Address
    raw_data: Dict[str, Any]


@dataclass
class TlocData:
    site_id: int
    system_ip: IPv4Address
    private_ip: IPv4Address
    public_ip: IPv4Address
    preference: int
    weight: int
    encapsulation: str
    color: str
    raw_data: Dict[str, Any]


class Vmanage:
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        verify: bool = False,
        port: int = 443,
        semaphore: asyncio.Semaphore = None,
        timeout:float = TIMEOUT
    ):
        """
        Initialize the Vmanage client and attempt an immediate login.

        Args:
            host:      Hostname or IP address of the vManage server.
            username:  Username for authentication.
            password:  Password for authentication.
            verify:    Verify SSL certificate (default: False).
            port:      Port of the vManage server (default: 443).
            semaphore: Max number of concurrent requests (default: 40).
            debug:     If True, print additional debug information (not currently used).
        """
        self.host = host
        self.base_url = f"https://{host}:{port}"
        self.verify = verify
        self.username = username
        self.password = password
        self.token_time = None
        self.timeout = timeout
        self.session: Optional[httpx.AsyncClient] = None
        if semaphore is None:
            self.semaphore = asyncio.Semaphore(SEMAPHORE)
        else:
            self.semaphore = semaphore


    def connect(self) -> bool:
        """
        Perform synchronous login to obtain session cookie and CSRF token.

        Args:
            username: Username for authentication.
            password: Password for authentication.

        Returns:
            True if login succeeds, False otherwise.

        Raises:
            ConnectionError: If a networking error occurs during login.
        """
        # check if a valid token is set
        if self.token_time is not None and (datetime.now(timezone.utc) - self.token_time) < timedelta(seconds=SESSION_LIFETIME):
            return True
        
        #client = httpx.AsyncClient(verify=self.verify)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"j_username": self.username, "j_password": self.password}

        # Attempt the POST to j_security_check
        try:
            response = httpx.post(f"{self.base_url}/j_security_check", data=data, headers=headers, verify=self.verify)
        except httpx.HTTPError as exc:
            raise ConnectionError(f"ConnectionError during login: {exc}") from exc

        # Check if login succeeded: status=200 and response is not an HTML login page
        if response.status_code == 200 and not response.text.startswith("<html>"):
            # Get session cookie
            set_cookie = response.headers.get("Set-Cookie", "")
            if not set_cookie:
                return False
            cookie = set_cookie.split(";")[0]

            # Prepare base headers
            self.headers = {
                "Content-Type": "application/json",
                "Cookie": cookie
            }

            # Retrieve CSRF token
            try:
                token_resp = httpx.get(f"{self.base_url}/dataservice/client/token", headers=self.headers, verify=self.verify)
            except httpx.HTTPError as exc:
                raise ConnectionError(f"ConnectionError fetching CSRF token: {exc}") from exc

            if token_resp.status_code == 200:
                self.token_time = datetime.now(timezone.utc)
                self.headers["X-XSRF-TOKEN"] = token_resp.text.strip()
                # Update base_url to /dataservice for subsequent calls
                self.base_url = f"{self.base_url}/dataservice"
                #self.session = client
                return True
        return False

    async def _get(self, path: str, params: Dict[str, Any] = None) -> Optional[str]:
        if not self.connect():
            return None

        params = params or {}
        try:
            async with httpx.AsyncClient(headers=self.headers,verify=self.verify,timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}{path}", params=params)
                if response.status_code == 200:
                    return response.text
                return None
        except httpx.HTTPError as exc:
            raise ConnectionError(f"ConnectionError on GET {path}: {exc}") from exc

    async def _post(
        self,
        path: str,
        params: Dict[str, Any] = None,
        data: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        Internal helper for asynchronous POST requests.

        Args:
            path:   The API endpoint path (appended to base_url).
            params: Optional query parameters.
            data:   The JSON data to be posted.

        Returns:
            The response body (str) if status_code == 200, otherwise None.

        Raises:
            ConnectionError: If a networking error occurs.
        """
        if not self.connect():
            return None

        params = params or {}
        data = data or {}

        try:
            async with httpx.AsyncClient(headers=self.headers,verify=self.verify,timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}{path}", params=params, data=json.dumps(data))
                if response.status_code == 200:
                    return response.text
                return None
        except httpx.HTTPError as exc:
            raise ConnectionError(f"ConnectionError on POST {path}: {exc}") from exc

    async def get(self, endpoint:str, params:Dict[str, Any] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Public asynchronous GET method that returns JSON 'data' list when present.

        Args:
            endpoint: The API endpoint path (e.g., "/device/interface/synced").
            params:   Optional dictionary of query parameters.

        Returns:
            A list of items (deserialized JSON from 'data' field),
            or None if the request or JSON parsing fails.
        """
        params = params or {}
        response_text = await self._get(endpoint, params=params)
        if not response_text:
            return None

        try:
            data_json = json.loads(response_text)
            # vManage typically returns {'data': [...]}
            return data_json.get("data")
        except (json.JSONDecodeError, AttributeError):
            return None

    async def post(
        self,
        endpoint: str,
        params: Dict[str, Any] = None,
        data: Dict[str, Any] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Public asynchronous POST method that returns JSON 'data' list when present.

        Args:
            endpoint: The API endpoint path (e.g., "/template/device/config/input").
            params:   Optional dictionary of query parameters.
            data:     Data to send as JSON in the POST body.

        Returns:
            A list of items (deserialized JSON from 'data' field),
            or None if the request or JSON parsing fails.
        """
        params = params or {}
        data = data or {}
        response_text = await self._post(endpoint, params=params, data=data)
        if not response_text:
            return None

        try:
            data_json = json.loads(response_text)
            # vManage typically returns {'data': [...]}
            return data_json.get("data")
        except (json.JSONDecodeError, AttributeError):
            return None

    async def run_task(self,task):
        async with self.semaphore:
            return await task
            
    async def run_tasks(self, tasks: List[asyncio.Task]) -> List[Any]:
        """
        Execute multiple coroutines concurrently, respecting a semaphore limit.

        Args:
            tasks: A list of coroutine objects (e.g., [self.get('/endpoint'), ...]).

        Returns:
            A list of results from each task, in the same order they were passed.
        """
        return await asyncio.gather(*(self.run_task(t) for t in tasks))

    async def get_devices(self) -> Dict[str, DeviceData]:
        """
        Fetch and consolidate device information (controllers, vEdges, statuses).

        Returns:
            A dictionary keyed by device UUID, with values as `DeviceData` objects.
        """
        tasks = [
            self.get("/system/device/controllers"),
            self.get("/system/device/vedges"),
            self.get("/device")
        ]

        results = await self.run_tasks(tasks)
        if not all(results):
            return {}

        controllers_raw, vedges_raw, status_raw = results

        controllers = {item["uuid"]: item for item in controllers_raw}
        vedges = {item["uuid"]: item for item in vedges_raw}
        statuses = {item["uuid"]: item for item in status_raw}

        # Combine both controllers and vedges by UUID
        merged = controllers | vedges

        # Merge status data by UUID
        for device_uuid in merged:
            if device_uuid in statuses:
                merged[device_uuid] = {**merged[device_uuid], **statuses[device_uuid]}

        devices: Dict[str, DeviceData] = {}
        for uuid_key, info in merged.items():
            # Defensive gets in case keys are missing
            system_ip = info.get("system-ip")

            # Fix broken properties
            for property in ["deviceEnterpriseCertificate","deviceCSR","oldSerialNumber","CSRDetail", "vedgeCSR"]:
                if property in info:
                    del info[property]

            # compute uptime
            if "uptime-date" in info:
                uptime = ms_to_uptime_days(int(info.get("uptime-date")))
            else:
                uptime = None
            devices[uuid_key] = DeviceData(
                uuid=info["uuid"],
                uptime=uptime,
                fabric=self.host,
                persona=info.get("personality", ""),
                system_ip=IPv4Address(system_ip) if system_ip else None,
                hostname=info.get("host-name"),
                site_id=self._safe_int(info.get("site-id")),
                model=info.get("deviceModel", "").replace("vedge-", "").replace("cloud", "vbond"),
                version=info.get("version"),
                template_id=info.get("templateId"),
                template_name=info.get("template"),
                is_managed=(
                    "managed-by" in info and info["managed-by"] != "Unmanaged"
                ),
                is_valid=(info.get("validity") == "valid"),
                is_sync=(info.get("configStatusMessage") == "In Sync"),
                is_reachable=(info.get("reachability") == "reachable"),
                latitude=float(info.get("latitude", 0.0)),
                longitude=float(info.get("longitude", 0.0)),
                raw_data=info
            )
        return devices

    async def get_device_interfaces(self, device: DeviceData) -> Optional[List[InterfaceData]]:
        """
        Retrieve interface details for a given device.

        Args:
            device: A `DeviceData` instance representing the device.

        Returns:
            A list of `InterfaceData` for the device, or None if the query fails.
        """
        if not device.system_ip:
            return None

        raw_data = await self.get("/device/interface/synced", {"deviceId": str(device.system_ip)})
        if not raw_data:
            return None

        interfaces = []
        for iface in raw_data:
            try:
                ip_str = iface["ip-address"]
                mask = iface["ipv4-subnet-mask"]
                interfaces.append(
                    InterfaceData(
                        if_name=iface["ifname"],
                        if_desc=iface.get("description", "N/A"),
                        if_type=iface["interface-type"],
                        if_mac=iface["hwaddr"],
                        vpn_id=str(iface["vpn-id"]),
                        ip=IPv4Address(ip_str),
                        network=IPv4Network(f"{ip_str}/{mask}", strict=False),
                        raw_data=iface
                    )
                )
            except KeyError:
                # Skip malformed interface entries
                continue

        return interfaces

    async def get_device_tlocs(self, device: DeviceData) -> Optional[List[TlocData]]:
        """
        Retrieve TLOC (Transport Locator) information for a given device.

        Args:
            device: A `DeviceData` instance representing the device.

        Returns:
            A list of `TlocData` objects, or None if the query fails.
        """
        if not device.system_ip:
            return None

        raw_data = await self.get("/device/omp/tlocs/advertised", {"deviceId": str(device.system_ip)})
        if not raw_data:
            return None

        tlocs = []
        for item in raw_data:
            try:
                tlocs.append(
                    TlocData(
                        site_id=self._safe_int(item["site-id"]),
                        system_ip=IPv4Address(item["ip"]),
                        private_ip=IPv4Address(item["tloc-private-ip"]),
                        public_ip=IPv4Address(item["tloc-public-ip"]),
                        preference=int(item["preference"]),
                        weight=int(item["weight"]),
                        encapsulation=item["encap"],
                        color=item["color"].lower(),
                        raw_data=item
                    )
                )
            except KeyError:
                # Skip malformed TLOC entries
                continue

        return tlocs

    async def get_device_vrrp(self, device: DeviceData) -> Optional[List[VrrpData]]:
        """
        Retrieve VRRP configuration and status for a given device.

        Args:
            device: A `DeviceData` instance representing the device.

        Returns:
            A list of `VrrpData` objects, or None if the query fails.
        """
        if not device.system_ip:
            return None

        raw_data = await self.get("/device/vrrp", {"deviceId": str(device.system_ip)})
        if not raw_data:
            return None

        vrrp_entries = []
        for item in raw_data:
            try:
                master = (item["vrrp-state"] == "proto-state-master")
                vrrp_entries.append(
                    VrrpData(
                        if_name=item["if-name"],
                        ip=IPv4Address(item["virtual-ip"]),
                        group=int(item["group-id"]),
                        priority=int(item["priority"]),
                        preempt=bool(item["preempt"]),
                        master=master,
                        raw_data=item
                    )
                )
            except KeyError:
                # Skip malformed VRRP entries
                continue
        return vrrp_entries

    async def get_device_template_values(self, device: DeviceData) -> Optional[Dict[str, Any]]:
        """
        Retrieve input values for a device's attached template.

        Args:
            device: A `DeviceData` instance with valid `uuid` and `template_id`.

        Returns:
            A dictionary of template values for the device, or None if unavailable.
        """
        if not device.uuid or not device.template_id:
            return None

        payload = {
            "templateId": device.template_id,
            "deviceIds": [device.uuid],
            "isEdited": False,
            "isMasterEdited": False
        }

        raw_data = await self.post("/template/device/config/input", data=payload)
        if not raw_data:
            return None

        try:
            return raw_data[0]
        except (IndexError, TypeError):
            return None

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        """
        Internal helper to safely convert a value to int, returning None if invalid.
        """
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
