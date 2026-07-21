"""
Opportunity Scorer

Scores job opportunities 1-10 based on:
- Budget (higher = better)
- Skills match (your expertise)
- Client quality (payment verified, history)
- Urgency (time-sensitive = higher priority)
- Competition (fewer applicants = better)
"""

import os
from typing import Dict


def score_opportunity(job: Dict) -> int:
    """
    Score job opportunity on scale of 1-10

    Scoring breakdown:
    - Budget (0-3 pts): Higher budget = better
    - Skills Match (0-3 pts): Match your expertise
    - Client Quality (0-2 pts): Payment verified, good history
    - Urgency (0-1 pt): Time-sensitive jobs get priority
    - Competition (0-1 pt): Fewer applicants = better odds

    Args:
        job: Job dictionary with budget, skills, client_info, etc.

    Returns:
        Score from 1-10
    """

    score = 0

    # 1. Budget scoring (0-3 points)
    budget = job.get('budget', 0)
    min_budget = int(os.getenv('MIN_BUDGET', '50'))

    if budget >= 300:
        score += 3
    elif budget >= 200:
        score += 2.5
    elif budget >= 100:
        score += 2
    elif budget >= min_budget:
        score += 1

    # 2. Skills match (0-3 points)
    job_skills = [s.lower() for s in job.get('skills', [])]
    your_skills_str = os.getenv('YOUR_SKILLS', 'react,javascript,python,node,typescript')
    your_skills = [s.strip().lower() for s in your_skills_str.split(',')]

    # Count how many job skills match your skills
    matches = len(set(job_skills) & set(your_skills))
    skill_score = min(matches, 3)
    score += skill_score

    # 3. Client quality (0-2 points)
    client_info = job.get('client_info', {})

    # Payment verified
    if client_info.get('payment_verified', False):
        score += 1

    # Good client history (5+ jobs)
    client_history = client_info.get('jobs_posted', 0)
    if client_history >= 5:
        score += 0.5
    if client_history >= 10:
        score += 0.5

    # 4. Urgency bonus (0-1 point)
    title_lower = job.get('title', '').lower()
    desc_lower = job.get('description', '').lower()

    urgent_keywords = ['urgent', 'asap', 'immediate', 'today', 'now', 'emergency']
    if any(kw in title_lower for kw in urgent_keywords):
        score += 1
    elif any(kw in desc_lower for kw in urgent_keywords):
        score += 0.5

    # 5. Competition penalty/bonus (0-1 point)
    proposal_count = job.get('proposal_count', 999)
    if proposal_count < 5:
        score += 1  # Very few applicants
    elif proposal_count < 10:
        score += 0.5  # Some applicants

    # Ensure score is within 1-10 range
    score = max(1, min(int(round(score)), 10))

    return score


def get_score_breakdown(job: Dict) -> Dict:
    """
    Get detailed breakdown of how score was calculated

    Useful for debugging and understanding why a job was scored a certain way

    Args:
        job: Job dictionary

    Returns:
        Dictionary with score breakdown:
        {
            "total": 8,
            "budget": 2,
            "skills": 3,
            "client": 2,
            "urgency": 1,
            "competition": 0,
            "explanation": "..."
        }
    """

    # TODO: Implement detailed breakdown
    # This would help understand scoring decisions

    total_score = score_opportunity(job)

    return {
        "total": total_score,
        "budget": 0,  # TODO: Calculate individual component
        "skills": 0,  # TODO
        "client": 0,  # TODO
        "urgency": 0,  # TODO
        "competition": 0,  # TODO
        "explanation": f"Total score: {total_score}/10"
    }


# TODO: Machine learning scoring
# def train_scorer_on_outcomes(jobs_with_outcomes: list):
#     """
#     Train ML model on historical job outcomes
#     - Which jobs led to interviews?
#     - Which jobs led to hires?
#     - Which proposals had high response rates?
#     """
#     pass
#
# def predict_success_probability(job: Dict) -> float:
#     """
#     Use ML to predict probability of success (0.0-1.0)
#     Based on historical patterns
#     """
#     pass
