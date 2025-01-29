from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
import os
from langchain.embeddings import OpenAIEmbeddings
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
)
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI

from langchain.docstore.document import Document
from langchain.vectorstores import FAISS


from dotenv import load_dotenv
load_dotenv('src/.env')


OPENAI_API_KEY= os.getenv("OPENAI_API_KEY")
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

class Interpretation(BaseModel):
    para_id : str = Field(description="Id of the para")
    if_interpretation: bool = Field(description="If the text contains a legal interpretation")
    interpretation_phrases: list = Field(description="List of interpretation phrases")
    reason: str = Field(description="Brief explanation of why or why not given paragraph contains any legal interpretation")

def getLegalClassifierChain(examples):
  
  model = "gpt-4o-mini"
  llm = ChatOpenAI(model= model,temperature=0)
  system_prompt = """You are a legal language model designed to analyze UK case law for paragraphs that contain legal interpretations. Your task is to identify text that interprets or explains legislative terms and concepts.

  1. Accurately identify and analyze any legal interpretations within given texts, focusing on how courts, tribunals, or authoritative bodies explain or clarify the meaning or scope of UK legislation.
  2. Distinguish between mere citations/references and actual legal interpretations. Text that simply cites a statute (e.g., “pursuant to s.100(2)(b)”) without any explanatory reasoning or discussion of its meaning does not qualify as interpretation.
  3. Focus on:
    - UK legislation (i.e., Acts of Parliament or other UK statutory instruments)
    - Judicial interpretation and statutory interpretation principles (e.g., purposive approach, mischief rule)
  4. Do not consider text as legal interpretation when it:
    - Merely mentions the law or quotes statutory wording without explaining it
    - Refers to non-UK conventions, treaties, or rulings
    - Discusses jurisdictional or procedural issues without interpreting legislative language
    - Recites the law verbatim (e.g., “Art. 8 provides…”) without additional interpretive commentary."""

  system_prompt2 = """You are a legal language model designed to analyze UK case law for paragraphs that contain legal interpretations. Your task is to identify text that interprets or explains legislative terms and concepts.

  1. Accurately identify and analyze legal interpretations within given texts
  2. Distinguish between mere citations/references and actual legal interpretations
  3. Focus specifically on how courts, tribunals, and authoritative bodies have interpreted legal concepts
  4. Pay special attention to:
    - UK legislation 
    - Judicial interpretation
    - Statutory interpretation principles
    - Development of legal concepts through case law

  Don't consider text as legal interpretation:
  - when law is mentioned as a reference
  - Any convention or ruling other than UK legislation
  - discussion of the jurisdictional issues
  - When law is stated as it is e.g. Art 8 provides..
  """
    # Create the example prompt template
  example_prompt = ChatPromptTemplate.from_messages([
      ("human", "para_id: {para_id} \npara_content: {para_content}"),
      ("ai", "para_id: {para_id}\nContains Interpretation: {if_interpretation}\nInterpreted Phrases: {interpreted_phrases}\nReason:")
  ])

  # Create the few-shot template
  few_shot_prompt = FewShotChatMessagePromptTemplate(
      examples=examples,  # Your examples list should contain dicts with all required keys
      example_prompt=example_prompt
  )

  # Create the final prompt template
  final_prompt = ChatPromptTemplate.from_messages([
      ("system", system_prompt),
      few_shot_prompt,
      ("human", "Content:\n para_id: {para_id}\npara_content: {para_content}\n{format_instructions}")
  ])
  parser = JsonOutputParser(pydantic_object=Interpretation)

  # Create the chain
  chain = final_prompt | llm | parser
  return parser,chain


def getPhraseExtractionChain():
  system_prompt = """You are a specialized legal analyst with expertise in matching legal interpretations between case law and legislation. Follow this systematic process:

  1. ANALYSIS PHASE:
    - Identify specific (not overly general) legal concepts or phrases in the case law.
    - Find the corresponding, equally specific portion in the legislation. This should be a somewhat longer, context-providing phrase.
    - From that longer legislative phrase, also extract the *key noun phrase(s)* or *core concept(s)*—the minimal expression that captures the critical legal idea.

  2. MATCHING CRITERIA:
    - Direct textual overlap or near-verbatim references (no paraphrasing).
    - Semantic equivalence in the same legal context (avoid purely generic wording).
    - Clear interpretative relationship (case law explains or applies the legislation).
    - Substantive connection (not merely tangential mentions).

  3. VALIDATION RULES:
    - **Only** extract text that actually appears in each source (verbatim).
    - For `"legislation_term"`, use the longer snippet that captures context.
    - For `"key_phrases/concepts"`, extract the essential, shorter noun phrase(s) from within that legislation snippet.
    - Ensure the match has legal interpretive or explanatory value (avoid trivial or broad phrases).

  4. OUTPUT STRUCTURE:
    Return a **JSON array** of objects. Each object must contain:
    - `"case_law_term"`: exact phrase from the case law (no rewording).
    - `"legislation_term"`: a longer, context-inclusive phrase from the legislation.
    - `"key_phrases/concepts"`: the shorter core phrase(s)—verbatim—taken from within `"legislation_term"` that most directly capture the legal concept (often a noun phrase).
    - `"reasoning"`: brief explanation of how the case law term interprets/applies the legislation.
    - `"confidence"`: "High", "Medium", or "Low" based on how closely they match in legal meaning.

  Example Output:
  [
    {{
      "case_law_term": "reasonable safety standards required documented weekly inspections",
      "legislation_term": "reasonable safety standards",
      "key_phrases":["reasoable safety standards"],
      "reasoning": "Case law directly interprets and defines the legislative phrase",
      "confidence": "High"
    }}
  ]

  Example Input:
  Legislation : "If a parent does not provide proper care and guardianship for a child, the local authority may intervene to ensure the child's welfare is safeguarded. A person is eligible for legal aid if they cannot afford legal representation and the matter pertains to family law or children's welfare."
  Case Law: "The parent failed to ensure the child received proper care, necessitating intervention by the local authority. Legal aid is required in this case due to the individual's inability to afford representation in a family law matter."

  Example Output:
  [
    {{
      "case_law_term": "parent failed to ensure the child received proper care",
      "legislation_term": "parent does not provide proper care and guardianship for a child",
      "key_phrases":["proper care and guardianship for a child"],
      "reasoning": "Direct interpretation of parental care obligation",
      "confidence": "High"
    }},
    {{
      "case_law_term": "individual's inability to afford representation in a family law matter",
      "legislation_term": "person is eligible for legal aid if they cannot afford legal representation and the matter pertains to family law",
      "key_phrases":["legal representation"],
      "reasoning": "Case applies legislative criteria for legal aid eligibility",
      "confidence": "High"
    }}
  ]

  Rules:
  - Extract only exact phrases from source texts
  - No rephrasing or inference
  - Include only paired matches with clear legal interpretation
  - Return raw JSON without formatting or explanation
  - ALWAYS RETURN SOME RESULT !!!

  """

  human_prompt = """Process these legal texts following the above methodology:

  Legislation:
  {legislation_text}

  Case Law:
  {case_text}

  There should be nothing produced from your own side -- Just extract from the given sections of caselaw and legislation.
  Don't return back the input. 
  Return only the JSON array with matches.
  Include reasoning and confidence scores.
  ALWAYS RETURN SOME RESULT !!!
  """

  prompt_template3 = ChatPromptTemplate.from_messages([
      SystemMessagePromptTemplate.from_template(system_prompt),
      HumanMessagePromptTemplate.from_template(human_prompt)
  ])
  # Initialize the language model
  model = "gpt-4o"
  llm = ChatOpenAI(model=model, temperature=0)
  llm_chain_extraction = LLMChain(llm=llm, prompt=prompt_template3)
  return llm_chain_extraction
    
def getEmbeddings():
    print(OPENAI_API_KEY)
    embeddings = OpenAIEmbeddings()
    return embeddings

def getInterPretations(legislation_text,case_text,llm_chain_extraction):
    input_data = {
        "legislation_text": legislation_text,
        "case_text": case_text
    }
    
    # Run the LLM chain
    result = llm_chain_extraction.invoke(input_data)
    try:
        return result['text']
    except:
        return result

def BuildVectorDB(directory,legislation_list):
    #directory = data/legislation
    def load_legislative_sections(directory, legislation_number):
        sections = []
        for filename in os.listdir(directory):
            if filename.endswith(".txt"):
                try:
                    section_number = filename.split('-')[1].split('.')[0]  # Extract section number
                    with open(os.path.join(directory, filename), 'r') as file:
                        text = file.read().strip()  # Read the content of the file
                        sections.append({
                            "id": f"{legislation_number}_section_{section_number}",
                            "text": text,
                            "legislation_id": legislation_number
                        })
                except:
                    pass
        return sections

    docs = []
    for legislation_number in legislation_list:
        try:
            #print(legislation_number)
            legislative_sections = load_legislative_sections(
                f"{directory}/{legislation_number}", legislation_number
            )
            doc = [
                Document(page_content=sec["text"], 
                         metadata={
                             "id": sec["id"],
                             "legislation_id": sec["legislation_id"]  # Add legislation_id to metadata
                         }) 
                for sec in legislative_sections
            ]
            docs.extend(doc)
        except Exception as e:
            print(f"Error processing legislation {legislation_number}: {str(e)}")

    try:
        embeddings = getEmbeddings()
        vectorstore = FAISS.from_documents(docs, embeddings)
    except Exception as e:
        print(f"Error creating vector store: {str(e)}")
        raise
    
    return vectorstore
if __name__ == "__main__":
    print("OpenAi Handler")

