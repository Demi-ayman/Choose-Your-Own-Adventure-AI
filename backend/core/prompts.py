# core/prompts.py
STORY_PROMPT = """
        Create a very short choose-your-own-adventure story about {theme}.

        Requirements:
        - Title: 2-3 words
        - Root node: 1-2 sentences, 2 options
        - 1-2 levels deep maximum  
        - Include one winning and one losing ending
        - Keep ALL content very brief (1 sentence per node)

        Output ONLY valid JSON in this exact structure:
        {format_instructions}

        Do not include any other text, explanations, or markdown formatting.
        """

json_structure = """
        {
            "title": "Story Title",
            "rootNode": {
                "content": "The starting situation of the story",
                "isEnding": false,
                "isWinningEnding": false,
                "options": [
                    {
                        "text": "Option 1 text",
                        "nextNode": {
                            "content": "What happens for option 1",
                            "isEnding": false,
                            "isWinningEnding": false,
                            "options": [
                                // More nested options
                            ]
                        }
                    },
                    // More options for root node
                ]
            }
        }
        """