from typing import Dict, Any

def generate_reasoning(candidate: Dict[str, Any], features: dict, semantic_score: float) -> str:
    """
    Generates a 1-2 sentence explanation as required by the hackathon spec.
    """
    profile = candidate.get("profile", {})
    title = profile.get("current_title", "Candidate")
    exp = profile.get("years_of_experience", 0)
    
    # Analyze what contributed most
    strengths = []
    if semantic_score > 0.6:
        strengths.append("strong semantic match to JD requirements")
    
    if features.get("hard_skills_score", 0) > 0.5:
        strengths.append("good overlap with required tech stack")
        
    if features.get("exp_score", 0) == 1.0:
        strengths.append(f"ideal {exp} years of experience")
        
    if features.get("behavioral_score", 0) > 0.7:
        strengths.append("highly active and responsive profile")
        
    concerns = []
    notice_period = candidate.get("redrob_signals", {}).get("notice_period_days", 90)
    if notice_period > 60:
        concerns.append(f"long notice period ({notice_period} days)")
        
    if exp > 10:
        concerns.append(f"potentially over-experienced ({exp} years)")
    elif exp < 5:
        concerns.append(f"slightly under-experienced ({exp} years)")

    reasoning = f"{title} with {exp} years of experience."
    if strengths:
        reasoning += " Strong fit due to " + " and ".join(strengths[:2]) + "."
    if concerns:
        reasoning += " Note: " + " and ".join(concerns) + "."
        
    return reasoning
