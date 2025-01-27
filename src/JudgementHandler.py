import xml.etree.ElementTree as ET
import html


from lxml import etree
import os
import pandas as pd


from xml.etree import ElementTree

class JudgmentParser:
    def __init__(self, xml_file):
        tree = ET.parse(xml_file)
        self.root = tree.getroot()
        self.namespace = {
            'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0',
            'uk': 'https://caselaw.nationalarchives.gov.uk/akn'
        }
    def has_legislation_reference(self):
        """Checks if there is any legislation reference in the judgment."""
        body = self.root.find('akn:judgment/akn:judgmentBody/akn:decision', self.namespace)
        if body is not None:
            for ref in body.findall('.//akn:ref', self.namespace):
                # Check if it's a legislation reference
                if ref.attrib.get('{https://caselaw.nationalarchives.gov.uk/akn}type') == 'legislation':
                    return True
        return False
    def extract_text_with_internal_tags(self, element):
        # Extract all text including nested tags, preserving the order
        return ''.join(element.itertext()).strip()
    def extract_legislation_refs(self,element):
            """Helper function to extract legislation references from an XML element"""
            legislation_refs = []
            refs = element.findall('.//akn:ref', self.namespace)
            for ref in refs:
                if ref.attrib.get('{https://caselaw.nationalarchives.gov.uk/akn}type') == 'legislation':
                    ref_text = self.extract_text_with_internal_tags(ref)
                    href = ref.get('href', '')
                    
                    # Extract legislation ID and section from href
                    legislation_id = None
                    section_num = None
                    if href:
                        parts = href.split('/')
                        bas_uri = href.split('/section')[0]
                        if 'section' in href:
                            try:
                                
                                # Get the full section path after 'section/'
                                print("================================")
                                print(href)
                                print("================================")
                                section_parts = href.split('section/')[1].split('/')
                                section_path = '/'.join(section_parts)
                                section_num = section_path  # Keep full section path like "1/3"
                                
                                # Get year/number from parts before section
                                section_idx = parts.index('section')
                                legislation_id  = '/'.join(bas_uri.split('/ukpga/')[-1].split('/'))
                                #number = parts[section_idx-1]
                                #legislation_id = f"{year}/{number}"
                            except:
                                section_num = None
                        elif len(parts) >= 2:
                            # No section - use last parts for year/number
                            year = parts[-2]
                            number = parts[-1]
                            legislation_id = '/'.join(bas_uri.split('/ukpga/')[-1].split('/'))
                    
                    legislation_refs.append({
                        'text': ref_text,
                        'href': href,
                        'legislation_section': (legislation_id, section_num) if legislation_id else None
                    })
            return legislation_refs
    def get_judgment_body_paragraphs_subpara_text(self):
        

        paragraphs = []
        para_id_counter = {}
        paras = self.get_judgment_body_paragraphs_xml()
        for para in paras:
            para_id = para.get('eId')
            
            # Process subparagraphs within the paragraph
            subparagraphs = para.findall('.//akn:subparagraph', self.namespace)

            if subparagraphs:
                # Has subparagraphs - only process those
                if para_id not in para_id_counter:
                    para_id_counter[para_id] = 1
                
                for sub in subparagraphs:
                    sub_text = self.extract_text_with_internal_tags(sub)
                    sub_id = f"{para_id}_{para_id_counter[para_id]}"
                    para_id_counter[para_id] += 1

                    if sub_text:
                        refs = self.extract_legislation_refs(sub)
                        legislation_sections = [ref['legislation_section'] for ref in refs if ref['legislation_section']]
                        paragraphs.append({
                            'id': sub_id,
                            'text': sub_text,
                            'references': refs,
                            'legislation_sections': legislation_sections
                        })
            else:
                # No subparagraphs - process the paragraph text directly
                para_text = self.extract_text_with_internal_tags(para)
                if para_text:
                    refs = self.extract_legislation_refs(para)
                    legislation_sections = [ref['legislation_section'] for ref in refs if ref['legislation_section']]
                    paragraphs.append({
                        'id': para_id,
                        'text': para_text,
                        'references': refs,
                        'legislation_sections': legislation_sections
                    })

        return paragraphs
    def check_legislation_reference(self,paragraph):
        """
        Check if the paragraph contains a reference to legislation.
        """
        refs = paragraph.findall('.//akn:ref', self.namespace)  # Look for akn:ref tags
    
        for ref in refs:
            # Check if the 'uk:type' attribute is 'legislation'
            if ref.attrib.get('{https://caselaw.nationalarchives.gov.uk/akn}type') == 'legislation':
                return True
        return False
    def get_caselaw_meta(self):
        """Returns the case metadata such as URI and ID."""
        meta = {}
        identification = self.root.find('akn:judgment/akn:meta/akn:identification', self.namespace)
        
        if identification is not None:
            work = identification.find('akn:FRBRExpression', self.namespace)
            if work is not None:
                meta['uri'] = work.find('akn:FRBRuri', self.namespace).attrib['value']
                meta['date'] = work.find('akn:FRBRdate', self.namespace).attrib['date']
        
        return meta

    def get_judgment_body_paragraphs_xml(self):
        """Returns all paragraphs of the judgment body as XML elements."""
        paragraphs = []
        body = self.root.find('akn:judgment/akn:judgmentBody/akn:decision', self.namespace)
        if body is not None:
            paragraphs = body.findall('akn:paragraph', self.namespace)
        return paragraphs
    
    def get_judgment_body_paragraphs_text(self):
        """Returns all paragraphs of the judgment body as plain text, including references."""
        result = []
        case_meta = self.get_caselaw_meta()
        case_uri = case_meta.get('uri', '')
        
        body = self.root.find('akn:judgment/akn:judgmentBody/akn:decision', self.namespace)
        
        if body is not None:
            # First check if body is not None and has paragraphs
            paragraphs = body.findall('akn:paragraph', self.namespace)
            print("Found paragraphs:", len(paragraphs) if paragraphs else 0)
            if len(paragraphs) == 0:
                # Try finding paragraphs within levels if none found directly
                paragraphs = body.findall('.//akn:paragraph', self.namespace)
                if len(paragraphs) == 0:
                    # As a last resort, try finding paragraphs within levels
                    levels = body.findall('akn:level', self.namespace)
                    for level in levels:
                        level_paragraphs = level.findall('akn:paragraph', self.namespace)
                        paragraphs.extend(level_paragraphs)


            for para in paragraphs:
               global para_counter
               if not hasattr(self, 'para_counter'):
                   self.para_counter = 1
               
               para_id = para.attrib.get('eId', '')

               if not para_id:
                   para_id = f'para_{self.para_counter}'
                   self.para_counter += 1
               print(para_id)
               text = self.get_paragraph_text(para)
               refs = self.extract_legislation_refs(para)
               result.append((case_uri, para_id, text, refs))
               
                   
                #text_content = para.find('akn:content', self.namespace).text
        return result
    
    def get_paragraph_text(self,paragraph):
        """
        Extracts the text from the paragraph, including references, and handles special characters.
        """
        text_pieces = []
    
        # Iterate over elements and extract text
        for elem in paragraph.iter():
            if elem.tag.endswith('ref') or elem.tag.endswith('a'):  # Handle references
                text_pieces.append(self.extract_text_with_internal_tags(elem))
                '''
                if 'uk:canonical' in elem.attrib:
                    text_pieces.append(f"({elem.attrib['uk:canonical']})")  # Add canonical reference
                elif 'href' in elem.attrib:
                    text_pieces.append(f" {elem.attrib['href']} ")  # Add href if no canonical reference
                '''
            else:
                if elem.text:
                    text_pieces.append(elem.text)

            if elem.tail:
                #print(elem.tail)
                text_pieces.append(elem.tail)

        # Join all text pieces
        paragraph_text = ' '.join(text_pieces)

        # Decode HTML entities like &#8217;, &#8220;, etc.
        paragraph_text = html.unescape(paragraph_text)

        return paragraph_text

    def get_references(self):
        """Returns a list of references used in the judgment body paragraphs."""
        references = []
        body = self.root.find('akn:judgment/akn:judgmentBody/akn:decision', self.namespace)
        if body is not None:
            for para in body.findall('akn:paragraph', self.namespace):
                for ref in para.findall('.//akn:ref', self.namespace):
                    references.append(ref.attrib['href'])
        return references
    def get_legislation_references(self):
        """Returns a list of all legislation references in the judgment."""
        legislation_refs = []
        body = self.root.find('akn:judgment/akn:judgmentBody/akn:decision', self.namespace)
        if body is not None:
            for ref in body.findall('.//akn:ref', self.namespace):
                # Check if it's a legislation reference
                if ref.attrib.get('{https://caselaw.nationalarchives.gov.uk/akn}type') == 'legislation':
                    href = ref.attrib.get('href')
                    if href:
                        legislation_refs.append(href)
        return list(set(legislation_refs))  # Remove duplicates
    
    def get_paragraph_by_eId(self, eId):
        """Returns the paragraph text corresponding to the given eId."""
        body = self.root.find('akn:judgment/akn:judgmentBody/akn:decision', self.namespace)
        if body is not None:
            paragraph = body.find(f".//akn:paragraph[@eId='{eId}']", self.namespace)
            if paragraph is not None:
                return paragraph.find('akn:content', self.namespace).text
        return None
    
    def get_all_paragraphs_with_legislation_ref(self):
        """
        Returns a list of tuples containing (caseUri, paragraphId, text, references)
        for each paragraph in the judgment body.
        """
        result = []
        case_meta = self.get_caselaw_meta()
        case_uri = case_meta.get('uri', '')
        
        body = self.root.find('akn:judgment/akn:judgmentBody/akn:decision', self.namespace)
        if body is not None:
            for para in body.findall('akn:paragraph', self.namespace):
                if self.check_legislation_reference(para):
                    # Get paragraph ID
                    para_id = para.attrib.get('eId', '')
                    content = self.get_paragraph_text(para)
                    refs = self.extract_legislation_refs(para) #[ref.attrib['href'] for ref in paragraph.findall('.//akn:ref', self.namespace)]
                
                    result_text = self.get_paragraph_with_references_by_eId(para_id)
                    text = content
                    refs = refs
                

                    # Create tuple and append to result
                    result.append((case_uri, para_id, text, refs))
        
        return result

    def get_references_by_paragraph_eId(self, eId):
        """Returns the paragraph text along with any references by the given eId."""
        body = self.root.find('akn:judgment/akn:judgmentBody/akn:decision', self.namespace)
        if body is not None:
            paragraph = body.find(f".//akn:paragraph[@eId='{eId}']", self.namespace)
            if paragraph is not None:
                refs = [ref.attrib['href'] for ref in paragraph.findall('.//akn:ref', self.namespace)]
                return refs
        return []
    
    def get_paragraph_with_references_by_eId(self, eId):
        """Returns the paragraph text along with any references by the given eId."""
        body = self.root.find('akn:judgment/akn:judgmentBody/akn:decision', self.namespace)
        if body is not None:
            paragraph = body.find(f".//akn:paragraph[@eId='{eId}']", self.namespace)
            #print("paragraph",eId)
            if paragraph is not None:
                content = self.get_paragraph_text(paragraph)
                refs = self.extract_legislation_refs(paragraph) #[ref.attrib['href'] for ref in paragraph.findall('.//akn:ref', self.namespace)]
                return {
                    'content': content,
                    'references': refs
                }
        return None

if __name__ == '__main__':
    import sys
    import json
    
    
        
    xml_file = "/Users/apple/Documents/Personal/Swansea/Odyssey/ewhc_fam/caselaw_ewhc_fam_2003/ewhc_fam_2003_2746.xml"
    handler = JudgmentParser(xml_file)
    
    # Get all paragraphs with legislation references
    results = handler.get_judgment_body_paragraphs_text()
    
    # Print results in JSON format
    output = []
    for case_uri, para_id, text, refs in results:
        output.append({
            'caseUri': case_uri,
            'paragraphId': para_id, 
            'text': text,
            'references': refs
        })
    
    print(json.dumps(output, indent=2))