import requests
import xml.etree.ElementTree as ET
import os
import util

#from keypharse import KeyPharse
class LegislationParser:
    """
    A parser for UK legislation that can extract terms and sections from legislation.gov.uk XML data.
    """

    def get_legislation_title(self):
        """
        Fetches the title of the legislation from the given XML URL.
        
        :param url: URL of the XML document.
        :return: The title of the legislation or an error message.
        """
        namespace = {
            'dc': 'http://purl.org/dc/elements/1.1/'  # Namespace for Dublin Core elements
        }
        
        try:
            # Fetch the XML data
            response = requests.get(self.url)
            if response.status_code == 200:
                # Parse the XML content
                root = ET.fromstring(response.content)
                # Find the dc:title element
                title_element = root.find('.//dc:title', namespace)
                if title_element is not None:
                    return title_element.text.strip()
                else:
                    return "Title not found in the XML document"
            else:
                return f"Error fetching data: {response.status_code}"
        except ET.ParseError:
            return "Error parsing the XML document"
        except Exception as e:
            return f"An unexpected error occurred: {e}"
    def get_act_name(self):
        """
        Fetches the act name from the legislation URL.
        """
        response = requests.get(self.url)
        if response.status_code == 200:
            # Parse the XML response
            root = self.tree#ET.fromstring(response.content)


            # Extract the act name from the appropriate XML element
            act_name_element = root.find('.//akn:title', self.namespace)

            if act_name_element is not None:
                return act_name_element.text
            else:
                return "Act name not found"
        else:
            return f"Error fetching data: {response.status_code}"
    def __init__(self, url,is_section):
        
        element_id,base_url = self.getTheSectionIdAndBaseUrl(url)
        #print(base_url)
        self.url =  base_url + "/data.akn"
        if "https:" in self.url:
            pass
        else:
            self.url = self.url.replace("http","https")

        '''
        if is_section == True:
               
            self.element_id = element_id
            print(self.url)
            print(self.element_id)
        else: 
            self.url = url
    '''
        self.namespace = {'akn': 'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}
        self.tree = self._load_legislation()
        # Debug: Print root and immediate children
        '''
        root = self.tree.getroot()


        print("Root tag:", root.tag)
        print("\nDirect children:")
        for child in root:
            print(f"- {child.tag}: {child.attrib}")
        print("\nSearching for all elements with eId attribute:")
        for elem in root.findall(".//*[@eId]", self.namespace):
            print(f"- {elem.tag}: eId={elem.get('eId')}")
            '''
        self.debug = False  # Toggle for debugging output
        #print(self.url)

    def get_terms(self):
        root = self.tree.getroot()
        
        # Find all references in the XML
        references = root.find('.//akn:references', self.namespace)
        if references is None:
            return []
            
        # Find all TLCTerm elements under references
        terms = []
        term_elements = references.findall('.//akn:TLCTerm', self.namespace)
        
        for term in term_elements:
            # Extract term attributes
            term_id = term.get('eId', '')
            term_href = term.get('href', '')
            term_text = term.get('showAs', '')
            
            terms.append({
                'id': term_id,
                'href': term_href, 
                'term': term_text
            })
                
        return terms
    def _load_legislation(self):
        """Fetches and parses the XML from the given URL."""
        response = requests.get(self.url)
        if response.status_code == 200:
            return ET.ElementTree(ET.fromstring(response.content))
        else:
            print(f"Failed to load legislation from URL: {self.url}")
            raise Exception(f"Failed to load legislation data: {response.status_code}")

    def get_element_by_id(self, element_id):
        """Fetches the text of a section or subsection by its eId."""
        root = self.tree.getroot()
        element = root.find(f".//*[@eId='{element_id}']", self.namespace)
        if element is None:
            return None
        return self._extract_text(element)
    def getPharses(self,text, tag):
        if tag == 'num' or len(text) < 2:
            return []  # Return as list even if no valid text
        if tag == 'term':
            return [text]
        try:
            phrases = util.extract_key_phrases(text)
            return phrases
        except Exception as e:
            print(f"Exception {e} in extracting pharses for text {text}")
            return []
    
    def _extract_text_with_features(self, element):
        """
        Extracts all text content from an XML element and its children,
        preserving the structure and order of the content, while maintaining KeyPharse objects.
        """
        def process_node(node, depth=0):
            """
            Recursively processes a node and all its content.
            Returns a list of KeyPharse objects in order of appearance.
            """
            node_phrases = []
            indent = "  " * depth if self.debug else ""
        
            # Debug output for tag information
            if self.debug:
                tag_name = node.tag.split('}')[-1] if '}' in node.tag else node.tag
                print(f"{indent}Processing tag: {tag_name}")
                if node.attrib:
                    print(f"{indent}Attributes: {node.attrib}")

            # Process node's immediate text
            if node.text and node.text.strip():
                text = node.text.strip()
                phrase = {}
                phrase['text'] = text
                tag_name = node.tag.split('}')[-1] if '}' in node.tag else node.tag
                phrase['tag'] = tag_name
                #phrase['pharses'] = util.extract_phrases(text,tag_name)
                phrase['new_pharses'] = self.getPharses(text,tag_name)

                if self.debug:
                    print(f"{indent}Direct text: {phrase['text']}")
                    print(f"{indent}tag: {phrase['tag']}")

                node_phrases.append(phrase)
        
            # Process all child nodes
            for child in node:
                # Recursively process child node
                child_phrases = process_node(child, depth + 1)
                node_phrases.extend(child_phrases)

                # Process tail text of the child
                if child.tail and child.tail.strip():
                    tail_text = child.tail.strip()
                    tail_phrase = {}
                    #tail_phrase.add_feature("tail_text")

                    

                    tail_phrase['text'] = tail_text
                    tail_phrase['tag'] = 'tail'
                    #tail_phrase['pharses'] = util.extract_phrases(tail_text,'tail')
                    tail_phrase['new_pharses'] = self.getPharses(tail_text,'tail')

                    node_phrases.append(tail_phrase)
                    if self.debug:
                        print(f"{indent}Tail Text: {tail_phrase['text']}")
                        print(f"{indent}tag: {tail_phrase['tag']}")

            return node_phrases

        # Process the entire element tree
        all_phrases = process_node(element)

        # Iterate over the results for debugging or further processing
        for phrase in all_phrases:
            if self.debug:
                print(f"Final Phrase: {phrase['text']}")
                print(f"Final Features: {phrase['tag']}")
    
        return all_phrases


    def _extract_text(self, element):
        """
        Extracts all text content from an XML element and its children,
        preserving the structure and order of the content.
        """
        texts = []

        def process_node(node, depth=0):
            """
            Recursively processes a node and all its content.
            Returns a list of text pieces in order of appearance.
            """
            node_texts = []
            indent = "  " * depth if self.debug else ""
            
            # Debug output for tag information
            if self.debug:
                tag_name = node.tag.split('}')[-1] if '}' in node.tag else node.tag
                print(f"{indent}Processing tag: {tag_name}")
                if node.attrib:
                    print(f"{indent}Attributes: {node.attrib}")

            # Process node's immediate text
            if node.text and node.text.strip():
                text = node.text.strip()
                if self.debug:
                    print(f"{indent}Direct text: {text}")
                node_texts.append(text)
                node_texts.append("\n")
                

            # Process all child nodes
            for child in node:
                # Recursively process child node
                child_texts = process_node(child, depth + 1)
                node_texts.extend(child_texts)
                node_texts.extend("\n")

                # Process tail text of the child
                if child.tail and child.tail.strip():
                    tail_text = child.tail.strip()
                    if self.debug:
                        print(f"{indent}Tail text after {child.tag.split('}')[-1]}: {tail_text}")
                    node_texts.append(tail_text)
                    node_texts.append("\n")

            return node_texts

        # Process the entire element tree
        all_texts = process_node(element)
        
        # Join text pieces with appropriate spacing
        text = '\n'.join(all_texts)
        
        # Clean up extra whitespace while preserving single spaces
        cleaned_text = ' '.join(text.split())
        
        return cleaned_text
    def save_all_sections_to_files(self, output_dir="legislation_sections"):
        """
        Saves all sections in the legislation to individual text files.

        Args:
            output_dir (str): Directory where section text files will be saved.
        """
        os.makedirs(output_dir, exist_ok=True)  # Create output directory if it doesn't exist
        root = self.tree.getroot()
        print(root.findall(".//akn:section", self.namespace))

        for section in root.findall(".//akn:section", self.namespace):
            
            section_id = section.attrib.get("eId", "unknown")
            section_text = self._extract_text(section)
            

            # Define the file path for each section
            file_path = os.path.join(output_dir, f"{section_id}.txt")
            
            # Save section text to the file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(section_text)
            print(f"Section {section_id} saved to {file_path}")

    def save_element_to_txt(self, element_id, output_file):
        """Saves the content of the given element to a text file."""
        element_text = self.get_element_by_id(element_id)
        if element_text:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(element_text)
            print(f"Element {element_id} saved to {output_file}")
        else:
            print(f"Element {element_id} not found in the legislation.")

    def set_debug(self, debug_mode):
        """Enables or disables debug output."""
        self.debug = debug_mode
    def getTheSectionIdAndBaseUrl(self,url):
        """
        Parse legislation URLs to extract section IDs and base URLs.
        Handles various formats and builds proper base URLs and element IDs.
        
        Args:
            url (str): Full legislation URL
            
        Returns:
            tuple: (element_id, base_url)
            
        Example:
            Input: "https://www.legislation.gov.uk/id/ukpga/Eliz2/8-9/65"
            Output: ("", "https://www.legislation.gov.uk/ukpga/Eliz2/8-9/65")

            Input: "http://www.legislation.gov.uk/id/ukpga/2004/7/section/2/1"
            Output: ("section-2-1", "http://www.legislation.gov.uk/ukpga/2004/7")
        """
        # Split URL into parts
        url_parts = url.split('/')
        
        # Remove '/id' if present
        if 'id' in url_parts:
            url_parts.remove('id')
            
        # Try to find 'section' to handle section URLs
        section_idx = -1
        for i, part in enumerate(url_parts):
            if part.lower() == 'section':
                section_idx = i
                break
                
        if section_idx == -1:
            # No 'section' found, return base URL without 'id'
            base_url = '/'.join(url_parts)
            return "", base_url  # Return empty string for element_id
        
        # Build section ID from parts after 'section'
        section_parts = url_parts[section_idx:]
        section_id = '-'.join(section_parts).lower()
        
        # Build base URL from parts before 'section'
        base_url = '/'.join(url_parts[:section_idx])
        
        return section_id, base_url
    '''
    def getTheSectionIdAndBaseUrl(self,url):
        """
        Parse legislation URLs to extract section IDs and base URLs.
        Handles various formats and builds proper base URLs and element IDs.
        
        Args:
            url (str): Full legislation URL
            
        Returns:
            tuple: (element_id, base_url)
            
        Example:
            Input: "http://www.legislation.gov.uk/id/ukpga/2004/7/section/2/1"
            Output: ("section-2-1", "http://www.legislation.gov.uk/id/ukpga/2004/7")
        """
        legislation_url = 'http://www.legislation.gov.uk'
        url_parts = url.split('/')
        url_parts_reverse = url_parts[::-1]
        
        # Process section parts
        section_part = []
        section = None
        processed_index = 0
        
        # Find and process section numbers
        for i, part in enumerate(url_parts_reverse):
            if part.isdigit():
                section_part.append(part)
            elif part.lower() == 'section': 
                section = part.lower()
                section_part = section_part[::-1]
                for section_part_num in section_part:
                    section = section + "-" + str(section_part_num)
                processed_index = i + 1  # Mark where we stopped processing
                break
        # If we've checked all parts but section wasn't found, reset processed_index
        if section is None:
            processed_index = 0
        # Remove processed parts from url_parts_reverse
        url_parts_reverse = url_parts_reverse[processed_index:]
        
        # Process law parts
        law_part = []
        law = None
        #print(url_parts_reverse)
        # Find and process law numbers
        for i, part in enumerate(url_parts_reverse):

            if part.isdigit():
                law_part.append(part)
            else:
                #if part.lower() in ['ukpga', 'uksi', 'nisi', 'asp']:  # Common legislation types
                law = part.lower()
                law_part = law_part[::-1]
                # Build the law path (e.g., ukpga/2004/7)
                for law_part_num in law_part:
                    law = law + "/" + str(law_part_num)
                    #print(law)
                break
        
        # Construct final URLs
        if law is not None:
            base_url = f"{legislation_url}/{law}"
        else:
            raise ValueError("Could not find valid legislation type in URL")
            
        if not section:
            pass
            #print("Could not find valid section in URL")
            
        return section, base_url
    '''
    def get_element_txt(self):
        element_text = self.get_element_by_id(self.element_id)
        return element_text

        

      
# Example usage:
if __name__ == "__main__":
    #url = "http://www.legislation.gov.uk/id/ukpga/1989/41/section/7"
    url = "https://www.legislation.gov.uk/ukpga/2018/16"
    parser = LegislationParser(url,False)
    # Create directory if it doesn't exist
    
    #parser.save_all_sections_to_files("data/legislation/2018/16")
    print(parser.get_legislation_title())

    '''
    parser = LegislationParser(url)
    
    # Enable debug mode if you want to see the processing details
    # parser.set_debug(True)
    
    element_id = "section-6"  # Example ID
    output_file = "data/section-6_text.txt"
    
    #parser.save_element_to_txt(element_id, output_file)
    parser.save_all_sections_to_files('output/legislation/1989/41')
    '''