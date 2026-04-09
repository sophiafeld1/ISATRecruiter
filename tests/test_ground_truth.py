"""
Test suite for evaluating RAG chatbot accuracy against ground truth.
Measures success rate using semantic similarity comparison.
"""
import sys
import os
from typing import List, Dict, Tuple

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from LangGraph.main import process_question
from langchain_openai import OpenAIEmbeddings
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


# Ground truth test cases: (question, expected_answer_keywords, expected_answer_concepts)
GROUND_TRUTH = [
    {
        "question": "What is ISAT?",
        "expected_keywords": ["Integrated Science and Technology", "ISAT", "program"],
        "expected_concepts": "ISAT is an integrated science and technology program",
        "category": "general"
    },
    {
        "question": "What are the ISAT concentrations?",
        "expected_keywords": ["concentration", "5 concentrations", "Energy", "Environment", "Manufacturing", "Biotechnology", "Applied Computing"],
        "expected_concepts": "ISAT has 5 concentrations including Energy, Environment, Manufacturing, and Biotechnology",
        "category": "curriculum"
    },
    {
        "question": "What is ISAT 212?",
        "expected_keywords": ["ISAT 212", "energy", "fossil energy","renewable energy"],
        "expected_concepts": "ISAT 212 is an energy issues in science and technology course",
        "category": "courses"
    },
    {
        "question": "What are the prerequisites for ISAT 391?",
        "expected_keywords": ["prerequisite", "ISAT "],
        "expected_concepts": "ISAT 390 is a prerequisite for ISAT 391",
        "category": "courses"
    },
    {
        "question": "What labs are available in ISAT?",
        "expected_keywords": ["lab", "laboratory", "facilities"],
        "expected_concepts": "ISAT has laboratory facilities",
        "category": "facilities"
    },
    # Add more test cases here
]


def calculate_semantic_similarity(text1: str, text2: str, embeddings_model) -> float:
    """Calculate cosine similarity between two texts using embeddings."""
    try:
        emb1 = embeddings_model.embed_query(text1)
        emb2 = embeddings_model.embed_query(text2)
        similarity = cosine_similarity([emb1], [emb2])[0][0]
        return float(similarity)
    except Exception as e:
        print(f"Error calculating similarity: {e}")
        return 0.0


def check_keywords(answer: str, expected_keywords: List[str]) -> Tuple[bool, int]:
    """Check if answer contains expected keywords."""
    answer_lower = answer.lower()
    found_keywords = [kw for kw in expected_keywords if kw.lower() in answer_lower]
    return len(found_keywords) > 0, len(found_keywords)


def evaluate_answer(answer: str, ground_truth: Dict, embeddings_model) -> Dict:
    """Evaluate a single answer against ground truth."""
    results = {
        "question": ground_truth["question"],
        "answer": answer,
        "keyword_match": False,
        "keywords_found": 0,
        "total_keywords": len(ground_truth["expected_keywords"]),
        "semantic_similarity": 0.0,
        "passed": False
    }
    
    # Check keyword matching
    keyword_match, keywords_found = check_keywords(answer, ground_truth["expected_keywords"])
    results["keyword_match"] = keyword_match
    results["keywords_found"] = keywords_found
    
    # Calculate semantic similarity
    semantic_sim = calculate_semantic_similarity(
        answer, 
        ground_truth["expected_concepts"], 
        embeddings_model
    )
    results["semantic_similarity"] = semantic_sim
    
    # Pass criteria: semantic similarity > 0.7 OR keyword match with at least 50% keywords found
    keyword_threshold = len(ground_truth["expected_keywords"]) * 0.5
    results["passed"] = (
        semantic_sim > 0.7 or 
        (keyword_match and keywords_found >= keyword_threshold)
    )
    
    return results


def run_evaluation() -> Dict:
    """Run evaluation on all ground truth test cases."""
    print("=" * 80)
    print("RAG Chatbot Evaluation - Ground Truth Testing")
    print("=" * 80)
    print()
    
    # Initialize embeddings model for similarity comparison
    embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
    
    results = []
    passed_count = 0
    
    for i, test_case in enumerate(GROUND_TRUTH, 1):
        print(f"\n[{i}/{len(GROUND_TRUTH)}] Testing: {test_case['question']}")
        print("-" * 80)
        
        try:
            # Get answer from RAG system
            answer, _ = process_question(test_case["question"])
            
            # Evaluate answer
            evaluation = evaluate_answer(answer, test_case, embeddings_model)
            results.append(evaluation)
            
            # Print results
            print(f"Answer: {answer[:200]}..." if len(answer) > 200 else f"Answer: {answer}")
            print(f"\nKeywords found: {evaluation['keywords_found']}/{evaluation['total_keywords']}")
            print(f"Semantic similarity: {evaluation['semantic_similarity']:.3f}")
            print(f"Status: {'✓ PASSED' if evaluation['passed'] else '✗ FAILED'}")
            
            if evaluation['passed']:
                passed_count += 1
                
        except Exception as e:
            print(f"✗ ERROR: {e}")
            results.append({
                "question": test_case["question"],
                "answer": f"ERROR: {str(e)}",
                "passed": False
            })
    
    # Calculate overall statistics
    total_tests = len(results)
    accuracy = (passed_count / total_tests * 100) if total_tests > 0 else 0
    
    print("\n" + "=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {total_tests - passed_count}")
    print(f"Accuracy: {accuracy:.2f}%")
    print("=" * 80)
    
    # Detailed breakdown by category
    category_stats = {}
    for result in results:
        category = next(
            (gt["category"] for gt in GROUND_TRUTH if gt["question"] == result["question"]),
            "unknown"
        )
        if category not in category_stats:
            category_stats[category] = {"total": 0, "passed": 0}
        category_stats[category]["total"] += 1
        if result.get("passed", False):
            category_stats[category]["passed"] += 1
    
    if category_stats:
        print("\nBreakdown by Category:")
        print("-" * 80)
        for category, stats in category_stats.items():
            cat_accuracy = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            print(f"{category.capitalize()}: {stats['passed']}/{stats['total']} ({cat_accuracy:.1f}%)")
    
    return {
        "total": total_tests,
        "passed": passed_count,
        "failed": total_tests - passed_count,
        "accuracy": accuracy,
        "results": results,
        "category_stats": category_stats
    }


if __name__ == "__main__":
    # Check if sklearn is available
    try:
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        print("ERROR: sklearn is required. Install with: pip install scikit-learn")
        sys.exit(1)
    
    evaluation_results = run_evaluation()
    
    # Exit with appropriate code
    sys.exit(0 if evaluation_results["accuracy"] >= 70 else 1)

