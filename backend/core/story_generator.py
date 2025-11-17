# core/story_generator.py

from sqlalchemy.orm import Session
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from core.prompts import STORY_PROMPT
from models.story import Story, StoryNode
from core.models import StoryNodeLLM, StoryLLMResponse
from dotenv import load_dotenv
import concurrent.futures

load_dotenv()

MAX_RECURSION_DEPTH = 3      # limit tree depth
MAX_OPTIONS_PER_NODE = 2      # limit options per node
LLM_TIMEOUT = 60              # timeout for LLM calls (seconds)

class StoryGenerator:
    @classmethod
    def _get_llm(cls):
        # Free local LLM
        return OllamaLLM(model="llama3.2")

    @staticmethod
    def safe_invoke(llm, prompt, timeout=LLM_TIMEOUT):
        """Run LLM with timeout to prevent API hanging"""
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(llm.invoke, prompt)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                raise Exception(f"LLM request timeout after {timeout} seconds (Ollama unresponsive). Check if Ollama is running and the model is loaded.")
            
            
    @classmethod
    def _check_ollama_health(cls):
        """Check if Ollama is running and model is available"""
        import requests
        try:
            # Check if Ollama service is running
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                available_models = [model.get("name") for model in models]
                print(f"Available Ollama models: {available_models}")
                
                # Check if our model is available
                target_model = "llama3.2"
                if not any(target_model in model for model in available_models):
                    print(f"Warning: Model '{target_model}' not found in available models")
                return True
            return False
        except Exception as e:
            print(f"Ollama health check failed: {e}")
            return False
    @classmethod
    def _create_fallback_story(cls, db: Session, session_id: str, theme: str) -> Story:
        """Create a simple fallback story when LLM fails"""
        story_db = Story(
            title=f"{theme.title()} Adventure",
            session_id=session_id
        )
        db.add(story_db)
        db.flush()

        # Create root node
        root_node = StoryNode(
            story_id=story_db.id,
            content=f"You begin your {theme} adventure. The journey ahead is full of mysteries and choices that will determine your fate.",
            is_ending=False,
            is_winning_ending=False,
            is_root=True,
            options=[]
        )
        db.add(root_node)
        db.flush()

        # Create a simple ending
        ending_node = StoryNode(
            story_id=story_db.id,
            content=f"Your {theme} adventure comes to an end. Though the path was uncertain, you emerged wiser from the experience.",
            is_ending=True,
            is_winning_ending=True,
            is_root=False,
            options=[]
        )
        db.add(ending_node)
        db.flush()

        # Add option from root to ending
        root_node.options = [{
            "text": "Continue the journey",
            "node_id": ending_node.id
        }]

        db.commit()
        return story_db

    @classmethod
    def generate_story(cls, db: Session, session_id: str, theme: str = "fantasy") -> Story:
        # Check Ollama health first
        if not cls._check_ollama_health():
            print("Ollama is not available, using fallback story immediately")
            return cls._create_fallback_story(db, session_id, theme)
        try:
            llm = cls._get_llm()
            story_parser = PydanticOutputParser(pydantic_object=StoryLLMResponse)

            prompt = ChatPromptTemplate.from_messages([
                ("system", STORY_PROMPT),
                ("human", "Create a story with theme: {theme}")
            ]).partial(format_instructions=story_parser.get_format_instructions(),theme=theme)
            
            # Initialize response_text to avoid scope issues
            response_text = "No response received"
            try:
                raw_response = cls.safe_invoke(llm, prompt.invoke({"theme": theme}))
                response_text = getattr(raw_response, "content", str(raw_response))
                
                # Debug: log the raw response
                print(f"Raw LLM Response: {response_text[:500]}...")  # First 500 chars
                
                # Try to clean the response if it contains markdown code blocks
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                    
                story_structure = story_parser.parse(response_text)

            except Exception as e:
                print(f"LLM Response parsing failed: {str(e)}")
                print(f"Response was: {response_text}")
                raise Exception(f"Failed to generate story structure: {str(e)}")

            # Store story in DB
            story_db = Story(title=story_structure.title, session_id=session_id)
            db.add(story_db)
            db.flush()

            # Process root node
            root_node_data = story_structure.rootNode
            cls._process_story_node(db, story_db.id, root_node_data, is_root=True, depth=0)
            db.commit()
            return story_db
        except Exception as e:
            print(f"LLM story generation failed, using fallback: {str(e)}")
            return cls._create_fallback_story(db, session_id, theme)        
    
    
    
    @classmethod
    def _process_story_node(cls, db: Session, story_id: int, node_data: StoryNodeLLM,
                            is_root: bool = False, depth: int = 0) -> StoryNode:
        node = StoryNode(
            story_id=story_id,
            content=getattr(node_data, "content", node_data["content"]),
            is_ending=getattr(node_data, "isEnding", node_data["isEnding"]),
            is_winning_ending=getattr(node_data, "isWinningEnding", node_data["isWinningEnding"]),
            is_root=is_root,
            options=[]
        )
        db.add(node)
        db.flush()

        # Stop recursion if max depth reached or node is ending
        if depth >= MAX_RECURSION_DEPTH or node.is_ending:
            return node

        # Process child nodes (limited options)
        if hasattr(node_data, "options") and node_data.options:
            options_list = []
            for option_data in node_data.options[:MAX_OPTIONS_PER_NODE]:
                next_node = getattr(option_data, "nextNode", None)
                if isinstance(next_node, dict):
                    next_node = StoryNodeLLM.model_validate(next_node)

                child_node = cls._process_story_node(
                    db, story_id, next_node, is_root=False, depth=depth+1
                )

                options_list.append({
                    "text": getattr(option_data, "text", option_data["text"]),
                    "node_id": child_node.id
                })
            node.options = options_list

        db.flush()
        return node
