import json


def export_recognition(data, command="recognize-video", message="Recognition completed.", status="success"):
    """
    Format and return recognition output dictionary adhering to locked JSON contract.
    
    LOCK 9: JSON Contract tidak berubah.
    
    :param data: dict recognition payload data
    :param command: str command name (e.g. 'recognize-video' or 'recognize-frame')
    :param message: str response message
    :param status: str response status ('success' or 'error')
    :return: dict formatted response contract
    """
    return {
        "status": status,
        "command": command,
        "message": message,
        "data": data
    }


def to_json_string(formatted_dict):
    """Convert formatted dictionary to standard formatted JSON string."""
    return json.dumps(formatted_dict, indent=2)
