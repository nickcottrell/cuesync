"""
Proposal Generator

Integrates with maestro's VRGB system to generate tone-appropriate proposals
"""

import sys
from pathlib import Path
from typing import Dict

# Add maestro to path
MAESTRO_PATH = Path(__file__).parent.parent.parent.parent / "maestro"
sys.path.insert(0, str(MAESTRO_PATH / "gen"))

# Import maestro's VRGB system
try:
    from ops.detect_job_vrgb import detect_job_vrgb, get_vrgb_description
    from ops.generate_proposal_vrgb import generate_proposal_with_vrgb
    from llm_client import LLMClient
    VRGB_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import maestro VRGB system: {e}")
    print(f"  Maestro path: {MAESTRO_PATH}")
    print(f"  Using fallback template generation")
    VRGB_AVAILABLE = False


def generate_proposal_for_job(job: Dict) -> Dict:
    """
    Generate VRGB-styled proposal for job

    Uses maestro's VRGB system:
    1. Detect appropriate VRGB coordinates (enterprise/startup/urgent/creative)
    2. Generate proposal with tone matching job type
    3. Return proposal + metadata

    Args:
        job: Job dictionary from parser

    Returns:
        Dictionary with:
        {
            "proposal_text": str,
            "vrgb_used": dict,
            "job_type": str,
            "word_count": int,
            "method": str,
            "vrgb_description": str
        }
    """

    if not VRGB_AVAILABLE:
        return _generate_fallback_proposal(job)

    try:
        # 1. Detect VRGB coordinates
        vrgb_coords = detect_job_vrgb(job)

        # 2. Initialize LLM client
        llm = LLMClient()

        # 3. Generate proposal
        result = generate_proposal_with_vrgb(job, vrgb_coords, llm)

        # Add human-readable description
        result['vrgb_description'] = get_vrgb_description(result['vrgb_used'])

        return result

    except Exception as e:
        print(f"Warning: VRGB generation failed: {e}")
        print(f"  Falling back to template generation")
        return _generate_fallback_proposal(job)


def _generate_fallback_proposal(job: Dict) -> Dict:
    """
    Fallback template-based proposal generation

    Used when:
    - Maestro VRGB system not available
    - LLM not available
    - VRGB generation fails
    """

    title = job.get('title', 'this project')
    budget = job.get('budget', 0)
    platform = job.get('platform', 'the platform')

    proposal_text = f"""I can help with {title}.

APPROACH:
I'll analyze the requirements, implement a clean solution following best practices, and ensure thorough testing.

EXPERIENCE:
I have experience with similar projects and can deliver quality work on schedule.

TIMELINE: Approximately {_estimate_hours(budget)} hours

Could you share more details about your current setup?"""

    return {
        "proposal_text": proposal_text,
        "vrgb_used": {
            "formality_level": "#8B8B8B",
            "humor_intensity": "#8B8B8B",
            "rationale": "Fallback - professional/balanced"
        },
        "job_type": "standard",
        "word_count": len(proposal_text.split()),
        "method": "template_fallback",
        "vrgb_description": "Professional + Balanced"
    }


def _estimate_hours(budget: int) -> str:
    """Estimate hours based on budget"""
    if budget < 100:
        return "4-6"
    elif budget < 200:
        return "8-12"
    elif budget < 300:
        return "12-16"
    else:
        return "16-20"


# TODO: Proposal customization
# def customize_proposal_for_client(proposal: str, client_info: dict) -> str:
#     """
#     Customize proposal based on client-specific info:
#     - Mention their company by name
#     - Reference their previous jobs/feedback
#     - Adapt tone to client's communication style
#     """
#     pass
#
# def add_portfolio_examples(proposal: str, job_skills: list) -> str:
#     """
#     Automatically add relevant portfolio examples
#     Based on job skills required
#     """
#     pass
