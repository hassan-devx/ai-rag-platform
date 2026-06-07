import os
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from app.pipeline import pipeline

load_dotenv()

class RAGEvaluator:
    def __init__(self):
        self.ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.pipeline = RAGPipeline()
        
        # Our ground-truth dataset to test the system's accuracy
        self.test_dataset = [
            {
                "question": "What is the primary goal of Project Emerald?",
                "expected_ground_truth": "To migrate all local text vector processing over to an optimized cluster architecture using custom Python daemons."
            },
            {
                "question": "When was Project Emerald launched?",
                "expected_ground_truth": "May 2026."
            },
            {
                "question": "What is the capital of France?",
                "expected_ground_truth": "This information is not present in the knowledge base." 
                # Out-of-bounds test: the system should safely refuse to answer
            }
        ]

    def judge_faithfulness(self, context: str, answer: str) -> int:
        """Asks a Judge LLM to evaluate if the answer hallucinates or sticks strictly to the context."""
        prompt = (
            "You are an unbiased QA auditor. Rate the FAITHFULNESS of the Generated Answer "
            "based strictly on the Provided Context. Do not use outside knowledge.\n\n"
            f"Context: {context}\n"
            f"Generated Answer: {answer}\n\n"
            "Respond with exactly one number:\n"
            "1 = The answer is entirely supported by the context without hallucination.\n"
            "0 = The answer introduces facts not found in the context."
        )
        
        try:
            response = self.ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0 # Strict compliance
            )
            score = response.choices[0].message.content.strip()
            return int(score)
        except Exception:
            return 0

    def run_evaluation(self):
        """Executes the test dataset through the pipeline and builds a performance report."""
        results = []
        
        print("🚀 Starting automated RAG evaluation loop...")
        
        for item in self.test_dataset:
            q = item["question"]
            gt = item["expected_ground_truth"]
            
            # 1. Fetch what the vector database retrieved
            retrieved_chunks = self.pipeline.query_similar_context(q, max_results=3)
            context_block = "\n".join(retrieved_chunks)
            
            # 2. Get the actual answer from the system (collecting streamed parts into a string)
            generated_answer = "".join(list(self.pipeline.generate_rag_response(q)))
            
            # 3. Grade the performance
            faithfulness_score = self.judge_faithfulness(context_block, generated_answer)
            
            # Is context empty for out-of-bound questions? 
            context_present = 1 if len(retrieved_chunks) > 0 else 0
            
            results.append({
                "Question": q,
                "Retrieved Chunks Count": len(retrieved_chunks),
                "Generated Answer": generated_answer,
                "Expected Truth": gt,
                "Faithfulness Score": faithfulness_score
            })
            
        # 4. Process metrics using Pandas
        df = pd.DataFrame(results)
        
        print("\n--- EVALUATION COMPLETE LOG ---")
        print(df[["Question", "Faithfulness Score"]])
        
        # Calculate summary statistics
        avg_faithfulness = df["Faithfulness Score"].mean() * 100
        print(f"\n📊 System Reliability Score: {avg_faithfulness:.1f}% Faithfulness")
        
        # Save to CSV for historical tracking
        df.to_csv("rag_evaluation_report.csv", index=False)
        print("💾 Report saved to 'rag_evaluation_report.csv'")
        return df

if __name__ == "__main__":
    evaluator = RAGEvaluator()
    evaluator.run_evaluation()