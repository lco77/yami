
from netmiko import ConnectHandler
from celery import Celery, shared_task 

# hello world task
@shared_task
def hello(world):
    return {
        "hello": world,
        "success": True
    }

# run_ssh_command
@shared_task
def run_ssh_command(host:str, username:str, password:str, command:str, device_type:str="cisco_ios", use_textfsm:bool=True, port:int=22, timeout:int=10):
    try:
        device = {
            "device_type": device_type,
            "ip": host,
            "username": username,
            "password": password,
            "port": port,
        }

        connection = ConnectHandler(**device)
        output = connection.send_command(command, use_textfsm=use_textfsm)
        connection.disconnect()

        return {
            "parsed": output if isinstance(output, list) else None,
            "raw": output if isinstance(output, str) else None,
            "success": True
        }

    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }