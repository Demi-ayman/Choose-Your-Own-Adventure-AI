from langchain_ollama import OllamaLLM

llm = OllamaLLM(model="llama3.2")
prompt = "Write a very short story (max 50 words) about a water park."
result = llm.invoke(prompt)
print(result)
