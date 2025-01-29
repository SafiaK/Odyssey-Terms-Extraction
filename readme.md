# Potential Terms Extraction System from UK Case Law

This repository contains a system for extracting potential terms from acts referred to in case law. Currently, the code only works on acts that have the reference `https://legislation.gov.uk/id/ukpga`. 

## Instructions

1. Place the XML case law files into the `data/sample` folder or any other preferred location.
2. Or Update the folder path in `main.py` accordingly.

## Pipeline Overview

The pipeline processes the case law by leveraging LegalDocML and OpenAI large language models. It extracts potential terms interpreted in the case laws from the referred acts.



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


   ### Files

   ```bash
   data/
   ├── sample/
   │   ├── files/                        # Put case law XML files here for processing
   │   ├── output/ # Processed output files
            ├── rows_with_phrases.csv #The interpreted paragraphs with the extraction module result
            ├── rows_without_keyphrases.csv #The interpreted paragraphs with the extraction module failed 
            ├── ExpldodedPhrases.csv #The interpreted phrases in one column instead of list
                       
   │   │   ├── xml_to_csv/               # CSVs generated from XMLs (created by pipeline)
   │   │       ├── csv_with_legislation/     # CSVs with legislation and raw results of the extraction module (created by pipeline)
   │   │       
   │   ├── legislation/                  # Downloaded legislative sections (created by pipeline)
   ├── cleaned_case_legislation_map.pkl  # Pickled data with cleaned references (created by pipeline)
   ```







