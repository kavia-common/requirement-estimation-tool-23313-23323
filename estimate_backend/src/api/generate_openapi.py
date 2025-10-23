import json
import os

from src.api.main import app

def main() -> None:
    """
    Generate the OpenAPI spec from the FastAPI app and write it to interfaces/openapi.json.
    This script can be run with:
        python -m src.api.generate_openapi
    or:
        python requirement-estimation-tool-23313-23323/estimate_backend/src/api/generate_openapi.py
    """
    schema = app.openapi()
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "interfaces")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "openapi.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print(f"OpenAPI schema written to {output_path}")


if __name__ == "__main__":
    main()
