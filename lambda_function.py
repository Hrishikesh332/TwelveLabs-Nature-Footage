import json
import os
from twelvelabs import TwelveLabs

def lambda_handler(event, context):

    try:

        video_id = event.get('video_id')
        api_key = event.get('api_key')
        
        if not video_id:
            return {
                'statusCode': 400,
                'error': 'Missing required parameter: video_id'
            }
        
        if not api_key:
            return {
                'statusCode': 400,
                'error': 'Missing required parameter: api_key'
            }
        
        structured_prompt = f"""
        Analyze this video and provide detailed information in the following categories:
        
        1. Shot: What type of camera shot is used? (e.g., Close Up, Medium Shot, Wide Shot)
        2. Subject: What is the main subject? Include specific details about:
           - Type (Animal, Human, Object)
           - Classification (Mammal, Bird, etc. if applicable)
           - Species/Category (Primate, Car, etc.)
           - Count (Single, Multiple)
           - Specific identification (Capuchin Monkey, etc.)
           - Color (Black, Brown, etc.)
        3. Action: What is the main action occurring? (e.g., display, groom, run)
        4. Environment: What is the setting? Include:
           - Time (Day, Night)
           - Location (forest, urban, indoor)
           - Weather/Conditions (Rainy, Sunny)
           - Position (Topside, Underwater)
           - Climate (Tropical, Desert)
        
        Format the response as a structured JSON object with these categories. Do not include explanations, just the structured data.
        
        """
        
        client = TwelveLabs(api_key=api_key)

        response = client.generate.text(
            video_id=video_id,
            prompt=structured_prompt
        )
        

        raw_analysis = response.data
        try:
            structured_data = json.loads(raw_analysis)
        except json.JSONDecodeError:

            structured_data = parse_unstructured_response(raw_analysis)
        

        return {
            'statusCode': 200,
            'data': raw_analysis,
            'structured_data': structured_data
        }
    
    except Exception as e:

        return {
            'statusCode': 500,
            'error': str(e)
        }

def parse_unstructured_response(text):

    result = {
        "Shot": "",
        "Subject": {
            "Type": "",
            "Classification": "",
            "Species": "",
            "Count": "",
            "Identification": "",
            "Color": ""
        },
        "Action": "",
        "Environment": {
            "Time": "",
            "Location": "",
            "Weather": "",
            "Position": "",
            "Climate": ""
        }
    }

    if "shot:" in text.lower():
        shot_section = text.lower().split("shot:")[1].split("\n")[0]
        result["Shot"] = shot_section.strip()

    if "subject:" in text.lower():
        subject_section = text.lower().split("subject:")[1].split("\n")[0]
        parts = subject_section.split()
        
        for type_key in ["animal", "human", "object"]:
            if type_key in parts:
                result["Subject"]["Type"] = type_key.capitalize()
                
        for class_key in ["mammal", "bird", "reptile", "amphibian", "fish", "insect"]:
            if class_key in parts:
                result["Subject"]["Classification"] = class_key.capitalize()
        
        for species_key in ["primate", "feline", "canine", "bovine", "equine"]:
            if species_key in parts:
                result["Subject"]["Species"] = species_key.capitalize()
 
        for count_key in ["single", "multiple", "pair", "group"]:
            if count_key in parts:
                result["Subject"]["Count"] = count_key.capitalize()
        
        result["Subject"]["Identification"] = subject_section.strip()
        

        for color in ["black", "white", "brown", "grey", "gray", "red", "blue", "green", "yellow"]:
            if color in parts:
                result["Subject"]["Color"] = color.capitalize()
    
    if "action:" in text.lower():
        action_section = text.lower().split("action:")[1].split("\n")[0]
        result["Action"] = action_section.strip()
    
    if "environment:" in text.lower():
        env_section = text.lower().split("environment:")[1].split("\n")[0]
        parts = env_section.split()
        
        for time_key in ["day", "night", "dusk", "dawn", "morning", "evening"]:
            if time_key in parts:
                result["Environment"]["Time"] = time_key.capitalize()

        for loc_key in ["forest", "urban", "indoor", "outdoor", "rural", "jungle", "desert", "mountain", "beach", "ocean", "river", "lake", "rainforest"]:
            if loc_key in parts:
                result["Environment"]["Location"] = loc_key.capitalize()
        
        for weather_key in ["sunny", "rainy", "cloudy", "snowy", "foggy", "clear"]:
            if weather_key in parts:
                result["Environment"]["Weather"] = weather_key.capitalize()
        

        for pos_key in ["topside", "underwater", "aerial", "ground"]:
            if pos_key in parts:
                result["Environment"]["Position"] = pos_key.capitalize()
        
  
        for climate_key in ["tropical", "temperate", "arctic", "desert", "mediterranean"]:
            if climate_key in parts:
                result["Environment"]["Climate"] = climate_key.capitalize()
    
 
    try:
        shot = result["Shot"]
        subject = "".join([
            result["Subject"]["Type"],
            result["Subject"]["Classification"],
            result["Subject"]["Species"],
            result["Subject"]["Count"],
            result["Subject"]["Identification"],
            result["Subject"]["Color"]
        ])
        action = result["Action"]
        environment = "".join([
            result["Environment"]["Time"],
            result["Environment"]["Location"],
            result["Environment"]["Weather"],
            result["Environment"]["Position"],
            result["Environment"]["Climate"]
        ])
        
        result["condensed_format"] = {
            "Shot": shot,
            "Subject": subject,
            "Action": action,
            "Environment": environment
        }
    except:

        pass
    
    return result