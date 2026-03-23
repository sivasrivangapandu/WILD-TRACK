"""
WildTrackAI — Species Routes
==============================
GET  /species          - List all species
GET  /species/{name}   - Species details
POST /species-search   - Gemini-powered species search
GET  /api/animal-info  - API Ninjas wildlife knowledge
"""

import json
import re

import requests
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import ANIMAL_INFO, NINJA_API_KEY
from database import get_db
from models import Prediction
from services.prediction_service import class_names
from services.gemini_provider import is_gemini_available, generate_gemini_text

router = APIRouter()

# In-memory search cache
_species_search_cache = {}


class SpeciesSearchRequest(BaseModel):
    query: str


@router.get("/species")
async def list_species(db: Session = Depends(get_db)):
    """List all supported species with info."""
    species_list = []
    try:
        counts = dict(
            db.query(Prediction.species, func.count(Prediction.id))
            .group_by(Prediction.species).all()
        )
    except Exception:
        counts = {}

    for name in class_names:
        info = ANIMAL_INFO.get(name, {})
        species_list.append({
            "name": name,
            "scientific_name": info.get("scientific_name", "Unknown"),
            "conservation_status": info.get("conservation_status", "Unknown"),
            "prediction_count": counts.get(name, 0),
            "info": info,
        })

    return {"species": species_list, "total": len(species_list)}


@router.get("/species/{name}")
async def get_species(name: str):
    """Get detailed info about a specific species."""
    if name not in ANIMAL_INFO:
        raise HTTPException(status_code=404, detail=f"Species '{name}' not found")
    return {"name": name, "info": ANIMAL_INFO[name]}


@router.post("/species-search")
async def species_search(req: SpeciesSearchRequest):
    """AI-powered wildlife footprint search engine."""
    query = req.query.strip().lower()

    if not query or len(query) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")

    if query in _species_search_cache:
        cached = _species_search_cache[query]
        cached["cached"] = True
        return cached

    for name, info in ANIMAL_INFO.items():
        if query in name.lower() or name.lower() in query:
            result = {
                "found": True,
                "source": "local_database",
                "trained_species": name in class_names,
                "species": {
                    "common_name": name.title(),
                    "scientific_name": info.get("scientific_name", "Unknown"),
                    "conservation_status": info.get("conservation_status", "Unknown"),
                    "weight": info.get("weight", "Unknown"),
                    "footprint_size": info.get("footprint_size", "Unknown"),
                    "habitat": info.get("habitat", "Unknown"),
                    "description": info.get("description", ""),
                    "distribution": info.get("distribution", "Unknown"),
                    "fun_facts": [],
                    "tracking_tips": "",
                    "confusion_species": [],
                },
                "cached": False,
            }
            _species_search_cache[query] = result
            return result

    if not is_gemini_available():
        raise HTTPException(status_code=503, detail="Gemini AI not available. Set GEMINI_API_KEY.")

    prompt = f"""You are a wildlife tracking expert and zoologist.
A user searched for: "{req.query}"

Provide detailed information about this animal's footprints and tracks.
Respond ONLY with valid JSON (no markdown, no code blocks, no extra text).
Use this exact structure:

{{
  "common_name": "Animal Name",
  "scientific_name": "Genus species",
  "conservation_status": "e.g., Endangered, Vulnerable, Least Concern",
  "weight": "typical range in kg",
  "footprint_size": "length in cm",
  "habitat": "primary habitats",
  "description": "Detailed description of the animal's footprints/tracks. 2-3 sentences.",
  "distribution": "geographic range",
  "fun_facts": ["fact 1 about their tracks", "fact 2", "fact 3"],
  "tracking_tips": "Practical advice for identifying this animal's tracks. 2-3 sentences.",
  "confusion_species": ["species 1 whose tracks look similar", "species 2"]
}}

If the query is not a real animal, respond with:
{{"common_name": null, "error": "Could not identify species"}}
"""

    try:
        raw_text = generate_gemini_text(
            prompt=prompt,
            temperature=0.3,
            max_output_tokens=1000,
        )
        if not raw_text:
            raise HTTPException(status_code=502, detail="AI returned empty response. Try again.")
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

        species_data = json.loads(raw_text)

        if species_data.get("common_name") is None:
            return {
                "found": False, "source": "gemini_ai",
                "error": species_data.get("error", "Species not recognized"),
                "query": req.query, "cached": False,
            }

        result = {
            "found": True, "source": "gemini_ai",
            "trained_species": False, "species": species_data, "cached": False,
        }
        _species_search_cache[query] = result
        return result

    except json.JSONDecodeError as e:
        print(f"Gemini JSON parse error: {e}")
        raise HTTPException(status_code=502, detail="AI returned invalid response. Try again.")
    except Exception as e:
        print(f"Gemini species search error: {e}")
        raise HTTPException(status_code=502, detail=f"AI search failed: {str(e)}")


@router.get("/api/animal-info")
async def get_animal_info(name: str = Query(..., min_length=1)):
    """WildTrackAI Knowledge Engine — structured wildlife intelligence."""
    if not NINJA_API_KEY:
        raise HTTPException(status_code=503, detail="Wildlife database not available")

    if not name or len(name.strip()) < 1:
        raise HTTPException(status_code=400, detail="Animal name required")

    try:
        response = requests.get(
            "https://api.api-ninjas.com/v1/animals",
            params={"name": name.strip()},
            headers={"X-Api-Key": NINJA_API_KEY},
            timeout=5
        )

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code,
                              detail=f"Unable to retrieve wildlife data: {response.status_code}")

        data = response.json()

        if not data:
            return {"found": False, "message": f"No species information found for '{name}'"}

        animal = data[0]

        name_common = animal.get("name", "").title()
        taxonomy = animal.get("taxonomy", {})
        characteristics = animal.get("characteristics", {})
        locations = animal.get("locations", [])

        sci_name = f"{taxonomy.get('genus', '')} {taxonomy.get('species', '')}".strip() or "Unknown"
        habitat = characteristics.get("habitat", "various ecosystems")
        diet = characteristics.get("diet", "unknown diet")
        weight = characteristics.get("weight", "variable")
        height = characteristics.get("height", "not documented")
        lifespan = characteristics.get("lifespan", "not documented")
        skin_type = characteristics.get("skin_type", "")
        raw_color = characteristics.get("color", "variable")
        color = re.sub(r'(?<=[a-z])(?=[A-Z])', ', ', raw_color) if raw_color else "variable"
        animal_type = characteristics.get("type", "")
        location_str = ", ".join(locations) if locations else "multiple regions"
        family = taxonomy.get("family", "")

        overview = (
            f"{name_common} ({sci_name}) is a {animal_type.lower() or 'vertebrate'} species "
            f"belonging to the family {family or 'unknown'}. "
            f"Found across {location_str}, this species inhabits {habitat}."
        )

        physical_traits = (
            f"{name_common} is characterized by {color.lower() if color != 'variable' else 'species-typical'} coloration. "
            f"Adults typically weigh {weight} and reach heights of {height}."
        )

        field_identification = (
            f"When tracking {name_common} in the field, focus on {habitat.lower()} environments. "
            f"Track surveys are most productive during dawn and dusk when activity peaks."
        )

        distribution_summary = (
            f"{name_common} ranges across {location_str}. "
            f"Within this range, the species selectively occupies {habitat.lower()}."
        )

        return {
            "found": True,
            "species": {
                "name": name_common,
                "scientific_name": sci_name,
                "overview": overview,
                "physical_traits": physical_traits,
                "field_identification": field_identification,
                "distribution_summary": distribution_summary,
                "info_panel": {
                    "habitat": habitat, "region": location_str, "weight": weight,
                    "height": height, "diet": diet, "lifespan": lifespan,
                    "type": animal_type, "color": color, "skin_type": skin_type,
                },
                "classification": {
                    "kingdom": taxonomy.get("kingdom", ""),
                    "phylum": taxonomy.get("phylum", ""),
                    "class": taxonomy.get("class", ""),
                    "order": taxonomy.get("order", ""),
                    "family": family,
                    "genus": taxonomy.get("genus", ""),
                },
            }
        }

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Request timeout")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Connection error: {str(e)}")
    except Exception as e:
        print(f"Wildlife info error: {e}")
        raise HTTPException(status_code=500, detail=f"Data retrieval failed: {str(e)}")
