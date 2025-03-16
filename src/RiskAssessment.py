
import gradio as gr
from gradio import themes
import os
from dotenv import find_dotenv, load_dotenv
import requests
import base64
from pathlib import Path

# Load environment variables from .env file
load_dotenv(find_dotenv())

def generate_summary_from_api(pdf_path):
    """Generate summary from PDF file using the API"""
    try:
        base_url = "http://localhost:8000"

        # Read the PDF file and encode it as base64
        with open(pdf_path, 'rb') as file:
            pdf_content = base64.b64encode(file.read()).decode('utf-8')

        # Prepare the request
        endpoint = f"{base_url}/summary/generate"
        headers = {
            'Content-Type': 'application/json'
        }
        payload = {
            "content": pdf_content,
            "project_name": Path(pdf_path).stem
        }

        # Make the API call
        print(f"Sending request to {endpoint}...")
        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()

        # Get the summary from response
        result = response.json()
        return result.get("project_summary", "No summary generated")

    except requests.exceptions.RequestException as e:
        print(f"API Error: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Response text: {e.response.text}")
        return f"API Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

def process_documents(uploaded_file):
    """Process the uploaded document and generate summary"""
    if not uploaded_file:
        return "Please upload a requirements document first."
    
    return generate_summary_from_api(uploaded_file.name)

def save_response_to_file(response, filename):
    """Save the response to a file"""
    with open(filename, 'w') as file:
        file.write(response + '\n')

def save_edited_summary(edited_summary):
    """Save the edited summary and return confirmation"""
    save_response_to_file(edited_summary, './modified_summary_report.txt')
    return "Edited summary saved successfully!"

# Custom JavaScript for theme handling
js_func = """
function refresh() {
    const url = new URL(window.location);
    if (url.searchParams.get('__theme') !== 'dark') {
        url.searchParams.set('__theme', 'dark');
        window.location.href = url.href;
    }
}
"""

# Gradio UI
with gr.Blocks(js=js_func) as demo:
    gr.Markdown(
        """
        ## Security Risk Assessment Using Multi-Agent RAG
        Upload your requirements specification document and the system will analyze potential security risks,
        vulnerabilities, and provide recommendations for security improvements.
        """
    )
    
    # Upload section
    with gr.Column():
        uploaded_file = gr.File(
            file_count="single", 
            file_types=[".pdf"], 
            label="Upload Requirements Specification Document",
            scale=4
        )
        
        status_message = gr.Textbox(
            interactive=False,
            visible=False,
            show_label=False,
            elem_classes="success-message"
        )
    
    # Action buttons
    with gr.Row():
        process_doc_btn = gr.Button("Process Document", variant="primary", size="sm")
        save_summary_btn = gr.Button("Save Summary", variant="secondary", size="sm")

    # Summary output
    summary_output = gr.Textbox(
        label="Generated Summary",
        lines=10,
        interactive=True
    )

    # Event handlers
    process_doc_btn.click(
        process_documents,
        inputs=[uploaded_file],
        outputs=[summary_output]
    )

    save_summary_btn.click(
        save_edited_summary,
        inputs=[summary_output],
        outputs=[status_message]
    )

if __name__ == "__main__":
    demo.launch()
