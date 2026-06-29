import os
import time
import pandas as pd
from src import config
from src.data_loader import stream_candidates, get_jd_text
from src.models.semantic import SemanticMatcher
from src.features.honeypot import is_honeypot
from src.features.extractor import extract_features
from src.ranker.scorer import calculate_final_score
from src.ranker.explainer import generate_reasoning

def main():
    start_time = time.time()
    
    # 1. Init model
    print("Loading Semantic Matcher...")
    matcher = SemanticMatcher()
    
    # 2. Stream candidates, filter traps, collect for batch indexing
    print("Streaming candidates and filtering traps...")
    valid_candidates = []
    
    jd_skills = {"python", "elasticsearch", "faiss", "pinecone", "weaviate", "qdrant", 
                 "milvus", "opensearch", "machine learning", "nlp", "llm", 
                 "sentence-transformers", "bge", "e5", "ndcg", "mrr", "map", "a/b test"}
                 
    # We must drastically reduce the pool to fit within the 5-minute CPU limit.
    # We will do a fast keyword/heuristic pre-filter to get ~2000-5000 candidates, 
    # then apply the slow semantic embedding to those.
    
    for cand in stream_candidates(config.CANDIDATES_PATH):
        if not is_honeypot(cand):
            profile = cand.get("profile", {})
            exp = profile.get("years_of_experience", 0)
            
            # The JD strictly requires 5-9 years, with slight flexibility.
            # We filter out anyone with < 4 years to aggressively prune the search space.
            if exp < 4:
                continue
                
            skills = cand.get("skills", [])
            cand_skills = {s.get("name", "").lower() for s in skills}
            
            # Must have Python
            text_blob = profile.get("summary", "").lower()
            for job in cand.get("career_history", []):
                text_blob += " " + job.get("title", "").lower() + " " + job.get("description", "").lower()
            
            has_python = "python" in cand_skills or "python" in text_blob
            if not has_python:
                continue
                
            # Must have explicit vector DB or embedding tech mentioned
            vector_techs = ["pinecone", "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch", "faiss", "sentence-transformers", "bge", "e5", "openai embeddings"]
            
            has_vector_tech = any(tech in cand_skills for tech in vector_techs) or any(tech in text_blob for tech in vector_techs)
            
            if has_vector_tech:
                valid_candidates.append(cand)
            
    print(f"Pre-filtered to {len(valid_candidates)} candidates with relevant skills.")
            
    print(f"Filtered to {len(valid_candidates)} valid candidates.")
    
    # 3. Index candidates
    print("Indexing candidates...")
    matcher.index_candidates(valid_candidates)
    
    # 4. Semantic Search
    jd_query = get_jd_text()
    print("Retrieving top candidates...")
    top_results = matcher.search(jd_query, top_k=config.TOP_K_RETRIEVAL)
    
    # 5. Reranking
    print("Reranking top candidates...")
    final_results = []
    
    for cand_id, sem_score in top_results:
        cand = matcher.candidate_cache[cand_id]
        features = extract_features(cand, jd_skills)
        score = calculate_final_score(sem_score, features)
        reasoning = generate_reasoning(cand, features, sem_score)
        
        final_results.append({
            "candidate_id": cand_id,
            "score": round(score, 4),
            "reasoning": reasoning
        })
        
    # Sort by rounded score descending, then candidate_id ascending
    final_results.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    
    # Take top 100
    top_100 = final_results[:100]
    
    # Format for submission
    submission_data = []
    for rank, res in enumerate(top_100, 1):
        submission_data.append({
            "candidate_id": res["candidate_id"],
            "rank": rank,
            "score": res["score"],
            "reasoning": res["reasoning"]
        })
        
    df = pd.DataFrame(submission_data)
    df.to_csv(config.SUBMISSION_OUT_PATH, index=False)
    
    elapsed = time.time() - start_time
    print(f"Done in {elapsed:.2f} seconds. Output saved to {config.SUBMISSION_OUT_PATH}")

if __name__ == "__main__":
    main()
