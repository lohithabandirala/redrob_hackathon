from typing import Dict, Any

def extract_features(candidate: Dict[str, Any], jd_skills_set: set) -> Dict[str, float]:
    """
    Extracts numerical features used for ranking a candidate.
    """
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    
    # 1. Hard Skills Match
    skills = candidate.get("skills", [])
    candidate_skills = {s.get("name", "").lower() for s in skills}
    overlap = len(candidate_skills.intersection(jd_skills_set))
    hard_skills_score = min(overlap / len(jd_skills_set), 1.0) if jd_skills_set else 0.0
    
    # 2. Experience Fit (Target: 5-9 years, 7 is optimal)
    # We penalize distance from the 5-9 range
    exp = profile.get("years_of_experience", 0)
    if 5 <= exp <= 9:
        exp_score = 1.0
    elif exp < 5:
        exp_score = max(0.0, 1.0 - (5 - exp) * 0.2)
    else:
        exp_score = max(0.0, 1.0 - (exp - 9) * 0.1) # Penalize over-experience less harshly
        
    # 3. Behavioral Score
    response_rate = signals.get("recruiter_response_rate", 0.0)
    completeness = signals.get("profile_completeness_score", 0.0) / 100.0
    open_to_work = 1.0 if signals.get("open_to_work_flag") else 0.0
    
    # Notice period penalty (target sub 30 days)
    notice_period = signals.get("notice_period_days", 90)
    notice_score = 1.0 if notice_period <= 30 else max(0.0, 1.0 - ((notice_period - 30) / 60))
    
    behavioral_score = (response_rate * 0.4) + (completeness * 0.2) + (open_to_work * 0.2) + (notice_score * 0.2)
    
    return {
        "hard_skills_score": hard_skills_score,
        "exp_score": exp_score,
        "behavioral_score": behavioral_score
    }
