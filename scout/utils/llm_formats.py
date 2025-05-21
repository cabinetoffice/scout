from typing import Dict, Any, List, Optional, Union


def format_llm_request(
    model_id: str, 
    prompt: str, 
    system_message: Optional[str] = None,
    max_tokens: int = 1000, 
    temperature: float = 0.5,
    images: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format a prompt for different LLM models based on model_id.
    
    Args:
        model_id: The model identifier
        prompt: The user prompt text
        system_message: Optional system message for models that support it
        max_tokens: Maximum number of tokens to generate
        temperature: Temperature parameter for generation
        images: List of image objects for multimodal models
        
    Returns:
        Dict containing the properly formatted request for the specified model
    """
    # Default format (for models not explicitly handled)
    request = {
        "modelId": model_id,
        "contentType": "application/json",
        "accept": "application/json",
    }
    
    # Handle Anthropic Claude models
    if "anthropic.claude" in model_id:
        messages = []
        
        # Add system message if provided
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        # Create user message with text and optional images
        user_content = []
        
        # Add images if provided
        if images:
            for img in images:
                user_content.append(img)
        
        # Add text prompt
        user_content.append({"type": "text", "text": prompt})
        
        # Add user message with content
        messages.append({"role": "user", "content": user_content})
        
        request["body"] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages
        }
    
    # Handle Meta Llama models
    elif "meta.llama" in model_id:
        # For Llama models, we concatenate system message and prompt if both provided
        full_prompt = prompt
        if system_message:
            full_prompt = f"{system_message}\n\n{prompt}"
            
        request["body"] = {
            "prompt": full_prompt,
            "max_gen_len": max_tokens,
            "temperature": temperature,
            "top_p": 0.9
        }
    
    # Handle Amazon Titan models
    elif "amazon.titan" in model_id:
        input_text = prompt
        if system_message:
            input_text = f"{system_message}\n\n{prompt}"
            
        request["body"] = {
            "inputText": input_text,
            "textGenerationConfig": {
                "maxTokenCount": max_tokens,
                "temperature": temperature,
                "topP": 0.9
            }
        }
    
    # Handle AI21 Jurassic models
    elif "ai21" in model_id:
        request["body"] = {
            "prompt": prompt,
            "maxTokens": max_tokens,
            "temperature": temperature,
            "topP": 0.9
        }
    
    # Handle Cohere models
    elif "cohere" in model_id:
        request["body"] = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

    # Handle Mistral models
    elif "mistral" in model_id:
        request["body"] = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "top_k": 50
        }

    # For any other models, use a generic format
    else:
        request["body"] = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
    
    # Convert body to JSON string for models that need it
    if "meta.llama" in model_id:
        import json
        request["body"] = json.dumps(request["body"])
    
    return request