"""
Cuesheet Dispatcher

POSTs cuesheets to cue-dispatcher with proper authentication
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict


def dispatch_cuesheet(cuesheet: Dict) -> Dict:
    """
    Dispatch cuesheet to cue-dispatcher

    The cue-dispatcher will:
    1. Validate the cuesheet
    2. Sign each cue
    3. POST to CueSync relay

    Args:
        cuesheet: Complete cuesheet dictionary

    Returns:
        {
            "success": bool,
            "error": str | None,
            "cuesheet_id": str,
            "cues_dispatched": int
        }
    """

    dispatcher_url = os.getenv('DISPATCHER_URL', 'http://localhost:8080/dispatch')

    try:
        # Encode cuesheet as JSON
        payload = json.dumps(cuesheet).encode('utf-8')

        # Create request
        req = urllib.request.Request(
            dispatcher_url,
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'job-alert-agent/1.0'
            },
            method='POST'
        )

        # Send request
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))

            return {
                "success": True,
                "error": None,
                "cuesheet_id": cuesheet['cuesheet_id'],
                "cues_dispatched": len(cuesheet.get('cues', [])),
                "dispatcher_response": result
            }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        return {
            "success": False,
            "error": f"HTTP {e.code}: {error_body}",
            "cuesheet_id": cuesheet['cuesheet_id'],
            "cues_dispatched": 0
        }

    except urllib.error.URLError as e:
        return {
            "success": False,
            "error": f"URL Error: {e.reason}",
            "cuesheet_id": cuesheet['cuesheet_id'],
            "cues_dispatched": 0
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error: {str(e)}",
            "cuesheet_id": cuesheet['cuesheet_id'],
            "cues_dispatched": 0
        }


def save_cuesheet_locally(cuesheet: Dict, output_dir: str = "./cuesheets") -> str:
    """
    Save cuesheet to local file for review/backup

    Useful for:
    - Debugging
    - Manual dispatch later
    - Historical record

    Args:
        cuesheet: Cuesheet dictionary
        output_dir: Directory to save cuesheets

    Returns:
        Path to saved cuesheet file
    """

    import os
    from pathlib import Path

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    cuesheet_id = cuesheet['cuesheet_id']
    filename = f"{cuesheet_id}.json"
    filepath = output_path / filename

    with open(filepath, 'w') as f:
        json.dump(cuesheet, f, indent=2)

    return str(filepath)


# TODO: Add retry logic
# def dispatch_with_retry(cuesheet: dict, max_retries: int = 3) -> dict:
#     """
#     Dispatch with exponential backoff retry
#     Useful for handling temporary network issues
#     """
#     pass
#
# TODO: Add batch dispatching
# def dispatch_multiple(cuesheets: list) -> list:
#     """
#     Dispatch multiple cuesheets in batch
#     Returns list of results
#     """
#     pass
