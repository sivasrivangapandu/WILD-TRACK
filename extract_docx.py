import zipfile
import xml.etree.ElementTree as ET
import sys

def extract_text_from_docx(docx_path):
    try:
        with zipfile.ZipFile(docx_path, 'r') as docx:
            xml_content = docx.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            
            # Namespace for Word XML
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            paragraphs = tree.findall('.//w:p', ns)
            text_lines = []
            
            for p in paragraphs:
                runs = p.findall('.//w:r', ns)
                paragraph_text = ""
                for r in runs:
                    t = r.find('.//w:t', ns)
                    if t is not None:
                        paragraph_text += t.text
                if paragraph_text:
                    text_lines.append(paragraph_text)
            
            return "\n".join(text_lines)
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_docx.py <path_to_docx>")
    else:
        # Use utf-8 for printing to avoid encoding errors in some environments
        sys.stdout.reconfigure(encoding='utf-8')
        print(extract_text_from_docx(sys.argv[1]))
