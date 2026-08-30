import os
from openai import AsyncOpenAI

# Initialize the async client using your API key from environment variables
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def llm_stream_generator(system_prompt: str, model: str = "gpt-4o"):
    """
    Streams text chunks from OpenAI back to the FastAPI SSE route.
    """
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
            ],
            stream=True,  # Enables chunk streaming
        )

        async for chunk in response:
            # Extract content delta from OpenAI chunk structure
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        print(f"❌ OpenAI Streaming Error: {e}")
        yield f"\n[Error generating response: {str(e)}]"