import json
import httpx
import asyncio
from dataclasses import dataclass, asdict, fields
from ipaddress import IPv4Address, IPv4Network
from typing import Any, Optional
from datetime import datetime, timedelta, timezone

SEMAPHORE = 10
TIMEOUT = 15.0
SESSION_LIFETIME = 300

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
class SdwanDevice:
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
    raw_data: dict[str, Any]
    latitude: float = 0.0
    longitude: float = 0.0
    uptime: str = None

    @classmethod
    def from_api(cls, fabric:str, device:dict[str, Any]) -> "SdwanDevice":
        # Defensive gets in case keys are missing
        system_ip = device.get("system-ip")

        # Fix broken properties
        for property in ["deviceEnterpriseCertificate","deviceCSR","oldSerialNumber","CSRDetail", "vedgeCSR"]:
            if property in device:
                del device[property]

        # compute uptime
        if "uptime-date" in device:
            uptime = ms_to_uptime_days(int(device.get("uptime-date")))
        else:
            uptime = None
        return SdwanDevice(
            uuid=device["uuid"],
            uptime=uptime,
            fabric=fabric,
            persona=device.get("personality", ""),
            system_ip=IPv4Address(system_ip) if system_ip else None,
            hostname=device.get("host-name"),
            site_id=device.get("site-id"),
            model=device.get("deviceModel", "").replace("vedge-", "").replace("cloud", "vbond"),
            version=device.get("version"),
            template_id=device.get("templateId"),
            template_name=device.get("template"),
            is_managed=(
                "managed-by" in device and device["managed-by"] != "Unmanaged"
            ),
            is_valid=(device.get("validity") == "valid"),
            is_sync=(device.get("configStatusMessage") == "In Sync"),
            is_reachable=(device.get("reachability") == "reachable"),
            latitude=float(device.get("latitude", 0.0)),
            longitude=float(device.get("longitude", 0.0)),
            raw_data=device
        )

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
    raw_data: dict[str, Any]


@dataclass
class VrrpData:
    if_name: str
    group: int
    priority: int
    preempt: bool
    master: bool
    ip: IPv4Address
    raw_data: dict[str, Any]


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
    raw_data: dict[str, Any]


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

    async def connect(self) -> bool:
        # check if a valid token is set
        token_check = self.token_time is not None
        time_check = (datetime.now(timezone.utc) - self.token_time) < timedelta(seconds=SESSION_LIFETIME) if token_check else False
        connect_check = token_check and time_check
        if connect_check:
            #print(f'Vmanage auth ok: token_check={token_check} time_check={time_check} connect_check={connect_check} token_time={self.token_time}')
            return True
        print(f'Vmanage re-auth triggered: token_check={token_check} time_check={time_check} connect_check={connect_check} token_time={self.token_time}')
        
        self.token_time = None
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"j_username": self.username, "j_password": self.password}

        # Attempt the POST to j_security_check
        try:
            async with httpx.AsyncClient(headers=headers, verify=self.verify, timeout=self.timeout) as client:
                # login form
                response = await client.post(f"{self.base_url}/j_security_check", data=data)
                print(f'LOGIN {response.status_code} text={response.text} headers={response.headers}')
                if (response.status_code != 200 or response.text.startswith('<html>')):
                    #print(f'Vmanage login failed: user {self.username} on {self.host}')
                    raise
                self.headers = {
                    "Content-Type": "application/json",
                    "Cookie": response.headers.get("Set-Cookie")
                }
                # CSRF token
                response = await client.get(f"{self.base_url}/dataservice/client/token")
                print(f'CSRF {response.status_code} text={response.text} headers={response.headers}')
                if response.status_code != 200:
                    raise
                # Update self
                self.token_time = datetime.now(timezone.utc)
                self.headers["X-XSRF-TOKEN"] = response.text
                return True
        except Exception:
            print(f'Vmanage: user {self.username} failed to authenticate to {self.host}')
            return False
        return True

    async def _get(self, path: str, params: dict[str, Any] = None) -> Optional[str]:
        check = await self.connect()
        print(f'check_auth={check}')
        if not await self.connect():
            return None

        params = params or {}
        try:
            async with httpx.AsyncClient(headers=self.headers,verify=self.verify,timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/dataservice{path}", params=params)
                if response.status_code == 200:
                    return response.text
                return None
        except httpx.HTTPError as exc:
            raise ConnectionError(f"ConnectionError on GET {path}: {exc}") from exc

    async def _post(
        self,
        path: str,
        params: dict[str, Any] = None,
        data: dict[str, Any] = None
    ) -> Optional[str]:

        if not await self.connect():
            return None

        params = params or {}
        data = data or {}

        try:
            async with httpx.AsyncClient(headers=self.headers,verify=self.verify,timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/dataservice{path}", params=params, data=json.dumps(data))
                if response.status_code == 200:
                    return response.text
                return None
        except httpx.HTTPError as exc:
            raise ConnectionError(f"ConnectionError on POST {path}: {exc}") from exc

    async def get(self, endpoint:str, params:dict[str, Any] = None) -> Optional[list[dict[str, Any]]]:
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
        params: dict[str, Any] = None,
        data: dict[str, Any] = None
    ) -> Optional[list[dict[str, Any]]]:
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
            
    async def run_tasks(self, tasks: list[asyncio.Task]) -> list[Any]:
        """
        Execute multiple coroutines concurrently, respecting a semaphore limit.

        Args:
            tasks: A list of coroutine objects (e.g., [self.get('/endpoint'), ...]).

        Returns:
            A list of results from each task, in the same order they were passed.
        """
        return await asyncio.gather(*(self.run_task(t) for t in tasks))

    async def get_devices(self) -> dict[str, SdwanDevice]:
        """
        Fetch and consolidate device information (controllers, vEdges, statuses).

        Returns:
            A dictionary keyed by device UUID, with values as `DeviceData` objects.
        """

        # check session before parallel tasks
        if not await self.connect():
            return None
        
        # define tasks
        tasks = [
            self.get("/system/device/controllers"),
            self.get("/system/device/vedges"),
            self.get("/device")
        ]

        # run tasks
        results = await self.run_tasks(tasks)
        if not all(results):
            return None
        controllers_raw, vedges_raw, status_raw = results

        # map results into dictionaries
        controllers = {item["uuid"]: item for item in controllers_raw}
        vedges = {item["uuid"]: item for item in vedges_raw}
        statuses = {item["uuid"]: item for item in status_raw}

        # Combine both controllers and vedges by UUID
        merged = controllers | vedges

        # Merge status data by UUID
        for device_uuid in merged:
            if device_uuid in statuses:
                merged[device_uuid] = {**merged[device_uuid], **statuses[device_uuid]}

        return { uuid:SdwanDevice.from_api(fabric=self.host, device=device) for uuid,device in merged.items() }

    async def get_device_interfaces(self, device: SdwanDevice) -> Optional[list[InterfaceData]]:
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

    async def get_device_tlocs(self, device: SdwanDevice) -> Optional[list[TlocData]]:
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

    async def get_device_vrrp(self, device: SdwanDevice) -> Optional[list[VrrpData]]:
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

    async def get_device_template_values(self, device_uuid:str, template_uuid:str) -> Optional[dict[str, Any]]:
        """
        Retrieve input values for a device's attached template.

        Args:
            device: A `DeviceData` instance with valid `uuid` and `template_id`.

        Returns:
            A dictionary of template values for the device, or None if unavailable.
        """
        if not device_uuid or not template_uuid:
            return None

        payload = {
            "templateId": template_uuid,
            "deviceIds": [device_uuid],
            "isEdited": False,
            "isMasterEdited": False
        }

        raw_data = await self.post("/template/device/config/input", data=payload)
        if not raw_data:
            return None

        try:
            return raw_data[0]
        except Exception:
            return None

    async def get_device_route_table(self, device_uuid:str) -> Optional[dict[str, Any]]:
        if not device_uuid:
            return None
        raw_data = await self.get("/device/ip/ipRoutes", {"deviceId":device_uuid})
        if not raw_data:
            return None
        try:
            return raw_data
        except Exception:
            return None
