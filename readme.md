# Information Extraction System

This repository contains a system for extracting structured information from text using various NLP techniques and language models.


## Setup

1. Clone the repository
2. Create a conda environment:
   ```bash
   conda create -n term_extractor
   conda activate term_extractor
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. make a .env file in src folder and put OPENAI_API_KEY = "your_api_key" 

### Source Code (`src/`)

#### Main Components

1. `main.py`
   - Main entry point for the information extraction pipeline
   - Orchestrates the overall extraction process
   - Handles input processing and output generation

2. `JudgementHandler.py`
   - Processes and analyzes legal judgment documents
   - Extracts key information like case details
   - Implements specialized parsing for judgment-specific structures
   - Handles citation extraction and cross-referencing
  

3. `LegislationHandler`
   - Handles processing and extraction from legislation documents
   - Implements specialized parsing for legal text structures
   - Extracts key sections, clauses, and amendments


### Supporting Files

data/
├── sample/
│   ├── files -- put caselaw xmls files here for processing              # Input XML files
│   ├── output/              # Processed output files
│   │   ├── xml_to_csv/      # CSVs generated from XMLs (created by pipeline)
│   │   ├── legislation/     # Downloaded legislative sections (created by pipeline)
├── cleaned_case_legislation_map.pkl   # Pickled data with cleaned references (created by pipeline)




## Note

The experimental code in the `exp/` directory is not intended for production use and may contain work-in-progress or deprecated code.





